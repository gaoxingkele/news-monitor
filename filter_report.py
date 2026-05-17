"""Post-filter: validate links, check dates, merge duplicates via LLM.

Usage:
    python filter_report.py output/reports/20260311_135822_uy.md
"""
from __future__ import annotations

import asyncio
import io
import json
import os
import re
import sys
from datetime import date, datetime, timedelta

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

# Target date range: past week from today
TODAY = date(2026, 3, 11)
WEEK_START = TODAY - timedelta(days=9)   # Mar 2
WEEK_END   = TODAY                        # Mar 11 (inclusive)

PROVIDERS = {
    "deepseek": {
        "base_url": os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
        "api_key_env": "DEEPSEEK_API_KEY",
        "model": "deepseek-chat",
        "overseas": False,
    },
    "kimi": {
        "base_url": os.environ.get("KIMI_BASE_URL", "https://api.moonshot.cn/v1"),
        "api_key_env": "KIMI_API_KEY",
        "model": "moonshot-v1-auto",
        "overseas": False,
    },
    "grok": {
        "base_url": os.environ.get("GROK_BASE_URL", "https://api.x.ai/v1"),
        "api_key_env": "GROK_API_KEY",
        "model": "grok-3-mini-fast",
        "overseas": True,
    },
}

OVERSEAS_PROXY = os.environ.get("OVERSEAS_PROXY", "")


# ── Parse MD report ─────────────────────────────────────────────────────────

def parse_report(md_path: str) -> list[dict]:
    """Extract articles from the MD report."""
    with open(md_path, "r", encoding="utf-8") as f:
        text = f.read()

    articles = []
    # Split by "### " headers
    blocks = re.split(r"(?=^### \d+\.)", text, flags=re.MULTILINE)

    for block in blocks:
        m_title = re.search(r"^### \d+\.\s*(.+)$", block, re.MULTILINE)
        if not m_title:
            continue

        title = m_title.group(1).strip()
        # Extract URL
        m_url = re.search(r">\s*\*\*链接：\*\*\s*(https?://\S+)", block)
        url = m_url.group(1).strip() if m_url else ""
        # Extract source
        m_src = re.search(r">\s*\*\*来源：\*\*\s*(.+)", block)
        source = m_src.group(1).strip() if m_src else ""
        # Extract body text (between title and first >)
        body_match = re.search(r"^### .+?\n\n(.+?)\n\n>", block, re.DOTALL)
        body = body_match.group(1).strip() if body_match else ""
        # Detect category from section header before this block
        category = ""

        articles.append({
            "title": title,
            "url": url,
            "source": source,
            "body": body,
            "block": block.strip(),
        })

    # Assign categories by scanning full text
    sections = re.split(r"^## ■\s*(.+?)$", text, flags=re.MULTILINE)
    # sections[0] = header, then alternating: category, content
    cat_articles: dict[str, list[str]] = {}
    for i in range(1, len(sections), 2):
        cat = sections[i].strip()
        content = sections[i + 1] if i + 1 < len(sections) else ""
        # Find titles in this section
        for m in re.finditer(r"^### \d+\.\s*(.+)$", content, re.MULTILINE):
            t = m.group(1).strip()
            cat_articles[t] = cat

    for art in articles:
        art["category"] = cat_articles.get(art["title"], "未分类")

    return articles


# ── Step 1: Extract date from URL ────────────────────────────────────────────

_DATE_PATTERNS = [
    # YYYYMMDD in path
    re.compile(r"/(\d{4})(\d{2})(\d{2})"),
    # YYYY/MM/DD or YYYY-MM-DD
    re.compile(r"/(\d{4})[/-](\d{2})[/-](\d{2})"),
    # YYYY/M/D
    re.compile(r"/(\d{4})/(\d{1,2})/(\d{1,2})"),
]


def extract_date_from_url(url: str) -> date | None:
    """Try to extract a publication date from the URL."""
    for pat in _DATE_PATTERNS:
        m = pat.search(url)
        if m:
            try:
                y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
                if 2020 <= y <= 2030 and 1 <= mo <= 12 and 1 <= d <= 31:
                    return date(y, mo, d)
            except ValueError:
                continue
    return None


def is_in_range(d: date) -> bool:
    return WEEK_START <= d <= WEEK_END


# ── Step 2: Check link validity ──────────────────────────────────────────────

async def check_links(articles: list[dict], concurrency: int = 10) -> dict[str, bool]:
    """HEAD-check all URLs, return {url: is_valid}."""
    sem = asyncio.Semaphore(concurrency)
    results: dict[str, bool] = {}

    async def _check(url: str):
        if not url:
            return
        async with sem:
            try:
                proxy = get_proxies_for_url(url, OVERSEAS_PROXY)
                async with build_httpx_client(proxy_url=proxy or "", timeout=15.0) as client:
                    resp = await client.head(url, follow_redirects=True)
                    valid = resp.status_code < 400
                    results[url] = valid
            except Exception:
                # Try GET if HEAD fails
                try:
                    async with build_httpx_client(proxy_url=proxy or "", timeout=15.0) as client:
                        resp = await client.get(url, follow_redirects=True)
                        results[url] = resp.status_code < 400
                except Exception:
                    results[url] = False

    tasks = [_check(a["url"]) for a in articles]
    await asyncio.gather(*tasks)
    return results


