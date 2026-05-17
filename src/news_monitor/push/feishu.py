"""Feishu (Lark) webhook push — Message Card format."""
from __future__ import annotations

import hashlib
import hmac
import base64
import logging
import time
from typing import Any

import httpx

from news_monitor.models import NewsArticle, PushResult
from news_monitor.push.base import PushChannel

logger = logging.getLogger("news_monitor.push.feishu")


def _gen_sign(secret: str, timestamp: int) -> str:
    """Generate Feishu webhook signature."""
    string_to_sign = f"{timestamp}\n{secret}"
    hmac_code = hmac.new(
        string_to_sign.encode("utf-8"), b"", digestmod=hashlib.sha256
    ).digest()
    return base64.b64encode(hmac_code).decode("utf-8")


class FeishuChannel(PushChannel):
    channel_type = "feishu"

    async def send(
        self, articles: list[NewsArticle], topic_name: str = ""
    ) -> PushResult:
        if not self.webhook_url:
            return PushResult(self.channel_type, error="Missing webhook_url")
        if not articles:
            return PushResult(self.channel_type, success=True, articles_count=0)

        # Build Message Card
        elements: list[dict[str, Any]] = []

        # Header
        elements.append({
            "tag": "markdown",
            "content": f"**{topic_name or '新闻更新'}** — 共 {len(articles)} 条",
        })
        elements.append({"tag": "hr"})

        # Each article as a card section
        for art in articles:
            title = art.title_zh or art.title
            desc = (art.description_zh or art.description or "")[:200]
            source = art.source_name or art.api_source
            pub_time = ""
            if art.published_at:
                pub_time = art.published_at.strftime("%m-%d %H:%M")

            md = f"**{title}**\n"
            if desc:
                md += f"{desc}\n"
            md += f"_{source}"
            if pub_time:
                md += f" | {pub_time}"
            md += "_"

            elements.append({"tag": "markdown", "content": md})
            if art.source_url:
                elements.append({
                    "tag": "action",
                    "actions": [{
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "阅读原文"},
                        "url": art.source_url,
                        "type": "primary",
                    }],
                })
            elements.append({"tag": "hr"})

        card = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": f"📰 {topic_name or '全球新闻监控'}",
                    },
                    "template": "blue",
                },
                "elements": elements,
            },
        }

        # Add signature if secret is configured
        if self.secret:
            timestamp = int(time.time())
            sign = _gen_sign(self.secret, timestamp)
            card["timestamp"] = str(timestamp)
            card["sign"] = sign

        try:
            async with httpx.AsyncClient(timeout=15.0, trust_env=False) as client:
                resp = await client.post(self.webhook_url, json=card)
                resp.raise_for_status()
                data = resp.json()

            if data.get("code", 0) != 0:
                err = data.get("msg", "Unknown error")
                logger.error("Feishu push error: %s", err)
                return PushResult(self.channel_type, error=err)

            logger.info("Feishu push OK: %d articles for [%s]", len(articles), topic_name)
            return PushResult(
                self.channel_type, success=True, articles_count=len(articles)
            )
        except Exception as exc:
            logger.error("Feishu push failed: %s", exc)
            return PushResult(self.channel_type, error=str(exc))
