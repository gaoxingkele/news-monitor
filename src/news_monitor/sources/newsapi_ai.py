"""NewsAPI.ai (Event Registry) — entity-level search with built-in dedup."""
from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Sequence

import httpx

from news_monitor.models import FetchResult, NewsArticle
from news_monitor.proxy import get_proxies_for_url, build_httpx_client
from news_monitor.sources.base import NewsSource

logger = logging.getLogger("news_monitor.sources.newsapi_ai")

_API_BASE = "https://eventregistry.org/api/v1/article/getArticles"

# Country code → EventRegistry conceptUri (Wikipedia entity)
_COUNTRY_CONCEPTS: dict[str, str] = {
    "uy": "http://en.wikipedia.org/wiki/Uruguay",
    "mx": "http://en.wikipedia.org/wiki/Mexico",
    "co": "http://en.wikipedia.org/wiki/Colombia",
    "ar": "http://en.wikipedia.org/wiki/Argentina",
    "br": "http://en.wikipedia.org/wiki/Brazil",
    "cl": "http://en.wikipedia.org/wiki/Chile",
    "pe": "http://en.wikipedia.org/wiki/Peru",
    "ve": "http://en.wikipedia.org/wiki/Venezuela",
    "ec": "http://en.wikipedia.org/wiki/Ecuador",
    "bo": "http://en.wikipedia.org/wiki/Bolivia",
    "py": "http://en.wikipedia.org/wiki/Paraguay",
    "gy": "http://en.wikipedia.org/wiki/Guyana",
    "sr": "http://en.wikipedia.org/wiki/Suriname",
    "gt": "http://en.wikipedia.org/wiki/Guatemala",
    "bz": "http://en.wikipedia.org/wiki/Belize",
    "sv": "http://en.wikipedia.org/wiki/El_Salvador",
    "hn": "http://en.wikipedia.org/wiki/Honduras",
    "ni": "http://en.wikipedia.org/wiki/Nicaragua",
    "cr": "http://en.wikipedia.org/wiki/Costa_Rica",
    "pa": "http://en.wikipedia.org/wiki/Panama",
    "do": "http://en.wikipedia.org/wiki/Dominican_Republic",
    "ht": "http://en.wikipedia.org/wiki/Haiti",
    "sb": "http://en.wikipedia.org/wiki/Solomon_Islands",
    "ki": "http://en.wikipedia.org/wiki/Kiribati",
    "nr": "http://en.wikipedia.org/wiki/Nauru",
    "bf": "http://en.wikipedia.org/wiki/Burkina_Faso",
    "sz": "http://en.wikipedia.org/wiki/Eswatini",
    "va": "http://en.wikipedia.org/wiki/Vatican_City",
    "tw": "http://en.wikipedia.org/wiki/Taiwan",
    "cn": "http://en.wikipedia.org/wiki/China",
    "us": "http://en.wikipedia.org/wiki/United_States",
}


def _split_keywords(query: str) -> list[str]:
    """Split a multi-word query string into individual search terms.

    EventRegistry treats each keyword item as a phrase match.
    'China Uruguay inversión comercio' → ['China', 'Uruguay', 'inversión', 'comercio']

    However, quoted phrases like '"Estados Unidos"' should stay intact.
    'site:xxx' queries are skipped (not supported by EventRegistry).
    """
    import re

    # Skip site: queries — not supported
    if query.strip().startswith("site:"):
        return []

    # Extract quoted phrases first
    tokens: list[str] = []
    remaining = query
    for match in re.finditer(r'"([^"]+)"', query):
        tokens.append(match.group(1))
    remaining = re.sub(r'"[^"]+"', '', remaining)

    # Split remaining by whitespace, filter noise
    _NOISE = {"NOT", "AND", "OR", "y", "a", "de", "del", "la", "el", "en", "con", "por", "para", "las", "los", "un", "una"}
    for word in remaining.split():
        word = word.strip()
        if word and word not in _NOISE and len(word) > 1:
            tokens.append(word)

    return tokens