# ── Step 3: LLM-based date verification + duplicate merging ──────────────────

_VERIFY_MERGE_PROMPT = """\
你是新闻分析专家。以下是一批关于乌拉圭的新闻文章，来源于搜索引擎。

你的任务：
1. **时效性判断**：根据文章标题、摘要和URL中的线索，判断每篇文章是否报道了 2026年3月2日 至 2026年3月11日 这一周内发生的事件。
   - 如果文章明显是旧闻（2025年或更早的事件、历史回顾、无时效性的分析文章），标记为 recent=false
   - 如果文章报道的是近期事件或无法确定时间，标记为 recent=true（宁可保留）

2. **去重合并**：识别报道同一事件的多篇文章，分配相同的 event_id。
   - 同一事件的不同报道应有相同的 event_id
   - 不同事件使用不同的 event_id（从1开始）
   - 对于同一事件的多篇报道，选出最佳的一篇（信息最丰富、来源最权威）标记 best=true

返回JSON数组，每个元素：
{
  "id": <文章序号，0-based>,
  "recent": true/false,
  "event_id": <事件编号>,
  "event_label": "<事件简短标签，中文，10字以内>",
  "best": true/false,
  "reason": "<判断理由，一句话>"
}

仅返回JSON数组，不要其他文字。"""


