"""三专家评审渠道配置。

- 国际关系专家A → Grok 直连（走本地 LLM_PROXY），模型 grok-4.20-0309-reasoning
- 台湾历史学家B  → Cloubic Claude（无代理）
- 台湾问题研究专家C → Cloubic Gemini（无代理）
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_env_file(path: Path) -> None:
    """轻量 dotenv 加载，不覆盖已存在的环境变量。"""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip()
        if k and k not in os.environ:
            os.environ[k] = v


def bootstrap_env() -> None:
    _load_env_file(PROJECT_ROOT / ".env")
    _load_env_file(PROJECT_ROOT / ".env.cloubic")


@dataclass
class ExpertChannel:
    expert_id: str            # A / B / C
    display_name: str         # 中文角色名
    provider: str             # grok_direct / cloubic_claude / cloubic_gemini
    base_url: str             # 完整 chat/completions URL
    api_key_env: str          # 取 key 的 env 变量名
    model: str
    use_proxy: bool           # 是否使用 LLM_PROXY
    temperature: float = 0.4
    max_tokens: int = 8000


def build_channels() -> list[ExpertChannel]:
    bootstrap_env()

    cloubic_url = os.getenv(
        "CLOUBIC_BASE_URL",
        "https://api.cloubic.com/v1/chat/completions",
    ).strip()

    return [
        ExpertChannel(
            expert_id="A",
            display_name="国际关系专家A",
            provider="perplexity",
            base_url="https://api.perplexity.ai/chat/completions",
            api_key_env="PERPLEXITY_API_KEY",
            model="sonar-pro",
            use_proxy=True,
            temperature=0.3,
            max_tokens=8000,
        ),
        ExpertChannel(
            expert_id="B",
            display_name="台湾历史学家B",
            provider="cloubic_claude",
            base_url=cloubic_url,
            api_key_env="CLOUBIC_API_KEY",
            model="claude-sonnet-4-6",
            use_proxy=False,
            temperature=0.4,
            max_tokens=8000,
        ),
        ExpertChannel(
            expert_id="C",
            display_name="台湾问题研究专家C",
            provider="cloubic_gemini",
            base_url=cloubic_url,
            api_key_env="CLOUBIC_API_KEY",
            model=(os.getenv("CLOUBIC_GEMINI_REASONING_MODEL", "gemini-3.1-pro-preview").split(",")[0].strip()
                   or "gemini-3.1-pro-preview"),
            use_proxy=False,
            temperature=0.4,
            max_tokens=8000,
        ),
        ExpertChannel(
            expert_id="D",
            display_name="情报收集专家D（凡博士）",
            provider="grok_direct_fast",
            base_url="https://api.x.ai/v1/chat/completions",
            api_key_env="GROK_API_KEY",
            model="grok-4-1-fast-non-reasoning",
            use_proxy=True,
            temperature=0.3,
            max_tokens=8000,
        ),
    ]
