"""SQLite storage layer — articles, push_log, cycle_log.

Shares data/news.db with DedupEngine (separate tables, separate connection).
All methods are synchronous; call from async code via asyncio.to_thread if needed.
"""
from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from news_monitor.models import CycleReport, NewsArticle

logger = logging.getLogger("news_monitor.db.sqlite")

_DDL = """
CREATE TABLE IF NOT EXISTS articles (
    fingerprint    TEXT PRIMARY KEY,
    title          TEXT,
    title_zh       TEXT,
    description    TEXT,
    description_zh TEXT,
    summary_zh     TEXT,
    category       TEXT,
    source_url     TEXT,
    published_at   TEXT,
    source_name    TEXT,
    topic_name     TEXT,
    language       TEXT,
    cycle_id       TEXT,
    stored_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS push_log (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    fingerprint    TEXT NOT NULL,
    channel        TEXT NOT NULL,
    topic          TEXT,
    status         TEXT NOT NULL,
    error_message  TEXT,
    pushed_at      TEXT NOT NULL,
    UNIQUE(fingerprint, channel)
);

CREATE TABLE IF NOT EXISTS cycle_log (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    cycle_id         TEXT,
    started_at       TEXT,
    finished_at      TEXT,
    total_fetched    INTEGER DEFAULT 0,
    total_after_dedup INTEGER DEFAULT 0,
    total_translated INTEGER DEFAULT 0,
    total_pushed     INTEGER DEFAULT 0,
    errors           TEXT
);
"""


class SqliteStore:
    """Lightweight local store: articles + push_log + cycle_log in a single SQLite file."""

    def __init__(self, db_path: str = "data/news.db") -> None:
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.executescript(_DDL)
        # Auto-migrate: add columns introduced after initial schema
        for col, typedef in [("summary_zh", "TEXT"), ("category", "TEXT")]:
            try:
                self._conn.execute(f"ALTER TABLE articles ADD COLUMN {col} {typedef}")
            except sqlite3.OperationalError:
                pass  # column already exists
        self._conn.commit()
        logger.debug("SqliteStore opened: %s", db_path)

    # ------------------------------------------------------------------
    # Articles
    # ------------------------------------------------------------------

    def upsert_articles(self, articles: list[NewsArticle], cycle_id: str = "") -> None:
        """Insert new articles; silently ignore fingerprint conflicts."""
        now = datetime.now(timezone.utc).isoformat()
        rows = [
            (
                art.fingerprint,
                art.title,
                getattr(art, "title_zh", None),
                art.description,
                getattr(art, "description_zh", None),
                getattr(art, "summary_zh", None),
                getattr(art, "category", None),
                art.source_url,
                art.published_at.isoformat() if art.published_at else None,
                art.source_name,
                art.topic_name,
                art.language,
                cycle_id,
                now,
            )
            for art in articles
            if art.fingerprint
        ]
        self._conn.executemany(
            """
            INSERT OR IGNORE INTO articles
              (fingerprint, title, title_zh, description, description_zh,
               summary_zh, category,
               source_url, published_at, source_name, topic_name, language,
               cycle_id, stored_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            rows,
        )
        self._conn.commit()
        logger.debug("Stored %d articles (new only) to SQLite", len(rows))

    # ------------------------------------------------------------------
    # Push log
    # ------------------------------------------------------------------

    def filter_unpushed(
        self, articles: list[NewsArticle], channel: str
    ) -> list[NewsArticle]:
        """Return articles not yet successfully pushed to channel."""
        if not articles:
            return []
        fps = [a.fingerprint for a in articles if a.fingerprint]
        if not fps:
            return articles
        placeholders = ",".join("?" * len(fps))
        pushed = {
            row[0]
            for row in self._conn.execute(
                f"SELECT fingerprint FROM push_log "
                f"WHERE channel = ? AND status = 'sent' AND fingerprint IN ({placeholders})",
                [channel, *fps],
            ).fetchall()
        }
        return [a for a in articles if a.fingerprint not in pushed]

    def record_push(
        self,
        articles: list[NewsArticle],
        channel: str,
        topic: str,
        status: str,
        error_message: str = "",
    ) -> None:
        """Record push attempt (upsert by fingerprint+channel)."""
        now = datetime.now(timezone.utc).isoformat()
        rows = [
            (a.fingerprint, channel, topic, status, error_message or None, now)
            for a in articles
            if a.fingerprint
        ]
        self._conn.executemany(
            """
            INSERT INTO push_log (fingerprint, channel, topic, status, error_message, pushed_at)
            VALUES (?,?,?,?,?,?)
            ON CONFLICT(fingerprint, channel) DO UPDATE SET
                status        = excluded.status,
                error_message = excluded.error_message,
                pushed_at     = excluded.pushed_at
            """,
            rows,
        )
        self._conn.commit()

    # ------------------------------------------------------------------
    # Cycle log
    # ------------------------------------------------------------------

    def write_cycle_log(self, report: CycleReport) -> None:
        """Append a cycle summary row."""
        self._conn.execute(
            """
            INSERT INTO cycle_log
              (cycle_id, started_at, finished_at, total_fetched, total_after_dedup,
               total_translated, total_pushed, errors)
            VALUES (?,?,?,?,?,?,?,?)
            """,
            (
                report.cycle_id,
                report.started_at.isoformat() if report.started_at else None,
                report.finished_at.isoformat() if report.finished_at else None,
                report.total_fetched,
                report.total_after_dedup,
                report.total_translated,
                report.total_pushed,
                json.dumps(report.errors, ensure_ascii=False) if report.errors else None,
            ),
        )
        self._conn.commit()

    # ------------------------------------------------------------------

    def close(self) -> None:
        self._conn.close()
