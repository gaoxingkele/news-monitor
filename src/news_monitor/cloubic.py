"""Cloubic routing helpers for OpenAI-compatible LLM calls.

This module mirrors the lightweight routing pattern used in the
``stockagent-analysis`` project:

- optionally load ``.env.cloubic``
- route selected providers via Cloubic
- provide model chains for fallback / reasoning variants

It is intentionally limited to chat-completions style calls. Provider-specific
search APIs such as Gemini Google Search grounding and Grok web/x search are
not routed here.
"""
from __future__ import annotations

import os
from pathlib import Path

_CLOUBIC_LOADED = False


def load_cloubic_env() -> None:
    """Load ``.env.cloubic`` from the project root if present."""
    global _CLOUBIC_LOADED
    if _CLOUBIC_LOADED:
        return

    env_path = Path(__file__).resolve().parents[2] / ".env.cloubic"
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            if key and key not in os.environ:
                os.environ[key] = value

    _CLOUBIC_LOADED = True


def cloubic_enabled() -> bool:
    """Whether Cloubic routing is enabled."""
    load_cloubic_env()
    return (
        os.getenv("CLOUBIC_ENABLED", "").strip().lower() == "true"
        and bool(os.getenv("CLOUBIC_API_KEY", "").strip())
    )


def should_route_via_cloubic(provider: str) -> bool:
    """Return whether the given provider should be routed via Cloubic."""
    if not cloubic_enabled():
        return False

    provider = (provider or "").strip().lower()
    if not provider:
        return False

    whitelist = os.getenv("CLOUBIC_ROUTED_PROVIDERS", "").strip()
    if not whitelist:
        return True

    allowed = {item.strip().lower() for item in whitelist.split(",") if item.strip()}
    return provider in allowed


def get_cloubic_base_url() -> str:
    """Return the Cloubic chat-completions base URL."""
    load_cloubic_env()
    return os.getenv("CLOUBIC_BASE_URL", "https://api.cloubic.com/v1/chat/completions").strip()


def get_cloubic_api_key() -> str:
    """Return the Cloubic API key."""
    load_cloubic_env()
    return os.getenv("CLOUBIC_API_KEY", "").strip()


def get_cloubic_model_chain(provider: str, *, reasoning: bool = False) -> list[str]:
    """Return the configured Cloubic model chain for a provider."""
    load_cloubic_env()
    provider = (provider or "").strip().upper()
    if not provider:
        return []

    keys: list[str] = []
    if reasoning:
        keys.append(f"CLOUBIC_{provider}_REASONING_MODEL")
    keys.append(f"CLOUBIC_{provider}_MODEL")

    for key in keys:
        raw = os.getenv(key, "").strip()
        if raw:
            return [item.strip() for item in raw.split(",") if item.strip()]
    return []


def resolve_openai_compatible_endpoint(
    provider: str,
    *,
    direct_api_key: str,
    direct_base_url: str,
    direct_model: str,
    reasoning: bool = False,
) -> tuple[str, str, list[str], bool]:
    """Resolve api_key/base_url/model chain for a chat-completions call."""
    via_cloubic = should_route_via_cloubic(provider)
    if via_cloubic:
        model_chain = get_cloubic_model_chain(provider, reasoning=reasoning) or [direct_model]
        return (
            get_cloubic_api_key(),
            get_cloubic_base_url(),
            model_chain,
            True,
        )

    return (
        direct_api_key,
        direct_base_url,
        [direct_model],
        False,
    )
