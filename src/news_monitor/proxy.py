"""Proxy routing — overseas APIs through proxy, domestic direct."""
from __future__ import annotations

import httpx

# Domains that should go through the overseas proxy
_OVERSEAS_DOMAINS = {
    "newsdata.io",
    "eventregistry.org",       # NewsAPI.ai backend
    "serpapi.com",
    "api.perplexity.ai",
    "api.worldnewsapi.com",
    "api.openai.com",
    "generativelanguage.googleapis.com",
    "www.googleapis.com",              # Google Custom Search API
    "api.search.brave.com",            # Brave Search API
    "api.x.ai",                        # Grok / xAI API
}

# Domestic providers — direct connection, no proxy
_DOMESTIC_DOMAINS = {
    "api.deepseek.com",
    "api.moonshot.cn",           # Kimi
    "open.bigmodel.cn",          # GLM
    "dashscope.aliyuncs.com",    # Qwen
    "open.feishu.cn",
    "oapi.dingtalk.com",
    "qyapi.weixin.qq.com",
}


def _is_overseas(url: str) -> bool:
    """Check if the URL targets an overseas domain."""
    for domain in _OVERSEAS_DOMAINS:
        if domain in url:
            return True
    return False


def build_httpx_client(
    proxy_url: str = "",
    timeout: float = 30.0,
) -> httpx.AsyncClient:
    """Create an httpx.AsyncClient with optional proxy for overseas APIs.

    The caller should use this as an async context manager or close it manually.
    """
    transport_kwargs: dict = {}
    if proxy_url:
        transport_kwargs["proxy"] = proxy_url

    return httpx.AsyncClient(
        timeout=httpx.Timeout(timeout),
        follow_redirects=True,
        **transport_kwargs,
    )


def get_proxies_for_url(url: str, overseas_proxy: str) -> str | None:
    """Return the proxy URL if the target is overseas, else None."""
    if overseas_proxy and _is_overseas(url):
        return overseas_proxy
    return None
