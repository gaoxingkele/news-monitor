"""Data models for the news monitoring pipeline."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class NewsArticle:
    """A single news article flowing through the pipeline."""
    title: str
    source_url: str
    source_name: str
    published_at: Optional[datetime] = None
    description: str = ""
    language: str = ""
    country: str = ""
    api_source: str = ""          # which API fetched it (e.g. "newsdata_io")
    found_by: list[str] = field(default_factory=list)  # search engines that found this article
    topic_name: str = ""
    # translated fields
    title_zh: str = ""
    description_zh: str = ""
    summary_zh: str = ""        # 100-150字关键词摘要（简体中文）
    event_date: str = ""        # 文中描述事件的发生时间（YYYY-MM-DD 或可读字符串）
    category: str = ""          # us | taiwan | china | sentiment | {country_key}
    # dedup / scoring
    fingerprint: str = ""
    relevance_score: float = 0.0

    def compute_fingerprint(self) -> str:
        """SHA-256 of title + source_url for exact dedup."""
        raw = f"{self.title}|{self.source_url}"
        self.fingerprint = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        return self.fingerprint


@dataclass
class FetchResult:
    """Result from a single source × topic fetch."""
    source_name: str
    topic_name: str
    articles: list[NewsArticle] = field(default_factory=list)
    error: str = ""
    elapsed_sec: float = 0.0


@dataclass
class PushResult:
    """Result from a single push channel."""
    channel_type: str
    success: bool = False
    articles_count: int = 0
    error: str = ""


@dataclass
class CycleReport:
    """Summary of one complete fetch→push cycle."""
    cycle_id: str = ""
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    total_fetched: int = 0
    total_after_dedup: int = 0
    total_translated: int = 0
    total_entities: int = 0
    total_embedded: int = 0
    total_pushed: int = 0
    errors: list[str] = field(default_factory=list)
    # Duration tracking (seconds)
    fetch_duration_sec: Optional[float] = None
    translate_duration_sec: Optional[float] = None
    ner_duration_sec: Optional[float] = None
    embed_duration_sec: Optional[float] = None
    push_duration_sec: Optional[float] = None

    def summary(self) -> str:
        elapsed = ""
        if self.started_at and self.finished_at:
            elapsed = f" ({(self.finished_at - self.started_at).total_seconds():.1f}s)"
        parts = [
            f"[Cycle {self.cycle_id}]{elapsed}",
            f"  fetched={self.total_fetched}",
            f"  after_dedup={self.total_after_dedup}",
            f"  translated={self.total_translated}",
        ]
        if self.total_entities:
            parts.append(f"  entities={self.total_entities}")
        if self.total_embedded:
            parts.append(f"  embedded={self.total_embedded}")
        parts.append(f"  pushed={self.total_pushed}")
        if self.errors:
            parts.append(f"  errors({len(self.errors)}): {'; '.join(self.errors[:5])}")
        return " | ".join(parts)
