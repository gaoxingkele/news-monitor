"""Core pipeline: fetch → dedup → translate → (store → NER+embed) → push."""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from datetime import date, datetime, timedelta, timezone

from news_monitor.dedup.engine import DedupEngine
from news_monitor.models import CycleReport, FetchResult, NewsArticle, PushResult
from news_monitor.push.registry import create_channel
from news_monitor.sources.registry import create_source
from news_monitor.translation.llm_translator import LLMTranslator

logger = logging.getLogger("news_monitor.pipeline")


def _last_week_range(time_range_hours: int = 168) -> tuple[str, str]:
    """Return (from_date, to_date) for time_range_hours ending at last Sunday.

    to_date  = last Sunday
    from_date = last Sunday − (time_range_hours / 24 − 1) days

    For the default 168 h (7 days): last Monday → last Sunday.
    The range is anchored to the past week boundary, not to "now".
    """
    today = date.today()
    # days_since_sunday: Mon=1, Tue=2, ..., Sat=6, Sun=7
    days_since_sunday = (today.weekday() + 1) % 7 or 7
    last_sunday = today - timedelta(days=days_since_sunday)
    from_date = last_sunday - timedelta(days=(time_range_hours // 24) - 1)
    return from_date.strftime("%Y-%m-%d"), last_sunday.strftime("%Y-%m-%d")


def _db_enabled(config: dict) -> bool:
    """Check whether database integration is active."""
    db_cfg = config.get("database", {})
    return db_cfg.get("enabled", False) and bool(db_cfg.get("dsn", ""))


async def run_cycle(config: dict) -> CycleReport:
    """Execute one full fetch → dedup → translate → push cycle."""
    report = CycleReport(
        cycle_id=uuid.uuid4().hex[:8],
        started_at=datetime.now(timezone.utc),
    )
    logger.info("=== Cycle %s started ===", report.cycle_id)

    overseas_proxy = config.get("proxy", {}).get("overseas_proxy", "")

    # ── 1. Fetch from all enabled sources × all topics ──
    t0 = time.monotonic()
    all_articles: list[NewsArticle] = []
    fetch_tasks = []

    sources_cfg = config.get("sources", {})
    topics = config.get("topics", [])

    for source_name, source_conf in sources_cfg.items():
        if not source_conf.get("enabled", False):
            continue
        try:
            source = create_source(source_name, source_conf, overseas_proxy)
        except ValueError as exc:
            report.errors.append(str(exc))
            continue

        for topic in topics:
            topic_name = topic.get("name", "")
            skip_sources = topic.get("skip_sources", [])
            if source_name in skip_sources:
                continue
            exclude_kw = topic.get("exclude_keywords")
            countries = topic.get("countries", [])
            languages = topic.get("languages", [])
            time_range_hours = topic.get("time_range_hours", 72)
            max_articles = topic.get("max_articles", 30)

            time_mode = topic.get("time_mode", "")
            from_date: str | None = None
            to_date: str | None = None
            if time_mode == "last_week":
                from_date, to_date = _last_week_range(time_range_hours)
                logger.info(
                    "Topic %s: last_week range %s → %s", topic_name, from_date, to_date
                )

            # query_groups: each entry becomes an independent API call
            query_groups: list[list[str]] = []
            if topic.get("query_groups"):
                # Each string in query_groups is treated as a single search phrase
                query_groups = [[q] for q in topic["query_groups"]]
            else:
                # Legacy: combine primary + secondary into one call
                keywords = topic.get("keywords", {})
                all_kw = keywords.get("primary", []) + keywords.get("secondary", [])
                if all_kw:
                    query_groups = [all_kw]

            for kw_list in query_groups:
                fetch_tasks.append(
                    source.fetch_articles(
                        keywords=kw_list,
                        countries=countries,
                        languages=languages,
                        time_range_hours=time_range_hours,
                        max_articles=max_articles,
                        exclude_keywords=exclude_kw,
                        topic_name=topic_name,
                        from_date=from_date,
                        to_date=to_date,
                    )
                )

    if fetch_tasks:
        results: list[FetchResult] = await asyncio.gather(
            *fetch_tasks, return_exceptions=True
        )
        for r in results:
            if isinstance(r, Exception):
                report.errors.append(str(r))
            elif isinstance(r, FetchResult):
                if r.error:
                    report.errors.append(f"{r.source_name}[{r.topic_name}]: {r.error}")
                all_articles.extend(r.articles)

    report.total_fetched = len(all_articles)
    report.fetch_duration_sec = time.monotonic() - t0
    logger.info("Fetched %d articles total from %d tasks", report.total_fetched, len(fetch_tasks))

    if not all_articles:
        report.finished_at = datetime.now(timezone.utc)
        logger.info("No articles fetched, cycle done. %s", report.summary())
        return report

    # ── 2. Dedup ──
    use_pg = _db_enabled(config)
    dedup_cfg = config.get("dedup", {})
    sqlite_db_path = config.get("sqlite", {}).get("db_path", "data/news.db")

    if use_pg:
        from news_monitor.db.dedup import PgDedupEngine

        pg_dedup = PgDedupEngine(
            ttl_days=dedup_cfg.get("ttl_days", 30),
            similarity_threshold=dedup_cfg.get("similarity_threshold", 0.85),
        )
        new_articles = await pg_dedup.filter_new(all_articles)
    else:
        dedup = DedupEngine(
            db_path=sqlite_db_path,
            ttl_days=dedup_cfg.get("ttl_days", 30),
            similarity_threshold=dedup_cfg.get("similarity_threshold", 0.85),
        )
        try:
            new_articles = dedup.filter_new(all_articles)
        finally:
            dedup.close()

    report.total_after_dedup = len(new_articles)
    logger.info("After dedup: %d new articles", report.total_after_dedup)

    if not new_articles:
        report.finished_at = datetime.now(timezone.utc)
        logger.info("All duplicates, cycle done. %s", report.summary())
        return report

    # ── 3. Translate ──
    t1 = time.monotonic()
    trans_cfg = config.get("translation", {})
    translator = LLMTranslator(
        provider=trans_cfg.get("provider", "qwen"),
        fallback_chain=trans_cfg.get("fallback_chain", ["deepseek", "grok", "doubao", "glm"]),
        batch_size=trans_cfg.get("batch_size", 0),
        skip_if_language=trans_cfg.get("skip_if_language", "zh"),
        overseas_proxy=overseas_proxy,
    )
    new_articles = await translator.translate_articles(
        new_articles, trans_cfg.get("target_language", "zh-CN")
    )
    report.total_translated = sum(1 for a in new_articles if a.title_zh)
    report.translate_duration_sec = time.monotonic() - t1

    # ── 3.2  Relevance filter ──
    filter_cfg = config.get("filter", {})
    if filter_cfg.get("enabled", False) and new_articles:
        from news_monitor.filter.relevance_filter import RelevanceFilter

        # Derive country info from first topic
        _country_zh = ""
        _country_en = ""
        if topics:
            _cc = (topics[0].get("countries") or [""])[0]
            # Simple lookup; fetch_topic.py has full map but pipeline keeps it light
            _country_zh = _cc
            _country_en = _cc

        rf = RelevanceFilter(
            provider=filter_cfg.get("provider", "grok"),
            fallback_provider=filter_cfg.get("fallback_provider", "deepseek"),
            second_fallback=filter_cfg.get("second_fallback", "kimi"),
            batch_size=filter_cfg.get("batch_size", 30),
            overseas_proxy=overseas_proxy,
        )
        filtered, _filter_log = await rf.filter_articles(
            new_articles, _country_zh, _country_en
        )
        logger.info("Relevance filter: %d → %d articles", len(new_articles), len(filtered))
        new_articles = filtered

    # ── 3.5  Store articles ──
    article_db_ids: list[int] = []
    sqlite_store = None
    if use_pg:
        from news_monitor.db.articles import upsert_articles

        article_db_ids = await upsert_articles(new_articles, cycle_id=report.cycle_id)
    else:
        from news_monitor.db.sqlite import SqliteStore

        sqlite_store = SqliteStore(db_path=sqlite_db_path)
        sqlite_store.upsert_articles(new_articles, cycle_id=report.cycle_id)

    # ── 3.6  NER + Embedding (parallel, async, PG only) ──
    if use_pg and article_db_ids:
        enrichment_tasks = []

        # NER
        ner_cfg = config.get("ner", {})
        if ner_cfg.get("enabled", False):
            from news_monitor.ner.extractor import extract_entities_batch

            enrichment_tasks.append(
                _run_ner(new_articles, article_db_ids, ner_cfg, overseas_proxy, report)
            )

        # Embedding
        embed_cfg = config.get("embeddings", {})
        if embed_cfg.get("enabled", False):
            from news_monitor.embeddings.generator import embed_articles_batch

            enrichment_tasks.append(
                _run_embedding(new_articles, article_db_ids, embed_cfg, overseas_proxy, report)
            )

        if enrichment_tasks:
            await asyncio.gather(*enrichment_tasks, return_exceptions=True)

    # ── 4. Group by topic and push ──
    t2 = time.monotonic()
    push_cfg = config.get("push", {})
    batch_size = push_cfg.get("batch_size", 10)
    channels_cfg = push_cfg.get("channels", [])

    # Group articles by topic
    by_topic: dict[str, list[NewsArticle]] = {}
    for art in new_articles:
        by_topic.setdefault(art.topic_name or "default", []).append(art)

    # Build fingerprint→db_id map for push_log
    fp_to_dbid: dict[str, int] = {}
    if use_pg and article_db_ids:
        for art, db_id in zip(new_articles, article_db_ids):
            fp_to_dbid[art.fingerprint] = db_id

    total_pushed = 0
    for ch_conf in channels_cfg:
        if not ch_conf.get("enabled", False):
            continue
        try:
            channel = create_channel(ch_conf["type"], ch_conf)
        except ValueError as exc:
            report.errors.append(str(exc))
            continue

        channel_type = ch_conf["type"]

        for topic_name, topic_articles in by_topic.items():
            # Filter out already-pushed articles
            articles_to_push = topic_articles
            if use_pg:
                from news_monitor.db.push_log import filter_unpushed

                articles_to_push = await filter_unpushed(
                    topic_articles, channel_type, fp_to_dbid
                )
            elif sqlite_store:
                articles_to_push = sqlite_store.filter_unpushed(topic_articles, channel_type)

            # Send in batches to respect rate limits
            for i in range(0, len(articles_to_push), batch_size):
                batch = articles_to_push[i : i + batch_size]
                result: PushResult = await channel.send(batch, topic_name)
                if result.success:
                    total_pushed += result.articles_count
                    if use_pg:
                        from news_monitor.db.push_log import record_push

                        await record_push(
                            batch, channel_type, topic_name, fp_to_dbid, status="sent"
                        )
                    elif sqlite_store:
                        sqlite_store.record_push(batch, channel_type, topic_name, status="sent")
                else:
                    report.errors.append(
                        f"{result.channel_type}[{topic_name}]: {result.error}"
                    )
                    if use_pg:
                        from news_monitor.db.push_log import record_push

                        await record_push(
                            batch, channel_type, topic_name, fp_to_dbid,
                            status="failed", error_message=result.error,
                        )
                    elif sqlite_store:
                        sqlite_store.record_push(
                            batch, channel_type, topic_name,
                            status="failed", error_message=result.error or "",
                        )

    report.total_pushed = total_pushed
    report.push_duration_sec = time.monotonic() - t2
    report.finished_at = datetime.now(timezone.utc)

    # ── 5. Write cycle log ──
    if use_pg:
        from news_monitor.db.cycle_log import write_cycle_log

        await write_cycle_log(report)
    elif sqlite_store:
        sqlite_store.write_cycle_log(report)
        sqlite_store.close()

    # ── 6. PDF Report (local output) ──
    output_cfg = config.get("output", {})
    if output_cfg.get("pdf_enabled", False):
        try:
            from news_monitor.output.pdf_reporter import generate_report
            md_path, pdf_path = generate_report(
                new_articles, report, output_cfg.get("pdf_dir", "output/reports")
            )
            logger.info("MD report saved: %s", md_path)
            if pdf_path:
                logger.info("PDF report saved: %s", pdf_path)
        except Exception as exc:
            logger.error("PDF report failed: %s", exc)
            report.errors.append(f"PDF: {exc}")

    logger.info("=== Cycle done. %s ===", report.summary())
    return report


async def _run_ner(
    articles: list[NewsArticle],
    db_ids: list[int],
    ner_cfg: dict,
    overseas_proxy: str,
    report: CycleReport,
) -> None:
    """Run NER extraction and store entities. Errors are non-fatal."""
    t = time.monotonic()
    try:
        from news_monitor.ner.extractor import extract_entities_batch

        total = await extract_entities_batch(
            articles, db_ids, ner_cfg, overseas_proxy
        )
        report.total_entities = total
        logger.info("NER: extracted %d entity links", total)
    except Exception as exc:
        logger.error("NER failed: %s", exc)
        report.errors.append(f"NER: {exc}")
    finally:
        report.ner_duration_sec = time.monotonic() - t


async def _run_embedding(
    articles: list[NewsArticle],
    db_ids: list[int],
    embed_cfg: dict,
    overseas_proxy: str,
    report: CycleReport,
) -> None:
    """Generate embeddings and store vectors. Errors are non-fatal."""
    t = time.monotonic()
    try:
        from news_monitor.embeddings.generator import embed_articles_batch

        total = await embed_articles_batch(
            articles, db_ids, embed_cfg, overseas_proxy
        )
        report.total_embedded = total
        logger.info("Embedding: embedded %d articles", total)
    except Exception as exc:
        logger.error("Embedding failed: %s", exc)
        report.errors.append(f"Embedding: {exc}")
    finally:
        report.embed_duration_sec = time.monotonic() - t
