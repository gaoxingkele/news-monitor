"""Source registry — name → class mapping and factory function."""
from __future__ import annotations

from typing import Type

from news_monitor.sources.base import NewsSource
from news_monitor.sources.perplexity import PerplexitySource
from news_monitor.sources.brave_search import BraveSearch
from news_monitor.sources.gemini_search import GeminiSearch
from news_monitor.sources.grok_search import GrokWebSearch, GrokXSearch
from news_monitor.sources.tavily_search import TavilySearch

_REGISTRY: dict[str, Type[NewsSource]] = {
    "perplexity": PerplexitySource,
    "brave_search": BraveSearch,
    "gemini_search": GeminiSearch,
    "grok_web_search": GrokWebSearch,
    "grok_x_search": GrokXSearch,
    "tavily_search": TavilySearch,
}


def create_source(name: str, config: dict, overseas_proxy: str = "") -> NewsSource:
    """Instantiate a news source by name."""
    cls = _REGISTRY.get(name)
    if cls is None:
        raise ValueError(f"Unknown news source: {name!r}. Available: {list(_REGISTRY)}")
    return cls(config=config, overseas_proxy=overseas_proxy)


def list_sources() -> list[str]:
    """Return all registered source names."""
    return list(_REGISTRY.keys())
