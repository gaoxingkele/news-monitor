"""Articles table CRUD — batch upsert translated news articles."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from news_monitor.db.pool import get_pool
from news_monitor.models import NewsArticle

logger = logging.getLogger("news_monitor.db.articles")


async def upsert_articles(
    articles: list[NewsArticle],
    cycle_id: str = "",
) -> list[int]:
    """Batch upsert articles into PostgreSQL.

    Returns list of article DB ids (same order as input).
    Uses ON CONFLICT (fingerprint) DO UPDATE for translated fields.
    """
    if not articles:
        return []

    pool = get_pool()
    now = datetime.now(timezone.utc)
    ids: list[int] = []

    async with pool.acquire() as conn:
        # Use a prepared statement for performance
        stmt = await conn.prepare("""
            INSERT INTO articles (
                fingerprint, title, description, source_url, source_name,
                published_at, language, country, api_source, topic_name,
                title_zh, description_zh, relevance_score, cycle_id, fetched_at
            ) VALUES (
                $1, $2, $3, $4, $5,
                $6, $7, $8, $9, $10,
                $11, $12, $13, $14, $15
            )
            ON CONFLICT (fingerprint) DO UPDATE SET
                title_zh       = EXCLUDED.title_zh,
                description_zh = EXCLUDED.description_zh,
                relevance_score = EXCLUDED.relevance_score,
                cycle_id       = EXCLUDED.cycle_id
            RETURNING id
        """)

        for art in articles:
            if not art.fingerprint:
                art.compute_fingerprint()

            row = await stmt.fetchrow(
                art.fingerprint,
                art.title,
                art.description,
                art.source_url,
                art.source_name,
                art.published_at,
                art.language,
                art.country,
                art.api_source,
                art.topic_name,
                art.title_zh,
                art.description_zh,
                art.relevance_score,
                cycle_id,
                now,
            )
            ids.append(row["id"])

    logger.info("Upserted %d articles (cycle %s)", len(ids), cycle_id)
    return ids


async def get_article_id_by_fingerprint(fingerprint: str) -> Optional[int]:
    """Look up an article's DB id by its fingerprint hash."""
    pool = get_pool()
    row = await pool.fetchrow(
        "SELECT id FROM articles WHERE fingerprint = $1", fingerprint
    )
    return row["id"] if row else None


async def get_article_ids_by_fingerprints(
    fingerprints: list[str],
) -> dict[str, int]:
    """Batch look-up: fingerprint → article id."""
    if not fingerprints:
        return {}
    pool = get_pool()
    rows = await pool.fetch(
        "SELECT fingerprint, id FROM articles WHERE fingerprint = ANY($1::char(64)[])",
        fingerprints,
    )
    return {r["fingerprint"]: r["id"] for r in rows}
