"""最后一轮：使用 Perplexity sonar-pro (deep research) 模型重跑 4 格。
sonar-pro 的检索更深、引用更多，是基础 sonar 的升级版。
"""
from __future__ import annotations
import asyncio, io, json, os, sys, logging
from pathlib import Path
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
ROOT = Path(r"D:\aicoding\news-monitor")
sys.path.insert(0, str(ROOT / "src"))
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError: pass

import httpx
from news_monitor.proxy import build_httpx_client, get_proxies_for_url

PPX = os.environ.get("PERPLEXITY_API_KEY", "")
DS = os.environ.get("DEEPSEEK_API_KEY", "")
PROXY = os.environ.get("LLM_PROXY", "")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("pro")

TASKS = [
    ("蒙古#43", "蒙古国 2024 年开设中文/汉语专业的高校数量和占全国高校总数的比例",
     "请列出蒙古国所有开设 Chinese language / Chinese studies / 汉语师范 专业的高校具体名单（含新蒙古国立大学、蒙古国立大学、蒙古国立师范大学等），并给出蒙古教育文化科学体育部（MECSS）公布的 2024 年高校总数。来源优先：mecss.gov.mn, edu.mn, 中国驻蒙古使馆。"),
    ("柬埔寨#32", "柬埔寨华文学校学生中非华裔（柬埔寨族 Khmer）学生的比例",
     "查找柬埔寨华文学校（如端华学校、崇正学校、广肇学校、集成学校）的学生族裔构成数据。可引用柬埔寨柬华理事总会年报、端华学校年鉴、以及陈奕志/信世昌 2024 论文《海外華裔傳承語教材之分析研究》或其他研究。给出具体调查年份、样本学校、非华裔百分比。"),
    ("菲律宾#41", "中国国际中文教育基金会 CIEF 理事会中来自菲律宾的理事成员数量",
     "中国国际中文教育基金会（CIEF, cief.org.cn）公开的理事会名单中，来自菲律宾的理事机构/个人数量。请找出 CIEF 章程第 9 条/第 10 条中列明的理事组成，以及最新理事会名录 URL。若 CIEF 未公开菲律宾籍理事，请转查世界汉语教学学会（WCLA）、国际中文教育学会的菲律宾会员。"),
    ("新加坡#31", "新加坡基础教育阶段华文学习者（CL/HCL/CLB 等）占总学生数的比例",
     "查新加坡 MOE Education Statistics Digest 2024/2025 中：(1) 小学+中学 Mother Tongue Language Chinese (CL/HCL/CLB) 学生人数；(2) 小学+中学总学生数；(3) 直接给出比例。其他来源：MOE 政策声明（Pathways and Possibilities）、新加坡统计局 SingStat 教育部分。"),
]

async def sonar_pro(client, q):
    """Use sonar-pro model (supports deep research and longer context)."""
    body = {
        "model": "sonar-pro",
        "messages": [
            {"role": "system", "content":
             "You are a deep research analyst. Use your strongest web retrieval. "
             "For every claim, cite the primary source URL directly. "
             "If the fact is uncertain, list all candidate values with their sources. "
             "Respond in Chinese."},
            {"role": "user", "content": q},
        ],
        "temperature": 0.05,
        "return_citations": True,
    }
    try:
        resp = await client.post(
            "https://api.perplexity.ai/chat/completions",
            json=body,
            headers={"Authorization": f"Bearer {PPX}", "Content-Type": "application/json"},
            timeout=180.0,
        )
        resp.raise_for_status()
        d = resp.json()
        return d["choices"][0]["message"]["content"], d.get("citations", [])[:15]
    except Exception as e:
        log.warning("sonar-pro err: %s", str(e)[:150])
        return "", []

async def main():
    p = get_proxies_for_url("https://api.perplexity.ai", PROXY)
    async with build_httpx_client(p or "", 180) as c:
        results = {}
        for name, short, q in TASKS:
            log.info("跑 %s...", name)
            ans, cites = await sonar_pro(c, q)
            results[name] = {"answer": ans, "citations": cites}
            log.info("  %s: %d 字答案, %d 引用", name, len(ans), len(cites))

    OUT = ROOT / "output" / "bri_sonar_pro_final.json"
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    log.info("saved %s", OUT.name)

    # print summary
    for name, r in results.items():
        print(f"\n{'='*70}\n{name}\n{'='*70}")
        print(r['answer'][:1500])
        print("\nCitations:")
        for c in r['citations']: print(f"  - {c}")

if __name__ == "__main__":
    asyncio.run(main())
