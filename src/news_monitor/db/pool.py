"""asyncpg connection pool lifecycle management."""
from __future__ import annotations

import logging
from typing import Optional

import asyncpg
from pgvector.asyncpg import register_vector

logger = logging.getLogger("news_monitor.db")

_pool: Optional[asyncpg.Pool] = None


async def init_pool(dsn: str, min_size: int = 1, max_size: int = 5) -> asyncpg.Pool:
    """Create the global connection pool and run migrations if needed."""
    global _pool
    if _pool is not None:
        return _pool

    logger.info("Connecting to PostgreSQL …")
    _pool = await asyncpg.create_pool(
        dsn,
        min_size=min_size,
        max_size=max_size,
        init=_init_connection,
    )
    logger.info("Connection pool created (min=%d, max=%d)", min_size, max_size)
    return _pool


async def _init_connection(conn: asyncpg.Connection) -> None:
    """Per-connection setup: register pgvector type codec."""
    await register_vector(conn)


async def close_pool() -> None:
    """Gracefully shut down the pool."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
        logger.info("Connection pool closed")


def get_pool() -> asyncpg.Pool:
    """Return the global pool, raising if not initialised."""
    if _pool is None:
        raise RuntimeError("Database pool not initialised — call init_pool() first")
    return _pool


async def run_migrations(auto_migrate: bool = True) -> None:
    """Execute pending schema migrations in order."""
    if not auto_migrate:
        return
    pool = get_pool()
    from news_monitor.db.migrations import v001_initial

    async with pool.acquire() as conn:
        await v001_initial.migrate(conn)
    logger.info("Migrations complete")
