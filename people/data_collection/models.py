"""数据模型：采集任务定义 + 搜索结果 + 提取事实。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SearchTask:
    """一条搜索采集任务。"""
    task_id: str                       # 如 "T1-13a"
    gap_id: int                        # 映射到执行计划30项的编号
    title: str                         # 采集项简称
    queries_zh: list[str]              # 正体中文关键词组
    queries_en: list[str] = field(default_factory=list)  # 英文关键词组
    engines: list[str] = field(default_factory=lambda: ["brave", "tavily"])
    time_range_hours: int = 8760       # 默认1年
    max_results_per_engine: int = 10
    extraction_schema: str = ""        # LLM 提取时的 JSON schema 描述
    v6_module: str = ""                # 映射 V6 模块编号
    tier: int = 1                      # 0/1/2/3


@dataclass
class SearchResult:
    """单条搜索结果。"""
    title: str
    url: str
    snippet: str
    published_date: str = ""
    source_engine: str = ""
    language: str = "zh"


@dataclass
class ExtractedFact:
    """LLM 从搜索结果中提取的结构化事实。"""
    fact_id: str
    gap_id: int
    content: str                       # 事实陈述
    evidence_grade: str = "B"          # A/B/C/D/E
    source_url: str = ""
    source_name: str = ""              # 如"联合新闻网"
    date_obtained: str = ""
    date_of_event: str = ""
    v6_module: str = ""
    raw_quote: str = ""                # 原文引用
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CollectionReport:
    """单个采集项的完成度报告。"""
    gap_id: int
    title: str
    status: str = "pending"            # pending/in_progress/completed/partial/failed
    facts_count: int = 0
    sources_count: int = 0
    notes: str = ""
