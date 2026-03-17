"""SerpAPI Google News — regional Google News aggregation."""
from __future__ import annotations

import logging
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Sequence

from news_monitor.models import FetchResult, NewsArticle
from news_monitor.proxy import get_proxies_for_url, build_httpx_client
from news_monitor.sources.base import NewsSource

logger = logging.getLogger("news_monitor.sources.serpapi_google")

_API_BASE = "https://serpapi.com/search.json"

# SerpAPI Google News language/country codes
_GL_MAP = {
    # North America
    "us": "us", "mx": "mx", "ca": "ca",
    # Central America
    "gt": "gt", "bz": "bz", "sv": "sv", "hn": "hn", "ni": "ni", "cr": "cr", "pa": "pa",
    # Caribbean
    "cu": "cu", "ht": "ht", "do": "do",
    # South America
    "co": "co", "ve": "ve", "gy": "gy", "sr": "sr", "br": "br", "ec": "ec",
    "pe": "pe", "bo": "bo", "cl": "cl", "ar": "ar", "uy": "uy", "py": "py",
    # Asia/Pacific
    "tw": "tw", "cn": "cn", "jp": "jp", "kr": "kr", "ph": "ph", "au": "au",
    "sb": "sb", "ki": "ki", "nr": "nr",
    # Africa
    "bf": "bf", "st": "st",
}
_HL_MAP = {"es": "es", "en": "en", "zh": "zh-TW", "pt": "pt", "fr": "fr", "ja": "ja"}

# Relative-date patterns returned by SerpAPI, e.g. "2 days ago", "1 week ago"
_REL_DATE_RE = re.compile(
    r"(\d+)\s+(second|minute|hour|day|week|month)s?\s+ago", re.IGNORECASE
)
_REL_UNITS_SEC = {
    "second": 1, "minute": 60, "hour": 3600,
    "day": 86400, "week": 604800, "month": 2592000,
}


_STRPTIME_FMTS = [
    "%b %d, %Y",    # Mar 5, 2026
    "%B %d, %Y",    # March 5, 2026
    "%b %d %Y",     # Mar 5 2026
    "%B %d %Y",     # March 5 2026
    "%Y-%m-%d",     # 2026-03-05
    "%m/%d/%Y",     # 03/05/2026
    "%d/%m/%Y",     # 05/03/2026
]


def _parse_serpapi_date(date_str: str) -> datetime | None:
    """Parse SerpAPI date strings (relative or absolute) to aware datetime."""
    if not date_str:
        return None
    s = date_str.strip()
    now = datetime.now(timezone.utc)

    # Handle "X units ago"
    m = _REL_DATE_RE.match(s)
    if m:
        n, unit = int(m.group(1)), m.group(2).lower()
        return now - timedelta(seconds=n * _REL_UNITS_SEC.get(unit, 86400))

    # strptime with common absolute formats (no external dependency)
    for fmt in _STRPTIME_FMTS:
        try:
            parsed = datetime.strptime(s, fmt)
            return parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    # Try dateutil for unusual formats
    try:
        from dateutil import parser as du_parser  # type: ignore
        parsed = du_parser.parse(s, default=now)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except Exception:
        pass

    # fromisoformat last resort
    try:
        parsed = datetime.fromisoformat(s)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except (ValueError, TypeError):
        return None


def _to_serpapi_date(iso_date: str) -> str:
    """Convert YYYY-MM-DD to MM/DD/YYYY required by SerpAPI cdr filter."""
    y, mo, d = iso_date.split("-")
    return f"{mo}/{d}/{y}"


class SerpAPIGoogle(NewsSource):
    name = "serpapi_google"

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

        query = " OR ".join(keywords)
        if exclude_keywords:
            query += " " + " ".join(f'-"{ew}"' for ew in exclude_keywords)

        gl = _GL_MAP.get(countries[0], "us") if countries else "us"
        hl = _HL_MAP.get(languages[0], "en") if languages else "en"

        # Prefer exact date range (cdr) over relative range (qdr)
        if from_date and to_date:
            tbs = f"cdr:1,cd_min:{_to_serpapi_date(from_date)},cd_max:{_to_serpapi_date(to_date)}"
        elif time_range_hours <= 24:
            tbs = "qdr:d"
        elif time_range_hours <= 168:
            tbs = "qdr:w"
        else:
            tbs = "qdr:m"

        params = {
            "engine": "google_news",
            "q": query,
            "gl": gl,
            "hl": hl,
            "tbs": tbs,
            "api_key": api_key,
        }

        # Date bounds for client-side filtering (aware datetimes)
        dt_from = (
            datetime.fromisoformat(from_date).replace(tzinfo=timezone.utc)
            if from_date else None
        )
        dt_to = (
            datetime.fromisoformat(to_date).replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
            if to_date else None
        )

        proxy = get_proxies_for_url(_API_BASE, self.overseas_proxy)
        articles: list[NewsArticle] = []
        skipped = 0
        try:
            async with build_httpx_client(proxy_url=proxy or "", timeout=30.0) as client:
                resp = await client.get(_API_BASE, params=params)
                resp.raise_for_status()
                data = resp.json()

            for item in data.get("news_results", [])[:max_articles]:
                pub = _parse_serpapi_date(item.get("date", ""))

                # Client-side date filter
                if pub and dt_from and pub < dt_from:
                    skipped += 1
                    continue
                if pub and dt_to and pub > dt_to:
                    skipped += 1
                    continue

                art = NewsArticle(
                    title=item.get("title", "").strip(),
                    source_url=item.get("link", ""),
                    source_name=item.get("source", {}).get("name", ""),
                    published_at=pub,
                    description=(item.get("snippet") or "").strip(),
                    language=hl,
                    country=gl,
                    api_source=self.name,
                    topic_name=topic_name,
                )
                art.compute_fingerprint()
                articles.append(art)

        except Exception as exc:
            logger.error("SerpAPI fetch error: %s", exc)
            return FetchResult(
                self.name, topic_name, error=str(exc),
                elapsed_sec=time.monotonic() - t0,
            )

        if skipped:
            logger.info("SerpAPI [%s]: skipped %d out-of-range articles", topic_name, skipped)
        logger.info("SerpAPI [%s]: fetched %d articles (tbs=%s)", topic_name, len(articles), tbs)
        return FetchResult(
            self.name, topic_name, articles=articles,
            elapsed_sec=time.monotonic() - t0,
        )
