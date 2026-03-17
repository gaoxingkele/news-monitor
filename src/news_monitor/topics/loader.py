"""Parse topics/*.md files into pipeline-compatible topic dicts."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


# Mapping from ## headings to dict keys
_SECTION_MAP = {
    "主要关键词": "primary",
    "次要关键词": "secondary",
    "排除关键词": "exclude",
    "搜索查询": "queries",   # each bullet = one independent API query
}


def _parse_topic_md(path: Path) -> dict[str, Any] | None:
    """Parse a single topic .md file. Returns None if disabled."""
    text = path.read_text(encoding="utf-8")

    # Extract YAML frontmatter between first two "---" fences
    frontmatter: dict[str, Any] = {}
    body = text
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            frontmatter = yaml.safe_load(parts[1]) or {}
            body = parts[2]

    # Skip disabled topics (default: enabled)
    if not frontmatter.get("enabled", True):
        return None

    # Parse markdown body for keyword sections
    primary: list[str] = []
    secondary: list[str] = []
    exclude: list[str] = []
    queries: list[str] = []       # independent search queries (one API call each)

    section_targets: dict[str, list[str]] = {
        "primary": primary,
        "secondary": secondary,
        "exclude": exclude,
        "queries": queries,
    }
    current_list: list[str] | None = None

    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            heading = stripped[3:].strip()
            key = _SECTION_MAP.get(heading)
            current_list = section_targets.get(key) if key else None
        elif stripped.startswith("- ") and current_list is not None:
            item = stripped[2:].strip()
            if item:
                current_list.append(item)

    # Build result dict — keep only keys the pipeline expects
    result: dict[str, Any] = {k: v for k, v in frontmatter.items()
                               if k not in ("enabled",)}

    keywords: dict[str, list[str]] = {}
    if primary:
        keywords["primary"] = primary
    if secondary:
        keywords["secondary"] = secondary
    if keywords:
        result["keywords"] = keywords
    if exclude:
        result["exclude_keywords"] = exclude
    if queries:
        result["query_groups"] = queries   # list[str], each str = one search

    return result


def load_topics_from_dir(topics_dir: str | Path) -> list[dict[str, Any]]:
    """Scan directory for .md files and return list of topic dicts."""
    topics_path = Path(topics_dir)
    topics: list[dict[str, Any]] = []
    for md_file in sorted(topics_path.glob("*.md")):
        topic = _parse_topic_md(md_file)
        if topic is not None:
            topics.append(topic)
    return topics
