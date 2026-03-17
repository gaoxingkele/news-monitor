"""Sentiment classifier: categorize articles by attitude/tone.

Uses an LLM to evaluate each article's sentiment toward the monitored event.
Designed for event-based monitoring (e.g., Boao Forum).

Smart batching: estimates output tokens, packs as many articles as possible
into each API call to minimize round-trips.
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from news_monitor.models import NewsArticle
from news_monitor.proxy import get_proxies_for_url, build_httpx_client

logger = logging.getLogger("news_monitor.filter.sentiment")

# ── Provider config ───────────────────────────────────────────────────────────
_PROVIDERS: dict[str, dict[str, Any]] = {
    "grok": {
        "base_url_env": "GROK_BASE_URL",
        "base_url_default": "https://api.x.ai/v1",
        "api_key_env": "GROK_API_KEY",
        "model": "grok-4-1-fast-reasoning",
        "overseas": True,
        "max_output_tokens": 100000,   # conservative estimate of output limit
        "tokens_per_article": 120,     # ~output tokens per article in response
    },
    "qwen": {
        "base_url_env": "QWEN_BASE_URL",
        "base_url_default": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "api_key_env": "QWEN_API_KEY",
        "model": "qwen-long",
        "overseas": False,
        "max_output_tokens": 8000,
        "tokens_per_article": 120,
    },
    "deepseek": {
        "base_url_env": "DEEPSEEK_BASE_URL",
        "base_url_default": "https://api.deepseek.com/v1",
        "api_key_env": "DEEPSEEK_API_KEY",
        "model": "deepseek-chat",
        "overseas": False,
        "max_output_tokens": 8000,
        "tokens_per_article": 120,
    },
    "doubao": {
        "base_url_env": "DOUBAO_BASE_URL",
        "base_url_default": "https://ark.cn-beijing.volces.com/api/v3",
        "api_key_env": "DOUBAO_API_KEY",
        "model_env": "DOUBAO_MODEL",
        "model": "doubao-1.5-pro-256k",
        "overseas": False,
        "max_output_tokens": 8000,
        "tokens_per_article": 120,
    },
    "kimi": {
        "base_url_env": "KIMI_BASE_URL",
        "base_url_default": "https://api.moonshot.cn/v1",
        "api_key_env": "KIMI_API_KEY",
        "model": "moonshot-v1-auto",
        "overseas": False,
        "max_output_tokens": 8000,
        "tokens_per_article": 120,
    },
}

# ── System prompt ─────────────────────────────────────────────────────────────
_SYSTEM_PROMPT_TEMPLATE = """\
You are a media sentiment analyst specializing in international events coverage.

Given a list of news articles about "{event_name_zh}" ({event_name_en}), \
classify each article's SENTIMENT toward the event and China.

Categories:
- "positive": praising, supportive, constructive, optimistic
- "neutral": factual reporting, balanced, data-driven
- "negative": critical, skeptical, hostile, questioning motives
- "analysis": deep geopolitical analysis, nuanced multi-angle commentary

For each article, return:
{{"id": <index>, "sentiment": "<positive|neutral|negative|analysis>", \
"key_attitude": "<一句话核心态度（中文）>", "importance": <1-5>}}

