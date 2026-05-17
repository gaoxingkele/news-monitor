"""Interactive Topic Builder — converts natural-language description into a topics/*.md file.

Usage:
    python tools/new_topic.py

Reads API credentials from the project root .env file.
Uses DeepSeek as primary LLM provider, Kimi as fallback.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Bootstrap: project root and .env
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

TOPICS_DIR = PROJECT_ROOT / "topics"

# ---------------------------------------------------------------------------
# LLM provider table (mirrors llm_translator.py conventions)
# ---------------------------------------------------------------------------

_PROVIDERS = {
    "deepseek": {
        "base_url": os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
        "api_key_env": "DEEPSEEK_API_KEY",
        "model": "deepseek-chat",
    },
    "kimi": {
        "base_url": os.environ.get("KIMI_BASE_URL", "https://api.moonshot.cn/v1"),
        "api_key_env": "KIMI_API_KEY",
        "model": "moonshot-v1-auto",
    },
}

_SYSTEM_PROMPT = """\
You are a senior media monitoring expert specializing in global news intelligence.

Given a natural-language description of a monitoring topic, produce a structured JSON object \
with the following fields:

{
  "name": "<concise Chinese topic name, ≤12 characters>",
  "filename": "<snake_case filename without .md extension>",
  "description": "<one-sentence Chinese description>",
  "countries": ["<ISO 3166-1 alpha-2 country codes>"],
  "languages": ["<ISO 639-1 language codes>"],
  "time_range_hours": <integer, e.g. 48 or 72>,
  "max_articles": <integer, e.g. 20 or 30>,
  "keywords": {
    "primary": ["<high-signal multi-word phrases in all relevant languages>"],
    "secondary": ["<single supporting keywords>"]
  },
  "exclude_keywords": ["<noise terms to filter out>"]
}

Rules:
- keywords.primary must cover Chinese, English, and the dominant local language(s).
- keywords.secondary contains contextual single-words (no phrases needed).
- exclude_keywords should reduce obvious off-topic noise.
- time_range_hours and max_articles must be reasonable integers.
- countries and languages must be valid ISO codes as lowercase strings.
- Return ONLY valid JSON, no markdown fences, no explanation text.
"""


# ---------------------------------------------------------------------------
# LLM call
# ---------------------------------------------------------------------------

def _call_llm(description: str) -> dict:
    """Call LLM with description; try primary then fallback provider."""
    for provider_name, cfg in _PROVIDERS.items():
        api_key = os.environ.get(cfg["api_key_env"], "")
        if not api_key:
            print(f"[skip] {provider_name}: API key not set ({cfg['api_key_env']})")
            continue
        try:
            response = httpx.post(
                f"{cfg['base_url']}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}",
                         "Content-Type": "application/json"},
                json={
                    "model": cfg["model"],
                    "messages": [
                        {"role": "system", "content": _SYSTEM_PROMPT},
                        {"role": "user", "content": description},
                    ],
                    "temperature": 0.3,
                    "response_format": {"type": "json_object"},
                },
                timeout=60.0,
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            return json.loads(content)
        except Exception as exc:
            print(f"[warn] {provider_name} failed: {exc}")
            continue
    raise RuntimeError("All LLM providers failed. Check API keys and network.")


# ---------------------------------------------------------------------------
# MD renderer
# ---------------------------------------------------------------------------

def _render_md(data: dict) -> str:
    """Render a topic dict as the standard topics/*.md format."""
    countries = json.dumps(data.get("countries", []), ensure_ascii=False)
    languages = json.dumps(data.get("languages", []), ensure_ascii=False)
    time_range = data.get("time_range_hours", 72)
    max_articles = data.get("max_articles", 30)

    lines = [
        "---",
        f"name: {data['name']}",
        f"countries: {countries}",
        f"languages: {languages}",
        f"time_range_hours: {time_range}",
        f"max_articles: {max_articles}",
        "enabled: true",
        "---",
        "",
        f"# {data['name']}",
        "",
        data.get("description", ""),
        "",
    ]

    primary = data.get("keywords", {}).get("primary", [])
    if primary:
        lines += ["## 主要关键词"]
        lines += [f"- {kw}" for kw in primary]
        lines.append("")

    secondary = data.get("keywords", {}).get("secondary", [])
    if secondary:
        lines += ["## 次要关键词"]
        lines += [f"- {kw}" for kw in secondary]
        lines.append("")

    exclude = data.get("exclude_keywords", [])
    if exclude:
        lines += ["## 排除关键词"]
        lines += [f"- {kw}" for kw in exclude]
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main interactive flow
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 60)
    print("  News Monitor — Interactive Topic Builder")
    print("=" * 60)
    print("Describe the monitoring topic in natural language.")
    print("(Press Enter twice / blank line to finish)\n")

    desc_lines: list[str] = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line == "" and desc_lines and desc_lines[-1] == "":
            break
        desc_lines.append(line)

    description = "\n".join(desc_lines).strip()
    if not description:
        print("No description provided. Exiting.")
        sys.exit(0)

    print("\nCalling LLM to generate topic structure...")
    try:
        data = _call_llm(description)
    except RuntimeError as exc:
        print(f"\nError: {exc}")
        sys.exit(1)

    # Suggest filename
    suggested_filename = data.get("filename", "new_topic")
    if not suggested_filename.endswith(".md"):
        suggested_filename += ".md"

    print("\n" + "-" * 60)
    print("Suggested filename:", suggested_filename)
    print("-" * 60)
    md_content = _render_md(data)
    print(md_content)
    print("-" * 60)

    filename_input = input(
        f"\nFile name to save (leave blank for '{suggested_filename}'): "
    ).strip()
    if filename_input:
        if not filename_input.endswith(".md"):
            filename_input += ".md"
        filename = filename_input
    else:
        filename = suggested_filename

    answer = input(f"Write to topics/{filename}? [Y/n] ").strip().lower()
    if answer in ("", "y", "yes"):
        TOPICS_DIR.mkdir(exist_ok=True)
        dest = TOPICS_DIR / filename
        dest.write_text(md_content, encoding="utf-8")
        print(f"\nSaved: {dest}")
    else:
        print("Aborted. No file written.")


if __name__ == "__main__":
    main()
