"""Topic merger: cluster similar articles into topics using LLM reasoning.

Fallback chain: Grok → Doubao → DeepSeek → Qwen

Usage:
    python merge_topics.py output/reports/20260314_072337_pa.json
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Fix Windows UTF-8 output
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from news_monitor.proxy import build_httpx_client, get_proxies_for_url

_RED = "\033[91m"
_GREEN = "\033[92m"
_YELLOW = "\033[93m"
_RESET = "\033[0m"

# ── LLM provider chain ──────────────────────────────────────────────────────
_PROVIDERS = [
    {
        "name": "grok",
        "url": "https://api.x.ai/v1/chat/completions",
        "api_key_env": "GROK_API_KEY",
        "model": "grok-3-mini",
        "overseas": True,
    },
    {
        "name": "doubao",
        "url": "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
        "api_key_env": "DOUBAO_API_KEY",
        "model_env": "DOUBAO_MODEL",
        "model": "doubao-1.5-pro-256k",
        "overseas": False,
    },
    {
        "name": "deepseek",
        "url": "https://api.deepseek.com/v1/chat/completions",
        "api_key_env": "DEEPSEEK_API_KEY",
        "model": "deepseek-chat",
        "overseas": False,
    },
    {
        "name": "qwen",
        "url": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        "api_key_env": "QWEN_API_KEY",
        "model": "qwen-long",
        "overseas": False,
    },
]

# Category display names and order
_CAT_ORDER = ["us", "taiwan", "china", "sentiment"]
_CAT_NAMES = {
    "us": "美国相关",
    "taiwan": "台湾相关",
    "china": "中国相关",
    "sentiment": "对华舆情",
}

_CLUSTER_PROMPT = """\
你是一个新闻分析师。下面是关于{country_zh}的{cat_name}新闻列表（JSON数组）。

你的任务：
1. 将报道同一事件/主题的文章归为一组（topic）
2. 每个topic给出：
   - topic_title: 主题标题（15-30字，概括核心事件）
   - summary: 整合摘要（综合该主题下所有文章的信息，提炼精华，200-300字）
   - article_ids: 包含的文章ID列表
   - importance: 重要性评分 1-5（5最重要）
3. 只有1篇文章的也要单独成topic
4. 按importance降序排列

返回JSON数组，格式：
[
  {{
    "topic_title": "...",
    "summary": "...",
    "article_ids": [0, 3, 5],
    "importance": 5
  }}
]

仅返回JSON数组，不要markdown包裹或其他文字。

