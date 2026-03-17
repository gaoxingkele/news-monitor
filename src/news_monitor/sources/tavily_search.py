"""Tavily Search API — AI-native news search with rich content extraction.

Uses topic="news" mode for better news coverage.
Returns richer content snippets than traditional search APIs.
"""
from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone
from typing import Sequence
from urllib.parse import urlparse

from news_monitor.models import FetchResult, NewsArticle
from news_monitor.proxy import build_httpx_client, get_proxies_for_url
from news_monitor.sources.base import NewsSource

logger = logging.getLogger("news_monitor.sources.tavily_search")

_API_URL = "https://api.tavily.com/search"


class TavilySearch(NewsSource):
    """Tavily Search — AI-native search with news topic mode."""
    name = "tavily_search"

    async def fetch_articles(
        self,
        keywords: Sequence[str],
        countries: Sequence[str],
        languages: Sequence[str],
        time_range_hours: int = 168,
        max_articles: int = 10,
        exclude_keywords: Sequence[str] | None = None,
        topic_name: str = "",
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> FetchResult:
        t0 = time.monotonic()
        api_key = (self.config.get("api_key", "")
                   or os.environ.get("TAVILY_API_KEY", "")
                   or os.environ.get("TAVILYAPI", ""))
        if not api_key:
            return FetchResult(self.name, topic_name, error="Missing TAVILY_API_KEY")

        query = " ".join(keywords)

        # Append exclude keywords
        if exclude_keywords:
            excludes = " ".join(f"-{kw}" for kw in list(exclude_keywords)[:5])
            query = f"{query} {excludes}"

        # Map time_range_hours to days parameter
        days = max(1, time_range_hours // 24)
        if days > 30:
            days = 30  # Tavily max

        # Build request body
        body: dict = {
            "api_key": api_key,
            "query": query,
            "topic": "news",
            "search_depth": "basic",
            "max_results": min(max_articles, 20),
            "days": days,
            "include_answer": False,
            "include_raw_content": False,
        }

        # Exclude blocked domains
        exclude_domains = list(self.config.get("exclude_domains", []))
        if exclude_domains:
            body["exclude_domains"] = exclude_domains[:50]

        proxy = get_proxies_for_url(_API_URL, self.overseas_proxy)
        articles: list[NewsArticle] = []

        try:
            async with build_httpx_client(proxy_url=proxy or "", timeout=30.0) as client:
                resp = await client.post(
                    _API_URL,
                    json=body,
                    headers={"Content-Type": "application/json"},
                )
                if resp.status_code != 200:
                    error_text = resp.text[:200]
                    logger.error("Tavily HTTP %d: %s", resp.status_code, error_text)
                    return FetchResult(
                        self.name, topic_name,
                        error=f"HTTP {resp.status_code}: {error_text}",
                        elapsed_sec=time.monotonic() - t0,
                    )
                data = resp.json()

            for item in data.get("results", []):
                title = (item.get("title") or "").strip()
                url = item.get("url") or ""
                # Tavily's content field is richer than typical snippets
                content = (item.get("content") or "").strip()

                if not title or not url:
                    continue

                # Parse published_date if available
                pub = None
                pub_str = item.get("published_date") or ""
                if pub_str:
                    for fmt in (
                        "%Y-%m-%dT%H:%M:%S",
                        "%Y-%m-%dT%H:%M:%S.%fZ",
                        "%Y-%m-%dT%H:%M:%SZ",
                        "%Y-%m-%d",
                    ):
                        try:
                            pub = datetime.strptime(pub_str[:25], fmt)
                            if pub.tzinfo is None:
                                pub = pub.replace(tzinfo=timezone.utc)
                            break
                        except ValueError:
                            continue

                art = NewsArticle(
                    title=title,
                    source_url=url,
                    source_name=urlparse(url).hostname or "",
                    published_at=pub,
                    description=content,
                    language=languages[0] if languages else "",
                    country=countries[0] if countries else "",
                    api_source=self.name,
                    found_by=["Tavily"],
                    topic_name=topic_name,
                )
                art.compute_fingerprint()
                articles.append(art)

        except Exception as exc:
            err_detail = f"{type(exc).__name__}: {exc!r}"
            logger.error("Tavily Search error: %s", err_detail)
            return FetchResult(
                self.name, topic_name, error=err_detail,
                elapsed_sec=time.monotonic() - t0,
            )

        logger.info(
            "Tavily [%s]: fetched %d articles (q=%s)",
            topic_name, len(articles), query[:60],
        )
        return FetchResult(
            self.name, topic_name, articles=articles,
            elapsed_sec=time.monotonic() - t0,
        )
