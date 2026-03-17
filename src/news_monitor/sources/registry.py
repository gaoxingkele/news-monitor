"""Source registry — name → class mapping and factory function."""
from __future__ import annotations

from typing import Type

from news_monitor.sources.base import NewsSource
from news_monitor.sources.newsdata_io import NewsDataIO
from news_monitor.sources.newsapi_ai import NewsAPIAI
from news_monitor.sources.serpapi_google import SerpAPIGoogle
from news_monitor.sources.perplexity import PerplexitySource
from news_monitor.sources.worldnews import WorldNewsSource
from news_monitor.sources.google_cse import GoogleCSE
from news_monitor.sources.brave_search import BraveSearch
from news_monitor.sources.gemini_search import GeminiSearch
from news_monitor.sources.grok_search import GrokWebSearch, GrokXSearch

_REGISTRY: dict[str, Type[NewsSource]] = {
    "newsdata_io": NewsDataIO,
    "newsapi_ai": NewsAPIAI,
    "serpapi_google": SerpAPIGoogle,
    "perplexity": PerplexitySource,
    "worldnews": WorldNewsSource,
    "google_cse": GoogleCSE,
    "brave_search": BraveSearch,
    "gemini_search": GeminiSearch,
    "grok_web_search": GrokWebSearch,
    "grok_x_search": GrokXSearch,
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