文章列表：
{articles_json}
"""


async def _call_llm(prompt: str, overseas_proxy: str) -> list[dict] | None:
    """Try providers in order; return parsed JSON list or None."""
    for prov in _PROVIDERS:
        api_key = os.environ.get(prov["api_key_env"], "")
        if not api_key:
            continue

        model = prov["model"]
        if prov.get("model_env"):
            model = os.environ.get(prov["model_env"], "") or model

        url = prov.get("url_env") and os.environ.get(prov["url_env"]) or prov["url"]
        body = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0,
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        proxy = ""
        if prov.get("overseas"):
            proxy = get_proxies_for_url(url, overseas_proxy) or ""

        try:
            async with build_httpx_client(proxy_url=proxy, timeout=180.0) as client:
                resp = await client.post(url, json=body, headers=headers)
                if resp.status_code != 200:
                    print(f"{_RED}  [{prov['name']}] HTTP {resp.status_code}: {resp.text[:200]}{_RESET}")
                    continue
                data = resp.json()

            content = data["choices"][0]["message"]["content"].strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

            results = json.loads(content)
            if isinstance(results, list):
                print(f"  [{prov['name']}] OK", end="")
                return results
            print(f"{_RED}  [{prov['name']}] non-list response{_RESET}")

        except json.JSONDecodeError as exc:
            print(f"{_RED}  [{prov['name']}] JSON parse error: {exc}{_RESET}")
        except Exception as exc:
            print(f"{_RED}  [{prov['name']}] {type(exc).__name__}: {exc}{_RESET}")

    return None


async def merge_topics(json_path: str) -> str:
    """Load articles, cluster by topic, generate merged report."""
    json_path = os.path.abspath(json_path)
    with open(json_path, "r", encoding="utf-8") as f:
        articles = json.load(f)

    print(f"Loaded {len(articles)} articles from {json_path}")

    overseas_proxy = os.environ.get("OVERSEAS_PROXY", "")

    # Detect country
    country_code = ""
    for a in articles:
        if a.get("country"):
            country_code = a["country"]
            break

    _COUNTRY_NAMES = {
        "pa": ("巴拿马", "Panama"), "mx": ("墨西哥", "Mexico"),
        "co": ("哥伦比亚", "Colombia"), "do": ("多米尼加", "Dominican Republic"),
        "uy": ("乌拉圭", "Uruguay"), "py": ("巴拉圭", "Paraguay"),
        "ar": ("阿根廷", "Argentina"), "br": ("巴西", "Brazil"),
        "cl": ("智利", "Chile"), "pe": ("秘鲁", "Peru"),
        "ve": ("委内瑞拉", "Venezuela"), "ec": ("厄瓜多尔", "Ecuador"),
        "bo": ("玻利维亚", "Bolivia"), "gt": ("危地马拉", "Guatemala"),
        "hn": ("洪都拉斯", "Honduras"), "sv": ("萨尔瓦多", "El Salvador"),
        "ni": ("尼加拉瓜", "Nicaragua"), "cr": ("哥斯达黎加", "Costa Rica"),
        "bz": ("伯利兹", "Belize"), "ht": ("海地", "Haiti"),
    }
    country_zh, country_en = _COUNTRY_NAMES.get(country_code, ("未知", "Unknown"))

    # Group articles by category
    cat_groups: dict[str, list[dict]] = {}
    for i, art in enumerate(articles):
        art["_idx"] = i
        cat = art.get("category", "other")
        cat_groups.setdefault(cat, []).append(art)

    all_topics: dict[str, list[dict]] = {}

    # Process all categories
    ordered_cats = [c for c in _CAT_ORDER if c in cat_groups]
    ordered_cats += [c for c in cat_groups if c not in _CAT_ORDER]

    for cat in ordered_cats:
        group = cat_groups[cat]
        cat_name = _CAT_NAMES.get(cat, f"{country_zh}国别")
        print(f"\n{_GREEN}[{cat_name}] {len(group)} articles → clustering...{_RESET}")

        compact = [
            {
                "id": i,
                "title": art.get("title_zh") or art.get("title", ""),
                "summary": art.get("summary_zh") or art.get("description", ""),
            }
            for i, art in enumerate(group)
        ]

        prompt = _CLUSTER_PROMPT.format(
            country_zh=country_zh,
            cat_name=cat_name,
            articles_json=json.dumps(compact, ensure_ascii=False, indent=1),
        )

        t0 = time.monotonic()
        topics = await _call_llm(prompt, overseas_proxy)
        elapsed = time.monotonic() - t0

        if topics is None:
            print(f"{_YELLOW}  All providers failed, keeping individual articles{_RESET}")
            topics = [
                {
                    "topic_title": (art.get("title_zh") or art.get("title", ""))[:30],
                    "summary": art.get("summary_zh") or art.get("description", ""),
                    "article_ids": [i],
                    "importance": 3,
                }
                for i, art in enumerate(group)
            ]

        topics.sort(key=lambda t: -t.get("importance", 0))
        all_topics[cat] = topics

        n_topics = len(topics)
        n_merged = sum(1 for t in topics if len(t.get("article_ids", [])) > 1)
        print(f", {n_topics} topics ({n_merged} merged) [{elapsed:.1f}s]")

    # Generate report
    report_lines = _build_report(articles, cat_groups, all_topics, country_zh)

    base = json_path.rsplit(".", 1)[0]
    out_md = f"{base}_topics.md"
    with open(out_md, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
    print(f"\n{_GREEN}Report saved: {out_md}{_RESET}")

    # PDF via pandoc
    out_pdf = f"{base}_topics.pdf"
    if _md_to_pdf(out_md, out_pdf):
        print(f"{_GREEN}PDF saved: {out_pdf}{_RESET}")
        return out_pdf

    print(f"{_YELLOW}PDF generation failed, returning MD{_RESET}")
    return out_md


def _md_to_pdf(md_path: str, pdf_path: str) -> bool:
    """Convert MD to PDF via fpdf2 with CJK support."""
    try:
        from fpdf import FPDF
    except ImportError:
        print(f"{_YELLOW}fpdf2 not installed{_RESET}")
        return False

    # Find CJK font
    font_path = ""
    for candidate in [
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simsun.ttc",
    ]:
        if os.path.exists(candidate):
            font_path = candidate
            break
    if not font_path:
        print(f"{_YELLOW}No CJK font found{_RESET}")
        return False

    md_content = Path(md_path).read_text(encoding="utf-8")

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_font("CJK", "", font_path, uni=True)
    pdf.add_page()

    for line in md_content.split("\n"):
        stripped = line.strip()
        if not stripped:
            pdf.ln(3)
            continue

        if stripped.startswith("# "):
            pdf.set_font("CJK", size=16)
            pdf.multi_cell(0, 9, stripped[2:], align="C", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(4)
        elif stripped.startswith("## "):
            pdf.ln(4)
            pdf.set_font("CJK", size=13)
            pdf.multi_cell(0, 7, stripped[3:], new_x="LMARGIN", new_y="NEXT")
            # Draw underline
            pdf.set_draw_color(136, 136, 136)
            pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
            pdf.ln(3)
        elif stripped.startswith("### "):
            pdf.ln(3)
            pdf.set_font("CJK", size=11)
            pdf.set_text_color(51, 51, 51)
            pdf.multi_cell(0, 6, stripped[4:], new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(0, 0, 0)
            pdf.ln(2)
        elif stripped.startswith("|"):
            # Table row
            pdf.set_font("CJK", size=9)
            cells = [c.strip() for c in stripped.split("|")[1:-1]]
            if cells and all(c.replace("-", "").replace(":", "") == "" for c in cells):
                continue  # skip separator row
            w = (pdf.w - pdf.l_margin - pdf.r_margin) / max(len(cells), 1)
            for cell in cells:
                pdf.cell(w, 6, cell, border=1, align="C")
            pdf.ln()
        elif stripped.startswith("> "):
            pdf.set_font("CJK", size=9)
            pdf.set_text_color(80, 80, 80)
            text = stripped[2:].replace("**", "")
            pdf.multi_cell(0, 5, "  " + text, new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(0, 0, 0)
        elif stripped == "---":
            pdf.ln(2)
            pdf.set_draw_color(200, 200, 200)
            pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
            pdf.ln(2)
        else:
            pdf.set_font("CJK", size=10)
            # Strip markdown bold markers for PDF
            text = stripped.replace("**", "")
            pdf.multi_cell(0, 6, text, new_x="LMARGIN", new_y="NEXT")

    pdf.output(pdf_path)
    return True


def _build_report(
    articles: list[dict],
    cat_groups: dict[str, list[dict]],
    all_topics: dict[str, list[dict]],
    country_zh: str,
) -> list[str]:
    """Build markdown report from clustered topics."""
    lines: list[str] = []
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines.append(f"# {country_zh}动态监测报告（主题合并版）")
    lines.append("")
    lines.append(f"**生成时间：** {now}")
    lines.append("")

    total_articles = len(articles)
    total_topics = sum(len(ts) for ts in all_topics.values())
    lines.append("## 总体统计")
    lines.append("")
    lines.append("| 指标 | 数量 |")
    lines.append("|:---|---:|")
    lines.append(f"| 原始文章数 | {total_articles} |")
    lines.append(f"| 合并后主题数 | {total_topics} |")
    lines.append(f"| 压缩比 | {total_articles / max(total_topics, 1):.1f}:1 |")
    lines.append("")

    lines.append("| 类别 | 文章数 | 主题数 |")
    lines.append("|:---|---:|---:|")

    ordered_cats = [c for c in _CAT_ORDER if c in all_topics]
    ordered_cats += [c for c in all_topics if c not in _CAT_ORDER]

    for cat in ordered_cats:
        cat_name = _CAT_NAMES.get(cat, f"{country_zh}国别")
        n_arts = len(cat_groups.get(cat, []))
        n_topics = len(all_topics[cat])
        lines.append(f"| {cat_name} | {n_arts} | {n_topics} |")
    lines.append("")
    lines.append("---")
    lines.append("")

    global_topic_num = 0
    for cat in ordered_cats:
        cat_name = _CAT_NAMES.get(cat, f"{country_zh}国别")
        topics = all_topics[cat]
        group = cat_groups.get(cat, [])
        n_arts = len(group)

        lines.append(f"## ■ {cat_name}（{len(topics)} 个主题，源自 {n_arts} 篇文章）")
        lines.append("")

        for topic in topics:
            global_topic_num += 1
            title = topic.get("topic_title", "未命名主题")
            summary = topic.get("summary", "")
            importance = topic.get("importance", 3)
            art_ids = topic.get("article_ids", [])

            stars = "★" * importance + "☆" * (5 - importance)
            n_sources = len(art_ids)

            lines.append(f"### {global_topic_num}. {title}")
            lines.append("")
            lines.append(f"**重要性：** {stars}　**相关报道：** {n_sources} 篇")
            lines.append("")
            lines.append(summary)
            lines.append("")

            # List articles under this topic
            if art_ids:
                lines.append(f"**相关报道列表：**")
                lines.append("")
                for aid in art_ids:
                    if aid < len(group):
                        art = group[aid]
                        art_title = art.get("title_zh") or art.get("title", "")
                        url = art.get("source_url", "")
                        source = art.get("source_name", "")
                        date = art.get("event_date", "") or "N/A"
                        found_by = ", ".join(art.get("found_by", []))
                        lines.append(f"> **{art_title}**")
                        lines.append(f"> 来源：{source} `[{found_by}]` | 日期：{date}")
                        lines.append(f"> {url}")
                        lines.append("")
            lines.append("---")
            lines.append("")

    return lines


async def main():
    if len(sys.argv) < 2:
        print("Usage: python merge_topics.py <json_path>")
        print("Example: python merge_topics.py output/reports/20260314_072337_pa.json")
        sys.exit(1)

    json_path = sys.argv[1]
    if not os.path.exists(json_path):
        print(f"{_RED}File not found: {json_path}{_RESET}")
        sys.exit(1)

    result_path = await merge_topics(json_path)

    # Open result
    if sys.platform == "win32":
        os.startfile(result_path)


if __name__ == "__main__":
    asyncio.run(main())
