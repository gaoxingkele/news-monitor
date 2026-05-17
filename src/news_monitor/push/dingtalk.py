"""DingTalk webhook push — feedCard format with HMAC-SHA256 signing."""
from __future__ import annotations

import hashlib
import hmac
import base64
import logging
import time
import urllib.parse

import httpx

from news_monitor.models import NewsArticle, PushResult
from news_monitor.push.base import PushChannel

logger = logging.getLogger("news_monitor.push.dingtalk")


def _sign_url(webhook_url: str, secret: str) -> str:
    """Add timestamp + sign params to DingTalk webhook URL."""
    timestamp = str(int(time.time() * 1000))
    string_to_sign = f"{timestamp}\n{secret}"
    hmac_code = hmac.new(
        secret.encode("utf-8"),
        string_to_sign.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    sign = urllib.parse.quote_plus(base64.b64encode(hmac_code).decode("utf-8"))
    sep = "&" if "?" in webhook_url else "?"
    return f"{webhook_url}{sep}timestamp={timestamp}&sign={sign}"


class DingTalkChannel(PushChannel):
    channel_type = "dingtalk"

    async def send(
        self, articles: list[NewsArticle], topic_name: str = ""
    ) -> PushResult:
        if not self.webhook_url:
            return PushResult(self.channel_type, error="Missing webhook_url")
        if not articles:
            return PushResult(self.channel_type, success=True, articles_count=0)

        url = self.webhook_url
        if self.secret:
            url = _sign_url(url, self.secret)

        # Build feedCard
        links = []
        for art in articles:
            title = art.title_zh or art.title
            links.append({
                "title": title,
                "messageURL": art.source_url or "https://news.google.com",
                "picURL": "",
            })

        body = {
            "msgtype": "feedCard",
            "feedCard": {"links": links},
        }

        try:
            async with httpx.AsyncClient(timeout=15.0, trust_env=False) as client:
                resp = await client.post(url, json=body)
                resp.raise_for_status()
                data = resp.json()

            if data.get("errcode", 0) != 0:
                err = data.get("errmsg", "Unknown error")
                logger.error("DingTalk push error: %s", err)
                return PushResult(self.channel_type, error=err)

            logger.info("DingTalk push OK: %d articles for [%s]", len(articles), topic_name)
            return PushResult(
                self.channel_type, success=True, articles_count=len(articles)
            )
        except Exception as exc:
            logger.error("DingTalk push failed: %s", exc)
            return PushResult(self.channel_type, error=str(exc))
