"""Relevance filter: keep only articles that matter to Chinese interests.

Uses an LLM (Grok preferred, fallback chain) to evaluate each article.
Runs as an independent Agent step after translation, before PDF generation.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

import httpx

from news_monitor.models import NewsArticle
from news_monitor.proxy import get_proxies_for_url, build_httpx_client

logger = logging.getLogger("news_monitor.filter.relevance")

# ── Provider config ───────────────────────────────────────────────────────────
_PROVIDERS: dict[str, dict[str, Any]] = {
    "grok": {
        "base_url_env": "GROK_BASE_URL",
        "base_url_default": "https://api.x.ai/v1",
        "api_key_env": "GROK_API_KEY",
        "model": "grok-4-1-fast-non-reasoning",
        "overseas": True,
        "max_batch": 200,    # 2M context
    },
    "doubao": {
        "base_url_env": "DOUBAO_BASE_URL",
        "base_url_default": "https://ark.cn-beijing.volces.com/api/v3",
        "api_key_env": "DOUBAO_API_KEY",
        "model_env": "DOUBAO_MODEL",
        "model": "doubao-1.5-pro-256k",
        "overseas": False,
        "max_batch": 50,
    },
    "deepseek": {
        "base_url_env": "DEEPSEEK_BASE_URL",
        "base_url_default": "https://api.deepseek.com/v1",
        "api_key_env": "DEEPSEEK_API_KEY",
        "model": "deepseek-chat",
        "overseas": False,
        "max_batch": 30,
    },
    "qwen": {
        "base_url_env": "QWEN_BASE_URL",
        "base_url_default": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "api_key_env": "QWEN_API_KEY",
        "model": "qwen-long",
        "overseas": False,
        "max_batch": 40,
    },
    "kimi": {
        "base_url_env": "KIMI_BASE_URL",
        "base_url_default": "https://api.moonshot.cn/v1",
        "api_key_env": "KIMI_API_KEY",
        "model": "moonshot-v1-auto",
        "overseas": False,
        "max_batch": 50,
    },
    "glm": {
        "base_url_env": "GLM_BASE_URL",
        "base_url_default": "https://open.bigmodel.cn/api/paas/v4",
        "api_key_env": "GLM_API_KEY",
        "model": "glm-4-flash",
        "overseas": False,
        "max_batch": 30,
    },
}

# ── System prompt ─────────────────────────────────────────────────────────────
_SYSTEM_PROMPT_TEMPLATE = """\
You are an analyst for Chinese foreign policy and strategic interests.

Your task: given a list of news articles about {country_zh} ({country_en}), \
decide which ones are RELEVANT and which are NOT.

An article is RELEVANT if it falls into ANY of these five lines:

━━ LINE 1: 中国线（中门槛）━━
KEEP:
- Chinese companies investing, expanding, or building in {country_zh} (factories, ports, mining, retail, tech)
- Bilateral diplomatic proposals, agreements, MOUs, friendship groups
- Policy changes affecting Chinese interests (tariffs, investment reviews, FDI restrictions)
- Chinese economic footprint data (market share, trade volume changes, industrial park presence)
- Natural resources (minerals, energy, ports) relevant to BRI or Chinese trade
FILTER:
- Pure travel/visa/tourism tips for Chinese tourists
- Chinese New Year or Spring Festival celebrations (unless politically significant)
- General food safety warnings about Chinese products (garlic, cosmetics) with no policy action
- Pure opinion/commentary articles that describe no new event
- Articles about China's domestic economy (GDP targets, FDI decline) with no direct link to {country_zh}

━━ LINE 2: 台湾线（低门槛 — 台湾的外交工具以软实力为主，门槛应低于其他线）━━
KEEP (almost everything Taiwan-related):
- Cultural diplomacy: dance groups, art exhibitions, cultural festivals, film screenings
- Education: scholarships, ICDF programs, university exchanges, training programs
- Sports diplomacy: youth exchanges, sports cooperation, athletic events
- Economic diplomacy: manufacturing alliances, trade partnerships, technology cooperation
- Official visits, diplomatic statements, embassy/representative office activities
- Taiwan flag/sovereignty incidents and China's reactions
- Any article mentioning Taiwan's diplomatic recognition or switching
FILTER:
- Articles about Taiwan's activities in OTHER countries that do NOT involve {country_zh} \
  (e.g., Taiwan scholarships in Paraguay when monitoring Uruguay — FILTER even if {country_zh} \
  is "in the same region"; the article must mention {country_zh} as an active participant or \
  direct target, not merely as a regional neighbor)
