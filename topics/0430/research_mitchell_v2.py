"""米切尔航空航天研究所 v2 深度研究 — 多源原生 API 取证 + Cloubic Gemini 整合。

四个搜索源（全部走系统代理 LLM_PROXY）:
  - Brave Search API           (api.search.brave.com)
  - Tavily Search API          (api.tavily.com)
  - Grok native API            (api.x.ai / OpenAI-compatible)
  - Gemini native API          (generativelanguage.googleapis.com, google search grounding)

整合:
  - Cloubic → gemini-3.1-pro-preview, key=sk-m92gPJJAjofAm0_Se3uZo2Zl6hlqd93DLUjmAtfrJE0

输出:
  topics/0430/raw_evidence_v2.json
  topics/0430/米切尔研究所_深度专家分析_v2.md
"""
from __future__ import annotations

import asyncio
import io
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

_HERE = Path(__file__).resolve()
_ROOT = _HERE.parent.parent.parent

try:
    from dotenv import load_dotenv
    load_dotenv()
    cloubic_env = _ROOT / ".env.cloubic"
    if cloubic_env.exists():
        load_dotenv(cloubic_env, override=True)
except ImportError:
    pass

import httpx

# ── Config ───────────────────────────────────────────────────────────────────

PROXY = os.environ.get("LLM_PROXY", "http://127.0.0.1:18182")
BRAVE_KEY = os.environ.get("BRAVEAPI", "")
TAVILY_KEY = os.environ.get("tavilyapi", os.environ.get("TAVILY_API_KEY", ""))
GROK_KEY = os.environ.get("GROK_API_KEY", "")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")

# 用户本次指定的 Cloubic key（不是 .env.cloubic 中默认的）
CLOUBIC_KEY = os.environ.get("CLOUBIC_API_KEY", "")
CLOUBIC_URL = os.environ.get("CLOUBIC_BASE_URL", "https://api.cloubic.com/v1/chat/completions")
CLOUBIC_MODEL = "gemini-3.1-pro-preview"   # 推理档（reasoning）
CLOUBIC_FALLBACK = "gemini-3-pro-preview"  # 余额不足时退到非 reasoning

OUT_DIR = Path(__file__).parent
OUT_DIR.mkdir(parents=True, exist_ok=True)

NOW = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

# ── 三大研究问题 + 检索词 ────────────────────────────────────────────────────

QUERIES = {
    "Q1_机构基本情况": [
        "Mitchell Institute for Aerospace Studies AFA leadership Deptula 2026",
        "Mitchell Institute funding sponsors corporate donors Boeing Lockheed Northrop",
        "Mitchell Institute 501c3 EIN tax filing Form 990 budget",
        "Mitchell Institute MI-SPACE MI-UAS organization centers",
        "米切尔航空航天研究所 资金 赞助商 美国空军协会",
    ],
    "Q2_涉台党政军合作": [
        "Mitchell Institute Taiwan INDSR cooperation visit",
        "Mitchell Institute Taiwan National Security Bureau NSB intelligence",
        "Mitchell Institute Taiwan Military Intelligence Bureau MIB",
        "Mitchell Institute Taiwan defense officials roundtable wargame 2025 2026",
        "Dahm Penney Deptula Taiwan delegation INDSR",
        "AFA Air Space Forces Association Taiwan exchange",
        "米切尔研究所 台湾 国安局 军情局 INDSR 国防安全研究院",
    ],
    "Q3_中国空军追踪器数据来源": [
        "China Airpower Tracker Mitchell Institute data sources methodology",
        "Mitchell Institute China Airpower Tracker Maxar Planet Labs satellite imagery OSINT",
        "J Michael Dahm China Airpower Tracker J-6 UCAV Fujian Guangdong",
        "China Airpower Tracker hardened aircraft shelters HAS PLA",
        "中国空军追踪器 米切尔 Dahm 数据 卫星 开源情报",
        "Mitchell Institute China tracker Sentinel ESA commercial imagery",
    ],
}


# ── HTTP helper ──────────────────────────────────────────────────────────────

