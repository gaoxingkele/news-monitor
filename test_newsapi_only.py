"""Test: NewsAPI.ai only, optimized queries, for Uruguay.

Usage:
    python test_newsapi_only.py
"""
from __future__ import annotations

import asyncio
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from datetime import date, timedelta, datetime, timezone

from news_monitor.config_loader import load_config
from news_monitor.models import NewsArticle, CycleReport
from news_monitor.sources.newsapi_ai import NewsAPIAI
from news_monitor.topics.loader import load_topics_from_dir
from news_monitor.translation.llm_translator import LLMTranslator
from news_monitor.filter.relevance_filter import RelevanceFilter
from news_monitor.output.pdf_reporter import generate_report


def _last_week_range() -> tuple[str, str]:
    today = date.today()
    return (today - timedelta(days=7)).strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")


def _dedup(articles: list[NewsArticle]) -> list[NewsArticle]:
    seen: set[str] = set()
    out: list[NewsArticle] = []
    for a in articles:
        key = a.fingerprint or a.source_url
        if key and key not in seen:
            seen.add(key)
            out.append(a)
    return out


async def main():
    config = load_config("config.yaml")
    overseas_proxy = config.get("proxy", {}).get("overseas_proxy", "")

    all_topics = load_topics_from_dir("topics")
    topic = next(t for t in all_topics if "乌拉圭" in t.get("name", ""))

    query_groups: list[list[str]] = [[q] for q in topic.get("query_groups", [])]
    time_range_hours = topic.get("time_range_hours", 168)
    max_articles = topic.get("max_articles", 20)
    exclude_kw = topic.get("exclude_keywords")
    languages = topic.get("languages", [])
    local_countries = topic.get("countries", [])
    from_date, to_date = _last_week_range()

    print(f"Topic     : {topic['name']}")
    print(f"Dates     : {from_date} → {to_date}")
    print(f"Languages : {languages}")
    print(f"Queries   : {len(query_groups)}")
    print(f"Source    : NewsAPI.ai (optimized)")

    na_cfg = config.get("sources", {}).get("newsapi_ai", {})
    if not na_cfg.get("api_key"):
        na_cfg["api_key"] = os.environ.get("NEWSAPI_AI_KEY", "")
    na = NewsAPIAI(na_cfg, overseas_proxy)

    print(f"\n[NewsAPI.ai] fetching {len(query_groups)} query groups...")
    all_arts: list[NewsArticle] = []
    for i, kw_list in enumerate(query_groups):
        result = await na.fetch_articles(
            keywords=kw_list,
            countries=local_countries,
            languages=languages,
            time_range_hours=time_range_hours,
            max_articles=max_articles,
            exclude_keywords=exclude_kw,
            topic_name=topic.get("name", ""),
            from_date=from_date,
            to_date=to_date,
        )
        kw = kw_list[0] if kw_list else ""
        if result.error:
            print(f"  [{i+1:>2}] WARN '{kw[:50]}': {result.error.splitlines()[0][:80]}")
        elif result.articles:
            print(f"  [{i+1:>2}] '{kw[:50]}': {len(result.articles)}")
        else:
            print(f"  [{i+1:>2}] '{kw[:50]}': 0")
        all_arts.extend(result.articles)
        await asyncio.sleep(0.3)

    unique = _dedup(all_arts)

    print(f"\n{'='*72}")
    print(f"Raw total  : {len(all_arts)}")
    print(f"After dedup: {len(unique)}  (removed {len(all_arts) - len(unique)})")
    print(f"{'='*72}")

    # Sort & print
    _EPOCH = datetime.min.replace(tzinfo=timezone.utc)
    def _sort_key(a):
        p = a.published_at
        if p is None: return _EPOCH
        if p.tzinfo is None: p = p.replace(tzinfo=timezone.utc)
        return p
    unique.sort(key=_sort_key, reverse=True)

    for i, a in enumerate(unique[:30], 1):
        pub = a.published_at.strftime("%Y-%m-%d %H:%M") if a.published_at else "?"
        print(f"  {i:>2}. {pub}  [{a.language}]  {a.source_name}")
        print(f"      {a.title[:90]}")
        print(f"      {a.source_url[:120]}")
        print()

    # ── Translate ──
    country_zh, country_en, country_code = "乌拉圭", "Uruguay", "uy"
    trans_cfg = config.get("translation", {})
    translator = LLMTranslator(
        provider=trans_cfg.get("provider", "deepseek"),
        fallback_provider=trans_cfg.get("fallback_provider", "kimi"),
        batch_size=trans_cfg.get("batch_size", 5),
        overseas_proxy=overseas_proxy,
        country_zh=country_zh, country_en=country_en, country_key=country_code,
    )
    print(f"\nTranslating {len(unique)} articles...")
    unique = await translator.translate_articles(unique)
    translated = sum(1 for a in unique if a.title_zh)
    print(f"Done. {translated} translated.")

    # ── Relevance filter ──
    rf = RelevanceFilter(
        provider="grok", fallback_provider="deepseek", second_fallback="kimi",
        batch_size=15, overseas_proxy=overseas_proxy,
    )
    print(f"\nFiltering {len(unique)} articles...")
    filtered, filter_log = await rf.filter_articles(unique, country_zh, country_en)
    removed = len(unique) - len(filtered)
    print(f"Kept {len(filtered)}, removed {removed}.")
    if removed:
        for entry in filter_log:
            if not entry["relevant"]:
                print(f"  ✗ {entry['title'][:55]}… ({entry['reason'][:40]})")

    # ── Generate report ──
    report = CycleReport(total_fetched=len(all_arts), total_after_dedup=len(unique), total_translated=translated)
    md_path, pdf_path = generate_report(
        articles=filtered, report=report, output_dir="output/reports",
        topic_name=topic["name"], country_key=country_code,
        country_label=f"{country_zh}相关", highlight_keywords=[country_zh, country_en],
    )
    print(f"\nMD saved  : {md_path}")
    if pdf_path:
        print(f"PDF saved : {pdf_path}")


if __name__ == "__main__":
    asyncio.run(main())
