"""Push log — prevent duplicate pushes and track delivery status."""
from __future__ import annotations

import logging
from typing import Optional

from news_monitor.db.pool import get_pool
from news_monitor.models import NewsArticle

logger = logging.getLogger("news_monitor.db.push_log")


async def filter_unpushed(
    articles: list[NewsArticle],
    channel_type: str,
    fp_to_dbid: dict[str, int],
) -> list[NewsArticle]:
    """Return only articles that have NOT been successfully pushed to this channel."""
    if not articles or not fp_to_dbid:
        return articles

    pool = get_pool()
    db_ids = [fp_to_dbid[a.fingerprint] for a in articles if a.fingerprint in fp_to_dbid]

    if not db_ids:
        return articles

    rows = await pool.fetch(
        """
        SELECT article_id FROM push_log
        WHERE article_id = ANY($1::bigint[])
          AND channel_type = $2
          AND status = 'sent'
        """,
        db_ids,
        channel_type,
    )
    already_pushed = {r["article_id"] for r in rows}

    result = [
        art for art in articles
        if fp_to_dbid.get(art.fingerprint) not in already_pushed
    ]

    skipped = len(articles) - len(result)
    if skipped:
        logger.info(
            "Push filter: skipped %d already-pushed articles for %s",
            skipped, channel_type,
        )
    return result


async def record_push(
    articles: list[NewsArticle],
    channel_type: str,
    topic_name: str,
    fp_to_dbid: dict[str, int],
    status: str = "sent",
    error_message: str = "",
) -> None:
    """Record push attempts in push_log (upsert)."""
    pool = get_pool()

    async with pool.acquire() as conn:
        stmt = await conn.prepare("""
            INSERT INTO push_log (article_id, channel_type, topic_name, status, error_message)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (article_id, channel_type) DO UPDATE SET
                status = EXCLUDED.status,
                error_message = EXCLUDED.error_message,
                attempted_at = NOW()
        """)
        for art in articles:
            db_id = fp_to_dbid.get(art.fingerprint)
            if db_id is None:
                continue
            await stmt.fetch(db_id, channel_type, topic_name, status, error_message)

    logger.debug(
        "Recorded %d push entries (%s, %s)", len(articles), channel_type, status
    )