def make_client(timeout: float = 60.0, use_proxy: bool = True) -> httpx.AsyncClient:
    kw: dict = {"timeout": httpx.Timeout(timeout), "follow_redirects": True, "trust_env": False}
    if use_proxy and PROXY:
        kw["proxy"] = PROXY
    return httpx.AsyncClient(**kw)


# ── Brave Search ─────────────────────────────────────────────────────────────

async def brave_search(query: str, count: int = 10) -> dict:
    if not BRAVE_KEY:
        return {"source": "brave", "query": query, "error": "no key"}
    url = "https://api.search.brave.com/res/v1/web/search"
    params = {"q": query, "count": count, "freshness": "py"}  # past year
    headers = {"X-Subscription-Token": BRAVE_KEY, "Accept": "application/json"}
    try:
        async with make_client() as c:
            r = await c.get(url, params=params, headers=headers)
            r.raise_for_status()
            data = r.json()
        results = []
        for w in (data.get("web", {}) or {}).get("results", [])[:count]:
            results.append({
                "title": w.get("title", ""),
                "url": w.get("url", ""),
                "snippet": w.get("description", "")[:600],
                "age": w.get("age", ""),
            })
        return {"source": "brave", "query": query, "results": results}
    except Exception as e:
        return {"source": "brave", "query": query, "error": str(e)}


# ── Tavily Search ────────────────────────────────────────────────────────────

async def tavily_search(query: str, count: int = 10) -> dict:
    if not TAVILY_KEY:
        return {"source": "tavily", "query": query, "error": "no key"}
    url = "https://api.tavily.com/search"
    body = {
        "api_key": TAVILY_KEY,
        "query": query,
        "search_depth": "advanced",
        "max_results": count,
        "include_answer": True,
        "include_raw_content": False,
    }
    try:
        async with make_client(timeout=90.0) as c:
            r = await c.post(url, json=body)
            r.raise_for_status()
            data = r.json()
        results = []
        for w in data.get("results", [])[:count]:
            results.append({
                "title": w.get("title", ""),
                "url": w.get("url", ""),
                "snippet": (w.get("content", "") or "")[:800],
                "score": w.get("score"),
            })
        return {
            "source": "tavily",
            "query": query,
            "answer": data.get("answer", ""),
            "results": results,
        }
    except Exception as e:
        return {"source": "tavily", "query": query, "error": str(e)}


# ── Grok native API (with Live Search) ───────────────────────────────────────

async def grok_search(query: str) -> dict:
    """新版 Grok Agent Tools API（/v1/responses + tools=[web_search]）。"""
    if not GROK_KEY:
        return {"source": "grok", "query": query, "error": "no key"}
    url = "https://api.x.ai/v1/responses"
    prompt = (
        "You are a senior defense intelligence analyst. Use web_search to find authoritative sources. "
        "Return concise factual findings with URLs.\n\n" + query +
        "\n\n请用中文返回 6-10 条关键事实，每条附原始 URL；优先 mitchellaerospacepower.org / afa.org / indsr.org.tw / uscc.gov / 官方报告。"
    )
    body = {
        "model": "grok-4.20-reasoning",
        "input": [{"role": "user", "content": prompt}],
        "tools": [{"type": "web_search"}],
    }
    headers = {"Authorization": f"Bearer {GROK_KEY}", "Content-Type": "application/json"}
    try:
        async with make_client(timeout=300.0) as c:
            r = await c.post(url, json=body, headers=headers)
            r.raise_for_status()
            data = r.json()
        # 提取最终 message
        content = ""
        citations: list = []
        for item in data.get("output", []):
            if item.get("type") == "message":
                for c_blk in item.get("content", []):
                    if c_blk.get("type") == "output_text":
                        content += c_blk.get("text", "")
                        # 提取 annotations 中的 URL
                        for ann in c_blk.get("annotations", []) or []:
                            if ann.get("type") in ("url_citation", "citation"):
                                citations.append({
                                    "title": ann.get("title", ""),
                                    "url": ann.get("url", ""),
                                })
        return {"source": "grok", "query": query, "content": content, "citations": citations}
    except Exception as e:
        return {"source": "grok", "query": query, "error": str(e)}


