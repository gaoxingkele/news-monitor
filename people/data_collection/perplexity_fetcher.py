"""Perplexity 台湾一手数据获取器 —— 从 v14_prep.py 提取。

用法：
    python -m people.data_collection.perplexity_fetcher --person 蒋万安
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from people.data_collection.config import bootstrap, get_env, EXTRACTED_DIR


def fetch_perplexity(query: str, timeout: int = 90) -> tuple[str, list]:
    """调用 Perplexity sonar-pro，返回 (content, citations)。"""
    api_key = get_env("PERPLEXITY_API_KEY")
    proxy = get_env("LLM_PROXY")

    client_kwargs: dict = {
        "timeout": httpx.Timeout(float(timeout)),
        "trust_env": False,
    }
    if proxy:
        client_kwargs["proxy"] = proxy

    with httpx.Client(**client_kwargs) as client:
        resp = client.post(
            "https://api.perplexity.ai/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "sonar-pro",
                "messages": [{"role": "user", "content": query}],
                "temperature": 0.1,
            },
        )
    data = resp.json()
    return data["choices"][0]["message"]["content"], data.get("citations", [])


# 蒋万安专用查询集
CHIANG_WANAN_QUERIES = {
    "cec_12district": "2022年台北市长选举（中华民国111年）各行政区得票数据。请列出台北市全部12个行政区（松山、信义、大安、中山、中正、大同、万华、文山、南港、内湖、士林、北投）的三位候选人（蒋万安、陈时中、黄珊珊）各自得票数和得票率。请引用中选会或权威来源。用简体中文回答，用表格格式。",
    "political_donation": "2022年台北市长选举蒋万安的政治献金数据：总收入金额、个人捐款总额、营利事业捐款总额、支出总额。如有前五大企业捐款来源请一并列出。请引用监察院政治献金公开查阅平台或权威报道。用简体中文回答。",
    "ly_performance": "蒋万安在台湾立法院第8届、第9届、第10届的立法委员任期中，主提案数、共同提案数、院会出席率、委员会出席率、质询次数分别是多少？请引用立法院公报或公督盟评鉴数据。用简体中文回答。",
    "ccw_rating": "公民监督国会联盟（公督盟）对蒋万安的历届评鉴结果是什么？在第8届、第9届、第10届的各会期中，他是否被评为「优秀立委」或「待观察立委」？请给出具体会期和评级。用简体中文回答。",
    "asset_declaration": "蒋万安最近几年的公职人员财产申报数据，包括不动产、存款、有价证券、汽车等。请引用监察院阳光法案主题网或权威报道。用简体中文回答。",
}


def run_fetch(person: str, queries: dict[str, str] | None = None) -> dict:
    """批量执行 Perplexity 查询，结果写入 extracted/ 目录。"""
    bootstrap()

    if queries is None:
        if person == "蒋万安":
            queries = CHIANG_WANAN_QUERIES
        else:
            print(f"No default queries for {person}, pass --queries or add to registry")
            return {}

    results = {}
    for qid, query in queries.items():
        print(f"  [{qid}]...", end=" ", flush=True)
        try:
            content, citations = fetch_perplexity(query)
            results[qid] = {"content": content, "citations": citations}
            print(f"{len(content)} chars, {len(citations)} citations")
        except Exception as e:
            results[qid] = {"content": "", "citations": [], "error": str(e)}
            print(f"FAIL: {e}")

    EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)
    out_file = EXTRACTED_DIR / "perplexity_taiwan_gov.json"
    out_file.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"→ {out_file}")
    return results


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Perplexity 台湾一手数据获取")
    ap.add_argument("--person", default="蒋万安", help="目标人物")
    args = ap.parse_args()
    run_fetch(args.person)