class NewsAPIAI(NewsSource):
    name = "newsapi_ai"

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

        # Language mapping: NewsAPI.ai uses 3-letter codes
        lang_map = {
            "es": "spa", "en": "eng", "zh": "zho",
            "pt": "por", "fr": "fra", "de": "deu",
        }
        langs = [lang_map.get(l, l) for l in languages]

        now = datetime.now(timezone.utc)
        date_start = from_date or (now - timedelta(hours=time_range_hours)).strftime("%Y-%m-%d")
        date_end = to_date or now.strftime("%Y-%m-%d")

        # Split multi-word query into individual keywords
        raw_kw = list(keywords)
        split_kw = []
        for kw in raw_kw:
            split_kw.extend(_split_keywords(kw))

        if not split_kw:
            return FetchResult(
                self.name, topic_name, articles=[],
                elapsed_sec=time.monotonic() - t0,
            )

        # Deduplicate while preserving order
        seen: set[str] = set()
        unique_kw: list[str] = []
        for w in split_kw:
            low = w.lower()
            if low not in seen:
                seen.add(low)
                unique_kw.append(w)

        # Separate country names from topic keywords
        _COUNTRY_KEYWORDS = {
            "china", "uruguay", "taiwan", "méxico", "colombia", "argentina",
            "brasil", "chile", "perú", "venezuela", "ecuador", "bolivia",
            "paraguay", "guyana", "suriname", "guatemala", "belice", "panamá",
            "nicaragua", "honduras", "中国", "乌拉圭", "台湾", "美国",
            "estados unidos", "united states", "ee.uu.",
        }
        topic_kw = [w for w in unique_kw if w.lower() not in _COUNTRY_KEYWORDS]

        # Build conceptUri from countries param (primary country + watch countries)
        concepts = []
        for c in countries:
            uri = _COUNTRY_CONCEPTS.get(c)
            if uri:
                concepts.append(uri)

        # Strategy: conceptUri pins the country entity, keywords use OR for breadth
        body: dict = {
            "action": "getArticles",
            "lang": langs,
            "dateStart": date_start,
            "dateEnd": date_end,
            "articlesCount": min(max_articles, 50),
            "articlesSortBy": "date",
            "articlesSortByAsc": False,
            "resultType": "articles",
            "apiKey": api_key,
        }

        if concepts:
            body["conceptUri"] = concepts

        # Use topic keywords with OR (broad match within country scope)
        if topic_kw:
            body["keyword"] = topic_kw
            body["keywordOper"] = "or"
        elif unique_kw:
            # Fallback: use all keywords with OR
            body["keyword"] = unique_kw
            body["keywordOper"] = "or"

        if exclude_keywords:
            # EventRegistry counts keyword + ignoreKeyword toward a 15-keyword limit.
            # Reserve slots for ignoreKeyword after accounting for search keywords.
            kw_count = len(body.get("keyword", []))
            max_ignore = max(15 - kw_count - 1, 0)  # leave 1 slot margin
            if max_ignore > 0:
                body["ignoreKeyword"] = list(exclude_keywords)[:max_ignore]
                body["ignoreKeywordOper"] = "or"

        proxy = get_proxies_for_url(_API_BASE, self.overseas_proxy)
        articles: list[NewsArticle] = []
        try:
            async with build_httpx_client(proxy_url=proxy or "", timeout=30.0) as client:
                resp = await client.post(_API_BASE, json=body)
                resp.raise_for_status()
                data = resp.json()

            if "error" in data:
                logger.warning("NewsAPI.ai API error: %s", data["error"])
                return FetchResult(
                    self.name, topic_name, error=data["error"],
                    elapsed_sec=time.monotonic() - t0,
                )

            for item in data.get("articles", {}).get("results", []):
                pub = None
                if item.get("dateTime"):
                    try:
                        pub = datetime.fromisoformat(item["dateTime"])
                    except (ValueError, TypeError):
                        pass

                # Extract country from source location if available
                country = ""
                src_loc = item.get("source", {}).get("uri", "")

                art = NewsArticle(
                    title=item.get("title", "").strip(),
                    source_url=item.get("url", ""),
                    source_name=item.get("source", {}).get("title", ""),
                    published_at=pub,
                    description=(item.get("body") or "")[:500].strip(),
                    language=item.get("lang", ""),
                    country=country,
                    api_source=self.name,
                    topic_name=topic_name,
                )
                art.compute_fingerprint()
                articles.append(art)

        except Exception as exc:
            logger.error("NewsAPI.ai fetch error: %s", exc)
            return FetchResult(
                self.name, topic_name, error=str(exc),
                elapsed_sec=time.monotonic() - t0,
            )

        logger.info("NewsAPI.ai [%s]: fetched %d articles (kw=%s)", topic_name, len(articles), unique_kw[:3])
        return FetchResult(
            self.name, topic_name, articles=articles,
            elapsed_sec=time.monotonic() - t0,
        )
