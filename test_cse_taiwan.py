"""Test: Google CSE for Taiwan site monitoring.

Tests 3 scenarios:
  1. CSE with siteSearch parameter (single site)
  2. CSE with site: in query (single site)
  3. CSE without site restriction (if CSE is configured with sites in console)

Usage:
    python test_cse_taiwan.py
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
from news_monitor.sources.google_cse import GoogleCSE


async def main():
    api_key = os.environ.get("GOOGLE_CSE_API_KEY", "")
    cx = os.environ.get("GOOGLE_CSE_CX", "")

    if not api_key:
        print("ERROR: GOOGLE_CSE_API_KEY not set")
        print("  1. Go to https://console.cloud.google.com/apis/credentials")
        print("  2. Create an API key")
        print("  3. Enable 'Custom Search API' at https://console.cloud.google.com/apis/library/customsearch.googleapis.com")
        print("  4. export GOOGLE_CSE_API_KEY='your-key'")
        sys.exit(1)
    if not cx:
        print("ERROR: GOOGLE_CSE_CX not set")
        print("  1. Go to https://programmablesearchengine.google.com/")
        print("  2. Create a search engine (add target sites or 'Search the entire web')")
        print("  3. Copy the Search Engine ID")
        print("  4. export GOOGLE_CSE_CX='your-cx-id'")
        sys.exit(1)

    proxy = os.environ.get("LLM_PROXY", "")
    print(f"API Key : {api_key[:8]}...{api_key[-4:]}")
    print(f"CSE ID  : {cx}")
    print(f"Proxy   : {proxy or '(none)'}")

    today = date.today().strftime("%Y-%m-%d")
    week_ago = (date.today() - timedelta(days=7)).strftime("%Y-%m-%d")

    cse = GoogleCSE(config={"api_key": api_key, "cx": cx}, overseas_proxy=proxy)

    # --- Test 1: site: in query ---
    print(f"\n{'='*60}")
    print("TEST 1: site:focustaiwan.tw in query string")
    print(f"{'='*60}")
    r1 = await cse.fetch_articles(
        keywords=["site:focustaiwan.tw"],
        countries=[], languages=["en"],
        time_range_hours=168, max_articles=10,
        topic_name="test_site_query",
        from_date=week_ago, to_date=today,
    )
    _print_result(r1)

    await asyncio.sleep(1)

    # --- Test 2: keyword search (relies on CSE console site list) ---
    print(f"\n{'='*60}")
    print("TEST 2: keyword 'Taiwan' (uses CSE console site restrictions)")
    print(f"{'='*60}")
    r2 = await cse.fetch_articles(
        keywords=["Taiwan"],
        countries=[], languages=["en"],
        time_range_hours=24, max_articles=10,
        topic_name="test_keyword",
        from_date=today, to_date=today,
    )
    _print_result(r2)

    await asyncio.sleep(1)

    # --- Test 3: wildcard (get everything from today) ---
    print(f"\n{'='*60}")
    print("TEST 3: wildcard '*' + dateRestrict=d1 (today's content)")
    print(f"{'='*60}")
    r3 = await cse.fetch_articles(
        keywords=["*"],
        countries=[], languages=["en"],
        time_range_hours=24, max_articles=10,
        topic_name="test_wildcard",
    )
    _print_result(r3)


def _print_result(result):
    if result.error:
        print(f"  ERROR: {result.error}")
        return
    print(f"  Fetched {len(result.articles)} articles in {result.elapsed_sec:.1f}s\n")
    _EPOCH = datetime.min.replace(tzinfo=timezone.utc)
    arts = sorted(result.articles, key=lambda a: a.published_at or _EPOCH, reverse=True)
    for i, a in enumerate(arts, 1):
        pub = a.published_at.strftime("%Y-%m-%d") if a.published_at else "?"
        print(f"  {i:>2}. [{pub}] {a.title[:80]}")
        print(f"      {a.source_name} — {a.source_url[:100]}")
        if a.description:
            print(f"      {a.description[:120]}")
        print()


if __name__ == "__main__":
    asyncio.run(main())
