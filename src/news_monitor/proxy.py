"""Proxy routing — only selected APIs go through proxy, all others direct."""
from __future__ import annotations

import httpx

# Domains that MUST use the configured proxy.
# Everything else is forced to connect directly, including Cloubic, Grok, Gemini,
# NewsData, SerpAPI, push webhooks, and domestic providers.
_PROXY_DOMAINS = {
    "api.search.brave.com",
    "api.tavily.com",
    "api.perplexity.ai",
}


def _is_overseas(url: str) -> bool:
    """Return True only for domains explicitly routed through proxy."""
    for domain in _PROXY_DOMAINS:
        if domain in url:
            return True
    return False


def build_httpx_client(
    proxy_url: str = "",
    timeout: float = 30.0,
) -> httpx.AsyncClient:
    """Create an AsyncClient with explicit proxy policy.

    - `trust_env=False` ensures system proxy settings do not leak into direct calls
    - only callers that pass `proxy_url` will use a proxy
    """
    transport_kwargs: dict = {}
    if proxy_url:
        transport_kwargs["proxy"] = proxy_url

    return httpx.AsyncClient(
        timeout=httpx.Timeout(timeout),
        follow_redirects=True,
        trust_env=False,
        **transport_kwargs,
    )


def get_proxies_for_url(url: str, overseas_proxy: str) -> str | None:
    """Return the proxy URL if the target is overseas, else None."""
    if overseas_proxy and _is_overseas(url):
        return overseas_proxy
    return None
