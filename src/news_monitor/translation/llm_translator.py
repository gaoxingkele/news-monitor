"""LLM-based batch translator — deepseek primary, qwen/kimi fallback.

Optimized for speed: only sends title + short description, large batches
sized to model context window.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

import httpx

from news_monitor.cloubic import resolve_openai_compatible_endpoint
from news_monitor.models import NewsArticle
from news_monitor.proxy import get_proxies_for_url, build_httpx_client
from news_monitor.translation.base import Translator

logger = logging.getLogger("news_monitor.translation")

# Provider configurations with max_batch (estimated by context window)
_PROVIDERS = {
    "doubao": {
        "base_url_env": "DOUBAO_BASE_URL",
        "base_url_default": "https://ark.cn-beijing.volces.com/api/v3",
        "api_key_env": "DOUBAO_API_KEY",
        "model_env": "DOUBAO_MODEL",
        "model": "doubao-1.5-pro-256k",
        "overseas": False,
        "max_batch": 20,     # reduced to avoid ReadTimeout
    },
    "deepseek": {
        "base_url_env": "DEEPSEEK_BASE_URL",
        "base_url_default": "https://api.deepseek.com/v1",
        "api_key_env": "DEEPSEEK_API_KEY",
        "model": "deepseek-chat",
        "overseas": False,
        "max_batch": 25,     # conservative for 128K context
    },
    "qwen": {
        "base_url_env": "QWEN_BASE_URL",
        "base_url_default": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "api_key_env": "QWEN_API_KEY",
        "model": "qwen-long",
        "overseas": False,
        "max_batch": 40,     # reduced from 100 to avoid content-filter killing entire batch
    },
    "kimi": {
        "base_url_env": "KIMI_BASE_URL",
        "base_url_default": "https://api.moonshot.cn/v1",
        "api_key_env": "KIMI_API_KEY",
        "model": "moonshot-v1-auto",
        "overseas": False,
        "max_batch": 50,     # 256K context
    },
    "grok": {
        "base_url_env": "GROK_BASE_URL",
        "base_url_default": "https://api.x.ai/v1",
        "api_key_env": "GROK_API_KEY",
        "model": "grok-4-1-fast-non-reasoning",
        "overseas": True,
        "max_batch": 600,    # 2M context; title-only mode ~50KB for 600 articles
    },
    "gemini": {
        "base_url_env": "GEMINI_BASE_URL",
        "base_url_default": "https://generativelanguage.googleapis.com/v1beta/openai",
        "api_key_env": "GEMINI_API_KEY",
        "model": "gemini-2.5-flash",
        "overseas": True,
        "max_batch": 80,
    },
    "glm": {
        "base_url_env": "GLM_BASE_URL",
        "base_url_default": "https://open.bigmodel.cn/api/paas/v4",
        "api_key_env": "GLM_API_KEY",
        "model": "glm-4-flash",
        "overseas": False,
        "max_batch": 40,
    },
}

_SYSTEM_PROMPT_TEMPLATE = """\
You are a professional news translator. Input may include news articles AND social media posts (tweets).
For each item, output a JSON array where each element has:

1. "title_zh": Simplified Chinese translation of the title.
   If the input is a social media post with no clear headline, condense the content into a \
concise Chinese title (15-30 characters) that captures the key event or claim.
2. "summary_zh": A 80-120 character Chinese summary mentioning {country_zh} and any relevant foreign country.
   If the item has no description (only a title/tweet), generate the summary from the title content.
3. "event_date": "YYYY-MM-DD" if known, else "".
4. "category": One of "china", "taiwan", "us", "sentiment".
   Priority: sentiment > china > taiwan > us.
   If the item does not fit any of these four, use the closest match.

