"""Gemini Search — Google Search grounding via Gemini API.

Uses the generateContent endpoint with google_search tool to find news articles.
Automatically resolves vertexaisearch.cloud.google.com redirect URLs.
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from datetime import datetime, timezone
from typing import Sequence
from urllib.parse import urlparse

from news_monitor.models import FetchResult, NewsArticle
from news_monitor.proxy import build_httpx_client, get_proxies_for_url
from news_monitor.sources.base import NewsSource

logger = logging.getLogger("news_monitor.sources.gemini_search")

_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
_REDIRECT_PREFIX = "vertexaisearch.cloud.google.com"
_RESOLVE_PROXY = "http://127.0.0.1:18182"


class GeminiSearch(NewsSource):
    name = "gemini_search"

    async def fetch_articles(
        self,
        keywords: Sequence[str],
        countries: Sequence[str],
        languages: Sequence[str],
        time_range_hours: int = 168,
        max_articles: int = 20,
        exclude_keywords: Sequence[str] | None = None,
        topic_name: str = "",
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> FetchResult:
        t0 = time.monotonic()
        api_key = self.config.get("api_key", "") or os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            return FetchResult(self.name, topic_name, error="Missing GEMINI_API_KEY")

        query = " ".join(keywords)

        # Build date range description
        date_desc = ""
        if from_date and to_date:
            date_desc = f" published between {from_date} and {to_date}"
        elif time_range_hours <= 168:
            date_desc = " from the past week"

        # Country context
        country_en = ""
        if countries:
            country_en = countries[0].upper()

        prompt = (
            f"Search for news articles{date_desc} about: {query}\n"
            f"{'Focus on ' + country_en + '. ' if country_en else ''}"
            f"Find real articles from news outlets.\n"
            f"For each article, provide title, source, date, and a brief summary."
        )

        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "tools": [{"google_search": {}}],
        }

        url = f"{_API_URL}?key={api_key}"
        proxy = get_proxies_for_url(_API_URL, self.overseas_proxy)

        articles: list[NewsArticle] = []
        try:
            async with build_httpx_client(proxy_url=proxy or "", timeout=60.0) as client:
                resp = await client.post(url, json=body)
                if resp.status_code != 200:
                    error_text = resp.text[:200]
                    logger.error("Gemini HTTP %d: %s", resp.status_code, error_text)
                    return FetchResult(
                        self.name, topic_name,
                        error=f"HTTP {resp.status_code}: {error_text}",
                        elapsed_sec=time.monotonic() - t0,
                    )
                data = resp.json()

            # Extract from groundingMetadata
            candidates = data.get("candidates", [])
            if not candidates:
                return FetchResult(
                    self.name, topic_name, articles=[],
                    elapsed_sec=time.monotonic() - t0,
                )

            # Extract LLM text content for descriptions
            llm_text = ""
            for part in candidates[0].get("content", {}).get("parts", []):
                llm_text += part.get("text", "")

            grounding = candidates[0].get("groundingMetadata", {})
            chunks = grounding.get("groundingChunks", [])

            # Also extract grounding supports (maps text segments to URLs)
            supports = grounding.get("groundingSupports", [])
            # Build URI -> description snippets mapping
            uri_descriptions: dict[int, str] = {}
            for sup in supports:
                text_seg = sup.get("segment", {}).get("text", "").strip()
                if text_seg:
                    for ci in sup.get("groundingChunkIndices", []):
                        if ci not in uri_descriptions:
                            uri_descriptions[ci] = text_seg
                        else:
                            uri_descriptions[ci] += " " + text_seg

            # Collect raw entries
            raw_entries: list[tuple[str, str, str]] = []  # (uri, title, description)
            for i, chunk in enumerate(chunks):
                web = chunk.get("web", {})
                uri = web.get("uri", "")
                title = web.get("title", "").strip()
                desc = uri_descriptions.get(i, "")
                if uri:
                    raw_entries.append((uri, title, desc))

            # Resolve redirects in parallel
            resolved = await asyncio.gather(
                *[self._resolve_redirect(u, t) for u, t in
                  [(e[0], e[1]) for e in raw_entries]]
            )

            seen_urls: set[str] = set()
            for (real_url, title), (_, _, desc) in zip(resolved, raw_entries):
                if real_url in seen_urls:
                    continue
                seen_urls.add(real_url)
                art = NewsArticle(
                    title=title,
                    source_url=real_url,
                    source_name=urlparse(real_url).hostname or "",
                    description=desc[:300] if desc else "",
                    api_source=self.name,
                    found_by=["Gemini"],
                    topic_name=topic_name,
                    country=countries[0] if countries else "",
                )
                art.compute_fingerprint()
                articles.append(art)

        except Exception as exc:
            err_detail = f"{type(exc).__name__}: {exc!r}"
            logger.error("Gemini Search error: %s", err_detail)
            print(f"    [Gemini] {err_detail}", flush=True)
            return FetchResult(
                self.name, topic_name, error=err_detail,
                elapsed_sec=time.monotonic() - t0,
            )

        logger.info("Gemini [%s]: fetched %d articles (q=%s)", topic_name, len(articles), query[:60])
        return FetchResult(
            self.name, topic_name, articles=articles,
            elapsed_sec=time.monotonic() - t0,
        )

    async def _resolve_redirect(self, uri: str, title: str) -> tuple[str, str]:
        """Resolve vertexaisearch redirect to real URL."""
        if _REDIRECT_PREFIX not in uri:
            return uri, title
        try:
            # vertexaisearch.cloud.google.com needs direct proxy (not in _OVERSEAS_DOMAINS)
            proxy = _RESOLVE_PROXY if self.overseas_proxy else ""
            async with build_httpx_client(proxy_url=proxy, timeout=10.0) as client:
                r = await client.get(uri, follow_redirects=False)
                loc = r.headers.get("location", "")
                if loc:
                    real_host = urlparse(loc).hostname or ""
                    return loc, title or real_host
        except Exception as exc:
            logger.debug("Redirect resolve failed for %s: %s", uri[:80], exc)
        return uri, title
