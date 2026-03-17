"""Cycle log — pipeline execution audit trail."""
from __future__ import annotations

import json
import logging

from news_monitor.db.pool import get_pool
from news_monitor.models import CycleReport

logger = logging.getLogger("news_monitor.db.cycle_log")


async def write_cycle_log(report: CycleReport) -> None:
    """Write a completed cycle report to the cycle_log table."""
    pool = get_pool()

    errors_json = json.dumps(report.errors[:50], ensure_ascii=False)

    await pool.execute(
        """
        INSERT INTO cycle_log (
            cycle_id, started_at, finished_at,
            total_fetched, total_after_dedup, total_translated,
            total_entities, total_embedded, total_pushed,
            errors,
            fetch_duration_sec, translate_duration_sec,
            ner_duration_sec, embed_duration_sec, push_duration_sec
        ) VALUES (
            $1, $2, $3,
            $4, $5, $6,
            $7, $8, $9,
            $10::jsonb,
            $11, $12,
            $13, $14, $15
        )
        ON CONFLICT (cycle_id) DO NOTHING
        """,
        report.cycle_id,
        report.started_at,
        report.finished_at,
        report.total_fetched,
        report.total_after_dedup,
        report.total_translated,
        report.total_entities,
        report.total_embedded,
        report.total_pushed,
        errors_json,
        report.fetch_duration_sec,
        report.translate_duration_sec,
        report.ner_duration_sec,
        report.embed_duration_sec,
        report.push_duration_sec,
    )
    logger.info("Cycle log written: %s", report.cycle_id)