- Routine consular cases (passport/visa processing) with no diplomatic significance
- One-sentence wire mentions with no substantive content

━━ LINE 3: 美国线（中高门槛）━━
KEEP:
- Summits, treaties, trade agreements (USMCA/T-MEC, CAFTA, etc.) — concrete events
- Sanctions, tariffs, policy changes affecting {country_zh}
- Military/security cooperation agreements
- Explicit diplomatic inclusion/exclusion actions (e.g., excluding from summits)
- US actions that directly constrain or enable China's position in the region
FILTER:
- Market second-order effects: oil price changes, bond ratings, currency movements
- REDUNDANCY: if the same event (e.g., USMCA review) already appears in 3+ articles, \
keep only the 2-3 with the most detail/substance, mark the rest as NOT RELEVANT \
with reason "同一事件重复报道"
- Pure analyst commentary with no new event

━━ LINE 4: 对华舆情与风险信号（新增维度）━━
KEEP:
- Anti-Chinese sentiment: protests, xenophobia incidents, "invasion" rhetoric
- Labor disputes at Chinese-owned companies (strikes, blockades, layoffs)
- Crimes targeting Chinese nationals or Chinese-owned businesses
- Legislative proposals to restrict Chinese investment or immigration
- Media campaigns or public opinion shifts regarding China
- Historical anti-Chinese events, persecution archives, reparation demands
- Community friction between Chinese immigrants and local residents
FILTER:
- Neutral immigration statistics with no conflict/reaction angle

━━ LINE 5: 地区地缘政治（高门槛）━━
KEEP:
- Regional diplomatic realignments (e.g., country X expels diplomats from country Y)
- Multilateral bloc changes that affect China/Taiwan/US power balance
- Cross-border events with direct strategic spillover to {country_zh}
FILTER:
- Third-country domestic events that only tangentially mention {country_zh}
- Natural disasters in other countries (earthquakes, flights) unless they create strategic consequences

━━ ALWAYS FILTER (regardless of line) ━━
- Pure domestic {country_zh} affairs: local elections, crime, entertainment, sports results, \
  internal politics with ZERO foreign dimension
- Generic financial reports: quarterly earnings, stock comparisons, market sizing reports
- {country_zh} airport/tourism statistics with no foreign policy angle
- Articles where {country_zh} is merely mentioned in passing but is not an active participant
- CRITICAL: Articles about events in OTHER countries that do NOT directly involve {country_zh}. \
  Being "in the same region" or "a neighboring country" is NOT sufficient. The article must \
  describe an event where {country_zh} is a named participant, target, or directly affected party. \
  Example: "Taiwan gives scholarships to Paraguay students" is NOT relevant when monitoring Uruguay.

For each article, return a JSON array (same length as input), each element:
{{
  "id": <0-based index>,
  "relevant": true or false,
  "line": "<china|taiwan|us|sentiment|geopolitics|none>",
  "reason": "<one short sentence in Chinese explaining why>"
}}

