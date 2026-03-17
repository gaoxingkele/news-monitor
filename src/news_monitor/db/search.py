"""Hybrid search — combines full-text search, trigram, and vector similarity with RRF fusion."""
from __future__ import annotations

import logging
from typing import Optional

import numpy as np

from news_monitor.db.pool import get_pool

logger = logging.getLogger("news_monitor.db.search")

# Reciprocal Rank Fusion constant (standard value)
_RRF_K = 60


async def hybrid_search(
    query_text: str,
    query_vector: Optional[list[float]] = None,
    limit: int = 10,
) -> list[dict]:
    """Run a hybrid search combining FTS, trigram, and vector similarity.

    Uses Reciprocal Rank Fusion (RRF) to merge multiple ranking signals
    into a single ranked result list.

    Returns list of {id, title, title_zh, source_url, published_at, rrf_score}.
    """
    pool = get_pool()

    # Build individual ranking CTEs
    ctes = []
    params: list = []
    param_idx = 1

    # CTE 1: Full-text search (original + Chinese)
    ctes.append(f"""
        fts_rank AS (
            SELECT id, ROW_NUMBER() OVER (
                ORDER BY ts_rank(fts_original, plainto_tsquery('simple', ${param_idx})) +
                         ts_rank(fts_zh, plainto_tsquery('simple', ${param_idx})) DESC
            ) AS rank
            FROM articles
            WHERE fts_original @@ plainto_tsquery('simple', ${param_idx})
               OR fts_zh @@ plainto_tsquery('simple', ${param_idx})
            LIMIT 100
        )
    """)
    params.append(query_text)
    param_idx += 1

    # CTE 2: Trigram similarity on title
    ctes.append(f"""
        trgm_rank AS (
            SELECT id, ROW_NUMBER() OVER (
                ORDER BY similarity(title, ${param_idx}) DESC
            ) AS rank
            FROM articles
            WHERE similarity(title, ${param_idx}) > 0.1
            LIMIT 100
        )
    """)
    params.append(query_text)
    param_idx += 1

    # CTE 3: Vector similarity (if vector provided)
    vec_join = ""
    if query_vector is not None:
        ctes.append(f"""
            vec_rank AS (
                SELECT id, ROW_NUMBER() OVER (
                    ORDER BY embedding <=> ${param_idx}
                ) AS rank
                FROM articles
                WHERE embedding IS NOT NULL
                LIMIT 100
            )
        """)
        params.append(np.array(query_vector, dtype=np.float32))
        param_idx += 1
        vec_join = f"""
            LEFT JOIN vec_rank v ON v.id = a.id
        """

    # RRF fusion query
    vec_rrf = ""
    if query_vector is not None:
        vec_rrf = f"+ COALESCE(1.0 / ({_RRF_K} + v.rank), 0)"

    sql = f"""
        WITH {', '.join(ctes)},
        all_ids AS (
            SELECT id FROM fts_rank
            UNION
            SELECT id FROM trgm_rank
            {'UNION SELECT id FROM vec_rank' if query_vector is not None else ''}
        )
        SELECT a.id, a.title, a.title_zh, a.source_url, a.published_at,
               a.source_name, a.topic_name,
               (
                   COALESCE(1.0 / ({_RRF_K} + f.rank), 0)
                 + COALESCE(1.0 / ({_RRF_K} + t.rank), 0)
                 {vec_rrf}
               ) AS rrf_score
        FROM all_ids ai
        JOIN articles a ON a.id = ai.id
        LEFT JOIN fts_rank f ON f.id = a.id
        LEFT JOIN trgm_rank t ON t.id = a.id
        {vec_join}
        ORDER BY rrf_score DESC
        LIMIT ${param_idx}
    """
    params.append(limit)

    rows = await pool.fetch(sql, *params)
    return [dict(r) for r in rows]