async def llm_verify_and_merge(articles: list[dict]) -> list[dict]:
    """Use LLM to verify recency and identify duplicates."""
    if not articles:
        return []

    # Build input
    items = []
    for i, art in enumerate(articles):
        url_date = extract_date_from_url(art["url"])
        items.append({
            "id": i,
            "title": art["title"],
            "summary": art["body"][:200] if art["body"] else "",
            "url": art["url"],
            "url_date": str(url_date) if url_date else "unknown",
            "source": art["source"],
        })

    user_msg = json.dumps(items, ensure_ascii=False)

    # Try providers in order
    for prov_name in ["deepseek", "kimi", "grok"]:
        prov = PROVIDERS[prov_name]
        api_key = os.environ.get(prov["api_key_env"], "")
        if not api_key:
            continue

        url = f"{prov['base_url']}/chat/completions"
        body = {
            "model": prov["model"],
            "messages": [
                {"role": "system", "content": _VERIFY_MERGE_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            "temperature": 0.0,
        }

        proxy = None
        if prov["overseas"]:
            proxy = get_proxies_for_url(url, OVERSEAS_PROXY)

        try:
            print(f"  Using {prov_name} for verification...")
            async with build_httpx_client(proxy_url=proxy or "", timeout=120.0) as client:
                resp = await client.post(
                    url, json=body,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                )
                resp.raise_for_status()
                data = resp.json()

            content = data["choices"][0]["message"]["content"].strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

            results = json.loads(content)
            if isinstance(results, list):
                return results
        except Exception as exc:
            print(f"  {prov_name} failed: {exc}")
            continue

    print("  WARNING: All providers failed, keeping all articles")
    return [{"id": i, "recent": True, "event_id": i + 1, "event_label": "unknown", "best": True, "reason": "无法验证"} for i in range(len(articles))]


# ── Step 4: Generate cleaned report ──────────────────────────────────────────

def generate_cleaned_report(
    articles: list[dict],
    link_status: dict[str, bool],
    llm_results: list[dict],
    output_path: str,
):
    """Generate filtered & merged MD report."""
    # Build lookup
    llm_map = {r["id"]: r for r in llm_results}

    # Stats
    total = len(articles)
    dead_links = sum(1 for a in articles if not link_status.get(a["url"], True))
    url_date_filtered = 0
    llm_old = 0
    duplicates_removed = 0

    # Filter pipeline
    kept: list[dict] = []
    removed_reasons: list[str] = []

    for i, art in enumerate(articles):
        url = art["url"]

        # Check link
        if not link_status.get(url, True):
            removed_reasons.append(f"❌ 链接失效: {art['title'][:50]}…")
            continue

        # Check URL date
        url_date = extract_date_from_url(url)
        if url_date and not is_in_range(url_date):
            url_date_filtered += 1
            removed_reasons.append(f"📅 URL日期不符({url_date}): {art['title'][:50]}…")
            continue

        # Check LLM recency
        llm_r = llm_map.get(i, {})
        if not llm_r.get("recent", True):
            llm_old += 1
            removed_reasons.append(f"🕐 LLM判定旧闻: {art['title'][:50]}… ({llm_r.get('reason', '')})")
            continue

        # Check if duplicate (not best)
        if not llm_r.get("best", True):
            duplicates_removed += 1
            event_label = llm_r.get("event_label", "")
            removed_reasons.append(f"🔁 重复合并({event_label}): {art['title'][:50]}…")
            continue

        art["event_label"] = llm_r.get("event_label", "")
        art["event_id"] = llm_r.get("event_id", 0)
        kept.append(art)

    # Group by category
    categories: dict[str, list[dict]] = {}
    for art in kept:
        cat = art.get("category", "未分类")
        categories.setdefault(cat, []).append(art)

    # Write report
    lines: list[str] = []
    lines.append("# 乌拉圭动态监测报告（过滤后）\n")
    lines.append(f"**生成时间：** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    lines.append(f"**过滤日期范围：** {WEEK_START} → {WEEK_END}\n")
    lines.append("")
    lines.append("## 过滤摘要\n")
    lines.append(f"| 指标 | 数量 |")
    lines.append(f"|:---|---:|")
    lines.append(f"| 原始文章数 | {total} |")
    lines.append(f"| 链接失效 | {dead_links} |")
    lines.append(f"| URL日期不符 | {url_date_filtered} |")
    lines.append(f"| LLM判定旧闻 | {llm_old} |")
    lines.append(f"| 重复合并 | {duplicates_removed} |")
    lines.append(f"| **最终保留** | **{len(kept)}** |")
    lines.append("")
    lines.append("---\n")

    # Articles by category
    for cat, arts in categories.items():
        lines.append(f"## ■ {cat}（{len(arts)} 篇）\n")
        for idx, art in enumerate(arts, 1):
            lines.append(f"### {idx}. {art['title']}\n")
            if art.get("event_label"):
                lines.append(f"**事件标签：** {art['event_label']}\n")
            lines.append(f"{art['body']}\n")
            lines.append(f"> **来源：** {art['source']}")
            url_d = extract_date_from_url(art["url"])
            if url_d:
                lines.append(f"> **URL日期：** {url_d}")
            lines.append(f"> **链接：** {art['url']}")
            lines.append("")
            lines.append("---\n")

    # Removed articles log
    lines.append("## 过滤日志\n")
    for r in removed_reasons:
        lines.append(f"- {r}")
    lines.append("")

    report_text = "\n".join(lines)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report_text)

    return output_path


# ── Main ─────────────────────────────────────────────────────────────────────

async def main(md_path: str):
    print(f"Reading report: {md_path}")
    articles = parse_report(md_path)
    print(f"Parsed {len(articles)} articles\n")

    # Step 1: URL date pre-filter stats
    print("Step 1: Extracting dates from URLs...")
    for art in articles:
        d = extract_date_from_url(art["url"])
        if d:
            status = "✓ in range" if is_in_range(d) else "✗ out of range"
            print(f"  {d} {status} — {art['title'][:60]}…")
    print()

    # Step 2: Check links
    print("Step 2: Checking link validity...")
    link_status = await check_links(articles)
    dead = [a["title"][:50] for a in articles if not link_status.get(a["url"], True)]
    print(f"  Valid: {sum(1 for v in link_status.values() if v)}")
    print(f"  Dead:  {len(dead)}")
    for d in dead:
        print(f"    ✗ {d}…")
    print()

    # Step 3: LLM verification + merge (process in batches)
    print("Step 3: LLM recency verification & duplicate detection...")
    # Filter out already-known bad ones before sending to LLM
    candidates = []
    candidate_indices = []
    for i, art in enumerate(articles):
        url_date = extract_date_from_url(art["url"])
        if url_date and not is_in_range(url_date):
            continue
        if not link_status.get(art["url"], True):
            continue
        candidates.append(art)
        candidate_indices.append(i)

    print(f"  Sending {len(candidates)} candidates to LLM...")

    # Process in batches of 20
    batch_size = 20
    all_llm_results: list[dict] = []
    for start in range(0, len(candidates), batch_size):
        batch = candidates[start:start + batch_size]
        print(f"  Batch {start // batch_size + 1} ({len(batch)} articles)...")
        batch_results = await llm_verify_and_merge(batch)

        # Remap IDs to original indices
        for r in batch_results:
            original_batch_idx = r["id"]
            if 0 <= original_batch_idx < len(batch):
                r["id"] = candidate_indices[start + original_batch_idx]
        all_llm_results.extend(batch_results)

    # Add pre-filtered articles as non-recent
    for i, art in enumerate(articles):
        if i not in candidate_indices:
            all_llm_results.append({
                "id": i,
                "recent": False,
                "event_id": 0,
                "event_label": "",
                "best": False,
                "reason": "URL日期不在范围内" if extract_date_from_url(art["url"]) else "链接失效",
            })

    print()

    # Step 4: Generate cleaned report
    base = os.path.splitext(md_path)[0]
    output_path = f"{base}_filtered.md"
    print("Step 4: Generating cleaned report...")
    generate_cleaned_report(articles, link_status, all_llm_results, output_path)
    print(f"\nDone! Filtered report: {output_path}")

    # Summary
    kept = sum(1 for r in all_llm_results if r.get("recent") and r.get("best"))
    print(f"\n{'='*60}")
    print(f"Original: {len(articles)} → Kept: {kept}")
    print(f"{'='*60}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))
