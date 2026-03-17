"""SQLite-based deduplication engine — exact fingerprint + fuzzy title matching."""
from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from pathlib import Path

from news_monitor.models import NewsArticle

logger = logging.getLogger("news_monitor.dedup")


class DedupEngine:
    """Two-layer dedup: SHA256 exact match + SequenceMatcher fuzzy title."""

    def __init__(
        self,
        db_path: str = "data/news.db",
        ttl_days: int = 30,
        similarity_threshold: float = 0.85,
    ):
        self.db_path = db_path
        self.ttl_days = ttl_days
        self.similarity_threshold = similarity_threshold

        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path)
        self._init_db()

    def _init_db(self) -> None:
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS seen_articles (
                fingerprint TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                source_url TEXT,
                seen_at TEXT NOT NULL
            )
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_seen_at ON seen_articles(seen_at)
        """)
        self._conn.commit()

    def filter_new(self, articles: list[NewsArticle]) -> list[NewsArticle]:
        """Return only articles not previously seen. Records new ones."""
        self._cleanup_expired()

        # Load recent titles for fuzzy matching
        recent_titles = self._load_recent_titles()
        new_articles: list[NewsArticle] = []
        now = datetime.now(timezone.utc).isoformat()

        for art in articles:
            if not art.fingerprint:
                art.compute_fingerprint()

            # Layer 1: exact fingerprint match
            row = self._conn.execute(
                "SELECT 1 FROM seen_articles WHERE fingerprint = ?",
                (art.fingerprint,),
            ).fetchone()
            if row:
                continue

            # Layer 2: fuzzy title similarity
            if self._is_title_similar(art.title, recent_titles):
                continue

            # It's new — record it
            self._conn.execute(
                "INSERT OR IGNORE INTO seen_articles (fingerprint, title, source_url, seen_at) "
                "VALUES (?, ?, ?, ?)",
                (art.fingerprint, art.title, art.source_url, now),
            )
            recent_titles.append(art.title)
            new_articles.append(art)

        self._conn.commit()
        logger.info(
            "Dedup: %d in → %d new (filtered %d duplicates)",
            len(articles), len(new_articles), len(articles) - len(new_articles),
        )
        return new_articles

    def _is_title_similar(self, title: str, existing: list[str]) -> bool:
        """Check if title is similar to any existing title."""
        title_lower = title.lower().strip()
        for existing_title in existing:
            ratio = SequenceMatcher(
                None, title_lower, existing_title.lower().strip()
            ).ratio()
            if ratio >= self.similarity_threshold:
                return True
        return False

    def _load_recent_titles(self) -> list[str]:
        """Load titles from the last TTL period for fuzzy matching."""
        cutoff = (
            datetime.now(timezone.utc) - timedelta(days=self.ttl_days)
        ).isoformat()
        rows = self._conn.execute(
            "SELECT title FROM seen_articles WHERE seen_at > ?", (cutoff,)
        ).fetchall()
        return [r[0] for r in rows]

    def _cleanup_expired(self) -> None:
        """Remove records older than TTL."""
        cutoff = (
            datetime.now(timezone.utc) - timedelta(days=self.ttl_days)
        ).isoformat()
        deleted = self._conn.execute(
            "DELETE FROM seen_articles WHERE seen_at < ?", (cutoff,)
        ).rowcount
        if deleted:
            self._conn.commit()
            logger.debug("Dedup cleanup: removed %d expired records", deleted)

    def close(self) -> None:
        self._conn.close()