Return ONLY a JSON array. No markdown, no extra text.\
"""


def _estimate_max_batch(provider_name: str) -> int:
    """Estimate how many articles fit in one API call based on output token budget."""
    prov = _PROVIDERS.get(provider_name, {})
    max_out = prov.get("max_output_tokens", 8000)
    per_article = prov.get("tokens_per_article", 120)
    return max(10, max_out // per_article)


def _repair_json(text: str) -> list[dict] | None:
    """Try to parse truncated/malformed JSON arrays.

    Strategies:
    1. Direct parse
    2. Strip markdown fences
    3. Truncated array: find last complete object, close array
    4. Parse line-by-line JSON objects
    """
    text = text.strip()

    # Strategy 1: direct
    try:
        result = json.loads(text)
        if isinstance(result, list):
            return result
    except json.JSONDecodeError:
        pass

    # Strategy 2: strip markdown
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        try:
            result = json.loads(text)
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass

    # Strategy 3: truncated array — find last complete }, close ]
    if text.startswith("["):
        # Find last complete JSON object
        last_brace = text.rfind("}")
        if last_brace > 0:
            candidate = text[:last_brace + 1].rstrip(", \n\r\t") + "]"
            try:
                result = json.loads(candidate)
                if isinstance(result, list):
                    return result
            except json.JSONDecodeError:
                pass

    # Strategy 4: extract individual objects with regex
    objects = []
    for m in re.finditer(r'\{[^{}]+\}', text):
        try:
            obj = json.loads(m.group())
            if "id" in obj:
                objects.append(obj)
        except json.JSONDecodeError:
            continue
    if objects:
        return objects

    return None


class SentimentClassifier:
    """LLM-powered sentiment classifier for event-based monitoring."""

    def __init__(
        self,
        provider: str = "grok",
        fallback_chain: list[str] | None = None,
        batch_size: int = 0,
        overseas_proxy: str = "",
    ):
        self.provider = provider
        if fallback_chain:
            self._chain = [provider] + [p for p in fallback_chain if p]
        else:
            self._chain = [provider]
        self.overseas_proxy = overseas_proxy
        # batch_size=0 means auto (estimate from output token budget)
        self._batch_size_override = batch_size

    def _get_batch_size(self, provider_name: str) -> int:
        if self._batch_size_override > 0:
            return self._batch_size_override
        return _estimate_max_batch(provider_name)

    async def classify_articles(
        self,
        articles: list[NewsArticle],
        event_name_zh: str,
        event_name_en: str,
    ) -> tuple[list[NewsArticle], list[dict]]:
        """Classify articles by sentiment. Sets art.category to sentiment value."""
        if not articles:
            return [], []

        system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(
            event_name_zh=event_name_zh,
            event_name_en=event_name_en,
        )

        log: list[dict] = []

        # Try providers in order
        for prov_name in self._chain:
            if not prov_name:
                continue
            prov_cfg = _PROVIDERS.get(prov_name, {})
            if not prov_cfg:
                continue
            api_key = os.environ.get(prov_cfg["api_key_env"], "")
            if not api_key:
                continue

            batch_size = self._get_batch_size(prov_name)
            total_batches = (len(articles) + batch_size - 1) // batch_size
            print(f"  [sentiment] {prov_name}: {len(articles)} articles → {total_batches} batch(es) of ~{batch_size}", flush=True)

            all_ok = True
            for batch_start in range(0, len(articles), batch_size):
                batch = articles[batch_start: batch_start + batch_size]
                batch_num = batch_start // batch_size + 1
                print(f"  [sentiment] batch {batch_num}/{total_batches} ({len(batch)} articles)...", flush=True)

                results = await self._call_with_retry(prov_name, batch, system_prompt)
                if results is None:
                    all_ok = False
                    break

                for entry in results:
                    idx = entry.get("id", 0)
                    if idx >= len(batch):
                        continue
                    art = batch[idx]
                    sentiment = entry.get("sentiment", "neutral")
                    if sentiment not in ("positive", "neutral", "negative", "analysis"):
                        sentiment = "neutral"
                    art.category = sentiment
                    key_attitude = entry.get("key_attitude", "")
                    if key_attitude and not art.summary_zh:
                        art.summary_zh = key_attitude

                    log.append({
                        "id": batch_start + idx,
                        "title": art.title_zh or art.title,
                        "sentiment": sentiment,
                        "key_attitude": key_attitude,
                        "importance": entry.get("importance", 3),
                        "reason": entry.get("reason", ""),
                    })

            if all_ok:
                return articles, log
            logger.warning("Provider %s had failures, trying next", prov_name)

        # All providers failed
        logger.error("All sentiment providers failed; defaulting to neutral")
        for art in articles:
            if not art.category:
                art.category = "neutral"
        return articles, log

    async def _call_with_retry(
        self, provider_name: str, batch: list[NewsArticle], system_prompt: str
    ) -> list[dict] | None:
        """Call provider; on failure, split in half and retry recursively."""
        result = await self._call_provider(provider_name, batch, system_prompt)
        if result is not None:
            return result

        # Failed — split in half if batch is large enough
        if len(batch) < 10:
            return None

        mid = len(batch) // 2
        print(f"  [sentiment] {provider_name} failed on {len(batch)}, splitting to 2×{mid}...", flush=True)
        left = await self._call_provider(provider_name, batch[:mid], system_prompt)
        right = await self._call_provider(provider_name, batch[mid:], system_prompt)

        if left is not None and right is not None:
            # Remap right-half IDs
            for r in right:
                r["id"] = r.get("id", 0) + mid
            return left + right

        # One half succeeded — fill the other with defaults
        if left is not None:
            defaults = [{"id": mid + i, "sentiment": "neutral", "key_attitude": "", "importance": 3} for i in range(len(batch) - mid)]
            return left + defaults
        if right is not None:
            defaults = [{"id": i, "sentiment": "neutral", "key_attitude": "", "importance": 3} for i in range(mid)]
            for r in right:
                r["id"] = r.get("id", 0) + mid
            return defaults + right

        return None

    async def _call_provider(
        self, provider_name: str, batch: list[NewsArticle], system_prompt: str
    ) -> list[dict] | None:
        prov = _PROVIDERS.get(provider_name)
        if not prov:
            return None

        api_key = os.environ.get(prov["api_key_env"], "")
        if not api_key:
            return None

        base_url = os.environ.get(prov["base_url_env"], "") or prov["base_url_default"]
        base_url = base_url.rstrip("/")
        if base_url.endswith("/chat/completions"):
            base_url = base_url[: -len("/chat/completions")]
        url = f"{base_url}/chat/completions"

        model = prov["model"]
        model_env = prov.get("model_env")
        if model_env:
            model = os.environ.get(model_env, "") or model

        items = []
        for i, art in enumerate(batch):
            title = art.title_zh or art.title
            items.append({"id": i, "title": title})
        user_msg = json.dumps(items, ensure_ascii=False)

        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_msg},
            ],
            "temperature": 0.0,
        }

        proxy = None
        if prov["overseas"]:
            proxy = get_proxies_for_url(url, self.overseas_proxy)

        try:
            timeout = max(120.0, len(batch) * 2.0)
            async with build_httpx_client(proxy_url=proxy or "", timeout=timeout) as client:
                resp = await client.post(
                    url, json=body,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                )
                resp.raise_for_status()
                data = resp.json()

            content = data["choices"][0]["message"]["content"].strip()
            results = _repair_json(content)

            if results:
                # Pad if short (some articles may have been skipped)
                seen_ids = {r.get("id") for r in results}
                for i in range(len(batch)):
                    if i not in seen_ids:
                        results.append({"id": i, "sentiment": "neutral", "key_attitude": "", "importance": 3})
                results.sort(key=lambda r: r.get("id", 0))
                parsed = len([r for r in results if r.get("id", -1) < len(batch)])
                print(f"  [sentiment] {provider_name}: parsed {parsed}/{len(batch)} articles", flush=True)
                return results[:len(batch)]

            logger.error("Sentiment %s: could not parse response (%d chars)", provider_name, len(content))

        except Exception as exc:
            err_detail = f"{type(exc).__name__}: {exc!r}"
            logger.error("Sentiment via %s failed: %s", provider_name, err_detail)
            print(f"\033[91m  [sentiment] {provider_name} error: {err_detail}\033[0m", flush=True)

        return None
