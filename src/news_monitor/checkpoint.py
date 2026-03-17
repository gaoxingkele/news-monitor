"""Unified checkpoint module for saving/loading pipeline stage results.

Used by both fetch_topic.py and fetch_event.py to persist intermediate
results (fetch, translate, filter, sentiment) so that runs can be resumed.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from news_monitor.models import NewsArticle

CHECKPOINT_DIR = "output/checkpoints"


# ── Article serialization ────────────────────────────────────────────────────

def articles_to_json(articles: list[NewsArticle]) -> list[dict]:
    """Serialize articles to JSON-safe dicts."""
    out = []
    for a in articles:
        d = {
            "title": a.title, "source_url": a.source_url,
            "source_name": a.source_name, "description": a.description,
            "language": a.language, "country": getattr(a, "country", ""),
            "api_source": a.api_source, "found_by": a.found_by,
            "topic_name": a.topic_name, "title_zh": a.title_zh,
            "description_zh": a.description_zh, "summary_zh": a.summary_zh,
            "event_date": a.event_date, "category": a.category,
            "fingerprint": a.fingerprint,
        }
        if a.published_at:
            d["published_at"] = a.published_at.isoformat()
        out.append(d)
    return out


def articles_from_json(data: list[dict]) -> list[NewsArticle]:
    """Deserialize articles from JSON dicts."""
    arts = []
    for d in data:
        a = NewsArticle(
            title=d.get("title", ""),
            source_url=d.get("source_url", ""),
            source_name=d.get("source_name", ""),
            description=d.get("description", ""),
            language=d.get("language", ""),
            country=d.get("country", ""),
            api_source=d.get("api_source", ""),
            found_by=d.get("found_by", []),
            topic_name=d.get("topic_name", ""),
            title_zh=d.get("title_zh", ""),
            description_zh=d.get("description_zh", ""),
            summary_zh=d.get("summary_zh", ""),
            event_date=d.get("event_date", ""),
            category=d.get("category", ""),
            fingerprint=d.get("fingerprint", ""),
        )
        if d.get("published_at"):
            try:
                a.published_at = datetime.fromisoformat(d["published_at"])
            except (ValueError, TypeError):
                pass
        arts.append(a)
    return arts


# ── Core checkpoint API ──────────────────────────────────────────────────────

def _ckpt_path(key: str, stage: str) -> str:
    """Build checkpoint file path for a given key and stage."""
    return str(Path(CHECKPOINT_DIR) / f"{key}_{stage}.json")


def save(
    key: str,
    stage: str,
    articles: list[NewsArticle],
    extra: dict | None = None,
) -> str:
    """Save articles + metadata at a checkpoint stage.

    Args:
        key: identifier like ``"country_cl"`` or ``"博鳌亚洲论坛2026舆情监测"``.
        stage: pipeline stage name (e.g. ``"fetch_dedup"``, ``"translated"``).
        articles: list of articles to persist.
        extra: optional dict with extra metadata (raw_total, translated, etc.).

    Returns:
        Path to the saved checkpoint file.
    """
    Path(CHECKPOINT_DIR).mkdir(parents=True, exist_ok=True)
    path = _ckpt_path(key, stage)
    payload = {
        "stage": stage,
        "key": key,
        "count": len(articles),
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "articles": articles_to_json(articles),
    }
    if extra:
        payload["extra"] = extra
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    return path


def load(key: str, stage: str) -> tuple[list[NewsArticle], dict] | None:
    """Load a checkpoint. Returns ``(articles, extra)`` or ``None``."""
    path = _ckpt_path(key, stage)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        articles = articles_from_json(payload.get("articles", []))
        extra = payload.get("extra", {})
        extra["_saved_at"] = payload.get("saved_at", "")
        return articles, extra
    except Exception:
        return None


def find_latest(key: str, stages: list[str]) -> str | None:
    """Find the latest completed checkpoint stage for a key.

    Checks stages in reverse order and returns the first one that exists.
    """
    for stage in reversed(stages):
        if os.path.exists(_ckpt_path(key, stage)):
            return stage
    return None
