"""WeCom (企业微信) webhook push — news/markdown format."""
from __future__ import annotations

import logging

import httpx

from news_monitor.models import NewsArticle, PushResult
from news_monitor.push.base import PushChannel

logger = logging.getLogger("news_monitor.push.wecom")


class WeComChannel(PushChannel):
    channel_type = "wecom"

    async def send(
        self, articles: list[NewsArticle], topic_name: str = ""
    ) -> PushResult:
        if not self.webhook_url:
            return PushResult(self.channel_type, error="Missing webhook_url")
        if not articles:
            return PushResult(self.channel_type, success=True, articles_count=0)

        template = self.config.get("template", "news")

        if template == "news":
            return await self._send_news(articles, topic_name)
        else:
            return await self._send_markdown(articles, topic_name)

    async def _send_news(
        self, articles: list[NewsArticle], topic_name: str
    ) -> PushResult:
        """Send as WeCom news (图文) message. Max 8 articles per message."""
        # WeCom news message supports up to 8 articles
        items = []
        for art in articles[:8]:
            title = art.title_zh or art.title
            desc = (art.description_zh or art.description or "")[:200]
            items.append({
                "title": title,
                "description": desc,
                "url": art.source_url or "https://news.google.com",
            })

        body = {
            "msgtype": "news",
            "news": {"articles": items},
        }
        return await self._post(body, len(articles), topic_name)

    async def _send_markdown(
        self, articles: list[NewsArticle], topic_name: str
    ) -> PushResult:
        """Send as WeCom markdown message."""
        lines = [f"## {topic_name or '新闻更新'}\n"]
        for i, art in enumerate(articles, 1):
            title = art.title_zh or art.title
            source = art.source_name or art.api_source
            pub_time = ""
            if art.published_at:
                pub_time = art.published_at.strftime("%m-%d %H:%M")
            line = f"{i}. [{title}]({art.source_url})"
            if source or pub_time:
                line += f"\n   _{source}"
                if pub_time:
                    line += f" | {pub_time}"
                line += "_"
            lines.append(line)

        body = {
            "msgtype": "markdown",
            "markdown": {"content": "\n".join(lines)},
        }
        return await self._post(body, len(articles), topic_name)

    async def _post(
        self, body: dict, count: int, topic_name: str
    ) -> PushResult:
        try:
            async with httpx.AsyncClient(timeout=15.0, trust_env=False) as client:
                resp = await client.post(self.webhook_url, json=body)
                resp.raise_for_status()
                data = resp.json()

            if data.get("errcode", 0) != 0:
                err = data.get("errmsg", "Unknown error")
                logger.error("WeCom push error: %s", err)
                return PushResult(self.channel_type, error=err)

            logger.info("WeCom push OK: %d articles for [%s]", count, topic_name)
            return PushResult(self.channel_type, success=True, articles_count=count)
        except Exception as exc:
            logger.error("WeCom push failed: %s", exc)
            return PushResult(self.channel_type, error=str(exc))