Return ONLY the JSON array. No markdown, no extra text.\
"""


class RelevanceFilter:
    """LLM-powered agent that filters articles by relevance to Chinese interests."""

    def __init__(
        self,
        provider: str = "grok",
        fallback_chain: list[str] | None = None,
        # Legacy compat
        fallback_provider: str = "",
        second_fallback: str = "",
        batch_size: int = 0,  # 0 = auto (use provider max_batch)
        overseas_proxy: str = "",
    ):
        self.provider = provider
        if fallback_chain:
            self._chain = [provider] + [p for p in fallback_chain if p]
        else:
            self._chain = [p for p in [provider, fallback_provider, second_fallback] if p]
        # Auto batch size from provider config
        prov_cfg = _PROVIDERS.get(provider, {})
        self.batch_size = batch_size or prov_cfg.get("max_batch", 30)
        self.overseas_proxy = overseas_proxy

    async def filter_articles(
        self,
        articles: list[NewsArticle],
        country_zh: str,
        country_en: str,
    ) -> tuple[list[NewsArticle], list[dict]]:
        """Return (kept_articles, filter_log)."""
        if not articles:
            return [], []

        system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(
            country_zh=country_zh,
            country_en=country_en,
        )

        kept: list[NewsArticle] = []
        log: list[dict] = []

        total_batches = (len(articles) + self.batch_size - 1) // self.batch_size
        for batch_num, batch_start in enumerate(range(0, len(articles), self.batch_size)):
            batch = articles[batch_start: batch_start + self.batch_size]
            print(f"  [filter] batch {batch_num + 1}/{total_batches} ({len(batch)} articles)...", flush=True)
            results = await self._evaluate_batch(batch, system_prompt)

            for entry in results:
                idx = entry.get("id", 0)
                if idx >= len(batch):
                    continue
                art = batch[idx]
                relevant = bool(entry.get("relevant", True))
                reason = entry.get("reason", "")
                log.append({
                    "id": batch_start + idx,
                    "title": art.title_zh or art.title,
                    "relevant": relevant,
                    "reason": reason,
                })
                if relevant:
                    kept.append(art)

        return kept, log

    async def _evaluate_batch(
        self, batch: list[NewsArticle], system_prompt: str
    ) -> list[dict]:
        """Try providers in order; return evaluation list."""
        for prov_name in self._chain:
            if not prov_name:
                continue
            prov_cfg = _PROVIDERS.get(prov_name, {})
            max_b = prov_cfg.get("max_batch", 30)

            if len(batch) <= max_b:
                result = await self._call_provider(prov_name, batch, system_prompt)
                if result is not None:
                    return result
            else:
                # Split into sub-batches for this provider
                all_results: list[dict] = []
                ok = True
                for sub_start in range(0, len(batch), max_b):
                    sub = batch[sub_start:sub_start + max_b]
                    # Remap IDs for sub-batch
                    result = await self._call_provider(prov_name, sub, system_prompt)
                    if result is None:
                        ok = False
                        break
                    # Offset IDs back to batch-level
                    for r in result:
                        r["id"] = r.get("id", 0) + sub_start
                    all_results.extend(result)
                if ok:
                    return all_results

            logger.warning("Provider %s failed, trying next", prov_name)

        # All providers failed — keep everything (safe default)
        logger.error("All filter providers failed; keeping entire batch")
        return [{"id": i, "relevant": True, "reason": "filter unavailable"} for i in range(len(batch))]

    async def _call_provider(
        self, provider_name: str, batch: list[NewsArticle], system_prompt: str
    ) -> list[dict] | None:
        prov = _PROVIDERS.get(provider_name)
        if not prov:
            return None

        api_key = os.environ.get(prov["api_key_env"], "")
        if not api_key:
            logger.debug("No API key for %s (%s), skipping", provider_name, prov["api_key_env"])
            return None

        base_url = os.environ.get(prov["base_url_env"], "") or prov["base_url_default"]
        base_url = base_url.rstrip("/")
        if base_url.endswith("/chat/completions"):
            base_url = base_url[: -len("/chat/completions")]
        url = f"{base_url}/chat/completions"

        # Model: support env var override (e.g. DOUBAO_MODEL)
        model = prov["model"]
        model_env = prov.get("model_env")
        if model_env:
            model = os.environ.get(model_env, "") or model

        # Build user message: id + title + summary
        items = []
        for i, art in enumerate(batch):
            title = art.title_zh or art.title
            summary = art.summary_zh or art.description or ""
            items.append({
                "id": i,
                "title": title,
                "summary": summary[:200],
            })
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
            # Scale timeout with batch size (min 60s, ~1s per article)
            timeout = max(60.0, len(batch) * 1.5)
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
            if content.startswith("```"):
                content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

            results = json.loads(content)
            if isinstance(results, list):
                # Pad if short
                while len(results) < len(batch):
                    results.append({"id": len(results), "relevant": True, "reason": "no judgment"})
                return results[:len(batch)]

        except Exception as exc:
            err_detail = f"{type(exc).__name__}: {exc!r}"
            logger.error("Filter via %s failed: %s", provider_name, err_detail)
            print(f"\033[91m  [filter] {provider_name} error: {err_detail}\033[0m", flush=True)

        return None
