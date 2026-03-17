"""Brave Search API — web search with native site: support and freshness filtering."""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Sequence

from news_monitor.models import FetchResult, NewsArticle
from news_monitor.proxy import get_proxies_for_url, build_httpx_client
from news_monitor.sources.base import NewsSource

logger = logging.getLogger("news_monitor.sources.brave_search")

_API_BASE = "https://api.search.brave.com/res/v1/web/search"


def _freshness(hours: int, from_date: str | None = None, to_date: str | None = None) -> str:
    """Map time range to Brave freshness parameter."""
    if from_date and to_date:
        return f"{from_date}to{to_date}"
    if hours <= 24:
        return "pd"
    if hours <= 168:
        return "pw"
    if hours <= 744:
        return "pm"
    return "py"


class BraveSearch(NewsSource):
    name = "brave_search"

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

        query = " ".join(keywords)

        # Append exclude keywords as -term (max 5 to keep query clean)
        if exclude_keywords:
            excludes = " ".join(f"-{kw}" for kw in list(exclude_keywords)[:5])
            query = f"{query} {excludes}"

        # Language: Brave uses specific lang codes (pt-br, pt-pt, zh-hans, etc.)
        _LANG_MAP = {"pt": "pt-br", "zh": "zh-hans"}
        raw_lang = languages[0] if languages else "en"
        search_lang = _LANG_MAP.get(raw_lang, raw_lang)

        # Country: Brave only supports a fixed set of country codes
        _BRAVE_COUNTRIES = {
            "AR", "AU", "AT", "BE", "BR", "CA", "CL", "DK", "FI", "FR",
            "DE", "GR", "HK", "IN", "ID", "IT", "JP", "KR", "MY", "MX",
            "NL", "NZ", "NO", "CN", "PL", "PT", "PH", "RU", "SA", "ZA",
            "ES", "SE", "CH", "TW", "TR", "GB", "US", "ALL",
        }
        country = (countries[0].upper()) if countries else ""

        params: dict = {
            "q": query,
            "count": min(max_articles, 20),  # Brave max is 20
            "freshness": _freshness(time_range_hours, from_date, to_date),
            "search_lang": search_lang,
            "text_decorations": False,
        }
        if country and country in _BRAVE_COUNTRIES:
            params["country"] = country

        headers = {
            "X-Subscription-Token": api_key,
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
        }

        proxy = get_proxies_for_url(_API_BASE, self.overseas_proxy)
        articles: list[NewsArticle] = []
        try:
            async with build_httpx_client(proxy_url=proxy or "", timeout=30.0) as client:
                resp = await client.get(_API_BASE, params=params, headers=headers)
                if resp.status_code != 200:
                    logger.error("Brave HTTP %d: %s", resp.status_code, resp.text[:500])
                    return FetchResult(
                        self.name, topic_name,
                        error=f"HTTP {resp.status_code}: {resp.text[:200]}",
                        elapsed_sec=time.monotonic() - t0,
                    )
                data = resp.json()

            # Parse web results
            web_results = data.get("web", {}).get("results", [])
            for item in web_results[:max_articles]:
                title = (item.get("title") or "").strip()
                url = item.get("url") or ""
                description = (item.get("description") or "").strip()

                # Parse date from age or page_age
                pub = None
                age_str = item.get("page_age") or item.get("age") or ""
                if age_str:
                    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%fZ",
                                "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
                        try:
                            pub = datetime.strptime(age_str[:25], fmt)
                            if pub.tzinfo is None:
                                pub = pub.replace(tzinfo=timezone.utc)
                            break
                        except ValueError:
                            continue

                art = NewsArticle(
                    title=title,
                    source_url=url,
                    source_name=item.get("meta_url", {}).get("hostname", ""),
                    published_at=pub,
                    description=description,
                    language=item.get("language") or search_lang,
                    country=countries[0] if countries else "",
                    api_source=self.name,
                    found_by=["Brave"],
                    topic_name=topic_name,
                )
                art.compute_fingerprint()
                articles.append(art)

        except Exception as exc:
            err_detail = f"{type(exc).__name__}: {exc!r}"
            logger.error("Brave Search error: %s", err_detail)
            return FetchResult(
                self.name, topic_name, error=err_detail,
                elapsed_sec=time.monotonic() - t0,
            )

        logger.info("Brave [%s]: fetched %d articles (q=%s)", topic_name, len(articles), query[:60])
        return FetchResult(
            self.name, topic_name, articles=articles,
            elapsed_sec=time.monotonic() - t0,
        )
