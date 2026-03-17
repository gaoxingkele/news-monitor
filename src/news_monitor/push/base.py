"""Abstract base class for push channels."""
from __future__ import annotations

import abc

from news_monitor.models import NewsArticle, PushResult


class PushChannel(abc.ABC):
    """Each channel implements send() to push articles to a messaging platform."""

    channel_type: str = "base"

    def __init__(self, config: dict):
        self.config = config
        self.webhook_url: str = config.get("webhook_url", "")
        self.secret: str = config.get("secret", "")

    @abc.abstractmethod
    async def send(
        self, articles: list[NewsArticle], topic_name: str = ""
    ) -> PushResult:
        """Send articles to the channel. Returns a PushResult."""
        ...
