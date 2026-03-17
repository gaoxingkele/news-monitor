"""PostgreSQL-based dedup engine — fingerprint UNIQUE + pg_trgm fuzzy matching."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from news_monitor.db.pool import get_pool
from news_monitor.models import NewsArticle

logger = logging.getLogger("news_monitor.db.dedup")


class PgDedupEngine:
    """Two-layer dedup backed by PostgreSQL.

    Layer 1: exact fingerprint match via UNIQUE constraint on articles.fingerprint
    Layer 2: fuzzy title similarity via pg_trgm similarity() function
    """

    def __init__(
        self,
        ttl_days: int = 30,
        similarity_threshold: float = 0.85,
    ):
        self.ttl_days = ttl_days
        self.similarity_threshold = similarity_threshold

    async def filter_new(self, articles: list[NewsArticle]) -> list[NewsArticle]:
        """Return only articles not previously seen.

        Unlike the SQLite engine, this does NOT insert records — that happens
        later in the pipeline via db.articles.upsert_articles() after translation.
        """
        if not articles:
            return []

        pool = get_pool()
        new_articles: list[NewsArticle] = []

        # Compute all fingerprints upfront
        for art in articles:
            if not art.fingerprint:
                art.compute_fingerprint()

        fingerprints = [art.fingerprint for art in articles]

        async with pool.acquire() as conn:
            # Layer 1: batch exact fingerprint lookup
            existing = await conn.fetch(
                "SELECT fingerprint FROM articles WHERE fingerprint = ANY($1::char(64)[])",
                fingerprints,
            )
            existing_fps = {r["fingerprint"].strip() for r in existing}

            # Filter to candidates that pass Layer 1
            candidates = [
                art for art in articles if art.fingerprint not in existing_fps
            ]

            if not candidates:
                logger.info(
                    "Dedup: %d in → 0 new (all exact duplicates)",
                    len(articles),
                )
                return []

            # Layer 2: fuzzy title similarity via pg_trgm
            # Check each candidate title against recent DB titles
            for art in candidates:
                is_similar = await conn.fetchval(
                    """
                    SELECT EXISTS(
                        SELECT 1 FROM articles
                        WHERE fetched_at > $1
                          AND similarity(title, $2) >= $3
                    )
                    """,
                    datetime.now(timezone.utc) - timedelta(days=self.ttl_days),
                    art.title,
                    self.similarity_threshold,
                )
                if not is_similar:
                    new_articles.append(art)

        logger.info(
            "Dedup(PG): %d in → %d new (filtered %d duplicates)",
            len(articles),
            len(new_articles),
            len(articles) - len(new_articles),
        )
        return new_articles
