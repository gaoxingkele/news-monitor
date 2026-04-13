"""统一搜索调度器 —— 异步并发调用多个搜索引擎，合并去重。

复用 news-monitor 已有的 Brave / Tavily / Grok / Gemini 搜索源。
"""
from __future__ import annotations

import asyncio
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

# 项目根及 src/ 加入 sys.path 以便导入 news_monitor
_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_root))
sys.path.insert(0, str(_root / "src"))

from news_monitor.sources.brave_search import BraveSearch
from news_monitor.sources.tavily_search import TavilySearch
from news_monitor.sources.grok_search import GrokWebSearch, GrokXSearch
from news_monitor.sources.gemini_search import GeminiSearch

from .config import bootstrap, get_env, RAW_DIR
from .models import SearchTask, SearchResult

logger = logging.getLogger("data_collection.search")


def _build_source(engine: str):
    """根据引擎名创建搜索源实例。"""
    proxy = get_env("LLM_PROXY")
    if engine == "brave":
        return BraveSearch(
            config={"api_key": get_env("BRAVEAPI")},
            overseas_proxy=proxy,
        )
    elif engine == "tavily":
        return TavilySearch(
            config={"api_key": get_env("tavilyapi") or get_env("TAVILYAPI")},
            overseas_proxy=proxy,
        )
    elif engine == "grok_web":
        return GrokWebSearch(
            config={
                "api_key": get_env("GROK_API_KEY"),
                "model": "grok-4-1-fast-non-reasoning",
            },
            overseas_proxy=proxy,
        )
    elif engine == "grok_x":
        return GrokXSearch(
            config={
                "api_key": get_env("GROK_API_KEY"),
                "model": "grok-4-1-fast-non-reasoning",
            },
            overseas_proxy=proxy,
        )
    elif engine == "gemini":
        return GeminiSearch(
            config={"api_key": get_env("GEMINI_API_KEY")},
            overseas_proxy=proxy,
        )
    else:
        raise ValueError(f"Unknown engine: {engine}")


async def _search_one(engine: str, task: SearchTask) -> list[SearchResult]:
    """对单个搜索引擎执行查询，返回结果列表。"""
    source = _build_source(engine)
    results: list[SearchResult] = []

    # 合并中英文关键词
    all_queries = task.queries_zh + task.queries_en

    for q in all_queries:
        try:
            fetch_result = await source.fetch_articles(
                keywords=q.split(),
                countries=[],
                languages=["zh", "en"],
                time_range_hours=task.time_range_hours,
                max_articles=task.max_results_per_engine,
                topic_name=task.task_id,
            )
            if fetch_result.error:
                logger.warning("[%s/%s] query=%r error=%s", task.task_id, engine, q, fetch_result.error)
                continue

            for art in fetch_result.articles:
                results.append(SearchResult(
                    title=art.title or art.title_zh or "",
                    url=art.source_url or "",
                    snippet=(art.description or art.description_zh or "")[:500],
                    published_date=art.published_at.isoformat() if art.published_at else "",
                    source_engine=engine,
                    language=art.language or "zh",
                ))
        except Exception as e:
            logger.warning("[%s/%s] query=%r exception=%s", task.task_id, engine, q, e)

    return results


def _dedup(results: list[SearchResult]) -> list[SearchResult]:
    """按 URL 去重，保留首次出现。"""
    seen: set[str] = set()
    deduped: list[SearchResult] = []
    for r in results:
        key = r.url.rstrip("/").lower()
        if key not in seen:
            seen.add(key)
            deduped.append(r)
    return deduped


async def dispatch_task(task: SearchTask) -> list[SearchResult]:
    """对一个 SearchTask 并发调用所有指定引擎，合并去重。"""
    bootstrap()

    coros = [_search_one(eng, task) for eng in task.engines]
    all_results: list[SearchResult] = []
    for batch in await asyncio.gather(*coros, return_exceptions=True):
        if isinstance(batch, Exception):
            logger.error("[%s] engine batch failed: %s", task.task_id, batch)
            continue
        all_results.extend(batch)

    deduped = _dedup(all_results)
    logger.info(
        "[%s] total=%d deduped=%d engines=%s",
        task.task_id, len(all_results), len(deduped), task.engines,
    )

    # 存档原始搜索结果
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    raw_file = RAW_DIR / f"{task.task_id}.json"
    raw_file.write_text(
        json.dumps(
            [{"title": r.title, "url": r.url, "snippet": r.snippet,
              "date": r.published_date, "engine": r.source_engine}
             for r in deduped],
            ensure_ascii=False, indent=2,
        ),
        encoding="utf-8",
    )

    return deduped


async def dispatch_batch(tasks: list[SearchTask], concurrency: int = 3) -> dict[str, list[SearchResult]]:
    """批量执行多个采集任务，控制并发数。"""
    sem = asyncio.Semaphore(concurrency)
    results: dict[str, list[SearchResult]] = {}

    async def _run(t: SearchTask):
        async with sem:
            results[t.task_id] = await dispatch_task(t)

    await asyncio.gather(*[_run(t) for t in tasks])
    return results
