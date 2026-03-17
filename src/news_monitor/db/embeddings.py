"""Embedding vector queries — semantic similarity search."""
from __future__ import annotations

import logging
from typing import Optional

import numpy as np

from news_monitor.db.pool import get_pool

logger = logging.getLogger("news_monitor.db.embeddings")


async def search_similar(
    query_vector: list[float],
    limit: int = 10,
    min_score: float = 0.3,
) -> list[dict]:
    """Find articles most similar to the query vector (cosine similarity).

    Returns list of {id, title, title_zh, source_url, score, published_at}.
    """
    pool = get_pool()
    vec = np.array(query_vector, dtype=np.float32)

    rows = await pool.fetch(
        """
        SELECT id, title, title_zh, source_url, published_at,
               1 - (embedding <=> $1) AS score
        FROM articles
        WHERE embedding IS NOT NULL
        ORDER BY embedding <=> $1
        LIMIT $2
        """,
        vec,
        limit,
    )
    return [
        dict(r) for r in rows
        if r["score"] >= min_score
    ]
