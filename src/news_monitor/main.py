"""CLI entry point — parse arguments and start the monitor."""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys

from news_monitor.config_loader import load_config
from news_monitor.logging_config import setup_logging


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Global News Monitor — fetch, translate, and push news"
    )
    parser.add_argument(
        "--config", "-c",
        default="config.yaml",
        help="Path to config YAML file (default: config.yaml)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run one cycle and exit (no scheduler)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )
    args = parser.parse_args()

    # Set up logging
    level = logging.DEBUG if args.debug else logging.INFO
    logger = setup_logging(level=level)

    # Load config
    config_path = args.config
    if not os.path.exists(config_path):
        logger.error("Config file not found: %s", config_path)
        sys.exit(1)

    config = load_config(config_path)
    logger.info("Config loaded from %s", config_path)

    # Summarize enabled sources and channels
    enabled_sources = [
        name for name, cfg in config.get("sources", {}).items()
        if cfg.get("enabled")
    ]
    enabled_channels = [
        ch["type"] for ch in config.get("push", {}).get("channels", [])
        if ch.get("enabled")
    ]
    topics = [t.get("name", "?") for t in config.get("topics", [])]

    logger.info("Sources: %s", ", ".join(enabled_sources) or "(none)")
    logger.info("Channels: %s", ", ".join(enabled_channels) or "(none)")
    logger.info("Topics: %s", ", ".join(topics) or "(none)")

    if args.once:
        # Single run mode
        from news_monitor.pipeline import run_cycle

        asyncio.run(_run_once(config, logger))
    else:
        # Daemon mode with scheduler
        from news_monitor.scheduler import start_scheduler

        start_scheduler(config)


async def _run_once(config: dict, logger: logging.Logger) -> None:
    """Run a single cycle with database lifecycle management."""
    from news_monitor.pipeline import run_cycle

    await _init_db(config, logger)
    try:
        report = await run_cycle(config)
        logger.info("Single run complete. %s", report.summary())
    finally:
        await _close_db(logger)


async def _init_db(config: dict, logger: logging.Logger) -> None:
    """Initialise the database pool and run migrations if enabled."""
    db_cfg = config.get("database", {})
    if not db_cfg.get("enabled", False):
        return
    dsn = db_cfg.get("dsn", "")
    if not dsn:
        logger.warning("database.enabled=true but DATABASE_URL is empty, skipping DB")
        return

    from news_monitor.db.pool import init_pool, run_migrations

    await init_pool(
        dsn,
        min_size=db_cfg.get("pool_min_size", 1),
        max_size=db_cfg.get("pool_max_size", 5),
    )
    await run_migrations(auto_migrate=db_cfg.get("auto_migrate", True))


async def _close_db(logger: logging.Logger) -> None:
    """Close the database pool if it was opened."""
    try:
        from news_monitor.db.pool import close_pool
        await close_pool()
    except Exception:
        logger.debug("No DB pool to close")
