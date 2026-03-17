"""Embedding generator — calls DeepSeek (or compatible) embedding API."""
from __future__ import annotations

import logging
import os

import httpx
import numpy as np

from news_monitor.db.pool import get_pool
from news_monitor.models import NewsArticle
from news_monitor.proxy import get_proxies_for_url

logger = logging.getLogger("news_monitor.embeddings")

_PROVIDERS = {
    "deepseek": {
        "base_url_env": "DEEPSEEK_BASE_URL",
        "base_url_default": "https://api.deepseek.com/v1",
        "api_key_env": "DEEPSEEK_API_KEY",
        "model": "deepseek-embedding",
        "overseas": False,
    },
    "openai": {
        "base_url_env": "OPENAI_BASE_URL",
        "base_url_default": "https://api.openai.com/v1",
        "api_key_env": "OPENAI_API_KEY",
        "model": "text-embedding-3-small",
        "overseas": True,
    },
}


def _build_embed_text(art: NewsArticle) -> str:
    """Combine title + description in both languages for cross-lingual embedding."""
    parts = [art.title]
    if art.title_zh and art.title_zh != art.title:
        parts.append(art.title_zh)
    if art.description:
        parts.append(art.description[:200])
    if art.description_zh and art.description_zh != art.description:
        parts.append(art.description_zh[:200])
    return " ".join(parts)


async def embed_articles_batch(
    articles: list[NewsArticle],
    db_ids: list[int],
    embed_cfg: dict,
    overseas_proxy: str,
) -> int:
    """Generate embeddings for articles and store in DB.

    Returns number of articles successfully embedded.
    """
    provider_name = embed_cfg.get("provider", "deepseek")
    model_override = embed_cfg.get("model", "")
    batch_size = embed_cfg.get("batch_size", 20)
    total_embedded = 0

    prov = _PROVIDERS.get(provider_name)
    if not prov:
        logger.error("Unknown embedding provider: %s", provider_name)
        return 0

    api_key = os.environ.get(prov["api_key_env"], "")
    if not api_key:
        logger.error("Missing API key for embedding provider %s", provider_name)
        return 0

    base_url = os.environ.get(prov["base_url_env"], prov["base_url_default"])
    url = f"{base_url}/embeddings"
    model = model_override or prov["model"]

    proxy = None
    if prov["overseas"]:
        proxy = get_proxies_for_url(url, overseas_proxy)

    for batch_start in range(0, len(articles), batch_size):
        batch_articles = articles[batch_start : batch_start + batch_size]
        batch_ids = db_ids[batch_start : batch_start + batch_size]

        texts = [_build_embed_text(art) for art in batch_articles]

        vectors = await _call_embedding_api(
            url, api_key, model, texts, proxy
        )
        if vectors is None:
            logger.error("Embedding API failed for batch starting at %d", batch_start)
            continue

        await _store_vectors(batch_ids, vectors)
        total_embedded += len(vectors)

    return total_embedded


async def _call_embedding_api(
    url: str,
    api_key: str,
    model: str,
    texts: list[str],
    proxy: str | None,
) -> list[list[float]] | None:
    """Call the embedding API and return a list of vectors."""
    body = {
        "model": model,
        "input": texts,
    }

    try:
        async with httpx.AsyncClient(
            timeout=60.0, proxy=proxy, follow_redirects=True
        ) as client:
            resp = await client.post(
                url, json=body,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        embeddings = data.get("data", [])
        # Sort by index to ensure order matches input
        embeddings.sort(key=lambda x: x.get("index", 0))
        return [e["embedding"] for e in embeddings]

    except Exception as exc:
        logger.error("Embedding API call failed: %s", exc)
        return None


async def _store_vectors(db_ids: list[int], vectors: list[list[float]]) -> None:
    """Write embedding vectors to the articles table."""
    pool = get_pool()

    async with pool.acquire() as conn:
        stmt = await conn.prepare(
            "UPDATE articles SET embedding = $1 WHERE id = $2"
        )
        for db_id, vec in zip(db_ids, vectors):
            await stmt.fetch(np.array(vec, dtype=np.float32), db_id)

    logger.debug("Stored %d embedding vectors", len(vectors))
