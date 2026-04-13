"""采集模块配置 —— 复用主项目 .env / .env.cloubic。"""
from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(__file__).resolve().parent


def _load_env(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip()
        if k and k not in os.environ:
            os.environ[k] = v


def bootstrap() -> None:
    _load_env(PROJECT_ROOT / ".env")
    _load_env(PROJECT_ROOT / ".env.cloubic")


def get_env(key: str, default: str = "") -> str:
    bootstrap()
    return os.getenv(key, default).strip()


# 路径常量
RAW_DIR = DATA_DIR / "raw"
EXTRACTED_DIR = DATA_DIR / "extracted"
REPORTS_DIR = DATA_DIR / "reports"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "output"
