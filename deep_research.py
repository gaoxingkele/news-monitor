"""Deep research via Perplexity Sonar: enrich confirmed articles + recover dead-link topics.

Usage:
    python deep_research.py output/reports/20260311_135822_uy_filtered.md
"""
from __future__ import annotations

import asyncio
import io
import json
import os
import re
import sys
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import httpx
from news_monitor.proxy import get_proxies_for_url, build_httpx_client

# ── Config ───────────────────────────────────────────────────────────────────

API_KEY = os.environ.get("PERPLEXITY_API_KEY", "")
API_URL = "https://api.perplexity.ai/chat/completions"
MODEL = "sonar"   # sonar has web search built in
OVERSEAS_PROXY = os.environ.get("LLM_PROXY", os.environ.get("OVERSEAS_PROXY", ""))
DELAY = 1.5  # seconds between calls to avoid rate limits


# ── Perplexity caller ────────────────────────────────────────────────────────

async def ask_perplexity(query: str, system: str = "", temperature: float = 0.1) -> dict:
    """Call Perplexity Sonar and return {content, citations}."""
    # Perplexity is always overseas — force proxy
    proxy = OVERSEAS_PROXY or get_proxies_for_url(API_URL, OVERSEAS_PROXY)

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": query})

    body = {
        "model": MODEL,
        "messages": messages,
        "temperature": temperature,
        "return_citations": True,
        "search_recency_filter": "week",   # only past week results
    }

    try:
        async with build_httpx_client(proxy_url=proxy or "", timeout=60.0) as client:
            resp = await client.post(
                API_URL, json=body,
                headers={
                    "Authorization": f"Bearer {API_KEY}",
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        citations = data.get("citations", [])
        return {"content": content, "citations": citations}

    except Exception as exc:
        return {"content": f"ERROR: {exc}", "citations": []}


# ── Part 1: Deep-dive confirmed articles ─────────────────────────────────────

ENRICH_SYSTEM = """\
你是中国对外关系新闻分析师。用户给你一条关于乌拉圭的新闻事件摘要。

请搜索过去一周（2026年3月2日-3月11日）与该事件相关的最新进展，返回：
1. **事件最新动态**：有无后续发展、官方声明、新协议等
2. **关键细节补充**：具体金额、参与方、时间线
3. **对中国/台湾利益的影响分析**：一句话点评

用中文回答，简洁精炼，200字以内。如果搜索不到最近一周的相关内容，请明确说明"未找到过去一周相关更新"。"""


async def enrich_confirmed(articles: list[dict]) -> list[dict]:
    """Deep-dive each confirmed article via Perplexity."""
    results = []
    for i, art in enumerate(articles):
        title = art["title"]
        body = art.get("body", "")
        query = f"事件：{title}\n摘要：{body[:300]}\n\n请搜索过去一周（2026年3月2日至3月11日）与此事件相关的最新消息。"

        print(f"  [{i+1}/{len(articles)}] 搜索: {title[:50]}...")
        result = await ask_perplexity(query, system=ENRICH_SYSTEM)
        results.append({
            "title": title,
            "category": art.get("category", ""),
            "event_label": art.get("event_label", ""),
            "original_body": body,
            "original_url": art.get("url", ""),
            "original_source": art.get("source", ""),
            "perplexity_content": result["content"],
            "perplexity_citations": result["citations"],
        })
        await asyncio.sleep(DELAY)

    return results


# ── Part 2: Recover dead-link topics ─────────────────────────────────────────

# Group dead-link articles into search themes to avoid redundant queries
DEAD_LINK_THEMES = [
    {
        "theme": "乌拉圭与中国经贸投资（含自贸协定、一带一路、基建）",
        "query": "Uruguay China trade investment FTA Belt Road infrastructure 2026 March （乌拉圭 中国 贸易 投资 自贸协定 一带一路 基础设施 2026年3月）",
    },
    {
        "theme": "乌拉圭与美国安全军事合作",
        "query": "Uruguay United States military cooperation defense security agreement 2026 March （乌拉圭 美国 军事 防务 合作 安全 2026年3月）",
    },
    {
        "theme": "中美贸易战对乌拉圭/拉美的影响",
        "query": "US China trade war tariff impact Uruguay Latin America 2026 March （中美 贸易战 关税 乌拉圭 拉美 影响 2026年3月）",
    },
    {
        "theme": "台湾在拉美的外交活动（乌拉圭及周边国家）",
        "query": "Taiwan Latin America diplomacy Uruguay ICDF scholarship cooperation 2026 March （台湾 拉丁美洲 外交 乌拉圭 合作 奖学金 ICDF 2026年3月）",
    },
    {
        "theme": "中国在乌拉圭港口/基建项目（含华为、CCCC等）",
        "query": "China Uruguay port Montevideo Huawei CCCC infrastructure project 2026 March （中国 乌拉圭 港口 蒙得维的亚 华为 中交建 基础设施 2026年3月）",
    },
    {
        "theme": "乌拉圭地缘政治立场（在中美之间的选择）",
        "query": "Uruguay geopolitics China United States foreign policy alignment 2026 March （乌拉圭 地缘政治 中国 美国 外交政策 立场 2026年3月）",
    },
    {
        "theme": "对华舆情（排华情绪、中资冲突、华人安全）",
        "query": "Uruguay China sentiment anti-Chinese protest conflict community safety 2026 March （乌拉圭 中国 舆情 排华 冲突 华人 安全 社区 2026年3月）",
    },
    {
        "theme": "乌拉圭与中国气候/能源合作",
        "query": "Uruguay China climate energy green hydrogen renewable cooperation 2026 March （乌拉圭 中国 气候 能源 绿色氢能 可再生 合作 2026年3月）",
    },
]

RECOVER_SYSTEM = """\
你是中国对外关系新闻分析师。用户给你一个新闻主题方向。

请搜索过去一周（2026年3月2日-3月11日）与该主题相关的、涉及乌拉圭的真实新闻报道。

要求：
- 只列出过去一周内确实发生的事件
- 只列出与台湾相关、或影响中国利益的新闻
- 每条新闻包含：事件标题、关键内容（50字内）、信息来源
- 如果搜索不到符合条件的新闻，请回复"未找到符合条件的近期新闻"

用中文回答，按重要性排序。"""


async def recover_dead_links() -> list[dict]:
    """Search for recent news on dead-link themes."""
    results = []
    for i, theme in enumerate(DEAD_LINK_THEMES):
        print(f"  [{i+1}/{len(DEAD_LINK_THEMES)}] 主题: {theme['theme'][:40]}...")
        result = await ask_perplexity(
            f"主题方向：{theme['theme']}\n\n搜索关键词：{theme['query']}",
            system=RECOVER_SYSTEM,
        )
        results.append({
            "theme": theme["theme"],
            "perplexity_content": result["content"],
            "perplexity_citations": result["citations"],
        })
        await asyncio.sleep(DELAY)

    return results


# ── Parse filtered report ────────────────────────────────────────────────────

def parse_filtered_report(md_path: str) -> list[dict]:
    """Extract kept articles from the filtered report."""
    with open(md_path, "r", encoding="utf-8") as f:
        text = f.read()

    articles = []
    # Find article blocks (### N. Title)
    blocks = re.split(r"(?=^### \d+\.)", text, flags=re.MULTILINE)

    for block in blocks:
        m_title = re.search(r"^### \d+\.\s*(.+)$", block, re.MULTILINE)
        if not m_title:
            continue

        title = m_title.group(1).strip()
        # Event label
        m_label = re.search(r"\*\*事件标签：\*\*\s*(.+)", block)
        event_label = m_label.group(1).strip() if m_label else ""
        # URL
        m_url = re.search(r">\s*\*\*链接：\*\*\s*(https?://\S+)", block)
        url = m_url.group(1).strip() if m_url else ""
        # Source
        m_src = re.search(r">\s*\*\*来源：\*\*\s*(.+)", block)
        source = m_src.group(1).strip() if m_src else ""
        # Body
        body_match = re.search(r"\*\*事件标签：\*\*.+?\n\n(.+?)\n\n>", block, re.DOTALL)
        if not body_match:
            body_match = re.search(r"^### .+?\n\n(.+?)\n\n>", block, re.DOTALL)
        body = body_match.group(1).strip() if body_match else ""

        # Category from preceding ## section
        category = ""

        articles.append({
            "title": title,
            "event_label": event_label,
            "url": url,
            "source": source,
            "body": body,
            "category": category,
        })

    # Assign categories
    sections = re.split(r"^## ■\s*(.+?)$", text, flags=re.MULTILINE)
    cat_map: dict[str, str] = {}
    for i in range(1, len(sections), 2):
        cat = sections[i].strip()
        content = sections[i + 1] if i + 1 < len(sections) else ""
        for m in re.finditer(r"^### \d+\.\s*(.+)$", content, re.MULTILINE):
            cat_map[m.group(1).strip()] = cat

    for art in articles:
        art["category"] = cat_map.get(art["title"], "未分类")

    return articles


# ── Generate final report ────────────────────────────────────────────────────

def generate_deep_report(
    enriched: list[dict],
    recovered: list[dict],
    output_path: str,
):
    lines: list[str] = []
    lines.append("# 乌拉圭动态监测 · 深度研究报告\n")
    lines.append(f"**生成时间：** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**数据来源：** Perplexity Sonar (web search, 过去一周)")
    lines.append(f"**时间范围：** 2026-03-02 → 2026-03-11\n")
    lines.append("---\n")

    # ── Part 1: Enriched confirmed articles ──
    lines.append("## 第一部分：已确认事件深度挖掘\n")

    # Group by category
    by_cat: dict[str, list[dict]] = {}
    for art in enriched:
        cat = art.get("category", "未分类")
        by_cat.setdefault(cat, []).append(art)

    for cat, arts in by_cat.items():
        lines.append(f"### ▸ {cat}\n")
        for idx, art in enumerate(arts, 1):
            lines.append(f"#### {idx}. {art['title']}\n")
            if art.get("event_label"):
                lines.append(f"**事件标签：** {art['event_label']}\n")
            lines.append(f"**原始摘要：** {art['original_body'][:200]}…\n")
            lines.append(f"**Perplexity 深度补充：**\n")
            lines.append(f"{art['perplexity_content']}\n")
            if art["perplexity_citations"]:
                lines.append("**参考来源：**")
                for c in art["perplexity_citations"][:5]:
                    lines.append(f"- {c}")
            lines.append(f"\n> 原始链接: {art.get('original_url', '')}")
            lines.append(f"> 原始来源: {art.get('original_source', '')}")
            lines.append("\n---\n")

    # ── Part 2: Recovered topics ──
    lines.append("## 第二部分：失效链接主题补救搜索\n")
    lines.append("以下为原报告中链接失效的主题方向，通过 Perplexity 重新搜索过去一周相关新闻：\n")

    has_findings = False
    for item in recovered:
        content = item["perplexity_content"]
        if "未找到" in content and len(content) < 100:
            continue  # Skip empty results

        has_findings = True
        lines.append(f"### ▸ {item['theme']}\n")
        lines.append(f"{content}\n")
        if item["perplexity_citations"]:
            lines.append("**参考来源：**")
            for c in item["perplexity_citations"][:5]:
                lines.append(f"- {c}")
        lines.append("\n---\n")

    if not has_findings:
        lines.append("所有主题方向均未搜索到过去一周内符合条件的新闻。\n")

    report_text = "\n".join(lines)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report_text)

    return output_path


# ── Main ─────────────────────────────────────────────────────────────────────

async def main(filtered_md: str):
    if not API_KEY:
        print("ERROR: PERPLEXITY_API_KEY not set")
        sys.exit(1)

    print(f"Reading filtered report: {filtered_md}")
    confirmed = parse_filtered_report(filtered_md)
    print(f"Found {len(confirmed)} confirmed articles\n")

    # Part 1: Enrich confirmed articles
    print("=" * 60)
    print("Part 1: Deep-diving confirmed articles via Perplexity...")
    print("=" * 60)
    enriched = await enrich_confirmed(confirmed)

    print()

    # Part 2: Recover dead-link topics
    print("=" * 60)
    print("Part 2: Searching dead-link themes for recent news...")
    print("=" * 60)
    recovered = await recover_dead_links()

    print()

    # Generate report
    base = os.path.splitext(filtered_md)[0]
    output_path = base.replace("_filtered", "") + "_deep_research.md"
    print("Generating deep research report...")
    generate_deep_report(enriched, recovered, output_path)
    print(f"\nDone! Report: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))
