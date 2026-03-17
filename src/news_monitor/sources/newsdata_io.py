"""NewsData.io — primary news source (89 languages, 206 countries)."""
from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Sequence

from news_monitor.models import FetchResult, NewsArticle
from news_monitor.proxy import get_proxies_for_url, build_httpx_client
from news_monitor.sources.base import NewsSource

logger = logging.getLogger("news_monitor.sources.newsdata_io")

_API_BASE = "https://newsdata.io/api/1/latest"

# strptime fallback formats for NewsData.io pubDate field
_NEWSDATA_DATE_FMTS = [
    "%Y-%m-%d %H:%M:%S",   # "2026-03-08 10:30:00"  (most common)
    "%Y-%m-%dT%H:%M:%S",   # "2026-03-08T10:30:00"
    "%Y-%m-%d",             # "2026-03-08"
]


def _parse_newsdata_date(date_str: str) -> datetime | None:
    """Parse NewsData.io pubDate to aware datetime.

    Handles:
    - "YYYY-MM-DD HH:MM:SS" (no timezone)
    - "YYYY-MM-DDTHH:MM:SSZ" (Z suffix — fromisoformat fails on Python < 3.11)
    - "YYYY-MM-DDTHH:MM:SS+HH:MM"
    """
    if not date_str:
        return None
    # Normalize Z → +00:00 so fromisoformat works on Python 3.7-3.10
    s = date_str.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(s)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except (ValueError, TypeError):
        pass
    # strptime fallbacks (no timezone in string → assume UTC)
    for fmt in _NEWSDATA_DATE_FMTS:
        try:
            return datetime.strptime(date_str.strip(), fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


class NewsDataIO(NewsSource):
    name = "newsdata_io"

    async def fetch_articles(
        self,
        keywords: Sequence[str],
        countries: Sequence[str],
        languages: Sequence[str],
        time_range_hours: int = 72,
        max_articles: int = 30,
        exclude_keywords: Sequence[str] | None = None,
        topic_name: str = "",
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> FetchResult:
        t0 = time.monotonic()
        api_key = self.config.get("api_key", "")
        if not api_key:
            return FetchResult(self.name, topic_name, error="Missing api_key")

        # NewsData.io free plan: q param max 100 chars, no quoted multi-word phrases
        # Use simple unquoted keywords joined by OR, stay within char limit
        ascii_kw = [kw for kw in keywords if kw.isascii()] or list(keywords)[:3]
        query = ""
        for kw in ascii_kw:
            candidate = f"{query} OR {kw}" if query else kw
            if len(candidate) <= 80:
                query = candidate
            elif not query:
                query = kw[:80]
            else:
                break

        # Append NOT exclusions inline (free plan supports NOT in q, up to 100 chars)
        if exclude_keywords and query:
            ascii_exc = [e for e in exclude_keywords if e.isascii()][:4]
            for exc in ascii_exc:
                candidate = f"{query} NOT {exc}"
                if len(candidate) <= 100:
                    query = candidate
                else:
                    break

        params: dict = {
            "apikey": api_key,
            "q": query,
            "language": ",".join(languages),
            "size": min(max_articles, self.config.get("max_results_per_query", 50)),
        }
        if countries:
            params["country"] = ",".join(countries)

        # Time filtering: NewsData.io free plan /latest returns last 48h, ignores date params.
        # We apply client-side filtering after fetch to discard out-of-range articles.

        proxy = get_proxies_for_url(_API_BASE, self.overseas_proxy)
        articles: list[NewsArticle] = []
        try:
            async with build_httpx_client(proxy_url=proxy or "", timeout=30.0) as client:
                resp = await client.get(_API_BASE, params=params)
                resp.raise_for_status()
                data = resp.json()

            if data.get("status") != "success":
                return FetchResult(
                    self.name, topic_name,
                    error=data.get("results", {}).get("message", "API error"),
                    elapsed_sec=time.monotonic() - t0,
                )

            # Client-side date bounds (aware datetimes)
            dt_from = (
                datetime.fromisoformat(from_date).replace(tzinfo=timezone.utc)
                if from_date else None
            )
            dt_to = (
                datetime.fromisoformat(to_date).replace(
                    hour=23, minute=59, second=59, tzinfo=timezone.utc
                )
                if to_date else None
            )

            skipped = 0
            for item in data.get("results", []):
                pub = _parse_newsdata_date(item.get("pubDate", ""))

                # Client-side date filter — only apply when date is known
                if pub:
                    if dt_from and pub < dt_from:
                        skipped += 1
                        continue
                    if dt_to and pub > dt_to:
                        skipped += 1
                        continue

                art = NewsArticle(
                    title=item.get("title", "").strip(),
                    source_url=item.get("link", ""),
                    source_name=item.get("source_name", item.get("source_id", "")),
                    published_at=pub,
                    description=(item.get("description") or "").strip(),
                    language=item.get("language", ""),
                    country=",".join(item.get("country", []) or []),
                    api_source=self.name,
                    topic_name=topic_name,
                )
                art.compute_fingerprint()
                articles.append(art)

            if skipped:
                logger.info(
                    "NewsData.io [%s]: skipped %d out-of-range articles (free plan returns last 48h)",
                    topic_name, skipped,
                )

        except Exception as exc:
            logger.error("NewsData.io fetch error: %s", exc)
            return FetchResult(
                self.name, topic_name, error=str(exc),
                elapsed_sec=time.monotonic() - t0,
            )

        logger.info("NewsData.io [%s]: fetched %d articles", topic_name, len(articles))
        return FetchResult(
            self.name, topic_name, articles=articles,
            elapsed_sec=time.monotonic() - t0,
        )
