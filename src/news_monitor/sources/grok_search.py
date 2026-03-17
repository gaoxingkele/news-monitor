"""Grok Search — web_search and x_search via xAI Responses API.

Uses the /v1/responses endpoint with server-side tools.
Default model: grok-3-mini-fast (cost-effective for search tasks).
"""
from __future__ import annotations

import logging
import os
import re
import time
from typing import Sequence
from urllib.parse import urlparse

from news_monitor.models import FetchResult, NewsArticle
from news_monitor.proxy import build_httpx_client, get_proxies_for_url
from news_monitor.sources.base import NewsSource

logger = logging.getLogger("news_monitor.sources.grok_search")

_API_URL = "https://api.x.ai/v1/responses"
_MODEL = "grok-4-1-fast-non-reasoning"


class GrokWebSearch(NewsSource):
    """Grok web_search — finds news articles from the web."""
    name = "grok_web_search"

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
        return await _fetch_grok(
            config=self.config,
            overseas_proxy=self.overseas_proxy,
            keywords=keywords,
            countries=countries,
            time_range_hours=time_range_hours,
            max_articles=max_articles,
            topic_name=topic_name,
            from_date=from_date,
            to_date=to_date,
            search_type="web_search",
            source_name=self.name,
            found_by_label="Grok",
        )

    async def fetch_articles_batch(
        self,
        query_groups: list[list[str]],
        countries: Sequence[str],
        languages: Sequence[str],
        time_range_hours: int = 168,
        max_articles: int = 20,
        topic_name: str = "",
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> FetchResult:
        return await _fetch_grok_batch(
            config=self.config,
            overseas_proxy=self.overseas_proxy,
            query_groups=query_groups,
            countries=countries,
            time_range_hours=time_range_hours,
            max_articles=max_articles,
            topic_name=topic_name,
            from_date=from_date,
            to_date=to_date,
            search_type="web_search",
            source_name=self.name,
            found_by_label="Grok",
        )


class GrokXSearch(NewsSource):
    """Grok x_search — finds posts and discussions on X/Twitter."""
    name = "grok_x_search"

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
        return await _fetch_grok(
            config=self.config,
            overseas_proxy=self.overseas_proxy,
            keywords=keywords,
            countries=countries,
            time_range_hours=time_range_hours,
            max_articles=max_articles,
            topic_name=topic_name,
            from_date=from_date,
            to_date=to_date,
            search_type="x_search",
            source_name=self.name,
            found_by_label="Grok",
        )

    async def fetch_articles_batch(
        self,
        query_groups: list[list[str]],
        countries: Sequence[str],
        languages: Sequence[str],
        time_range_hours: int = 168,
        max_articles: int = 20,
        topic_name: str = "",
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> FetchResult:
        return await _fetch_grok_batch(
            config=self.config,
            overseas_proxy=self.overseas_proxy,
            query_groups=query_groups,
            countries=countries,
            time_range_hours=time_range_hours,
            max_articles=max_articles,
            topic_name=topic_name,
            from_date=from_date,
            to_date=to_date,
            search_type="x_search",
            source_name=self.name,
            found_by_label="Grok",
        )


async def _fetch_grok(
    *,
    config: dict,
    overseas_proxy: str,
    keywords: Sequence[str],
    countries: Sequence[str],
    time_range_hours: int,
    max_articles: int,
    topic_name: str,
    from_date: str | None,
    to_date: str | None,
    search_type: str,
    source_name: str,
    found_by_label: str,
) -> FetchResult:
    """Shared implementation for Grok web_search and x_search."""
    t0 = time.monotonic()
    api_key = config.get("api_key", "") or os.environ.get("GROK_API_KEY", "")
    if not api_key:
        return FetchResult(source_name, topic_name, error="Missing GROK_API_KEY")

    query = " ".join(keywords)

    # Date context
    date_desc = ""
    if from_date and to_date:
        date_desc = f" between {from_date} and {to_date}"
    elif time_range_hours <= 168:
        date_desc = " from the past week"

    country_en = countries[0].upper() if countries else ""

    if search_type == "x_search":
        prompt = (
            f"Search X/Twitter for posts and discussions{date_desc} about: {query}\n"
            f"{'Focus on ' + country_en + '. ' if country_en else ''}"
            f"Find tweets from journalists, officials, news outlets.\n"
            f"For each post, provide the key content, author, date, and any linked article URL."
        )
    else:
        prompt = (
            f"Search for news articles{date_desc} about: {query}\n"
            f"{'Focus on ' + country_en + '. ' if country_en else ''}"
            f"Find real articles from news outlets.\n"
            f"For each article, provide title, source, date, and a brief summary."
        )

    body = {
        "model": config.get("model", _MODEL),
        "input": prompt,
        "tools": [{"type": search_type}],
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    proxy = get_proxies_for_url(_API_URL, overseas_proxy)
    articles: list[NewsArticle] = []

    try:
        async with build_httpx_client(proxy_url=proxy or "", timeout=120.0) as client:
            resp = await client.post(_API_URL, json=body, headers=headers)
            if resp.status_code != 200:
                error_text = resp.text[:200]
                logger.error("Grok %s HTTP %d: %s", search_type, resp.status_code, error_text)
                return FetchResult(
                    source_name, topic_name,
                    error=f"HTTP {resp.status_code}: {error_text}",
                    elapsed_sec=time.monotonic() - t0,
                )
            data = resp.json()

        # Parse output array — two formats:
        # Legacy: search_call_result with results[] (title, url, snippet)
        # Current: web_search_call + message with url_citation annotations
        output_items = data.get("output", [])
        seen_urls: set[str] = set()
        url_meta: dict[str, dict] = {}  # url -> {title, description}

        def _add_url(url: str, title: str = "", description: str = "") -> None:
            if not url:
                return
            if url in url_meta:
                if title and not url_meta[url].get("title"):
                    url_meta[url]["title"] = title
                if description and not url_meta[url].get("description"):
                    url_meta[url]["description"] = description
                return
            url_meta[url] = {"title": title, "description": description}

        # Pass 1: legacy search_call_result (if present)
        for item in output_items:
            item_type = item.get("type", "")
            if item_type == "search_call_result":
                for result in item.get("results", []):
                    _add_url(
                        result.get("url", ""),
                        result.get("title", "").strip(),
                        result.get("snippet", "").strip() or result.get("description", "").strip(),
                    )
            if item_type == "web_search_call":
                action = item.get("action", {})
                if action.get("type") == "open_page":
                    _add_url(action.get("url", ""))

        # Pass 2: extract url_citations from message annotations
        # The annotation title is often just a number ("1", "2"...).
        # Real context is in the message text around each citation.
        for item in output_items:
            if item.get("type") != "message":
                continue
            for content_block in item.get("content", []):
                block_text = content_block.get("text", "")
                annotations = content_block.get("annotations", [])
                for ann in annotations:
                    ann_url = ann.get("url", "")
                    if not ann_url:
                        continue
                    ann_title = ann.get("title", "").strip()
                    # Extract context: find the sentence/paragraph before this citation
                    start_idx = ann.get("start_index", 0)
                    context_title = ""
                    if block_text and start_idx > 0:
                        # Look backwards from citation to find descriptive text
                        before = block_text[:start_idx].rstrip()
                        before = re.sub(r'\[\[\d+\]\]\([^)]*\)\s*$', '', before).rstrip()
                        # Find the last sentence or bold header
                        # Try to find **bold header** first
                        bold_match = re.search(r'\*\*([^*]+)\*\*[^*]*$', before)
                        if bold_match:
                            context_title = bold_match.group(1).strip()
                        else:
                            # Take last sentence (after last period/newline)
                            for sep in ['\n', '. ', '。']:
                                pos = before.rfind(sep)
                                if pos >= 0:
                                    context_title = before[pos+len(sep):].strip()
                                    break
                            if not context_title:
                                context_title = before[-150:].strip()
                        # Clean up markdown
                        context_title = re.sub(r'\*+', '', context_title).strip()
                        context_title = re.sub(r'\[+\d+\]+', '', context_title).strip()
                        if len(context_title) > 150:
                            context_title = context_title[:150]
                    # Use context_title if ann_title is just a number
                    real_title = ann_title
                    if not real_title or real_title.isdigit() or len(real_title) < 5:
                        real_title = context_title
                    _add_url(ann_url, real_title, "")

        # Build articles from collected URL metadata
        for url, meta in url_meta.items():
            if url in seen_urls:
                continue
            seen_urls.add(url)
            raw_title = meta.get("title", "").strip()
            raw_desc = meta.get("description", "").strip()
            if not raw_title or raw_title.isdigit() or len(raw_title) < 5:
                if raw_desc and len(raw_desc) >= 10:
                    raw_title = raw_desc[:120]
                    raw_desc = ""
                else:
                    continue
            art = NewsArticle(
                title=raw_title,
                source_url=url,
                source_name=urlparse(url).hostname or "",
                description=raw_desc,
                api_source=source_name,
                found_by=[found_by_label],
                topic_name=topic_name,
                country=countries[0] if countries else "",
            )
            art.compute_fingerprint()
            articles.append(art)

    except Exception as exc:
        err_detail = f"{type(exc).__name__}: {exc!r}"
        logger.error("Grok %s error: %s", search_type, err_detail)
        print(f"\033[91m    [Grok {search_type}] {err_detail}\033[0m", flush=True)
        return FetchResult(
            source_name, topic_name, error=err_detail,
            elapsed_sec=time.monotonic() - t0,
        )

    logger.info(
        "Grok %s [%s]: fetched %d articles (q=%s)",
        search_type, topic_name, len(articles), query[:60],
    )
    return FetchResult(
        source_name, topic_name, articles=articles,
        elapsed_sec=time.monotonic() - t0,
    )


async def _fetch_grok_batch(
    *,
    config: dict,
    overseas_proxy: str,
    query_groups: list[list[str]],
    countries: Sequence[str],
    time_range_hours: int,
    max_articles: int,
    topic_name: str,
    from_date: str | None,
    to_date: str | None,
    search_type: str,
    source_name: str,
    found_by_label: str,
) -> FetchResult:
    """Batch variant: merge multiple query groups into a single API call."""
    t0 = time.monotonic()
    api_key = config.get("api_key", "") or os.environ.get("GROK_API_KEY", "")
    if not api_key:
        return FetchResult(source_name, topic_name, error="Missing GROK_API_KEY")

    # Build merged query list
    queries = [" ".join(kw) for kw in query_groups]

    # Date context
    date_desc = ""
    if from_date and to_date:
        date_desc = f" between {from_date} and {to_date}"
    elif time_range_hours <= 168:
        date_desc = " from the past week"

    country_en = countries[0].upper() if countries else ""

    # Build numbered topic list
    topic_lines = "\n".join(f"{i+1}. {q}" for i, q in enumerate(queries))

    if search_type == "x_search":
        prompt = (
            f"Search X/Twitter for posts and discussions{date_desc}.\n"
            f"{'Focus on ' + country_en + '. ' if country_en else ''}"
            f"Search for ALL of the following topics separately:\n\n"
            f"{topic_lines}\n\n"
            f"For each topic, find tweets from journalists, officials, news outlets.\n"
            f"Provide the key content, author, date, and any linked article URL for each post."
        )
    else:
        prompt = (
            f"Search for news articles{date_desc}.\n"
            f"{'Focus on ' + country_en + '. ' if country_en else ''}"
            f"Search for ALL of the following topics separately:\n\n"
            f"{topic_lines}\n\n"
            f"For each topic, find real articles from news outlets.\n"
            f"Provide title, source, date, and a brief summary for each article."
        )

    body = {
        "model": config.get("model", _MODEL),
        "input": prompt,
        "tools": [{"type": search_type}],
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    proxy = get_proxies_for_url(_API_URL, overseas_proxy)
    articles: list[NewsArticle] = []

    try:
        async with build_httpx_client(proxy_url=proxy or "", timeout=180.0) as client:
            resp = await client.post(_API_URL, json=body, headers=headers)
            if resp.status_code != 200:
                error_text = resp.text[:200]
                logger.error("Grok %s batch HTTP %d: %s", search_type, resp.status_code, error_text)
                return FetchResult(
                    source_name, topic_name,
                    error=f"HTTP {resp.status_code}: {error_text}",
                    elapsed_sec=time.monotonic() - t0,
                )
            data = resp.json()

        # Reuse the same parsing logic as single-query
        output_items = data.get("output", [])
        seen_urls: set[str] = set()
        url_meta: dict[str, dict] = {}

        def _add_url(url: str, title: str = "", description: str = "") -> None:
            if not url:
                return
            if url in url_meta:
                if title and not url_meta[url].get("title"):
                    url_meta[url]["title"] = title
                if description and not url_meta[url].get("description"):
                    url_meta[url]["description"] = description
                return
            url_meta[url] = {"title": title, "description": description}

        for item in output_items:
            item_type = item.get("type", "")
            if item_type == "search_call_result":
                for result in item.get("results", []):
                    _add_url(
                        result.get("url", ""),
                        result.get("title", "").strip(),
                        result.get("snippet", "").strip() or result.get("description", "").strip(),
                    )
            if item_type == "web_search_call":
                action = item.get("action", {})
                if action.get("type") == "open_page":
                    _add_url(action.get("url", ""))

        for item in output_items:
            if item.get("type") != "message":
                continue
            for content_block in item.get("content", []):
                block_text = content_block.get("text", "")
                annotations = content_block.get("annotations", [])
                for ann in annotations:
                    ann_url = ann.get("url", "")
                    if not ann_url:
                        continue
                    ann_title = ann.get("title", "").strip()
                    start_idx = ann.get("start_index", 0)
                    context_title = ""
                    if block_text and start_idx > 0:
                        before = block_text[:start_idx].rstrip()
                        before = re.sub(r'\[\[\d+\]\]\([^)]*\)\s*$', '', before).rstrip()
                        bold_match = re.search(r'\*\*([^*]+)\*\*[^*]*$', before)
                        if bold_match:
                            context_title = bold_match.group(1).strip()
                        else:
                            for sep in ['\n', '. ', '。']:
                                pos = before.rfind(sep)
                                if pos >= 0:
                                    context_title = before[pos+len(sep):].strip()
                                    break
                            if not context_title:
                                context_title = before[-150:].strip()
                        context_title = re.sub(r'\*+', '', context_title).strip()
                        context_title = re.sub(r'\[+\d+\]+', '', context_title).strip()
                        if len(context_title) > 150:
                            context_title = context_title[:150]
                    real_title = ann_title
                    if not real_title or real_title.isdigit() or len(real_title) < 5:
                        real_title = context_title
                    _add_url(ann_url, real_title, "")

        for url, meta in url_meta.items():
            if url in seen_urls:
                continue
            seen_urls.add(url)
            raw_title = meta.get("title", "").strip()
            raw_desc = meta.get("description", "").strip()
            if not raw_title or raw_title.isdigit() or len(raw_title) < 5:
                if raw_desc and len(raw_desc) >= 10:
                    raw_title = raw_desc[:120]
                    raw_desc = ""
                else:
                    continue
            art = NewsArticle(
                title=raw_title,
                source_url=url,
                source_name=urlparse(url).hostname or "",
                description=raw_desc,
                api_source=source_name,
                found_by=[found_by_label],
                topic_name=topic_name,
                country=countries[0] if countries else "",
            )
            art.compute_fingerprint()
            articles.append(art)

    except Exception as exc:
        err_detail = f"{type(exc).__name__}: {exc!r}"
        logger.error("Grok %s batch error: %s", search_type, err_detail)
        print(f"\033[91m    [Grok {search_type} batch] {err_detail}\033[0m", flush=True)
        return FetchResult(
            source_name, topic_name, error=err_detail,
            elapsed_sec=time.monotonic() - t0,
        )

    logger.info(
        "Grok %s batch [%s]: fetched %d articles from %d queries in 1 API call",
        search_type, topic_name, len(articles), len(queries),
    )
    return FetchResult(
        source_name, topic_name, articles=articles,
        elapsed_sec=time.monotonic() - t0,
    )