Return ONLY the JSON array, no markdown.\
"""


def _build_system_prompt(country_zh: str, country_en: str, country_key: str = "") -> str:
    return _SYSTEM_PROMPT_TEMPLATE.format(
        country_zh=country_zh,
        country_en=country_en,
    )


def _is_chinese(text: str) -> bool:
    if not text:
        return False
    chinese_chars = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
    return chinese_chars / max(len(text), 1) > 0.3


def _get_max_batch(provider_name: str) -> int:
    prov = _PROVIDERS.get(provider_name, {})
    return prov.get("max_batch", 30)


class LLMTranslator(Translator):
    """Batch translate articles via OpenAI-compatible LLM API."""

    def __init__(
        self,
        provider: str = "qwen",
        fallback_provider: str = "deepseek",
        second_fallback: str = "grok",
        fallback_chain: list[str] | None = None,
        batch_size: int = 0,  # 0 = auto (use provider max_batch)
        skip_if_language: str = "zh",
        overseas_proxy: str = "",
        country_zh: str = "",
        country_en: str = "",
        country_key: str = "",
    ):
        self.provider = provider
        # Build ordered provider chain: explicit list or legacy 3-field style
        if fallback_chain:
            self._chain = [provider] + [p for p in fallback_chain if p]
        else:
            self._chain = [p for p in [provider, fallback_provider, second_fallback] if p]
        self._batch_size_override = batch_size
        self.batch_size = batch_size or _get_max_batch(provider)
        self.skip_if_language = skip_if_language
        self.overseas_proxy = overseas_proxy
        self.country_zh = country_zh
        self.country_en = country_en
        self.country_key = country_key

    async def translate_articles(
        self, articles: list[NewsArticle], target_language: str = "zh-CN"
    ) -> list[NewsArticle]:
        """Translate articles in batches sized to model capacity."""
        to_translate: list[int] = []
        for i, art in enumerate(articles):
            if art.language.startswith(self.skip_if_language) or _is_chinese(art.title):
                art.title_zh = art.title
                art.description_zh = art.description
            to_translate.append(i)

        if not to_translate:
            return articles

        # Batch translate + classify
        bs = self.batch_size
        total_batches = (len(to_translate) + bs - 1) // bs
        for batch_num, batch_start in enumerate(range(0, len(to_translate), bs)):
            batch_indices = to_translate[batch_start:batch_start + bs]
            batch = [articles[i] for i in batch_indices]
            print(f"  [translate] batch {batch_num + 1}/{total_batches} ({len(batch)} articles)...", flush=True)
            translations = await self._translate_batch(batch)

            for idx, trans in zip(batch_indices, translations):
                articles[idx].title_zh = trans.get("title_zh", articles[idx].title)
                articles[idx].description_zh = trans.get(
                    "description_zh", articles[idx].description
                )
                articles[idx].summary_zh = trans.get("summary_zh", "")
                articles[idx].event_date = trans.get("event_date", "")
                articles[idx].category = trans.get("category", "china")

        translated_count = sum(1 for i in to_translate if articles[i].title_zh)
        logger.info("Translated %d/%d articles", translated_count, len(articles))
        return articles

    async def _translate_batch(self, batch: list[NewsArticle]) -> list[dict]:
        """Try providers in order with auto batch-size adjustment and split-retry."""
        for prov_name in self._chain:
            max_b = _get_max_batch(prov_name)
            result = await self._try_provider_with_split(prov_name, batch, max_b)
            if result is not None:
                return result
            logger.warning("Provider %s failed, trying next", prov_name)

    async def _try_provider_with_split(
        self, prov_name: str, batch: list[NewsArticle], max_b: int
    ) -> list[dict] | None:
        """Try a provider; on failure, split batch in half and retry (min 5 per sub-batch)."""
        if len(batch) <= max_b:
            result = await self._call_provider(prov_name, batch)
            if result is not None:
                return result
            # Failed — try splitting in half if batch is large enough
            if len(batch) >= 10:
                mid = len(batch) // 2
                print(f"  [translate] {prov_name} failed on {len(batch)} articles, retrying as 2×{mid}...", flush=True)
                left = await self._call_provider(prov_name, batch[:mid])
                right = await self._call_provider(prov_name, batch[mid:])
                if left is not None and right is not None:
                    return left + right
                # Partial success: keep what we got
                if left is not None:
                    # Right half failed, fill with originals
                    right = [{"title_zh": a.title, "summary_zh": "", "category": "china"} for a in batch[mid:]]
                    return left + right
                if right is not None:
                    left = [{"title_zh": a.title, "summary_zh": "", "category": "china"} for a in batch[:mid]]
                    return left + right
            return None
        else:
            # Batch exceeds provider max — split into sub-batches
            all_results: list[dict] = []
            for sub_start in range(0, len(batch), max_b):
                sub = batch[sub_start:sub_start + max_b]
                result = await self._call_provider(prov_name, sub)
                if result is None:
                    # Try split-retry for this sub-batch
                    if len(sub) >= 10:
                        mid = len(sub) // 2
                        left = await self._call_provider(prov_name, sub[:mid])
                        right = await self._call_provider(prov_name, sub[mid:])
                        if left is not None and right is not None:
                            all_results.extend(left + right)
                            continue
                    return None
                all_results.extend(result)
            return all_results

        # All failed — return originals
        logger.error("All translation providers failed, keeping original text")
        return [
            {"title_zh": art.title, "description_zh": art.description,
             "summary_zh": "", "category": "china"}
            for art in batch
        ]

    async def _call_provider(
        self, provider_name: str, batch: list[NewsArticle]
    ) -> list[dict] | None:
        """Call a single LLM provider for translation.

        Only sends title + truncated description (max 100 chars) to minimize tokens.
        """
        prov = _PROVIDERS.get(provider_name)
        if not prov:
            return None

        api_key = os.environ.get(prov["api_key_env"], "")
        if not api_key:
            logger.error("Missing API key for %s", provider_name)
            return None

        base_url = os.environ.get(prov["base_url_env"], "") or prov["base_url_default"]
        # Normalize: strip /chat/completions if already in base_url (e.g. DOUBAO_BASE_URL)
        base_url = base_url.rstrip("/")
        if base_url.endswith("/chat/completions"):
            base_url = base_url[: -len("/chat/completions")]

        # Model: support env var override (e.g. DOUBAO_MODEL)
        model = prov["model"]
        model_env = prov.get("model_env")
        if model_env:
            model = os.environ.get(model_env, "") or model

        api_key, resolved_base_url, model_chain, via_cloubic = resolve_openai_compatible_endpoint(
            provider_name,
            direct_api_key=api_key,
            direct_base_url=base_url,
            direct_model=model,
            reasoning=False,
        )
        if not api_key:
            logger.error("Missing resolved API key for %s", provider_name)
            return None
        base_url = resolved_base_url.rstrip("/")
        if base_url.endswith("/chat/completions"):
            base_url = base_url[: -len("/chat/completions")]
        url = f"{base_url}/chat/completions"
        model = model_chain[0]

        # Build compact payload: title + description
        items = []
        for art in batch:
            desc = (art.description or "")[:200].strip()
            items.append({"t": art.title, "d": desc})

        user_msg = json.dumps(items, ensure_ascii=False)

        system_prompt = _build_system_prompt(
            self.country_zh, self.country_en, self.country_key
        )
        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_msg},
            ],
            "temperature": 0.1,
        }

        proxy = None
        if prov["overseas"] and not via_cloubic:
            proxy = get_proxies_for_url(url, self.overseas_proxy)

        try:
            timeout = max(60.0, len(batch) * 2.0)  # scale timeout with batch size
            async with build_httpx_client(proxy_url=proxy or "", timeout=timeout) as client:
                resp = await client.post(
                    url, json=body,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                )
                if resp.status_code != 200:
                    body_text = resp.text[:500]
                    logger.error("%s HTTP %d: %s", provider_name, resp.status_code, body_text)
                    print(f"\033[91m  [translate] {provider_name} HTTP {resp.status_code}: {body_text[:200]}\033[0m", flush=True)
                    return None
                data = resp.json()

            content = data["choices"][0]["message"]["content"]
            text = content.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

            translations = json.loads(text)
            if isinstance(translations, list):
                # Pad if short
                while len(translations) < len(batch):
                    translations.append({
                        "title_zh": batch[len(translations)].title,
                        "summary_zh": "",
                        "category": self.country_key,
                    })
                return translations[:len(batch)]
            return None

        except Exception as exc:
            err_detail = f"{type(exc).__name__}: {exc!r}"
            logger.error("Translation via %s failed: %s", provider_name, err_detail)
            print(f"\033[91m  [translate] {provider_name} error: {err_detail}\033[0m", flush=True)
            return None
