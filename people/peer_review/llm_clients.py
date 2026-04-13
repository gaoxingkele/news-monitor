"""OpenAI 兼容三通道 LLM 客户端封装。

- Grok 直连：走 LLM_PROXY 代理
- Cloubic Claude：无代理直连 Cloubic
- Cloubic Gemini：无代理直连 Cloubic

全部使用 httpx 同步客户端以便脚本化运行。
"""
from __future__ import annotations

import json
import logging
import os
import time

import httpx

from .config import ExpertChannel

logger = logging.getLogger("peer_review.llm_clients")


class LLMCallError(RuntimeError):
    pass


def _build_client(channel: ExpertChannel, timeout: float) -> httpx.Client:
    proxy = os.getenv("LLM_PROXY", "").strip() if channel.use_proxy else ""
    kwargs: dict = {
        "timeout": httpx.Timeout(timeout),
        "follow_redirects": True,
        "trust_env": False,
    }
    if proxy:
        kwargs["proxy"] = proxy
    return httpx.Client(**kwargs)


def call_expert(
    channel: ExpertChannel,
    system_prompt: str,
    user_prompt: str,
    *,
    timeout: float = 600.0,
    retries: int = 2,
) -> tuple[str, dict]:
    """对某一专家渠道发起一次 chat/completions 请求。

    返回 (assistant_text, meta)。失败会抛 LLMCallError。
    """
    api_key = os.getenv(channel.api_key_env, "").strip()
    if not api_key:
        raise LLMCallError(f"缺少 API Key: env {channel.api_key_env}")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": channel.model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": channel.temperature,
        "max_tokens": channel.max_tokens,
    }

    last_err: Exception | None = None
    for attempt in range(retries + 1):
        try:
            with _build_client(channel, timeout) as client:
                logger.info(
                    "[%s/%s] POST %s model=%s proxy=%s attempt=%d",
                    channel.expert_id,
                    channel.provider,
                    channel.base_url,
                    channel.model,
                    channel.use_proxy,
                    attempt + 1,
                )
                resp = client.post(channel.base_url, headers=headers, json=payload)
            if resp.status_code != 200:
                raise LLMCallError(
                    f"HTTP {resp.status_code}: {resp.text[:500]}"
                )
            data = resp.json()
            choices = data.get("choices") or []
            if not choices:
                raise LLMCallError(f"空 choices: {json.dumps(data)[:500]}")
            message = choices[0].get("message") or {}
            content = message.get("content") or ""
            if isinstance(content, list):
                # Claude 返回可能是 content blocks
                pieces = []
                for block in content:
                    if isinstance(block, dict) and "text" in block:
                        pieces.append(block["text"])
                content = "\n".join(pieces)
            if not isinstance(content, str) or not content.strip():
                raise LLMCallError(f"空 content: {json.dumps(data)[:500]}")

            meta = {
                "provider": channel.provider,
                "model": channel.model,
                "attempt": attempt + 1,
                "usage": data.get("usage", {}),
                "finish_reason": choices[0].get("finish_reason"),
            }
            return content.strip(), meta
        except Exception as e:  # noqa: BLE001
            last_err = e
            logger.warning(
                "[%s] call failed attempt=%d err=%s", channel.expert_id, attempt + 1, e
            )
            if attempt < retries:
                time.sleep(2.0 * (attempt + 1))

    raise LLMCallError(f"[{channel.expert_id}] 所有重试均失败: {last_err}")
