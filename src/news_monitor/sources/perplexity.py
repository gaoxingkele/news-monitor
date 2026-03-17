"""Perplexity Sonar — AI-powered news search with web grounding."""
from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime, timezone
from typing import Sequence

import httpx

from news_monitor.models import FetchResult, NewsArticle
from news_monitor.proxy import get_proxies_for_url, build_httpx_client
from news_monitor.sources.base import NewsSource

logger = logging.getLogger("news_monitor.sources.perplexity")

_API_BASE = "https://api.perplexity.ai/chat/completions"

# Map time_range_hours to Perplexity's recency filter
def _recency_filter(hours: int) -> str:
    if hours <= 24:
        return "day"
    if hours <= 168:
        return "week"
    return "month"


class PerplexitySource(NewsSource):
    name = "perplexity"

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
        api_key = self.config.get("api_key", "")
        if not api_key:
            return FetchResult(self.name, topic_name, error="Missing api_key")

        model = self.config.get("model", "sonar")
        countries_str = ", ".join(countries) if countries else "global"
        keywords_str = " ".join(keywords)
        cap = min(max_articles, 10)

        date_hint = ""
        if from_date and to_date:
            date_hint = f" Date range: {from_date} to {to_date}."

        exclude_hint = ""
        if exclude_keywords:
            exclude_hint = f" Exclude topics: {', '.join(exclude_keywords)}."

        prompt = (
            f"Search for recent news articles about: {keywords_str}. "
            f"Focus on country/region: {countries_str}.{date_hint}{exclude_hint} "
            f"Return up to {cap} real news articles with VALID, WORKING URLs. "
            f"Each result must be a real published article, not a summary you generate. "
            f'Return a JSON array of objects with fields: '
            f'"title" (original language), "url" (direct article URL), '
            f'"source" (publisher name), "date" (YYYY-MM-DD), '
            f'"summary" (2-3 sentence summary in original language), '
            f'"language" (ISO 639-1 code like "es", "en", "zh"). '
            f"Return ONLY the JSON array, no other text."
        )

        body = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "return_citations": True,
            "search_recency_filter": _recency_filter(time_range_hours),
        }

        proxy = get_proxies_for_url(_API_BASE, self.overseas_proxy)
        articles: list[NewsArticle] = []
        try:
            async with build_httpx_client(proxy_url=proxy or "", timeout=60.0) as client:
                resp = await client.post(
                    _API_BASE, json=body,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                )
                resp.raise_for_status()
                data = resp.json()

            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            citations = data.get("citations", [])

            # Strip markdown code fences if present
            text = content.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

            try:
                items = json.loads(text)
            except json.JSONDecodeError:
                # Fall back: create a single article from the whole response
                items = []
                if content.strip():
                    art = NewsArticle(
                        title=f"[Perplexity Summary] {keywords_str[:80]}",
                        source_url=citations[0] if citations else "",
                        source_name="Perplexity",
                        published_at=datetime.now(timezone.utc),
                        description=content[:1000].strip(),
                        language="en",
                        api_source=self.name,
                        topic_name=topic_name,
                    )
                    art.compute_fingerprint()
                    articles.append(art)

            for item in items[:max_articles]:
                if not isinstance(item, dict):
                    continue

                # Parse date
                pub = None
                date_str = item.get("date") or ""
                if date_str:
                    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"):
                        try:
                            pub = datetime.strptime(date_str, fmt).replace(tzinfo=timezone.utc)
                            break
                        except ValueError:
                            continue

                lang = item.get("language") or "en"
                art = NewsArticle(
                    title=(item.get("title") or "").strip(),
                    source_url=item.get("url") or "",
                    source_name=item.get("source") or "Perplexity",
                    published_at=pub or datetime.now(timezone.utc),
                    description=(item.get("summary") or "").strip(),
                    language=lang,
                    country=countries[0] if countries else "",
                    api_source=self.name,
                    topic_name=topic_name,
                )
                art.compute_fingerprint()
                articles.append(art)

        except Exception as exc:
            logger.error("Perplexity fetch error: %s", exc)
            return FetchResult(
                self.name, topic_name, error=str(exc),
                elapsed_sec=time.monotonic() - t0,
            )

        logger.info("Perplexity [%s]: fetched %d articles", topic_name, len(articles))
        return FetchResult(
            self.name, topic_name, articles=articles,
            elapsed_sec=time.monotonic() - t0,
        )