# ── Gemini native API (with Google Search grounding) ─────────────────────────

async def gemini_search(query: str) -> dict:
    if not GEMINI_KEY:
        return {"source": "gemini", "query": query, "error": "no key"}
    model = "gemini-2.5-pro"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_KEY}"
    body = {
        "contents": [{
            "role": "user",
            "parts": [{"text": query + "\n\n请用中文返回 6-10 条关键事实，每条附原始 URL；优先 mitchellaerospacepower.org / afa.org / indsr.org.tw / uscc.gov / 官方报告。"}]
        }],
        "tools": [{"google_search": {}}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 4096},
    }
    try:
        async with make_client(timeout=180.0) as c:
            r = await c.post(url, json=body)
            r.raise_for_status()
            data = r.json()
        cands = data.get("candidates", [])
        if not cands:
            return {"source": "gemini", "query": query, "error": "no candidates", "raw": data}
        parts = cands[0].get("content", {}).get("parts", [])
        text = "\n".join(p.get("text", "") for p in parts if "text" in p)
        gm = cands[0].get("groundingMetadata", {}) or {}
        chunks = gm.get("groundingChunks", []) or []
        citations = []
        for ch in chunks:
            web = ch.get("web", {}) or {}
            if web:
                citations.append({"title": web.get("title", ""), "url": web.get("uri", "")})
        return {"source": "gemini", "query": query, "content": text, "citations": citations}
    except Exception as e:
        return {"source": "gemini", "query": query, "error": str(e)}


# ── Cloubic 整合 (gemini-3.1-pro-preview) ────────────────────────────────────

async def gemini_synthesize(prompt: str, model: str = "gemini-2.5-pro") -> str:
    """Cloubic 余额耗尽时的回退方案：直接调 Gemini 原生 API（走代理）。"""
    if not GEMINI_KEY:
        raise RuntimeError("no GEMINI_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_KEY}"
    body = {
        "contents": [{
            "role": "user",
            "parts": [{"text": prompt}],
        }],
        "systemInstruction": {
            "parts": [{"text": "你是国际关系、军事战略与混合情报领域的资深研究员。学术严谨的中文撰写；区分『事实/经核实数据』vs『推断/合理推论』；所有事实附来源 URL；不写客套语。"}],
        },
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 16000,
        },
    }
    async with make_client(timeout=600.0, use_proxy=True) as c:
        r = await c.post(url, json=body)
        if r.status_code != 200:
            raise RuntimeError(f"gemini {r.status_code}: {r.text[:500]}")
        data = r.json()
    cands = data.get("candidates", [])
    if not cands:
        raise RuntimeError(f"gemini no candidates: {str(data)[:300]}")
    parts = cands[0].get("content", {}).get("parts", [])
    return "\n".join(p.get("text", "") for p in parts if "text" in p)


