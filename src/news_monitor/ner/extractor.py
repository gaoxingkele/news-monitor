"""LLM-based NER extraction — reuses the translation provider pattern."""
from __future__ import annotations

import json
import logging
import os
from typing import Any

import httpx

from news_monitor.models import NewsArticle
from news_monitor.ner.prompts import NER_SYSTEM_PROMPT
from news_monitor.proxy import get_proxies_for_url

logger = logging.getLogger("news_monitor.ner")

# Reuse the same provider map as llm_translator
_PROVIDERS = {
    "deepseek": {
        "base_url_env": "DEEPSEEK_BASE_URL",
        "base_url_default": "https://api.deepseek.com/v1",
        "api_key_env": "DEEPSEEK_API_KEY",
        "model": "deepseek-chat",
        "overseas": False,
    },
    "kimi": {
        "base_url_env": "KIMI_BASE_URL",
        "base_url_default": "https://api.moonshot.cn/v1",
        "api_key_env": "KIMI_API_KEY",
        "model": "moonshot-v1-auto",
        "overseas": False,
    },
    "grok": {
        "base_url_env": "GROK_BASE_URL",
        "base_url_default": "https://api.x.ai/v1",
        "api_key_env": "GROK_API_KEY",
        "model": "grok-3-mini-fast",
        "overseas": True,
    },
    "gemini": {
        "base_url_env": "GEMINI_BASE_URL",
        "base_url_default": "https://generativelanguage.googleapis.com/v1beta/openai",
        "api_key_env": "GEMINI_API_KEY",
        "model": "gemini-2.5-flash",
        "overseas": True,
    },
}


async def extract_entities_batch(
    articles: list[NewsArticle],
    db_ids: list[int],
    ner_cfg: dict,
    overseas_proxy: str,
) -> int:
    """Extract entities from articles and store in DB.

    Returns total number of article-entity links created.
    """
    provider = ner_cfg.get("provider", "deepseek")
    fallback = ner_cfg.get("fallback_provider", "kimi")
    batch_size = ner_cfg.get("batch_size", 3)
    total_links = 0

    for batch_start in range(0, len(articles), batch_size):
        batch_articles = articles[batch_start : batch_start + batch_size]
        batch_ids = db_ids[batch_start : batch_start + batch_size]

        ner_result = await _call_ner_provider(provider, batch_articles, overseas_proxy)
        if ner_result is None and fallback:
            logger.warning("NER primary %s failed, trying fallback %s", provider, fallback)
            ner_result = await _call_ner_provider(fallback, batch_articles, overseas_proxy)

        if ner_result is None:
            logger.error("NER: all providers failed for batch starting at %d", batch_start)
            continue

        links = await _store_ner_results(ner_result, batch_articles, batch_ids)
        total_links += links

    return total_links


async def _call_ner_provider(
    provider_name: str,
    batch: list[NewsArticle],
    overseas_proxy: str,
) -> dict | None:
    """Call LLM provider for NER extraction."""
    prov = _PROVIDERS.get(provider_name)
    if not prov:
        logger.error("Unknown NER provider: %s", provider_name)
        return None

    api_key = os.environ.get(prov["api_key_env"], "")
    if not api_key:
        logger.error("Missing API key for NER provider %s", provider_name)
        return None

    base_url = os.environ.get(prov["base_url_env"], prov["base_url_default"])
    url = f"{base_url}/chat/completions"

    items = []
    for art in batch:
        items.append({
            "title": art.title,
            "description": art.description[:300],
            "title_zh": art.title_zh,
            "description_zh": art.description_zh[:300],
        })

    body = {
        "model": prov["model"],
        "messages": [
            {"role": "system", "content": NER_SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(items, ensure_ascii=False)},
        ],
        "temperature": 0.1,
    }

    proxy = None
    if prov["overseas"]:
        proxy = get_proxies_for_url(url, overseas_proxy)

    try:
        async with httpx.AsyncClient(
            timeout=60.0, proxy=proxy, follow_redirects=True
        ) as client:
            resp = await client.post(
                url, json=body,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        content = data["choices"][0]["message"]["content"]
        text = content.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

        result = json.loads(text)
        if isinstance(result, dict) and "entities" in result:
            return result
        logger.warning("NER %s returned unexpected format", provider_name)
        return None

    except Exception as exc:
        logger.error("NER via %s failed: %s", provider_name, exc)
        return None


async def _store_ner_results(
    ner_result: dict,
    articles: list[NewsArticle],
    db_ids: list[int],
) -> int:
    """Store extracted entities and relations into the DB."""
    from news_monitor.db.entities import upsert_entity, link_article_entity, upsert_relation

    entities_data = ner_result.get("entities", [])
    relations_data = ner_result.get("relations", [])
    total_links = 0

    # Map entity name → db entity id for relation linking
    entity_name_to_id: dict[str, int] = {}

    for ent in entities_data:
        idx = ent.get("article_index", 0)
        if idx < 0 or idx >= len(db_ids):
            continue

        entity_id = await upsert_entity(
            name=ent.get("name", ""),
            entity_type=ent.get("type", "TOPIC"),
            name_zh=ent.get("name_zh", ""),
        )
        if entity_id is None:
            continue

        entity_name_to_id[ent["name"]] = entity_id

        await link_article_entity(
            article_id=db_ids[idx],
            entity_id=entity_id,
            role=ent.get("role", "mentioned"),
        )
        total_links += 1

    # Store relations
    for rel in relations_data:
        src_id = entity_name_to_id.get(rel.get("source", ""))
        tgt_id = entity_name_to_id.get(rel.get("target", ""))
        if src_id and tgt_id:
            await upsert_relation(
                source_entity=src_id,
                target_entity=tgt_id,
                relation_type=rel.get("relation", "related_to"),
            )

    return total_links
