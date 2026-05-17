"""Fetch Mexico topic: newsdata_io only, two scopes (targeted + global), dedup."""
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

from datetime import date, timedelta

from news_monitor.config_loader import load_config
from news_monitor.models import NewsArticle
from news_monitor.sources.newsdata_io import NewsDataIO
from news_monitor.topics.loader import load_topics_from_dir


def _last_week_range(time_range_hours: int = 168) -> tuple[str, str]:
    today = date.today()
    days_since_sunday = (today.weekday() + 1) % 7 or 7
    last_sunday = today - timedelta(days=days_since_sunday)
    from_date = last_sunday - timedelta(days=(time_range_hours // 24) - 1)
    return from_date.strftime("%Y-%m-%d"), last_sunday.strftime("%Y-%m-%d")


def _dedup(articles: list[NewsArticle]) -> list[NewsArticle]:
    seen: set[str] = set()
    out: list[NewsArticle] = []
    for a in articles:
        if a.fingerprint and a.fingerprint not in seen:
            seen.add(a.fingerprint)
            out.append(a)
    return out


async def _fetch_scope(
    source: NewsDataIO,
    query_groups: list[list[str]],
    scope_label: str,
    *,
    topic_name: str,
    countries: list[str],
    languages: list[str],
    time_range_hours: int,
    max_articles: int,
    exclude_kw: list[str] | None,
    from_date: str,
    to_date: str,
    delay: float = 1.5,
) -> list[NewsArticle]:
    """Run all queries sequentially for one country scope."""
    articles: list[NewsArticle] = []
    for kw_list in query_groups:
        result = await source.fetch_articles(
            keywords=kw_list,
            countries=countries,
            languages=languages,
            time_range_hours=time_range_hours,
            max_articles=max_articles,
            exclude_keywords=exclude_kw,
            topic_name=topic_name,
            from_date=from_date,
            to_date=to_date,
        )
        kw = kw_list[0] if kw_list else ""
        if result.error:
            print(f"  WARN [{scope_label}] '{kw}': {result.error.splitlines()[0]}")
        else:
            n = len(result.articles)
            if n:
                print(f"  [{scope_label}] '{kw}': {n}")
            articles.extend(result.articles)
        await asyncio.sleep(delay)
    return articles


async def main() -> None:
    config = load_config("config.yaml")
    overseas_proxy = config.get("proxy", {}).get("overseas_proxy", "")

    all_topics = load_topics_from_dir("topics")
    topics = [t for t in all_topics if "墨西哥" in t.get("name", "")]
    if not topics:
        print("Mexico topic not found"); return
    topic = topics[0]

    query_groups: list[list[str]] = [[q] for q in topic.get("query_groups", [])]
    time_range_hours = topic.get("time_range_hours", 168)
    max_articles     = topic.get("max_articles", 20)
    exclude_kw       = topic.get("exclude_keywords")
    languages        = topic.get("languages", [])
    from_date, to_date = _last_week_range(time_range_hours)

    local_countries   = topic.get("countries", [])
    watch_countries   = topic.get("watch_countries", [])
    targeted          = local_countries + watch_countries   # e.g. [mx, tw, cn, us]
    search_global     = topic.get("search_global", False)

    print(f"Topic     : {topic['name']}")
    print(f"Dates     : {from_date} → {to_date}")
    print(f"Languages : {languages}")
    print(f"Targeted  : {targeted}  |  global: {search_global}")
    print(f"Queries   : {len(query_groups)}  ×  {'2 scopes' if search_global else '1 scope'}"
          f" = {len(query_groups) * (2 if search_global else 1)} calls\n")

    nd = NewsDataIO(config.get("sources", {}).get("newsdata_io", {}), overseas_proxy)
    kw = dict(
        topic_name=topic.get("name", ""),
        languages=languages,
        time_range_hours=time_range_hours,
        max_articles=max_articles,
        exclude_kw=exclude_kw,
        from_date=from_date,
        to_date=to_date,
    )

    # Scope 1: targeted countries (mx + tw + cn + us)
    scope_label = "+".join(targeted) if targeted else "global"
    print(f"── scope 1: country={scope_label} ──")
    arts_targeted = await _fetch_scope(nd, query_groups, scope_label,
                                       countries=targeted, **kw)
    print(f"  subtotal: {len(arts_targeted)}\n")

    # Scope 2: global (no country filter)
    arts_global: list[NewsArticle] = []
    if search_global:
        print("── scope 2: global (no country filter) ──")
        arts_global = await _fetch_scope(nd, query_groups, "global",
                                         countries=[], **kw)
        print(f"  subtotal: {len(arts_global)}\n")

    raw    = arts_targeted + arts_global
    unique = _dedup(raw)

    print(f"Raw total : {len(raw)}  (targeted={len(arts_targeted)}, global={len(arts_global)})")
    print(f"After dedup: {len(unique)}  (removed {len(raw) - len(unique)})")
    print("=" * 72)

    unique.sort(key=lambda a: a.published_at or date.min, reverse=True)
    for i, a in enumerate(unique, 1):
        pub    = a.published_at.strftime("%Y-%m-%d %H:%M") if a.published_at else "?"
        ctry   = a.country or "?"
        lang   = a.language or "?"
        print(f"{i:>3}. {pub}  [{lang}/{ctry}]  {a.source_name or ''}")
        print(f"      {a.title}")
        if a.description:
            print(f"      {a.description[:140].replace(chr(10),' ').strip()}")
        print(f"      {a.source_url}")
        print()

    print(f"Total unique: {len(unique)}")


if __name__ == "__main__":
    asyncio.run(main())
