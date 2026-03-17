"""APScheduler-based periodic execution."""
from __future__ import annotations

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from news_monitor.pipeline import run_cycle

logger = logging.getLogger("news_monitor.scheduler")


async def _job(config: dict) -> None:
    """Wrapper that runs one pipeline cycle and logs errors."""
    try:
        report = await run_cycle(config)
        logger.info("Scheduled cycle complete: %s", report.summary())
    except Exception:
        logger.exception("Scheduled cycle failed with unhandled exception")


def start_scheduler(config: dict) -> None:
    """Start the APScheduler loop. Blocks until interrupted."""
    sched_cfg = config.get("schedule", {})
    interval = sched_cfg.get("interval_minutes", 60)
    tz = sched_cfg.get("timezone", "Asia/Shanghai")
    startup_run = sched_cfg.get("startup_run", True)

    scheduler = AsyncIOScheduler(timezone=tz)
    scheduler.add_job(
        _job,
        trigger=IntervalTrigger(minutes=interval),
        args=[config],
        id="news_cycle",
        name="News monitor cycle",
        max_instances=1,
    )

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def _main() -> None:
        # Initialise database pool (if enabled) before any cycle
        from news_monitor.main import _init_db, _close_db
        await _init_db(config, logger)

        try:
            if startup_run:
                logger.info("Running startup cycle before scheduling...")
                await _job(config)

            scheduler.start()
            logger.info(
                "Scheduler started: every %d min (tz=%s). Press Ctrl+C to stop.",
                interval, tz,
            )
            try:
                while True:
                    await asyncio.sleep(3600)
            except (KeyboardInterrupt, asyncio.CancelledError):
                pass
            finally:
                scheduler.shutdown(wait=False)
                logger.info("Scheduler stopped.")
        finally:
            await _close_db(logger)

    try:
        loop.run_until_complete(_main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user.")
    finally:
        loop.close()