async def cloubic_synthesize(prompt: str, max_tokens: int = 60000, model: str | None = None) -> str:
    body = {
        "model": model or CLOUBIC_MODEL,
        "messages": [
            {"role": "system", "content": "你是国际关系、军事战略与混合情报领域的资深研究员，曾任美国国防情报机构与台海问题研究室高级分析师。请用学术严谨的中文撰写报告，区分『事实/经核实数据』与『推断/合理推论』，所有事实陈述都要给出可追溯的来源标注（URL 或机构）。不要写任何客套语或免责声明。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "max_tokens": max_tokens,
    }
    headers = {"Authorization": f"Bearer {CLOUBIC_KEY}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=httpx.Timeout(900.0), trust_env=False) as c:
        r = await c.post(CLOUBIC_URL, json=body, headers=headers)
        if r.status_code != 200:
            raise RuntimeError(f"cloubic {r.status_code}: {r.text[:500]}")
        data = r.json()
    return data["choices"][0]["message"]["content"]


# ── 主流程 ────────────────────────────────────────────────────────────────────

async def collect_evidence() -> dict:
    """对三大问题并发跑四源检索（Brave/Tavily/Grok/Gemini）。"""
    evidence: dict = {"timestamp": NOW, "sections": {}}
    for qname, queries in QUERIES.items():
        print(f"\n=== {qname} : {len(queries)} 个 query × 4 源 ===", file=sys.stderr)
        section: list = []
        tasks = []
        for q in queries:
            tasks.append(brave_search(q))
            tasks.append(tavily_search(q))
            tasks.append(grok_search(q))
            tasks.append(gemini_search(q))
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, Exception):
                section.append({"error": str(r)})
            else:
                section.append(r)
        evidence["sections"][qname] = section
        ok = sum(1 for r in section if isinstance(r, dict) and "error" not in r)
        by_src: dict = {}
        for it in section:
            if isinstance(it, dict):
                by_src.setdefault(it.get("source", "?"), [0, 0])
                if "error" in it:
                    by_src[it.get("source", "?")][1] += 1
                else:
                    by_src[it.get("source", "?")][0] += 1
        src_summary = ", ".join(f"{s}={ok}/{ok+er}" for s, (ok, er) in by_src.items())
        print(f"  完成: {ok}/{len(section)} 成功 [{src_summary}]", file=sys.stderr)
    return evidence


def format_evidence_markdown(evidence: dict) -> str:
    """把 raw evidence 拍平成 markdown 给 Gemini 阅读。"""
    out = [f"# 多源原生 API 取证（生成于 {evidence['timestamp']}）\n"]
    for qname, items in evidence["sections"].items():
        out.append(f"\n## {qname}\n")
        for it in items:
            if not isinstance(it, dict) or "error" in it:
                continue
            src = it.get("source", "?")
            q = it.get("query", "")
            out.append(f"\n### [{src}] {q}\n")
            if it.get("answer"):
                out.append(f"**Tavily 综合回答**: {it['answer']}\n")
            if it.get("content"):
                txt = it["content"][:3500]
                out.append(f"{txt}\n")
            for r in it.get("results", [])[:8]:
                t = r.get("title", "")
                u = r.get("url", "")
                s = r.get("snippet", "")[:400]
                out.append(f"- [{t}]({u}) — {s}")
            for c in it.get("citations", [])[:10]:
                if isinstance(c, dict):
                    out.append(f"- {c.get('title','')} {c.get('url','')}")
                else:
                    out.append(f"- {c}")
    return "\n".join(out)


SYNTH_INTRO = """\
你将以国际关系学者 + 军事战略分析师 + 混合情报（OSINT/HUMINT/SIGINT 综合）专家的三重身份，
基于下文【一手取证摘要】与你已掌握的公开知识，撰写一份关于
"美国空军协会下属米切尔航空航天研究所"的中文深度专家分析报告（v2 升级版）。

【报告必须覆盖三大主题】
一、米切尔航空航天研究所基本情况
    - 法律定性（501(c)(3)、EIN、AFA 隶属）、组织沿革、领导班底
    - 资金链：DoD/DARPA/AFRL 拨款 vs 军工企业（Boeing/LM/Northrop/Raytheon/GA/L3Harris/Pratt&Whitney/BAE 等）
    - 旗下中心：MI-SPACE / MI-UAS / Mitchell Forum / Aerospace Advantage 播客
    - 关键产出（Policy Papers、Forum Papers、兵棋推演、China Airpower Tracker）
    - 所处的 "旋转门 + 军工复合体" 生态位刻画
二、与台湾地区党政军合作、联系、交流（重点：国家安全局 NSB、军事情报局 MIB、INDSR）
    - 直接证据 vs 间接证据 的清晰切分（不要把推论当事实）
    - 官方对话、Track-2 机制、AIT-INDSR 中介渠道
    - INDSR 引用米切尔产出的频率与语境（特别是 Penney/Dahm/Deptula 的论述）
    - J-6 无人机案例的"情报释放→台湾国安验证→对台军售推动"政策闭环
    - 涉 NSB 与 MIB 的可证据链：列出已知的会议、证词、人员往来；明确指出哪些是"推论"
三、《中国空军追踪器》(China Airpower Tracker) 数据来源分析
    - 多模态 OSINT 数据矩阵：商业卫星（Maxar/Planet Labs/Capella SAR/BlackSky）、
      官方/半官方数据（PLA 报刊、CCTV-7、官方采办公告、地方政府公示）、
      行业期刊与展会公开资料（航展、专业期刊）、社交媒体与中文军事论坛、
      USCC 等美方公开听证证词
    - 分析方法论：图像几何识别 → 工程量计数 → 战术意图反推
    - 案例：歼-6 UCAV、HAS（加固机库）计数、福建/广东前沿机场升级
    - OSINT 方法可复制性、可证伪性与误差边界
    - 与 CASI（空军大学中国航空研究所）、CSIS ChinaPower、IISS Military Balance 等的差异化定位

【撰写硬性要求】
1. 以"资深专家"口吻，不写公关稿；要给出战略判断、不确定性评估、风险识别
2. 所有事实/数据/人物/项目都要在行内或脚注给出来源（URL 或权威机构）
3. 区分四级置信度：【已证实】【高度可信】【合理推断】【未证实/存疑】
4. 出现具体数字（赞助金额、报告数量、UCAV 数量等）必须附来源；无源数据要标"未公开/估算"
5. 篇幅 ≥ 8000 字中文，结构清晰、小节清单
6. 末尾给出"未解决问题与后续侦察方向"清单（10 条以上）
7. 末尾"引用著作"列出 25 条以上权威来源 URL
8. 用 markdown 格式，含一级到三级标题，关键结论用 **加粗**

【一手取证摘要 — 来自 Brave/Tavily/Grok/Gemini 原生 API 检索】

{evidence_md}

【现在开始撰写完整报告】
"""


async def main():
    # 1. 取证
    print("[1/3] 多源原生 API 取证…", file=sys.stderr)
    evidence = await collect_evidence()
    raw_path = OUT_DIR / "raw_evidence_v2.json"
    raw_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  写入 {raw_path}", file=sys.stderr)

    md_evidence = format_evidence_markdown(evidence)
    ev_md_path = OUT_DIR / "raw_evidence_v2.md"
    ev_md_path.write_text(md_evidence, encoding="utf-8")
    print(f"  写入 {ev_md_path} ({len(md_evidence)} 字符)", file=sys.stderr)

    # 2. 多轮整合 — 分章节产出避免单次截断
    print(f"[2/3] Cloubic → {CLOUBIC_MODEL} 多轮整合…", file=sys.stderr)
    # 新 key 余额充足，送较大取证（~120KB ≈ 30K tokens）以充分上下文
    if len(md_evidence) > 130000:
        md_evidence = md_evidence[:130000] + "\n\n[…取证过长，已截断]"

    # 章节定义：每节 2500-4000 字
    SECTIONS = [
        ("Q1", "第一章 · 机构基本情况", """\
请专门撰写【第一章 · 机构基本情况】，约 3500-4500 字中文。覆盖：
1.1 法律地位与归属：501(c)(3)、EIN: 52-6043929、AFA 隶属、阿灵顿总部、命名缘起（Billy Mitchell）
1.2 沿革：2004 成立、2013 更名、AFA 12 万会员结构（40% 现役 / 64% 退/前役）
1.3 三大使命：Informing / Educating / Cultivating
1.4 领导班底（详细）：David Deptula 院长、Kevin Chilton（MI-SPACE 探索主席）、Mark Gunzinger、Heather Penney、J. Michael Dahm、Larry Stutzriem、Douglas Birkey 等关键研究员的履历、军种背景、博士/情报背景
1.5 旗下研究中心：MI-SPACE（太空力量优势中心，2020/2021 由 Chilton 领衔）、MI-UAS（无人机与自主系统中心，2022/3 成立）、Mitchell Forum（论坛系列）
1.6 资金链全景：DoD/DARPA/AFRL/OSD ONA 政府拨款；Boeing/Lockheed Martin/Northrop Grumman/Raytheon Technologies/General Atomics/L3Harris/BAE Systems/Pratt & Whitney 等企业赞助；GSA 采购目录（2024-12 续签 5 年）；可证实的赞助金额（如有）和"利益冲突"批评（F-47 / B-21 案例）
1.7 旗舰产出（按类型）：Policy Paper 系列、Forum Paper 系列、Aerospace Advantage 播客、Aerospace Nation 高层圆桌、China Airpower Tracker、兵棋推演（含 2025-06 的 60 人推演 → 2026-04《Rebuilding American Airpower》）
1.8 战略生态位刻画：与 CSIS / RAND / Stimson / Hudson 等的差异化定位；"旋转门 + 军工复合体" 中的关键节点角色

要求：每个事实/数字/项目都要有来源（URL 或权威机构）；区分四级置信度【已证实】【高度可信】【合理推断】【未证实/存疑】；用 markdown 三级标题分小节。
不要写引言、不要写结语、只产出本章正文。
"""),
        ("Q2", "第二章 · 与台湾地区党政军合作、联系、交流（重点：国安局 NSB / 军情局 MIB / INDSR）", """\
请专门撰写【第二章 · 涉台合作与情报联动】，约 4000-5000 字中文。这是本报告最敏感最关键的一章。
请以严肃情报分析口吻撰写，明确区分"已证实事实链"与"基于行为模式的合理推断"。

2.1 战略背景：印太"前沿威慑"格局下台湾在米切尔议程中的位置
2.2 与 INDSR 的学术嵌合：
    - INDSR 法人结构（财团法人，台立法院监督，经费几乎全来自台防务部门）
    - 引用频率与典型语境（Penney/Dahm/Deptula 论述被 INDSR 出版物 / 季报引用的案例）
    - 是否有正式 MOU？（明确说明：现有公开材料中未发现正式 MOU；但有大量间接共振）
    - 共同会议/对话渠道（如 INDSR 台北安全对话、Aspen Security Forum、Halifax Forum 等多边场域）
2.3 与台湾国家安全局（NSB）的可证据链：
    - NSB 对米切尔产出的直接引用（J-6 UCAV 案例：台湾安全官员对国际媒体证实情报）
    - NSB 局长蔡明彦关于海事监控、电缆监控、间谍案的公开研判与米切尔研究的"跨洋呼应"
    - 是否有 NSB 人员直接出席米切尔活动？（明确说明：未见公开记录；但通过 AIT-INDSR 中介的可能性）
    - 信息战 / OSINT 共享：USCC 上 Dahm 的证词如何映射到 NSB 关切
2.4 与军事情报局（MIB）的可证据链：
    - MIB 在台湾国防部体制内的定位
    - 米切尔研究员军方背景（Dahm 25 年海军情报官）与 MIB 的"同业语言"
    - 公开记录中的会议交集（如军情系统智库 / 国防大学）
    - 明确说明哪些是合理推断而非证据
2.5 AIT-INDSR-米切尔的"三角中介"机制：
    - AIT 国务院资助 + INDSR 台府资助 → 多边研讨会 → 米切尔研究员获邀
    - 雷蒙德·格林（AIT 处长）2026 年 1 月在 INDSR 演讲事件
2.6 关键案例：J-6 UCAV 政策闭环
    - 米切尔（Dahm/Rice）发布 → 国际媒体放大（Reuters/SCMP/AP）→ 台湾防务高官证实战术 → INDSR 评估"不对称作战" → 美对台军售（Switchblade 等无人系统）的政策推动链
2.7 兵棋推演的台海回响：2025-06 60 人推演 → 2026-04 报告"美军 2035 无法保卫台湾" → 台湾媒体 / 立法院压力 → 军费上调
2.8 综合判断：米切尔与台湾党政军关系的本质（"平台型"而非"协议型"，但战略效果显著）

要求：所有事实/人物/项目附来源（URL 或机构）；置信度四级标注；NSB/MIB 的合作不要硬编故事，没证据就明说"未证实/存疑"。
不要写引言、不要写结语、只产出本章正文。
"""),
        ("Q3", "第三章 · 《中国空军追踪器》数据来源与方法论分析", """\
请专门撰写【第三章 · China Airpower Tracker 数据来源与方法论】，约 4000-5000 字中文。

3.1 项目概况：mitchellaerospacepower.org/china、2026-02-25 上线、Dahm 主导、定位为"权威在线评估平台"
3.2 数据采集的多维矩阵（详细分类与举例）：
    A) 商业卫星影像
       - Maxar（WorldView 系列）、Planet Labs（SkySat / PlanetScope）、Capella Space（SAR）、BlackSky（高频次重访）
       - 欧空局 Sentinel-1/2（免费 SAR + 多光谱）作为补充
       - 谷歌地球历史影像、Apple Maps、Esri 等公开底图
       - 各类影像的分辨率级别、采购方式（订阅 / 项目 / 学术合作）
    B) 中国官方/半官方公开信息
       - PLA 报刊：《解放军报》、《中国空军》、《航空知识》、CCTV-7 国防军事频道
       - 政府采办公告、招投标公告、地方政府环评公示（机场扩建）
       - 中国军队官方网站（81.cn）、中国国防部新闻发布会实录
    C) 行业期刊与展会资料
       - 航空工业集团（AVIC）年报、各大研究院公告、珠海航展、ZHUHAI Airshow 展品资料
       - 《Aviation Week》、《Janes Defence Weekly》、IISS Military Balance 数据
    D) 中文社交媒体与军迷情报
       - 微博、抖音、超大军事论坛、铁血军事的飞机靠近基地、新机型试飞照片
       - "民间军迷情报" 的真实性筛选
    E) 美方公开听证证词
       - USCC（U.S.-China Economic and Security Review Commission）听证、Dahm 自己的多次证词
       - 国会研究服务部 CRS 报告、DoD 中国军力年度报告
    F) 学术合作伙伴：CASI（空军大学中国航空研究所，Air University）、CSIS ChinaPower、CMSI（海军战争学院中国海事研究所）、IISS
3.3 分析方法论的四步流程：
    步骤一：物理识别（影像中的几何形状、机型轮廓比对）
    步骤二：工程量计数（HAS 数量、跑道长度、油料库容量、滑行道布局）
    步骤三：战术意图反推（永久驻扎 vs 临时部署、UCAV 饱和攻击 vs 常规作战）
    步骤四：交叉验证（多源对照，排除单源误判）
3.4 标志性案例深度复盘：
    案例一：J-6 UCAV 改装机部署（福建/广东 6 个基地 200+ 架）
        - 影像证据链、几何识别、官方采办文件交叉、台湾官员公开印证
    案例二：HAS 加固机库爆炸式扩建
        - Daniel Rice 2022 论文 → "永久前沿基地"判断
        - 反驳"临时部署地点"旧认知
    案例三：远西"红剑"演习的"透明化披露"
        - 通过卫星捕捉演习地理痕迹 → 透过开源运输调度信息匹配
3.5 OSINT 方法的可复制性、可证伪性与误差边界
    - 与 ISW、Bellingcat 的方法论对比
    - 主要误差源：影像分辨率边界、改装真实意图判断、低分辨率红外辨识
    - 经常被批评的"分析师确认偏误"问题
3.6 与 CASI、CSIS ChinaPower、IISS、CMSI、Janes 的差异化定位
    - 定位光谱：CASI（学术 / 翻译型）→ CMSI（学院型）→ Janes（订阅型商业）→ CSIS ChinaPower（仪表盘型）→ Mitchell Tracker（战术情报型）
3.7 战略溢出效应：
    - 驱动美国国会预算审议（B-21 / NGAD / CCA / JADC2）
    - 驱动印太盟友（日 / 韩 / 澳 / 台）军费决策
    - "透明化威慑"（Deterrence through Transparency）的认知作战意义

要求：每个数据源类别给出 2-3 个真实示例 URL；置信度标注；指出哪些是研究所明确披露的方法、哪些是基于 Dahm 公开证词反推的。
不要写引言、不要写结语、只产出本章正文。
"""),
        ("Q4", "第四章 · 战略评估、风险识别与后续侦察方向", """\
请撰写【第四章 · 综合战略评估、风险识别与后续侦察方向】，约 2500-3500 字中文。包含：
4.1 综合战略评估
    - 米切尔在美国对华空天战略生态中的"独特但非唯一"地位
    - "智库-军工-军方"三角中作为"思想包装机"的角色
    - 与 CSIS、Hudson、AEI 等的功能差异
4.2 对中国大陆的潜在风险
    - 通过 Tracker 公开的影像情报对中国军事透明度的"被动施压"
    - 台海冲突情境下"情报-行动"链路中可能扮演的角色
    - 对中国境内军事设施安全的"持续聚光灯"效应
    - 在认知作战层面塑造美 / 盟 / 第三方观感
4.3 对台湾地区民进党当局的赋能与风险
    - 赋能：提供"国际化论据"为军购、防御部署辩护
    - 风险：被反向利用为"以武拒统"的策略工具
4.4 学界 / 智库圈对米切尔方法论的批评汇总
    - 利益冲突质疑（赞助商与推荐采购的关联）
    - "威胁通胀"（Threat Inflation）批评
    - 影像解读的"过度自信"问题
4.5 未解决问题与后续侦察方向（≥12 条具体待查项）
    - 例：是否存在 NSB 直接联系？Dahm 是否曾访台？INDSR-米切尔的具体合作协议细节？资金来源中是否有未披露的"暗渠"？追踪器的承包商身份？
4.6 对中国大陆相关研究者的应对建议（≥6 条）
4.7 引用著作（汇总全报告）：列出 ≥30 条权威 URL 来源，用 markdown 列表格式

要求：明确"未解决问题"清单要具体可执行；引用著作部分要把全报告各章用到的来源都汇总到这里。
不要写引言、不要写结语、只产出本章正文。
"""),
    ]

    sections_out = []
    for tag, title, sec_prompt in SECTIONS:
        # 增量缓存：避免重跑
        cache_path = OUT_DIR / f"_section_cache_{tag}.md"
        if cache_path.exists() and cache_path.stat().st_size > 1000:
            text = cache_path.read_text(encoding="utf-8")
            print(f"  [{tag}] 命中缓存 {len(text)} 字符", file=sys.stderr)
            sections_out.append((title, text))
            continue

        print(f"  正在生成 [{tag}] {title}…", file=sys.stderr)
        full_prompt = (
            SYNTH_INTRO
            + "\n\n"
            + sec_prompt
            + "\n\n【一手取证摘要 — Brave/Grok/Gemini 原生 API 检索】\n\n"
            + md_evidence
        )
        text = ""
        try:
            text = await cloubic_synthesize(full_prompt, max_tokens=20000)
        except Exception as e:
            err = str(e)
            print(f"    {tag} Cloubic 主模型失败: {err[:200]}", file=sys.stderr)
            try:
                print(f"    重试 {CLOUBIC_FALLBACK}…", file=sys.stderr)
                text = await cloubic_synthesize(full_prompt, max_tokens=15000, model=CLOUBIC_FALLBACK)
            except Exception as e2:
                err2 = str(e2)
                print(f"    备用模型也失败: {err2[:200]}; 回退 Gemini 原生 API", file=sys.stderr)
                text = await gemini_synthesize(full_prompt)
        cache_path.write_text(text, encoding="utf-8")
        sections_out.append((title, text))
        print(f"    [{tag}] 完成 {len(text)} 字符", file=sys.stderr)
        await asyncio.sleep(2)

    # 拼装
    report_parts = []
    for title, text in sections_out:
        if text.strip().startswith("#"):
            report_parts.append(text)
        else:
            report_parts.append(f"## {title}\n\n{text}")
    report = "\n\n---\n\n".join(report_parts)

    # 3. 输出
    print("[3/3] 写出 markdown 报告…", file=sys.stderr)
    out_md = OUT_DIR / "米切尔研究所_深度专家分析_v2.md"
    header = f"""# 美空军协会下属米切尔航空航天研究所 — 深度专家分析报告 v2

> 撰写时间：{NOW}
> 分析视角：国际关系 / 军事战略 / 混合情报（OSINT-HUMINT-SIGINT）
> 取证来源：Brave Search · Tavily · Grok（Live Search）· Gemini（Google Search Grounding）原生 API
> 整合模型：Cloubic → {CLOUBIC_MODEL}

---

"""
    out_md.write_text(header + report, encoding="utf-8")
    print(f"  写入 {out_md} ({len(report)} 字符)", file=sys.stderr)
    print("\n[OK] 完成。", file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(main())
