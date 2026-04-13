"""LLM 结构化信息提取器 —— 从搜索结果中提取可追溯的结构化事实。

使用 Grok-fast（走代理）或 Qwen（直连 Cloubic）做批量提取。
"""
from __future__ import annotations

import datetime
import json
import logging
import os

import httpx

from .config import bootstrap, get_env, EXTRACTED_DIR
from .models import SearchResult, ExtractedFact

logger = logging.getLogger("data_collection.extractor")

_SYSTEM_PROMPT = """\
你是一个严格的开源情报（OSINT）信息提取专家。
你的任务是从搜索结果中提取【可核验的结构化事实】，用于补充台湾政治人物分析报告。

提取规则：
1. 只提取有明确来源的事实陈述，不做任何推断
2. 每条事实必须标注证据等级：
   A = 官方/法定记录  B = 权威媒体实名报道  C = 单一来源/待核实  D = 弱来源
3. 保留原文关键引用（20-50字）
4. 标注事件日期（若可确定）
5. 如果搜索结果中没有与提取目标相关的有效信息，返回空数组

输出格式：严格 JSON 数组，每个元素结构如下：
{
  "content": "事实陈述（简体中文，50-150字）",
  "evidence_grade": "A/B/C/D",
  "source_name": "来源媒体/机构名",
  "source_url": "原始 URL",
  "date_of_event": "YYYY-MM-DD 或空字符串",
  "raw_quote": "原文关键引用（正体中文原文）"
}

只返回 JSON 数组，不要 markdown 代码块，不要解释。
"""


def _build_user_prompt(
    task_title: str,
    extraction_schema: str,
    results: list[SearchResult],
) -> str:
    items = []
    for i, r in enumerate(results[:30], 1):  # 最多30条避免超长
        items.append(f"[{i}] {r.title}\n    URL: {r.url}\n    日期: {r.published_date}\n    摘要: {r.snippet}")

    return f"""# 提取目标
{task_title}

# 期望提取的信息类型
{extraction_schema or '与标题相关的所有可核验事实'}

# 搜索结果（共{len(items)}条）
{"".join(items)}

请从以上搜索结果中提取所有相关的结构化事实。"""


def extract_facts(
    task_id: str,
    task_title: str,
    gap_id: int,
    extraction_schema: str,
    results: list[SearchResult],
    v6_module: str = "",
    provider: str = "grok",
) -> list[ExtractedFact]:
    """调用 LLM 从搜索结果中提取结构化事实。"""
    if not results:
        return []

    bootstrap()

    user_prompt = _build_user_prompt(task_title, extraction_schema, results)

    # 选择 LLM 通道
    if provider == "grok":
        api_key = get_env("GROK_API_KEY")
        base_url = "https://api.x.ai/v1/chat/completions"
        model = "grok-4-1-fast-non-reasoning"
        proxy = get_env("LLM_PROXY")
    elif provider == "gemini":
        api_key = get_env("CLOUBIC_API_KEY")
        base_url = get_env("CLOUBIC_BASE_URL", "https://api.cloubic.com/v1/chat/completions")
        model = get_env("CLOUBIC_GEMINI_MODEL", "gemini-3-flash-preview").split(",")[0].strip()
        proxy = ""
    elif provider == "claude":
        api_key = get_env("CLOUBIC_API_KEY")
        base_url = get_env("CLOUBIC_BASE_URL", "https://api.cloubic.com/v1/chat/completions")
        model = "claude-sonnet-4-6"
        proxy = ""
    else:
        # 默认走 Cloubic Qwen
        api_key = get_env("CLOUBIC_API_KEY")
        base_url = get_env("CLOUBIC_BASE_URL", "https://api.cloubic.com/v1/chat/completions")
        model = get_env("CLOUBIC_QWEN_MODEL", "qwen3-max").split(",")[0].strip()
        proxy = ""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.1,
        "max_tokens": 4000,
    }

    client_kwargs: dict = {
        "timeout": httpx.Timeout(120.0),
        "follow_redirects": True,
        "trust_env": False,
    }
    if proxy:
        client_kwargs["proxy"] = proxy

    try:
        with httpx.Client(**client_kwargs) as client:
            resp = client.post(base_url, headers=headers, json=payload)
        if resp.status_code != 200:
            logger.error("[%s] LLM extraction failed: HTTP %d %s", task_id, resp.status_code, resp.text[:300])
            return []

        data = resp.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        if isinstance(content, list):
            content = "\n".join(b.get("text", "") for b in content if isinstance(b, dict))

        # 清理可能的 markdown 代码块包裹
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[-1]
        if content.endswith("```"):
            content = content.rsplit("```", 1)[0]
        content = content.strip()

        facts_raw = json.loads(content)
        if not isinstance(facts_raw, list):
            facts_raw = [facts_raw]

    except (json.JSONDecodeError, KeyError, IndexError) as e:
        logger.error("[%s] LLM response parse failed: %s content=%s", task_id, e, content[:200] if 'content' in dir() else "N/A")
        return []
    except Exception as e:
        logger.error("[%s] LLM extraction exception: %s", task_id, e)
        return []

    # 转换为 ExtractedFact
    facts: list[ExtractedFact] = []
    for i, raw in enumerate(facts_raw):
        if not isinstance(raw, dict):
            continue
        facts.append(ExtractedFact(
            fact_id=f"{task_id}-F{i+1:02d}",
            gap_id=gap_id,
            content=raw.get("content", ""),
            evidence_grade=raw.get("evidence_grade", "C"),
            source_url=raw.get("source_url", ""),
            source_name=raw.get("source_name", ""),
            date_obtained=datetime.date.today().isoformat(),
            date_of_event=raw.get("date_of_event", ""),
            v6_module=v6_module,
            raw_quote=raw.get("raw_quote", ""),
        ))

    # 持久化
    EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)
    out_file = EXTRACTED_DIR / f"{task_id}.json"
    out_file.write_text(
        json.dumps(
            [{"fact_id": f.fact_id, "content": f.content, "grade": f.evidence_grade,
              "source_url": f.source_url, "source_name": f.source_name,
              "date_of_event": f.date_of_event, "raw_quote": f.raw_quote,
              "v6_module": f.v6_module}
             for f in facts],
            ensure_ascii=False, indent=2,
        ),
        encoding="utf-8",
    )
    logger.info("[%s] extracted %d facts → %s", task_id, len(facts), out_file.name)

    return facts
