"""Load config.yaml with environment variable substitution."""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


def _substitute_env(value: Any) -> Any:
    """Recursively replace ${VAR} patterns with env values."""
    if isinstance(value, str):
        def _replace(m: re.Match) -> str:
            return os.environ.get(m.group(1), "")
        return re.sub(r"\$\{(\w+)}", _replace, value)
    if isinstance(value, dict):
        return {k: _substitute_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_substitute_env(v) for v in value]
    return value


def load_config(config_path: str = "config.yaml") -> dict:
    """Load YAML config, apply env-var substitution, return dict."""
    # Load .env from the project root (same directory as config or cwd)
    project_root = Path(config_path).resolve().parent
    env_file = project_root / ".env"
    if env_file.exists():
        load_dotenv(env_file)

    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    result = _substitute_env(raw)

    # Load topics from topics_dir (overrides any inline topics: block)
    topics_dir_val = result.get("topics_dir", "topics")
    topics_dir_path = Path(config_path).resolve().parent / topics_dir_val
    if topics_dir_path.is_dir():
        from news_monitor.topics.loader import load_topics_from_dir
        result["topics"] = load_topics_from_dir(topics_dir_path)

    return result
