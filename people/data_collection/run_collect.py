"""数据采集主入口 —— 按 Tier 分阶段执行采集。

用法：
    # 执行 Tier-1 全部搜索任务
    python -m people.data_collection.run_collect --person 蒋万安 --tier 1

    # 仅执行指定任务
    python -m people.data_collection.run_collect --person 蒋万安 --tier 1 --only T1-07,T1-12

    # 仅搜索不提取
    python -m people.data_collection.run_collect --person 蒋万安 --tier 1 --search-only

    # 仅提取（基于已有 raw/ 中的搜索结果）
    python -m people.data_collection.run_collect --person 蒋万安 --tier 1 --extract-only
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_root))
sys.path.insert(0, str(_root / "src"))

from people.data_collection.config import bootstrap, RAW_DIR, EXTRACTED_DIR, REPORTS_DIR
from people.data_collection.models import SearchTask, SearchResult, CollectionReport
from people.data_collection.search_dispatcher import dispatch_batch
from people.data_collection.extractor import extract_facts

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("data_collection.run")


_TASK_REGISTRY: dict[tuple[str, int], str] = {
    ("蒋万安", 0): "people.data_collection.tasks.chiang_wanan_t0.get_all_tier0_tasks",
    ("蒋万安", 1): "people.data_collection.tasks.chiang_wanan.get_all_tier1_tasks",
}


def _load_tasks(person: str, tier: int) -> list[SearchTask]:
    key = (person, tier)
    if key not in _TASK_REGISTRY:
        logger.error("No tasks defined for person=%s tier=%d", person, tier)
        return []
    module_path, func_name = _TASK_REGISTRY[key].rsplit(".", 1)
    from importlib import import_module
    mod = import_module(module_path)
    return getattr(mod, func_name)()


def _load_raw_results(task_id: str) -> list[SearchResult]:
    raw_file = RAW_DIR / f"{task_id}.json"
    if not raw_file.is_file():
        return []
    data = json.loads(raw_file.read_text(encoding="utf-8"))
    return [
        SearchResult(
            title=r.get("title", ""),
            url=r.get("url", ""),
            snippet=r.get("snippet", ""),
            published_date=r.get("date", ""),
            source_engine=r.get("engine", ""),
        )
        for r in data
    ]


async def run_tier1(
    tasks: list[SearchTask],
    search_only: bool = False,
    extract_only: bool = False,
    concurrency: int = 3,
) -> list[CollectionReport]:
    reports: list[CollectionReport] = []

    # Step 1: 搜索
    if not extract_only:
        logger.info("=== Step 1: 搜索 (%d tasks, concurrency=%d) ===", len(tasks), concurrency)
        await dispatch_batch(tasks, concurrency=concurrency)

    if search_only:
        logger.info("search-only mode, skipping extraction")
        return reports

    # Step 2: LLM 提取
    logger.info("=== Step 2: LLM 结构化提取 ===")
    for task in tasks:
        results = _load_raw_results(task.task_id)
        if not results:
            logger.warning("[%s] no raw results, skipping extraction", task.task_id)
            reports.append(CollectionReport(
                gap_id=task.gap_id,
                title=task.title,
                status="failed",
                notes="no search results",
            ))
            continue

        logger.info("[%s] extracting from %d results...", task.task_id, len(results))
        facts = extract_facts(
            task_id=task.task_id,
            task_title=task.title,
            gap_id=task.gap_id,
            extraction_schema=task.extraction_schema,
            results=results,
            v6_module=task.v6_module,
        )
        reports.append(CollectionReport(
            gap_id=task.gap_id,
            title=task.title,
            status="completed" if facts else "partial",
            facts_count=len(facts),
            sources_count=len(results),
        ))

    return reports


def _write_summary(person: str, reports: list[CollectionReport]) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out = REPORTS_DIR / f"{person}_collection_summary.md"

    lines = [f"# {person} 数据采集汇总\n"]
    lines.append(f"| # | 采集项 | 状态 | 搜索结果数 | 提取事实数 | 备注 |")
    lines.append(f"|---|--------|------|-----------|-----------|------|")

    total_facts = 0
    for r in reports:
        lines.append(f"| {r.gap_id} | {r.title} | {r.status} | {r.sources_count} | {r.facts_count} | {r.notes} |")
        total_facts += r.facts_count

    lines.append(f"\n**总计**：{len(reports)} 项任务，{total_facts} 条结构化事实\n")

    completed = sum(1 for r in reports if r.status == "completed")
    partial = sum(1 for r in reports if r.status == "partial")
    failed = sum(1 for r in reports if r.status == "failed")
    lines.append(f"- 完成：{completed}  部分：{partial}  失败：{failed}\n")

    out.write_text("\n".join(lines), encoding="utf-8")
    logger.info("summary → %s", out)


def main() -> None:
    ap = argparse.ArgumentParser(description="OSINT 数据采集流水线")
    ap.add_argument("--person", required=True, help="目标人物")
    ap.add_argument("--tier", type=int, default=1, help="执行层级 (0/1/2/3)")
    ap.add_argument("--only", default="", help="仅执行指定任务ID，逗号分隔")
    ap.add_argument("--search-only", action="store_true", help="仅搜索不提取")
    ap.add_argument("--extract-only", action="store_true", help="仅提取（需已有raw）")
    ap.add_argument("--concurrency", type=int, default=3, help="搜索并发数")
    args = ap.parse_args()

    bootstrap()

    tasks = _load_tasks(args.person, args.tier)
    if args.only:
        only_ids = {x.strip() for x in args.only.split(",") if x.strip()}
        tasks = [t for t in tasks if t.task_id in only_ids]

    if not tasks:
        logger.error("No tasks to execute")
        return

    logger.info("Executing %d tasks for %s (tier=%d)", len(tasks), args.person, args.tier)

    reports = asyncio.run(run_tier1(
        tasks,
        search_only=args.search_only,
        extract_only=args.extract_only,
        concurrency=args.concurrency,
    ))

    _write_summary(args.person, reports)
    print(json.dumps(
        [{"gap_id": r.gap_id, "title": r.title, "status": r.status,
          "facts": r.facts_count, "sources": r.sources_count}
         for r in reports],
        ensure_ascii=False, indent=2,
    ))


if __name__ == "__main__":
    main()
