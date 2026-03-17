"""Time series trend data storage for event monitoring.

Records timestamped snapshots of sentiment distribution so that
trends can be tracked across multiple fetch/analysis runs.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

TREND_DIR = "output/trends"


def record_snapshot(
    event_key: str,
    articles: list,
    sentiment_dist: dict,
    clusters: list | None = None,
) -> str:
    """Save a timestamped snapshot of sentiment distribution for trend tracking.

    Args:
        event_key: identifier for the event (e.g. ``"boao_forum_2026"``).
        articles: list of article dicts or NewsArticle objects.
        sentiment_dist: dict mapping sentiment category to count.
        clusters: optional list of cluster dicts from semantic clustering.

    Returns:
        Path to the saved snapshot file.
    """
    Path(TREND_DIR).mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc)
    ts_str = ts.strftime("%Y%m%d_%H%M%S")

    # Extract top keywords from titles
    from collections import Counter
    title_words: Counter[str] = Counter()
    source_counter: Counter[str] = Counter()
    for a in articles:
        if isinstance(a, dict):
            title = a.get("title_zh") or a.get("title", "")
            src = a.get("source_name", "")
        else:
            title = getattr(a, "title_zh", "") or getattr(a, "title", "")
            src = getattr(a, "source_name", "")
        # Simple word-level extraction (works for both CJK and latin)
        for w in title.split():
            if len(w) >= 2:
                title_words[w] += 1
        if src:
            source_counter[src] += 1

    snapshot = {
        "timestamp": ts.isoformat(),
        "event_key": event_key,
        "total_count": len(articles),
        "sentiment_dist": sentiment_dist,
        "top_keywords": [kw for kw, _ in title_words.most_common(20)],
        "top_sources": [
            {"name": name, "count": count}
            for name, count in source_counter.most_common(15)
        ],
    }
    if clusters:
        snapshot["cluster_count"] = len(clusters)
        snapshot["cluster_topics"] = [
            c.get("topic", "") for c in clusters[:20]
        ]

    file_path = str(Path(TREND_DIR) / f"{event_key}_{ts_str}.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)
    return file_path


def load_snapshots(event_key: str) -> list[dict]:
    """Load all snapshots for an event, sorted by time (oldest first)."""
    trend_dir = Path(TREND_DIR)
    if not trend_dir.exists():
        return []

    snapshots = []
    for fp in sorted(trend_dir.glob(f"{event_key}_*.json")):
        try:
            with open(fp, "r", encoding="utf-8") as f:
                snapshots.append(json.load(f))
        except Exception:
            continue
    return snapshots


def generate_trend_summary(event_key: str) -> str:
    """Generate a text summary of sentiment trends over time.

    Returns a human-readable string describing how sentiment has shifted
    across snapshots. Returns empty string if fewer than 2 snapshots exist.
    """
    snapshots = load_snapshots(event_key)
    if len(snapshots) < 2:
        return ""

    lines = [f"## {event_key} 舆情趋势（{len(snapshots)} 次快照）", ""]

    # Table header
    lines.append("| 时间 | 总量 | 正面 | 中性 | 负面 | 分析 |")
    lines.append("|:---|---:|---:|---:|---:|---:|")

    for s in snapshots:
        ts = s.get("timestamp", "")[:16].replace("T", " ")
        total = s.get("total_count", 0)
        dist = s.get("sentiment_dist", {})
        pos = dist.get("positive", 0)
        neu = dist.get("neutral", 0)
        neg = dist.get("negative", 0)
        ana = dist.get("analysis", 0)
        lines.append(f"| {ts} | {total} | {pos} | {neu} | {neg} | {ana} |")

    lines.append("")

    # Trend description
    first = snapshots[0].get("sentiment_dist", {})
    last = snapshots[-1].get("sentiment_dist", {})
    first_total = snapshots[0].get("total_count", 1) or 1
    last_total = snapshots[-1].get("total_count", 1) or 1

    neg_pct_first = first.get("negative", 0) / first_total * 100
    neg_pct_last = last.get("negative", 0) / last_total * 100
    pos_pct_first = first.get("positive", 0) / first_total * 100
    pos_pct_last = last.get("positive", 0) / last_total * 100

    if neg_pct_last > neg_pct_first + 5:
        lines.append(f"**趋势：** 负面报道占比上升（{neg_pct_first:.0f}% -> {neg_pct_last:.0f}%），需关注。")
    elif pos_pct_last > pos_pct_first + 5:
        lines.append(f"**趋势：** 正面报道占比上升（{pos_pct_first:.0f}% -> {pos_pct_last:.0f}%），舆情向好。")
    else:
        lines.append("**趋势：** 舆情态度分布基本稳定。")

    return "\n".join(lines)
