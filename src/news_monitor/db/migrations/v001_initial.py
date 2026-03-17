"""v001 — Initial schema: articles, entities, knowledge graph, push/cycle logs."""
from __future__ import annotations

import logging

import asyncpg

logger = logging.getLogger("news_monitor.db.migrations")

_MIGRATION_ID = "v001_initial"

# ── Extensions ────────────────────────────────────────────────────────────────

_EXTENSIONS = """
CREATE EXTENSION IF NOT EXISTS pgvector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
"""

# ── Tables ────────────────────────────────────────────────────────────────────

_ARTICLES = """
CREATE TABLE IF NOT EXISTS articles (
    id              BIGSERIAL PRIMARY KEY,
    fingerprint     CHAR(64) NOT NULL UNIQUE,
    -- original text
    title           TEXT NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    source_url      TEXT NOT NULL,
    source_name     TEXT NOT NULL DEFAULT '',
    published_at    TIMESTAMPTZ,
    language        VARCHAR(10) NOT NULL DEFAULT '',
    country         VARCHAR(100) NOT NULL DEFAULT '',
    api_source      VARCHAR(50) NOT NULL DEFAULT '',
    topic_name      VARCHAR(200) NOT NULL DEFAULT '',
    -- translated text
    title_zh        TEXT NOT NULL DEFAULT '',
    description_zh  TEXT NOT NULL DEFAULT '',
    -- vector & full-text search
    embedding       vector(1024),
    fts_original    tsvector,
    fts_zh          tsvector,
    -- metadata
    relevance_score REAL NOT NULL DEFAULT 0.0,
    cycle_id        VARCHAR(20) NOT NULL DEFAULT '',
    fetched_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

_ARTICLES_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_articles_published    ON articles (published_at DESC);",
    "CREATE INDEX IF NOT EXISTS idx_articles_topic        ON articles (topic_name);",
    "CREATE INDEX IF NOT EXISTS idx_articles_fetched      ON articles (fetched_at DESC);",
    "CREATE INDEX IF NOT EXISTS idx_articles_title_trgm   ON articles USING gin (title gin_trgm_ops);",
    "CREATE INDEX IF NOT EXISTS idx_articles_fts_original ON articles USING gin (fts_original);",
    "CREATE INDEX IF NOT EXISTS idx_articles_fts_zh       ON articles USING gin (fts_zh);",
    "CREATE INDEX IF NOT EXISTS idx_articles_embedding    ON articles USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);",
]

_ENTITIES = """
CREATE TABLE IF NOT EXISTS entities (
    id              BIGSERIAL PRIMARY KEY,
    name            TEXT NOT NULL,
    name_zh         TEXT NOT NULL DEFAULT '',
    entity_type     VARCHAR(50) NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    canonical_id    BIGINT REFERENCES entities(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_entity UNIQUE (name, entity_type)
);
"""

_ARTICLE_ENTITIES = """
CREATE TABLE IF NOT EXISTS article_entities (
    id              BIGSERIAL PRIMARY KEY,
    article_id      BIGINT NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    entity_id       BIGINT NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    role            VARCHAR(50) NOT NULL DEFAULT 'mentioned',
    confidence      REAL NOT NULL DEFAULT 1.0,
    context_snippet TEXT NOT NULL DEFAULT '',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_article_entity_role UNIQUE (article_id, entity_id, role)
);
"""

_ENTITY_RELATIONS = """
CREATE TABLE IF NOT EXISTS entity_relations (
    id              BIGSERIAL PRIMARY KEY,
    source_entity   BIGINT NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    target_entity   BIGINT NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    relation_type   VARCHAR(100) NOT NULL,
    confidence      REAL NOT NULL DEFAULT 1.0,
    first_seen_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    article_count   INT NOT NULL DEFAULT 1,
    CONSTRAINT uq_entity_relation UNIQUE (source_entity, target_entity, relation_type)
);
"""

_PUSH_LOG = """
CREATE TABLE IF NOT EXISTS push_log (
    id              BIGSERIAL PRIMARY KEY,
    article_id      BIGINT NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    channel_type    VARCHAR(50) NOT NULL,
    topic_name      VARCHAR(200) NOT NULL DEFAULT '',
    status          VARCHAR(20) NOT NULL DEFAULT 'pending',
    error_message   TEXT NOT NULL DEFAULT '',
    attempted_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_push UNIQUE (article_id, channel_type)
);
"""

_CYCLE_LOG = """
CREATE TABLE IF NOT EXISTS cycle_log (
    id                      BIGSERIAL PRIMARY KEY,
    cycle_id                VARCHAR(20) NOT NULL UNIQUE,
    started_at              TIMESTAMPTZ NOT NULL,
    finished_at             TIMESTAMPTZ,
    total_fetched           INT NOT NULL DEFAULT 0,
    total_after_dedup       INT NOT NULL DEFAULT 0,
    total_translated        INT NOT NULL DEFAULT 0,
    total_entities          INT NOT NULL DEFAULT 0,
    total_embedded          INT NOT NULL DEFAULT 0,
    total_pushed            INT NOT NULL DEFAULT 0,
    errors                  JSONB NOT NULL DEFAULT '[]',
    fetch_duration_sec      REAL,
    translate_duration_sec  REAL,
    ner_duration_sec        REAL,
    embed_duration_sec      REAL,
    push_duration_sec       REAL
);
"""

# ── Trigger: auto-generate tsvectors on INSERT/UPDATE ─────────────────────────

_FTS_TRIGGER_FUNC = """
CREATE OR REPLACE FUNCTION articles_fts_trigger() RETURNS trigger AS $$
BEGIN
    NEW.fts_original := to_tsvector('simple',
        coalesce(NEW.title, '') || ' ' || coalesce(NEW.description, ''));
    NEW.fts_zh := to_tsvector('simple',
        coalesce(NEW.title_zh, '') || ' ' || coalesce(NEW.description_zh, ''));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""

_FTS_TRIGGER = """
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'trg_articles_fts'
    ) THEN
        CREATE TRIGGER trg_articles_fts
            BEFORE INSERT OR UPDATE OF title, description, title_zh, description_zh
            ON articles FOR EACH ROW EXECUTE FUNCTION articles_fts_trigger();
    END IF;
END;
$$;
"""

# ── View: entity co-occurrence network ────────────────────────────────────────

_COOCCURRENCE_VIEW = """
CREATE OR REPLACE VIEW entity_cooccurrence AS
SELECT ae1.entity_id AS entity_a, ae2.entity_id AS entity_b,
       COUNT(DISTINCT ae1.article_id) AS co_occurrence_count
FROM article_entities ae1
JOIN article_entities ae2
  ON ae1.article_id = ae2.article_id AND ae1.entity_id < ae2.entity_id
GROUP BY ae1.entity_id, ae2.entity_id;
"""

# ── Migration tracking ───────────────────────────────────────────────────────

_MIGRATION_TABLE = """
CREATE TABLE IF NOT EXISTS _migrations (
    id          TEXT PRIMARY KEY,
    applied_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""


async def migrate(conn: asyncpg.Connection) -> None:
    """Apply this migration if not already applied."""
    # Ensure migration tracking table
    await conn.execute(_MIGRATION_TABLE)

    row = await conn.fetchrow(
        "SELECT 1 FROM _migrations WHERE id = $1", _MIGRATION_ID
    )
    if row:
        logger.debug("Migration %s already applied, skipping", _MIGRATION_ID)
        return

    logger.info("Applying migration %s …", _MIGRATION_ID)

    # Extensions (require superuser or rds_superuser on Aliyun)
    for stmt in _EXTENSIONS.strip().split(";"):
        stmt = stmt.strip()
        if stmt:
            await conn.execute(stmt + ";")

    # Tables
    for ddl in [
        _ARTICLES, _ENTITIES, _ARTICLE_ENTITIES,
        _ENTITY_RELATIONS, _PUSH_LOG, _CYCLE_LOG,
    ]:
        await conn.execute(ddl)

    # Indexes
    for idx_sql in _ARTICLES_INDEXES:
        await conn.execute(idx_sql)

    # Trigger
    await conn.execute(_FTS_TRIGGER_FUNC)
    await conn.execute(_FTS_TRIGGER)

    # View
    await conn.execute(_COOCCURRENCE_VIEW)

    # Mark as applied
    await conn.execute(
        "INSERT INTO _migrations (id) VALUES ($1)", _MIGRATION_ID
    )
    logger.info("Migration %s applied successfully", _MIGRATION_ID)
