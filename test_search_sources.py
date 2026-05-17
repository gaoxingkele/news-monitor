"""Search source comparison: Brave vs Gemini vs Grok (web + x_search).

Usage:
    python test_search_sources.py 乌拉圭
    python test_search_sources.py 巴拉圭
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

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

from news_monitor.config_loader import load_config
from news_monitor.models import NewsArticle
from news_monitor.proxy import build_httpx_client, get_proxies_for_url
from news_monitor.sources.brave_search import BraveSearch

# ── Config ────────────────────────────────────────────────────────────────────

FROM_DATE = "2026-03-05"
TO_DATE = "2026-03-12"

_COUNTRY_MAP: dict[str, tuple[str, str, str]] = {
    # filter_name: (code, zh, en)
    "乌拉圭": ("uy", "乌拉圭", "Uruguay"),
    "uruguay": ("uy", "乌拉圭", "Uruguay"),
    "巴拉圭": ("py", "巴拉圭", "Paraguay"),
    "paraguay": ("py", "巴拉圭", "Paraguay"),
}

# 8 representative queries per country (covering 6 relation lines)
_QUERIES: dict[str, list[tuple[str, str]]] = {
    "uy": [
        ("中国 ES", "China Uruguay inversión comercio acuerdo diplomacia"),
        ("中国 ZH", "乌拉圭 中国 投资 贸易 合作 外交 协议"),
        ("美国 ES", '"Estados Unidos" Uruguay acuerdo seguridad cooperación defensa'),
        ("台湾 ES", "Taiwan Uruguay diplomacia visita ministro congreso cooperación"),
        ("台湾 ZH", "乌拉圭 台湾 外交 访问 合作 奖学金 医疗 部长"),
        ("跨议题1", "Uruguay comunidad china empresa crimen seguridad inmigrante"),
        ("跨议题2", "Uruguay cambio climático carbono medio ambiente acuerdo"),
        ("舆情", "Uruguay China protesta xenofobia rechazo invasión empresa china"),
    ],
    "py": [
        ("中国 ES", "China Paraguay inversión comercio acuerdo diplomacia"),
        ("中国 ZH", "巴拉圭 中国 投资 贸易 合作 外交 协议"),
        ("美国 ES", '"Estados Unidos" Paraguay acuerdo seguridad cooperación defensa'),
        ("台湾 ES", "Taiwan Paraguay diplomacia visita ministro congreso cooperación"),
        ("台湾 ZH", "巴拉圭 台湾 外交 访问 合作 奖学金 医疗 部长"),
        ("跨议题1", "Paraguay comunidad china empresa crimen seguridad inmigrante"),
        ("跨议题2", "Paraguay cambio climático carbono medio ambiente acuerdo"),
        ("舆情", "Paraguay China protesta xenofobia rechazo invasión empresa china"),
    ],
}


# ── URL normalization ─────────────────────────────────────────────────────────

def _normalize_url(url: str) -> str:
    """Normalize URL for overlap comparison: strip scheme, www, query, trailing slash."""
    try:
        p = urlparse(url)
        host = p.hostname or ""
        if host.startswith("www."):
            host = host[4:]
        path = p.path.rstrip("/")
        return f"{host}{path}".lower()
    except Exception:
        return url.lower().strip("/")


# ── Brave (baseline) ─────────────────────────────────────────────────────────

async def fetch_brave(
    source: BraveSearch,
    query: str,
    country_code: str,
) -> list[NewsArticle]:
    """Fetch via existing BraveSearch class."""
    result = await source.fetch_articles(
        keywords=[query],
        countries=[country_code],
        languages=["es", "en", "zh"],
        time_range_hours=168,
        max_articles=20,
        topic_name="search_comparison",
        from_date=FROM_DATE,
        to_date=TO_DATE,
    )
    if result.error:
        print(f"    [Brave] error: {result.error[:100]}")
    return result.articles


# ── Gemini Search ─────────────────────────────────────────────────────────────

_GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"


async def fetch_gemini(
    query: str,
    country_en: str,
    overseas_proxy: str,
) -> list[NewsArticle]:
    """Fetch via Gemini with Google Search grounding."""
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        print("    [Gemini] SKIP: GEMINI_API_KEY not set")
        return []

    prompt = (
        f"Search for news articles published between {FROM_DATE} and {TO_DATE} about: {query}\n"
        f"Focus on {country_en}. Find real articles from news outlets.\n"
        f"For each article, provide title, source, date, and a brief summary."
    )

    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "tools": [{"google_search": {}}],
    }

    url = f"{_GEMINI_URL}?key={api_key}"
    proxy = get_proxies_for_url(_GEMINI_URL, overseas_proxy)

    articles: list[NewsArticle] = []
    try:
        async with build_httpx_client(proxy_url=proxy or "", timeout=60.0) as client:
            resp = await client.post(url, json=body)
            if resp.status_code != 200:
                print(f"    [Gemini] HTTP {resp.status_code}: {resp.text[:200]}")
                return []
            data = resp.json()

        # Extract from groundingMetadata
        candidates = data.get("candidates", [])
        if not candidates:
            return []

        grounding = candidates[0].get("groundingMetadata", {})
        chunks = grounding.get("groundingChunks", [])

        # Collect redirect URLs to resolve
        raw_entries: list[tuple[str, str]] = []  # (uri, title)
        for chunk in chunks:
            web = chunk.get("web", {})
            uri = web.get("uri", "")
            title = web.get("title", "").strip()
            if uri:
                raw_entries.append((uri, title))

        # Resolve vertexaisearch redirects in parallel
        redirect_prefix = "vertexaisearch.cloud.google.com"
        resolved: list[tuple[str, str]] = []

        async def _resolve(uri: str, title: str) -> tuple[str, str]:
            if redirect_prefix not in uri:
                return uri, title
            try:
                rp = get_proxies_for_url(uri, overseas_proxy)
                async with build_httpx_client(proxy_url=rp or "", timeout=10.0) as rc:
                    r = await rc.get(uri, follow_redirects=False)
                    loc = r.headers.get("location", "")
                    if loc:
                        real_host = urlparse(loc).hostname or ""
                        return loc, title or real_host
            except Exception:
                pass
            return uri, title

        resolved = await asyncio.gather(*[_resolve(u, t) for u, t in raw_entries])

        for real_url, title in resolved:
            art = NewsArticle(
                title=title,
                source_url=real_url,
                source_name=urlparse(real_url).hostname or "",
                api_source="gemini_search",
                topic_name="search_comparison",
            )
            art.compute_fingerprint()
            articles.append(art)

    except Exception as exc:
        print(f"    [Gemini] error: {exc}")

    return articles


# ── Grok (web_search / x_search) ─────────────────────────────────────────────

_GROK_URL = "https://api.x.ai/v1/responses"


async def fetch_grok(
    query: str,
    country_en: str,
    overseas_proxy: str,
    *,
    search_type: str = "web_search",
) -> list[NewsArticle]:
    """Fetch via Grok with web_search or x_search tool."""
    api_key = os.environ.get("XAI_API_KEY", "") or os.environ.get("GROK_API_KEY", "")
    if not api_key:
        print(f"    [Grok {search_type}] SKIP: XAI_API_KEY/GROK_API_KEY not set")
        return []

    if search_type == "x_search":
        prompt = (
            f"Search X/Twitter for posts and discussions between {FROM_DATE} and {TO_DATE} about: {query}\n"
            f"Focus on {country_en}. Find tweets from journalists, officials, news outlets.\n"
            f"For each post, provide the key content, author, date, and any linked article URL."
        )
    else:
        prompt = (
            f"Search for news articles published between {FROM_DATE} and {TO_DATE} about: {query}\n"
            f"Focus on {country_en}. Find real articles from news outlets.\n"
            f"For each article, provide title, source, date, and a brief summary."
        )

    body = {
        "model": "grok-4-1-fast-non-reasoning",
        "input": prompt,
        "tools": [{"type": search_type}],
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    proxy = get_proxies_for_url(_GROK_URL, overseas_proxy)
    articles: list[NewsArticle] = []

    try:
        async with build_httpx_client(proxy_url=proxy or "", timeout=120.0) as client:
            resp = await client.post(_GROK_URL, json=body, headers=headers)
            if resp.status_code != 200:
                print(f"    [Grok {search_type}] HTTP {resp.status_code}: {resp.text[:200]}")
                return []
            data = resp.json()

        # Parse output array
        output_items = data.get("output", [])
        seen_urls: set[str] = set()

        def _add_url(url: str, title: str = "") -> None:
            if url and url not in seen_urls:
                seen_urls.add(url)
                art = NewsArticle(
                    title=title or url,
                    source_url=url,
                    source_name=urlparse(url).hostname or "",
                    api_source=f"grok_{search_type}",
                    topic_name="search_comparison",
                )
                art.compute_fingerprint()
                articles.append(art)

        for item in output_items:
            item_type = item.get("type", "")

            # Extract open_page URLs from web_search_call actions
            if item_type == "web_search_call":
                action = item.get("action", {})
                if action.get("type") == "open_page":
                    _add_url(action.get("url", ""))

            # Extract url_citations from message annotations
            if item_type == "message":
                for content_block in item.get("content", []):
                    for ann in content_block.get("annotations", []):
                        _add_url(ann.get("url", ""), ann.get("title", "").strip())

            # Also check search_call_results
            if item_type == "search_call_result":
                for result in item.get("results", []):
                    _add_url(result.get("url", ""), result.get("title", "").strip())

    except Exception as exc:
        print(f"    [Grok {search_type}] error: {exc}")

    return articles


# ── Dedup ─────────────────────────────────────────────────────────────────────

def _dedup(articles: list[NewsArticle]) -> list[NewsArticle]:
    seen: set[str] = set()
    out: list[NewsArticle] = []
    for a in articles:
        norm = _normalize_url(a.source_url)
        if norm and norm not in seen:
            seen.add(norm)
            out.append(a)
    return out


# ── Report generation ─────────────────────────────────────────────────────────

def _generate_report(
    country_zh: str,
    country_code: str,
    query_results: dict[str, dict[str, list[NewsArticle]]],
) -> str:
    """Generate a markdown comparison report."""
    sources = ["Brave", "Gemini", "Grok Web", "Grok X"]
    source_keys = ["brave", "gemini", "grok_web", "grok_x"]

    # Aggregate stats
    totals: dict[str, int] = {k: 0 for k in source_keys}
    deduped: dict[str, int] = {k: 0 for k in source_keys}
    all_articles: dict[str, list[NewsArticle]] = {k: [] for k in source_keys}
    all_urls: dict[str, set[str]] = {k: set() for k in source_keys}

    lines: list[str] = []
    lines.append(f"# 数据源对比：{country_zh}")
    lines.append(f"日期范围：{FROM_DATE} → {TO_DATE}")
    lines.append(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")

    # Per-query section
    lines.append("## 按查询对比")
    lines.append("")

    for label, query in _QUERIES[country_code]:
        lines.append(f"### [{label}] {query[:80]}")
        lines.append("")
        lines.append("| 数据源 | 结果数 | 去重后 |")
        lines.append("|--------|--------|--------|")

        for src_name, src_key in zip(sources, source_keys):
            raw = query_results.get(query, {}).get(src_key, [])
            unique = _dedup(raw)
            totals[src_key] += len(raw)
            deduped[src_key] += len(unique)
            all_articles[src_key].extend(unique)
            for a in unique:
                all_urls[src_key].add(_normalize_url(a.source_url))
            lines.append(f"| {src_name} | {len(raw)} | {len(unique)} |")

        lines.append("")

        # Show top articles per source
        for src_name, src_key in zip(sources, source_keys):
            arts = _dedup(query_results.get(query, {}).get(src_key, []))
            if arts:
                lines.append(f"**{src_name}** ({len(arts)}):")
                for a in arts[:5]:
                    host = urlparse(a.source_url).hostname or ""
                    is_redirect = "vertexaisearch" in a.source_url
                    redirect_tag = " [重定向]" if is_redirect else ""
                    lines.append(f"- {a.title[:80]} ({host}){redirect_tag}")
                    lines.append(f"  {a.source_url}")
                if len(arts) > 5:
                    lines.append(f"  ...and {len(arts) - 5} more")
                lines.append("")
        lines.append("---")
        lines.append("")

    # Overall stats
    lines.insert(4, "## 总体统计")
    lines.insert(5, "")
    lines.insert(6, "| 数据源 | 总结果 | 去重后 | 独有URL |")
    lines.insert(7, "|--------|--------|--------|---------|")

    # Compute unique URLs per source (not in any other source)
    other_urls: dict[str, set[str]] = {}
    for sk in source_keys:
        others = set()
        for sk2 in source_keys:
            if sk2 != sk:
                others |= all_urls[sk2]
        other_urls[sk] = all_urls[sk] - others

    insert_idx = 8
    for src_name, src_key in zip(sources, source_keys):
        unique_count = len(other_urls[src_key])
        lines.insert(insert_idx, f"| {src_name} | {totals[src_key]} | {deduped[src_key]} | {unique_count} |")
        insert_idx += 1

    lines.insert(insert_idx, "")

    # URL overlap analysis
    lines.append("## URL 重叠分析")
    lines.append("")
    lines.append("| 对比 | 共同 | 仅左 | 仅右 | Jaccard |")
    lines.append("|------|------|------|------|---------|")

    pairs = [
        ("Brave", "brave", "Gemini", "gemini"),
        ("Brave", "brave", "Grok Web", "grok_web"),
        ("Brave", "brave", "Grok X", "grok_x"),
        ("Gemini", "gemini", "Grok Web", "grok_web"),
        ("Gemini", "gemini", "Grok X", "grok_x"),
        ("Grok Web", "grok_web", "Grok X", "grok_x"),
    ]
    for left_name, left_key, right_name, right_key in pairs:
        left_set = all_urls[left_key]
        right_set = all_urls[right_key]
        common = left_set & right_set
        only_left = left_set - right_set
        only_right = right_set - left_set
        union = left_set | right_set
        jaccard = len(common) / len(union) if union else 0
        lines.append(
            f"| {left_name} vs {right_name} | {len(common)} | {len(only_left)} | {len(only_right)} | {jaccard:.2f} |"
        )
    lines.append("")

    # Unique discoveries
    lines.append("## 独有发现")
    lines.append("")
    for src_name, src_key in zip(sources, source_keys):
        unique_urls = other_urls[src_key]
        if unique_urls:
            lines.append(f"### 仅 {src_name} 发现 ({len(unique_urls)})")
            unique_arts = [a for a in all_articles[src_key] if _normalize_url(a.source_url) in unique_urls]
            for a in unique_arts[:10]:
                lines.append(f"- {a.title[:80]}")
                lines.append(f"  {a.source_url}")
            if len(unique_arts) > 10:
                lines.append(f"  ...and {len(unique_arts) - 10} more")
            lines.append("")

    # Conclusion
    lines.append("## 结论")
    lines.append("")
    lines.append(f"- Brave 基准：{deduped['brave']} 篇去重文章")
    lines.append(f"- Gemini (Google Search grounding)：{deduped['gemini']} 篇，独有 {len(other_urls['gemini'])} 篇")
    lines.append(f"- Grok Web：{deduped['grok_web']} 篇，独有 {len(other_urls['grok_web'])} 篇")
    lines.append(f"- Grok X Search：{deduped['grok_x']} 篇，独有 {len(other_urls['grok_x'])} 篇")
    lines.append("")

    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────────────────────

async def run_comparison(country_filter: str) -> None:
    needle = country_filter.lower()
    match = _COUNTRY_MAP.get(needle)
    if not match:
        # Try partial match
        for k, v in _COUNTRY_MAP.items():
            if needle in k:
                match = v
                break
    if not match:
        print(f"Country not found: {country_filter!r}")
        print(f"Available: {list(_COUNTRY_MAP.keys())}")
        return

    country_code, country_zh, country_en = match
    queries = _QUERIES[country_code]

    config = load_config("config.yaml")
    overseas_proxy = config.get("proxy", {}).get("overseas_proxy", "")

    # Init Brave
    bv_cfg = config.get("sources", {}).get("brave_search", {})
    if not bv_cfg.get("api_key"):
        bv_cfg["api_key"] = os.environ.get("BRAVEAPI", "")
    brave = BraveSearch(bv_cfg, overseas_proxy)

    print(f"Country : {country_zh} ({country_en}, {country_code})")
    print(f"Dates   : {FROM_DATE} → {TO_DATE}")
    print(f"Queries : {len(queries)}")
    print(f"Proxy   : {overseas_proxy[:30]}..." if overseas_proxy else "Proxy   : (none)")
    print(f"Sources : Brave, Gemini, Grok Web, Grok X")
    print("=" * 72)

    query_results: dict[str, dict[str, list[NewsArticle]]] = {}

    for i, (label, query) in enumerate(queries, 1):
        print(f"\n[{i}/{len(queries)}] [{label}] {query[:60]}...")

        # Run all 4 sources in parallel
        brave_task = fetch_brave(brave, query, country_code)
        gemini_task = fetch_gemini(query, country_en, overseas_proxy)
        grok_web_task = fetch_grok(query, country_en, overseas_proxy, search_type="web_search")
        grok_x_task = fetch_grok(query, country_en, overseas_proxy, search_type="x_search")

        results = await asyncio.gather(
            brave_task, gemini_task, grok_web_task, grok_x_task,
            return_exceptions=True,
        )

        source_results: dict[str, list[NewsArticle]] = {}
        for key, res in zip(["brave", "gemini", "grok_web", "grok_x"], results):
            if isinstance(res, Exception):
                print(f"    [{key}] exception: {res}")
                source_results[key] = []
            else:
                source_results[key] = res
                print(f"    [{key}]: {len(res)} articles")

        query_results[query] = source_results

        # Rate limit between queries
        if i < len(queries):
            await asyncio.sleep(1.5)

    # Generate report
    print("\n" + "=" * 72)
    print("Generating comparison report...")

    report = _generate_report(country_zh, country_code, query_results)
    output_path = f"output/reports/search_comparison_{country_code}.md"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"Report saved: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    asyncio.run(run_comparison(sys.argv[1]))
