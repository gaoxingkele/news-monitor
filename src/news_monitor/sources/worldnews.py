"""World News API — geo-search with 210+ countries."""
from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Sequence

import httpx

from news_monitor.models import FetchResult, NewsArticle
from news_monitor.proxy import get_proxies_for_url
from news_monitor.sources.base import NewsSource

logger = logging.getLogger("news_monitor.sources.worldnews")

_API_BASE = "https://api.worldnewsapi.com/search-news"

# World News API uses full language names
_LANG_MAP = {
    "es": "es", "en": "en", "zh": "zh",
    "pt": "pt", "fr": "fr", "de": "de",
}


class WorldNewsSource(NewsSource):
    name = "worldnews"

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

        now = datetime.now(timezone.utc)
        earliest = (now - timedelta(hours=time_range_hours)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        query = " OR ".join(keywords)

        params: dict = {
            "text": query,
            "language": ",".join(_LANG_MAP.get(l, l) for l in languages),
            "earliest-publish-date": earliest,
            "number": min(max_articles, self.config.get("max_results_per_query", 50)),
            "sort": "publish-time",
            "sort-direction": "DESC",
        }
        if countries:
            # World News API uses ISO 3166-1 alpha-2 uppercased
            params["source-countries"] = ",".join(c.upper() for c in countries)

        proxy = get_proxies_for_url(_API_BASE, self.overseas_proxy)
        articles: list[NewsArticle] = []
        try:
            client_kwargs = {
                "timeout": 30.0,
                "follow_redirects": True,
                "trust_env": False,
            }
            if proxy:
                client_kwargs["proxy"] = proxy
            async with httpx.AsyncClient(**client_kwargs) as client:
                resp = await client.get(
                    _API_BASE, params=params,
                    headers={"x-api-key": api_key},
                )
                resp.raise_for_status()
                data = resp.json()

            for item in data.get("news", []):
                pub = None
                if item.get("publish_date"):
                    try:
                        pub = datetime.fromisoformat(item["publish_date"])
                    except (ValueError, TypeError):
                        pass
                art = NewsArticle(
                    title=item.get("title", "").strip(),
                    source_url=item.get("url", ""),
                    source_name=item.get("source_country", ""),
                    published_at=pub,
                    description=(item.get("text") or "")[:500].strip(),
                    language=item.get("language", ""),
                    country=item.get("source_country", ""),
                    api_source=self.name,
                    topic_name=topic_name,
                )
                art.compute_fingerprint()
                articles.append(art)

        except Exception as exc:
            logger.error("World News API fetch error: %s", exc)
            return FetchResult(
                self.name, topic_name, error=str(exc),
                elapsed_sec=time.monotonic() - t0,
            )

        logger.info("WorldNews [%s]: fetched %d articles", topic_name, len(articles))
        return FetchResult(
            self.name, topic_name, articles=articles,
            elapsed_sec=time.monotonic() - t0,
        )
