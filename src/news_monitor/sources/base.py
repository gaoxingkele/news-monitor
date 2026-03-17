"""Abstract base class for news sources."""
from __future__ import annotations

import abc
from typing import Sequence

from news_monitor.models import FetchResult


class NewsSource(abc.ABC):
    """Each source implements fetch_articles with a unified signature."""

    name: str = "base"

    def __init__(self, config: dict, overseas_proxy: str = ""):
        self.config = config
        self.overseas_proxy = overseas_proxy

    @abc.abstractmethod
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
        """Fetch articles matching the given criteria.

        Returns a FetchResult with articles list or error string.
        """
        ...
