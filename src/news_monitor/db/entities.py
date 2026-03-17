"""Entities + knowledge graph CRUD — nodes, article links, and entity relations."""
from __future__ import annotations

import logging
from typing import Optional

from news_monitor.db.pool import get_pool

logger = logging.getLogger("news_monitor.db.entities")


async def upsert_entity(
    name: str,
    entity_type: str,
    name_zh: str = "",
    description: str = "",
) -> Optional[int]:
    """Insert or update an entity, returning its DB id."""
    if not name or not entity_type:
        return None

    pool = get_pool()
    row = await pool.fetchrow(
        """
        INSERT INTO entities (name, entity_type, name_zh, description)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (name, entity_type) DO UPDATE SET
            name_zh = CASE WHEN EXCLUDED.name_zh != '' THEN EXCLUDED.name_zh
                           ELSE entities.name_zh END,
            description = CASE WHEN EXCLUDED.description != '' THEN EXCLUDED.description
                               ELSE entities.description END
        RETURNING id
        """,
        name,
        entity_type,
        name_zh,
        description,
    )
    return row["id"] if row else None


async def link_article_entity(
    article_id: int,
    entity_id: int,
    role: str = "mentioned",
    confidence: float = 1.0,
    context_snippet: str = "",
) -> None:
    """Create an article ↔ entity link (upsert)."""
    pool = get_pool()
    await pool.execute(
        """
        INSERT INTO article_entities (article_id, entity_id, role, confidence, context_snippet)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (article_id, entity_id, role) DO UPDATE SET
            confidence = EXCLUDED.confidence
        """,
        article_id,
        entity_id,
        role,
        confidence,
        context_snippet,
    )


async def upsert_relation(
    source_entity: int,
    target_entity: int,
    relation_type: str,
    confidence: float = 1.0,
) -> None:
    """Create or update an entity → entity relation edge."""
    pool = get_pool()
    await pool.execute(
        """
        INSERT INTO entity_relations (source_entity, target_entity, relation_type, confidence)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (source_entity, target_entity, relation_type) DO UPDATE SET
            last_seen_at = NOW(),
            article_count = entity_relations.article_count + 1,
            confidence = GREATEST(entity_relations.confidence, EXCLUDED.confidence)
        """,
        source_entity,
        target_entity,
        relation_type,
        confidence,
    )


async def get_entity_graph(entity_name: str, max_hops: int = 2) -> list[dict]:
    """Multi-hop graph traversal from a starting entity using recursive CTE.

    Returns list of {source, target, relation, hop} edges.
    """
    pool = get_pool()
    rows = await pool.fetch(
        """
        WITH RECURSIVE graph AS (
            -- Base: find the starting entity
            SELECT er.source_entity, er.target_entity, er.relation_type, 1 AS hop
            FROM entity_relations er
            JOIN entities e ON e.id = er.source_entity
            WHERE e.name = $1

            UNION ALL

            SELECT er.source_entity, er.target_entity, er.relation_type, g.hop + 1
            FROM entity_relations er
            JOIN graph g ON er.source_entity = g.target_entity
            WHERE g.hop < $2
        )
        SELECT
            src.name  AS source_name,
            tgt.name  AS target_name,
            g.relation_type,
            g.hop
        FROM graph g
        JOIN entities src ON src.id = g.source_entity
        JOIN entities tgt ON tgt.id = g.target_entity
        ORDER BY g.hop, src.name
        """,
        entity_name,
        max_hops,
    )
    return [dict(r) for r in rows]


async def get_entity_cooccurrences(
    entity_name: str, limit: int = 20
) -> list[dict]:
    """Find entities that co-occur with the given entity in articles."""
    pool = get_pool()
    rows = await pool.fetch(
        """
        SELECT e2.name, e2.entity_type, e2.name_zh,
               COUNT(DISTINCT ae1.article_id) AS co_count
        FROM article_entities ae1
        JOIN entities e1 ON e1.id = ae1.entity_id
        JOIN article_entities ae2 ON ae2.article_id = ae1.article_id
                                  AND ae2.entity_id != ae1.entity_id
        JOIN entities e2 ON e2.id = ae2.entity_id
        WHERE e1.name = $1
        GROUP BY e2.id, e2.name, e2.entity_type, e2.name_zh
        ORDER BY co_count DESC
        LIMIT $2
        """,
        entity_name,
        limit,
    )
    return [dict(r) for r in rows]
