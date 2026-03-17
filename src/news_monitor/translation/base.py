"""Abstract base class for translators."""
from __future__ import annotations

import abc

from news_monitor.models import NewsArticle


class Translator(abc.ABC):
    """Translate a batch of articles to the target language."""

    @abc.abstractmethod
    async def translate_articles(
        self, articles: list[NewsArticle], target_language: str = "zh-CN"
    ) -> list[NewsArticle]:
        """Translate title and description, filling title_zh / description_zh.

        Returns the same list with translated fields populated.
        """
        ...
