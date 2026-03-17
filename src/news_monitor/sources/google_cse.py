"""Google Custom Search Engine — real Google results with site: support."""
from __future__ import annotations

import logging
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Sequence

from news_monitor.models import FetchResult, NewsArticle
from news_monitor.proxy import get_proxies_for_url, build_httpx_client
from news_monitor.sources.base import NewsSource

logger = logging.getLogger("news_monitor.sources.google_cse")

_API_BASE = "https://www.googleapis.com/customsearch/v1"


def _date_restrict(hours: int) -> str:
    """Map time_range_hours to Google CSE dateRestrict format."""
    days = max(hours // 24, 1)
    return f"d{days}"


class GoogleCSE(NewsSource):
    name = "google_cse"

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
        cx = self.config.get("cx", "")
        if not api_key:
            return FetchResult(self.name, topic_name, error="Missing api_key")
        if not cx:
            return FetchResult(self.name, topic_name, error="Missing cx (Search Engine ID)")

        query = " ".join(keywords)

        # Detect site: prefix and use siteSearch parameter
        site_search = ""
        site_match = re.match(r'site:(\S+)\s*(.*)', query)
        if site_match:
            site_search = site_match.group(1)
            query = site_match.group(2).strip()
            if not query:
                # site: with no extra query — search for recent content
                query = "*"

        # Append exclude keywords as -term
        if exclude_keywords:
            excludes = " ".join(f"-{kw}" for kw in exclude_keywords[:5])
            query = f"{query} {excludes}"

        # Calculate date restriction
        if from_date and to_date:
            try:
                d_from = datetime.strptime(from_date, "%Y-%m-%d")
                d_to = datetime.strptime(to_date, "%Y-%m-%d")
                days_diff = (d_to - d_from).days + 1
                date_restrict = f"d{days_diff}"
            except ValueError:
                date_restrict = _date_restrict(time_range_hours)
        else:
            date_restrict = _date_restrict(time_range_hours)

        # Language: use first language for lr parameter
        lr = ""
        if languages:
            lr = f"lang_{languages[0]}"

        params: dict = {
            "key": api_key,
            "cx": cx,
            "q": query,
            "num": min(max_articles, 10),  # Google CSE max is 10 per request
            "dateRestrict": date_restrict,
        }
        if site_search:
            params["siteSearch"] = site_search
            params["siteSearchFilter"] = "i"  # include only
        if lr:
            params["lr"] = lr

        proxy = get_proxies_for_url(_API_BASE, self.overseas_proxy)
        articles: list[NewsArticle] = []
        try:
            async with build_httpx_client(proxy_url=proxy or "", timeout=30.0) as client:
                resp = await client.get(_API_BASE, params=params)
                resp.raise_for_status()
                data = resp.json()

            if "error" in data:
                error_msg = data["error"].get("message", str(data["error"]))
                logger.warning("Google CSE error: %s", error_msg)
                return FetchResult(
                    self.name, topic_name, error=error_msg,
                    elapsed_sec=time.monotonic() - t0,
                )

            for item in data.get("items", []):
                title = (item.get("title") or "").strip()
                link = item.get("link") or ""
                snippet = (item.get("snippet") or "").strip()
                display_link = item.get("displayLink") or ""

                # Try to extract date from pagemap metatags
                pub = None
                metatags = (item.get("pagemap", {}).get("metatags") or [{}])
                if metatags:
                    for tag_key in ("article:published_time", "og:updated_time", "date"):
                        date_str = metatags[0].get(tag_key, "")
                        if date_str:
                            for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ",
                                        "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"):
                                try:
                                    pub = datetime.strptime(date_str[:25], fmt)
                                    if pub.tzinfo is None:
                                        pub = pub.replace(tzinfo=timezone.utc)
                                    break
                                except ValueError:
                                    continue
                            if pub:
                                break

                # Determine language from the search or result
                lang = languages[0] if languages else ""

                art = NewsArticle(
                    title=title,
                    source_url=link,
                    source_name=display_link,
                    published_at=pub,
                    description=snippet,
                    language=lang,
                    country=countries[0] if countries else "",
                    api_source=self.name,
                    topic_name=topic_name,
                )
                art.compute_fingerprint()
                articles.append(art)

        except Exception as exc:
            logger.error("Google CSE fetch error: %s", exc)
            return FetchResult(
                self.name, topic_name, error=str(exc),
                elapsed_sec=time.monotonic() - t0,
            )

        logger.info("Google CSE [%s]: fetched %d articles (q=%s)", topic_name, len(articles), query[:60])
        return FetchResult(
            self.name, topic_name, articles=articles,
            elapsed_sec=time.monotonic() - t0,
        )
