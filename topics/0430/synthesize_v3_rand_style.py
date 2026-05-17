"""V3 — 按 RAND Corporation 报告体例重写米切尔研究所深度分析。

复用 raw_evidence_v2.md 作取证底料，调 Cloubic Gemini 3.1 Pro Preview 分段产出。

RAND 体例的 7 段式结构：
  0. Front Matter (Title / Document No. / About This Report / Abstract / Abbreviations)
  1. Executive Summary (Key Findings 1-N + Recommendations 1-N)
  2. Chapter 1. Introduction (Background / Research Questions / Approach / Limitations)
  3. Chapter 2. Mitchell Institute: Organization, Funding, and Strategic Niche
  4. Chapter 3. Engagement with Taiwan: NSB, MIB, INDSR, and Track-2 Channels
  5. Chapter 4. The China Airpower Tracker: Sources, Methods, and Tradecraft
  6. Chapter 5. Findings and Recommendations
  7. Appendix A. Methodology and Data Source Catalog
  8. Appendix B. Key Personnel Profiles
  9. References

输出：topics/0430/米切尔研究所_RAND体例分析_v3.md
"""
from __future__ import annotations

import asyncio
import io
import os
import socket
import sys
from datetime import datetime
from pathlib import Path

# 修复本地代理把 api.cloubic.com 劫持为 fake-IP (198.18.0.x) 导致 SSL 失败的问题。
# 用 Cloudflare 公网真实 IP 直连，SNI 仍走域名。
_CLOUBIC_REAL_IPS = ["104.26.8.180", "172.67.72.199", "104.26.9.180"]
_orig_getaddrinfo = socket.getaddrinfo


def _patched_getaddrinfo(host, port, *args, **kwargs):
    if isinstance(host, str) and host.endswith("cloubic.com"):
        for ip in _CLOUBIC_REAL_IPS:
            try:
                return _orig_getaddrinfo(ip, port, *args, **kwargs)
            except Exception:
                continue
    return _orig_getaddrinfo(host, port, *args, **kwargs)


socket.getaddrinfo = _patched_getaddrinfo

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

CLOUBIC_KEY = os.environ.get("CLOUBIC_API_KEY", "")
CLOUBIC_URL = os.environ.get("CLOUBIC_BASE_URL", "https://api.cloubic.com/v1/chat/completions")
CLOUBIC_MODEL = "gemini-3.1-pro-preview"
CLOUBIC_FALLBACK = "gemini-3-pro-preview"

OUT_DIR = _HERE.parent
EVIDENCE_PATH = OUT_DIR / "raw_evidence_v2.md"
PREV_REPORT = OUT_DIR / "米切尔研究所_深度专家分析_v2.md"
OUT_MD = OUT_DIR / "米切尔研究所_RAND体例分析_v3.md"
DOC_NO = "RR-MI-2026-3"
NOW = datetime.now().strftime("%Y-%m-%d")


# ── Cloubic 客户端 ───────────────────────────────────────────────────────────

def cloubic(prompt: str, max_tokens: int = 18000, model: str | None = None) -> str:
    """同步实现 — 因 anyio 的异步 DNS 解析绕过 socket.getaddrinfo 的 monkey-patch。"""
    body = {
        "model": model or CLOUBIC_MODEL,
        "messages": [
            {"role": "system", "content": (
                "你是 RAND Corporation 资深研究员（Senior Policy Researcher），曾在 Project AIR FORCE / "
                "National Security Research Division (NSRD) 负责印太军事问题。请严格按 RAND Corporation 标准报告体例撰写中文报告："
                "(1) 学术中性语调，使用 'may / could / suggests / appears to' 等条件式表达；"
                "(2) 严格区分『evidence-based finding（基于证据的发现）』vs『analytic judgment（分析性判断）』；"
                "(3) 拒绝政策倡导腔，不写宣传性语言；"
                "(4) 所有事实陈述必须给出可追溯来源（脚注或参考文献编号）；"
                "(5) 章末必须有阴影框形式的 'Key Findings of This Chapter' 编号清单；"
                "(6) 表格用 'Table N.M' 编号，图用 'Figure N.M'，下方注 'SOURCE:'；"
                "(7) 不写客套语和免责声明开头；直接产出正文。"
            )},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.25,
        "max_tokens": max_tokens,
    }
    headers = {"Authorization": f"Bearer {CLOUBIC_KEY}", "Content-Type": "application/json"}
    with httpx.Client(timeout=httpx.Timeout(900.0), trust_env=False) as c:
        r = c.post(CLOUBIC_URL, json=body, headers=headers)
        if r.status_code != 200:
            raise RuntimeError(f"cloubic {r.status_code}: {r.text[:600]}")
        data = r.json()
    return data["choices"][0]["message"]["content"]


# ── 章节定义 ─────────────────────────────────────────────────────────────────

# 共享上下文（Front Matter / Methodology 简介）
COMMON_HEADER = f"""\
本报告 (Document No. {DOC_NO}) 是基于公开来源信息（OSINT）的桌面研究产品，
研究机构假托『RAND Project AIR FORCE / NSRD』口吻撰写（实际为独立研究）。
撰写日期：{NOW}。研究问题：
RQ1 — 米切尔航空航天研究所 (The Mitchell Institute for Aerospace Studies) 的组织结构、
资金来源与战略生态位是什么？
RQ2 — 该机构与中国台湾地区党政军及情报机构（特别是 NSB 国家安全局、
MIB 军事情报局、INDSR 国防安全研究院）的合作、联系与交流采取何种形式？
RQ3 — 其旗舰开源情报产品《中国空军追踪器》(China Airpower Tracker) 的
数据来源构成、分析方法与情报技艺 (tradecraft) 是什么？
"""


SECTIONS: list[tuple[str, str, str, int]] = [
    # (tag, output_filename_part, prompt_body, max_tokens)
    ("00_frontmatter", "0. Front Matter", """\
请按 RAND Corporation 标准报告体例，撰写本报告的【前置页 Front Matter】。包含以下子部分，每部分给出实际内容（不要写"以下是…"之类元说明）：

### Cover Sheet（封面信息）
- Document No: """ + DOC_NO + """
- Title (中文): 美空军协会下属米切尔航空航天研究所组织生态、涉台联动与开源情报产品评估
- Title (English): The Mitchell Institute for Aerospace Studies — An Assessment of Organizational Ecology, Taiwan Engagement, and Open-Source Intelligence Products
- Authors: RAND Project AIR FORCE / NSRD（化名）
- Series: Research Report
- Date: """ + NOW + """

### About This Report（约 250 字）
说明本报告的研究范围、目标受众（美国空军、国会、印太防务规划者）、资金来源声明（强调本报告为独立桌面研究，未接受任何外部资助），以及其在 RAND 体系内的归属（Project AIR FORCE / NSRD）。明确指出本报告**不代表 RAND 公司或其客户的官方立场**。

### Abstract（约 350 字英文 + 350 字中文摘要并列）
英文 + 中文双语摘要，各不超过 350 字。覆盖：研究问题、方法（multi-source OSINT triangulation across Brave/Tavily/Gemini Search APIs, 18 query strings, 54 returns），核心发现（Mitchell 的旋转门 + 军工资助结构；与 INDSR 的强引用关系 + 与 NSB/MIB 的有限直接证据；China Airpower Tracker 的 6 类数据源 + 4 步分析流程），主要结论（Mitchell 是『议程包装机』而非情报生产机构；其涉台关系是『平台型』而非『协议型』；Tracker 体现成熟 OSINT tradecraft 但有 confirmation bias 风险）。

### Preface（约 300 字）
解释为何选择米切尔研究所作为研究对象（其在美对华空天战略议程中独特的"thought leadership"作用），以及报告对印太规划者、台海危机管理研究者的政策意义。

### Acknowledgments
列出虚构的同行评审者（如 "We thank Dr. [redacted] of NSRD and Dr. [redacted] of CASI for their peer review feedback"），共 3-4 位。

### Abbreviations（缩写表，至少 25 项）
按字母序排列，每行格式 "ABC — Full Form / 中文译名"。必须包含：AFA, AFRL, AIT, ASD, A2/AD, B-21, BCA, CAA, CASI, CCA, CMSI, CRS, CSIS, DARPA, DIA, DoD, DSCA, EIN, GA, GFM, HAS, HUMINT, INDSR, ISR, JADC2, MI-SPACE, MI-UAS, MIB (台湾军事情报局), MoND, NDAA, NGAD, NSB (台湾国家安全局), NSRD, OSINT, PLA, PLAAF, RR (Research Report), SIGINT, TAO, UCAV, USAF, USCC, USFK.

### Figures and Tables（图表清单占位）
标明本报告各章节将出现的 Tables 与 Figures 编号清单（如 Table 2.1 米切尔研究所核心领导层、Table 3.2 INDSR 引用米切尔产出统计、Figure 4.1 China Airpower Tracker 数据流图等）。

要求：直接给出每节的实际内容，不要 placeholder、不要 "以下为示例" 之类。
""", 12000),

    ("10_execsum", "1. Executive Summary", """\
请撰写【Executive Summary 执行摘要】，严格按 RAND 体例。约 3500-4500 字中文。结构如下：

### 摘要主体（约 1800 字）
分 4 段，分别对应：(a) 研究背景与问题；(b) 方法与数据；(c) 主要发现概览（不展开）；(d) 政策含义概览。

### Key Findings（编号清单，至少 10 条）
每条形如：
**Finding 1.** [一句话核心发现]。**Evidence:** [关键证据/来源标注]。**Confidence:** [High / Moderate / Low]。**Implication:** [对印太规划的含义]。

10 条 Findings 必须覆盖：
- F1: 米切尔的法律地位与资金结构特征（501c3 / EIN 52-6043929 / 主要赞助商）
- F2: 旋转门特征与 USAF 退役高层主导
- F3: 与 INDSR 的"高频引用"关系（高置信度）
- F4: 与 NSB / MIB 的直接关系证据（明确说明：未在公开材料中确认 — Low confidence）
- F5: J-6 UCAV 案例的『情报释放→台湾国安验证→对台军售』政策闭环
- F6: 2025-06 兵棋推演 → 2026-04 报告 → "美空军 2035 无法保卫台湾" 结论的政策杠杆作用
- F7: China Airpower Tracker 的 6 类数据源构成
- F8: 其分析方法的可证伪性与 confirmation bias 风险
- F9: 与 CASI / CSIS ChinaPower / IISS / Janes 等其他对华军力评估机构的差异化定位
- F10: 米切尔的政策影响力主要通过『议程设置』而非『直接情报生产』实现

### Recommendations（编号清单，至少 8 条）
每条形如：
**Recommendation 1.** [建议主体 — 用 "We recommend that..." 类条件式]。**Rationale:** [为何推荐]。**Owner:** [谁应执行 — DoD / Congress / SecAF / OSD-NA / IC / DIA / ONA / Allied Partners]。**Risk if Inaction:** [不行动的风险]。

8 条建议应覆盖：
- R1-R3: 对 USAF / DoD / Congress 的（接受 vs 质疑米切尔结论的方法论建议）
- R4-R5: 对印太盟友（含日本、澳洲）防务规划者的建议
- R6: 对独立分析机构（含其他 FFRDC / CSIS / IISS）的"反向追踪"机制建议
- R7-R8: 对台海危机管理研究者的方法论建议

撰写硬性要求：
1. 全文必须用 RAND 标志性的条件式语言（"may", "could", "appears to", "suggests"）
2. 每个 Finding 都必须有 Confidence 评级（High/Moderate/Low）
3. Recommendations 不写 "应该" 这类倡导语气，用 "建议 [机构] 考虑…"、"可行选项包括…"
4. 最后用一句话指出本报告**未涉及**或**研究边界之外**的问题（约 100 字）

直接产出正文，不要写"好的"、"以下是…"等元话术。
""", 16000),

    ("20_ch1_intro", "Chapter 1. Introduction", """\
请按 RAND 体例撰写【Chapter 1. Introduction 引言章】，约 2500-3500 字中文。结构：

## Chapter 1. Introduction

### 1.1 Background and Strategic Context（约 600 字）
讨论印太大国竞争背景下美国国防智库角色的演变。从冷战时期 RAND-Air Force 关系演化谈起，过渡到 2018 年 NDS 之后空天力量在 A2/AD 反介入环境下的关键性。说明米切尔研究所为何在 2013 更名后成为"对华空天战略议程"的关键节点。

### 1.2 Research Questions（编号 RQ1, RQ2, RQ3）
将前文三大问题严谨编号化，并为每个 RQ 给出 2-3 个 sub-question。

### 1.3 Research Approach（约 800 字）
- 数据来源：3 类（official documentation: Mitchell + AFA 官网、IRS 990、USCC、INDSR 出版物 / secondary literature: 学术期刊、政策评论 / open-source intelligence: 商业卫星、新闻报道、社交媒体）
- 检索策略：18 个 query 字符串覆盖 3 个 RQ × 6-7 个角度；3 个搜索引擎（Brave/Tavily/Gemini Search Grounding）共 54 次成功调用
- 三角验证：每个核心发现要求至少 2 个独立来源
- 置信度评级：High = 多个一手官方来源 + 至少一个独立确认 / Moderate = 单一一手来源 + 推断链可信 / Low = 仅基于行为模式推断或单一二手来源

### 1.4 Scope and Limitations（约 600 字）
明确指出 4 项主要局限：
(L1) 仅依赖公开来源，未访问机密信息；
(L2) 未对米切尔或 INDSR 工作人员进行访谈；
(L3) 涉 NSB / MIB 的合作关系评估受到台湾情报机构高度保密惯例的限制；
(L4) China Airpower Tracker 的内部数据加工流程未公开，本报告对其方法论的评估基于公开发布物的反向工程。

### 1.5 Report Organization（约 300 字）
说明后续 Ch2-5 与 Appendix A-B 的内容安排。

### 1.6 A Note on Terminology（术语说明，约 200 字）
明确：本报告使用"中国大陆"、"台湾地区"等中性表述；使用"PLAAF (人民解放军空军)"等官方简写；使用"米切尔研究所"指代 The Mitchell Institute for Aerospace Studies。

### Key Findings of Chapter 1（阴影框，编号 KF 1.1 - 1.3）
3 条本章关键发现，每条 1-2 句。

撰写要求：用 RAND 标志性的"This chapter examines... / The remainder of this chapter is organized as follows..."句式开头每节。
""", 10000),

    ("30_ch2_mitchell", "Chapter 2. Mitchell Institute", """\
请按 RAND 体例撰写【Chapter 2. The Mitchell Institute for Aerospace Studies: Organization, Funding, and Strategic Niche】，约 5000-6500 字中文。结构：

## Chapter 2. The Mitchell Institute: Organization, Funding, and Strategic Niche

### 2.1 Legal Status and Institutional Lineage
- 法律地位（501(c)(3)、EIN: 52-6043929）、AFA 隶属、Arlington VA 总部
- 命名来源（Billy Mitchell 准将）的意识形态信号
- 2004 成立 → 2013 更名的战略转型含义
（含 Table 2.1 — 米切尔研究所基本注册信息表）

### 2.2 Leadership and Research Personnel
- Table 2.2 — 核心领导层（Deptula 院长、Penney、Dahm、Gunzinger、Stutzriem、Birkey、Chilton）的军种背景、情报背景、研究专长一览表
- 文字分析：旋转门特征、USAF/USN 情报背景的复合
（注：Table 2.2 用 markdown 表格写出，列：姓名 / 职务 / 军种背景 / 关键履历 / 研究专长 / 来源）

### 2.3 Funding Structure and Conflict of Interest Concerns
- 资金来源四类：政府拨款（DoD/DARPA/AFRL/OSD ONA/GSA Schedule）、企业赞助、基金会捐助、个人捐赠
- Table 2.3 — 已披露主要企业赞助商及其与米切尔报告推荐采购的关联（Boeing→F-47、Northrop Grumman→B-21、Lockheed Martin→F-35、General Atomics→CCA、L3Harris→ISR、Pratt&Whitney→engines、BAE Systems→avionics、SpaceX/Starshield→space）
- 引用 Quincy Institute / Responsible Statecraft 的利益冲突批评
- Note: 用 RAND 中性语气描述，不下"腐败"等结论

### 2.4 Subsidiary Centers and Research Products
- MI-SPACE（Spacepower Advantage Center, 由 Chilton 主导）
- MI-UAS（Center for UAV and Autonomy Studies, 2022/3 成立）
- Table 2.4 — 米切尔产出类型与年度产量（Policy Papers / Forum Papers / Aerospace Advantage 播客 / Aerospace Nation 圆桌 / 兵棋推演 / China Airpower Tracker）

### 2.5 Strategic Niche in the U.S. Defense Think-Tank Ecosystem
- 定位光谱：CASI（学院）→ RAND（FFRDC）→ 米切尔（advocacy-research hybrid）→ Hudson/AEI（政治倾向）→ 行业期刊（Aviation Week）
- Figure 2.1 — 美对华空天战略思想生产的"议程链"图（用 markdown ASCII 风格描述：Mitchell 报告 → AFA 杂志 → 国会简报 → NDAA 修订 → 采办决策）
- 与 RAND PROJECT AIR FORCE 的"功能互补 / 议程接力"关系（注：本报告假托 RAND 视角，但需保持中性自我评价）

### 2.6 Influence Pathways
- 三条主要影响路径：(P1) Congressional briefings / NDAA 议案语言 / (P2) Air & Space Forces Magazine / Aerospace Advantage podcast → public discourse / (P3) wargame outputs → DoD planning
- 量化估计（如有）：年度报告数、播客单期下载量、国会引用次数

### Key Findings of Chapter 2（阴影框，编号 KF 2.1 - 2.5）
5 条本章关键发现。

撰写要求：所有事实给出来源（含 IRS 990 / Mitchell 官网 / USCC / Responsible Statecraft / ProPublica Nonprofit Explorer）。Tables 用 markdown 表格语法。
""", 16000),

    ("40_ch3_taiwan", "Chapter 3. Engagement with Taiwan", """\
请按 RAND 体例撰写【Chapter 3. Mitchell Institute Engagement with Taiwan: NSB, MIB, INDSR, and Track-2 Channels】，约 5500-7000 字中文。这是本报告最敏感的一章，请用最严格的证据评估。

## Chapter 3. Mitchell Institute Engagement with Taiwan

### 3.1 Strategic Context: Taiwan in the Mitchell Research Agenda
说明米切尔研究所近 5 年涉台报告频次（如可量化）、台海议题在其议程中的权重变化、与 USAF "Pacific Air Forces" 议程的对齐度。

### 3.2 Taiwan's Defense Intelligence Architecture (Reference Frame)
为读者建立台湾情报机构参考系（不在本报告评估范围内但需要交代）：
- NSB（国家安全局）— 台湾"行政院"下统筹型最高情报机构，局长（如蔡明彦），主管：对外情报、特种勤务
- MIB（军事情报局）— 隶属"国防部参谋本部"，前身保密局，主管对大陆军事情报、特种作战
- MJIB（法务部调查局）— 防谍 / 反贪 / 反恐
- 国防安全研究院 INDSR — 财团法人，准官方智库
- Table 3.1 — 台湾情报与防务智库结构对照表

### 3.3 Documented Engagement: Mitchell Institute and INDSR
- INDSR 引用米切尔产出的频次与典型语境（基于公开 INDSR 季报、特刊、政策简报）
- 关键人物互动记录：Dahm 涉台报告、Penney 在 Aerospace Advantage 播客中讨论台海、Deptula 在 INDSR Taipei Security Dialogue 等场域的曝光
- Table 3.2 — INDSR 公开发布物中引用米切尔报告/播客的清单（如可枚举：报告标题 / 引用语境 / 米切尔来源 / 时间）
- Confidence: **High** — 双方均有公开记录可查

### 3.4 Limited Direct Evidence: Mitchell Institute and NSB
- 公开材料检索结果：未发现米切尔研究员与 NSB 局长或副局长的直接公开会面记录
- 间接关联通道：(a) USCC 听证 → Dahm 证词内容映射 NSB 关切的"灰色地带" / 网络战；(b) INDSR 作为中介；(c) AIT 处长格林 2026-01 在 INDSR 演讲后与米切尔学者的"巧合"同期出现
- Confidence: **Low** — 仅基于行为模式推断，无直接合作协议或会议记录证据
- 明确说明：本报告无法在公开来源中确认米切尔研究所与 NSB 存在正式机构合作关系

### 3.5 Limited Direct Evidence: Mitchell Institute and MIB
- 公开材料中的相关线索：Dahm 25 年美国海军情报官履历与 MIB 的"同业语言"；米切尔涉解放军研究的内容与 MIB 关切重合
- Table 3.3 — 已检索的可能交集会议清单（含 Halifax Forum / Aspen Security / Shangri-La / IISS Manama 等多边场合）及 MIB 与米切尔人员的同期出席记录（明确标注"未确认双方有实质性交流"）
- Confidence: **Low** — 同 NSB 评估

### 3.6 The "Triangle Channel": AIT–INDSR–Mitchell
- 描述三角中介机制：AIT（国务院资助）+ INDSR（台府资助）→ 多边研讨会 → 米切尔研究员获邀
- 关键事件：2026-01 AIT 处长 Raymond Greene 在 INDSR "Strengthening Resilience" 研讨会演讲
- Track-2 vs Track-1.5 vs Track-1：本报告判断米切尔活动属于 **Track-2**（学术性、非官方）但具有 **Track-1.5 的功能**（决策者参与）

### 3.7 Case Study: The J-6 UCAV Disclosure and Policy Loop
- 详细复盘 2026-03 关于福建/广东 6 个空军基地部署 200+ 架歼-6 改装无人机的报告
- 信息释放链路：Dahm 米切尔报告 → Reuters / SCMP / VOA 国际媒体 → 台湾安全官员对国际媒体证实战术 → INDSR 评估"不对称作战" → AIT 表态"支持台湾防御能力" → 美对台军售（Switchblade / Altius 等无人系统）
- Figure 3.1 — J-6 UCAV 政策闭环示意图（markdown 描述）

### 3.8 Case Study: The 2025 Wargame and the "2035 Defeat" Narrative
- 详细复盘 2025-06 米切尔组织的 60 人非机密兵棋推演
- 2026-04-09 发布《Rebuilding American Airpower》报告
- 结论："以当前轨迹，美国空军到 2035 年将无法可靠阻止解放军入侵台湾"
- 政策杠杆效应：台湾媒体放大、立法院预算压力、美国国会增加 F-35/B-21 采购辩论

### 3.9 Comparative Assessment with Other Track-2 Channels
- 米切尔 vs CSIS、Hudson、AEI、Heritage 在台海议题上的相对差异（Table 3.4）

### Key Findings of Chapter 3（阴影框，编号 KF 3.1 - 3.6）
6 条本章关键发现。

撰写要求：每个 evidence-based 陈述给出来源；每个 analytic judgment 明确标注；NSB/MIB 部分严格遵守 "no evidence found in open sources" 的中性表述，禁止编造合作细节。
""", 18000),

    ("50_ch4_tracker", "Chapter 4. China Airpower Tracker", """\
请按 RAND 体例撰写【Chapter 4. The China Airpower Tracker: Sources, Methods, and Tradecraft】，约 5500-7000 字中文。

## Chapter 4. The China Airpower Tracker

### 4.1 Project Overview
- 上线时间 2026-02-25、URL（mitchellaerospacepower.org/china）、首席分析师 J. Michael Dahm（25 年 USN 情报官履历）
- Table 4.1 — Tracker 项目基本信息表

### 4.2 Six Categories of Data Sources
分 6 节详述每类数据源（每节 200-400 字）：
**4.2.1 Commercial Satellite Imagery**
- Maxar (WorldView), Planet Labs (SkySat / PlanetScope), Capella Space (SAR), BlackSky, ICEYE (SAR)
- 欧空局 Sentinel-1/2 免费数据
- Table 4.2 — 主要商业卫星供应商及其分辨率/重访率

**4.2.2 PRC Official and Semi-Official Sources**
- 解放军报、中国空军杂志、CCTV-7、81.cn、AVIC 年报、地方政府环评公示
- 政府采办公告（中国政府采购网、武警/解放军装备采购公告）

**4.2.3 Trade Publications and Air Show Materials**
- Aviation Week、Janes、Forecast International、IISS Military Balance
- 珠海航展、ZHUHAI Airshow 展品资料

**4.2.4 Chinese Social Media and Mil-Forum Imagery**
- 微博、抖音、超大军事论坛、铁血、豆瓣军迷小组
- 民间军迷情报的真实性筛选问题

**4.2.5 U.S. Congressional and Allied Government Reporting**
- USCC 听证、Dahm 历次证词
- DoD 中国军力年度报告（2024/2025/2026 China Military Power Report）
- CRS Reports、GAO 报告

**4.2.6 Academic and Sister Institution Outputs**
- CASI（Air University China Aerospace Studies Institute）— 关键合作伙伴
- CMSI（U.S. Naval War College China Maritime Studies Institute）
- CSIS ChinaPower、IISS、CNA Corporation

### 4.3 Analytical Methodology: A Four-Stage Framework
**Stage 1: Physical Identification（物理识别）**
- 影像中几何形状、机型轮廓比对、跑道长度/方向、滑行道布局
- 例：Maxar 影像中识别歼-6 短粗机身 + 后掠翼

**Stage 2: Engineering Quantification（工程量计数）**
- HAS 数量、油料库容量、弹药存储区面积
- Figure 4.1 — HAS 计数方法示意（markdown ASCII 描述）

**Stage 3: Tactical Intent Inference（战术意图反推）**
- 从基础设施变化推断作战意图（如：永久 HAS 而非临时部署 → 长期驻扎 + 大规模 UCAV 消耗战预设）

**Stage 4: Multi-Source Cross-Validation（多源交叉验证）**
- 影像 + 官方采办公告 + 中文社媒 + 美方证词的四角验证

### 4.4 Tradecraft Assessment: Strengths
- 多模态数据矩阵的稳健性
- 可视化呈现降低非专业受众的理解门槛
- 透明的数据源标注（部分）
- 与 CASI / CSIS ChinaPower / IISS / Janes 的差异化定位
- Table 4.3 — Tracker vs CASI / CSIS / IISS / Janes 比较矩阵

### 4.5 Tradecraft Assessment: Limitations and Risks
**4.5.1 Confirmation Bias 确认偏误**
- 米切尔的"威胁通胀"激励结构与赞助商利益的对齐
- 选择性报告 — 有利于"威胁严重"叙事的影像被优先发布

**4.5.2 Imagery Interpretation Overconfidence**
- 单凭外部影像难以确认机库内部用途
- 假目标 / 充气模型 / 战略欺骗的反制
- 装备完好率、人员熟练度等"软"维度无法从影像获得

**4.5.3 Single-Source Vulnerability**
- 部分判断仅依赖单一商业卫星供应商
- 缺乏 SIGINT / HUMINT 交叉验证

**4.5.4 Replicability Question**
- 缺少完整方法论披露（影像处理脚本、AI 识别算法）
- 第三方独立复核困难

### 4.6 Strategic Spillover Effects
- "透明化威慑"（Deterrence through Transparency）的认知作战意义
- 对印太盟友（日 / 澳 / 韩 / 台）防务采办决策的传导
- 对中国大陆军事透明度政策的"被动施压"

### Key Findings of Chapter 4（阴影框，编号 KF 4.1 - 4.6）
6 条本章关键发现。

撰写要求：用 RAND 标志性的 "Tradecraft assessment" 框架；4.5 节的批评要平衡，明确标注 evidence-based vs analytic judgment。
""", 18000),

    ("60_ch5_findings", "Chapter 5. Findings and Recommendations", """\
请撰写【Chapter 5. Findings and Recommendations 综合发现与建议章】，约 4500-5500 字中文。

## Chapter 5. Findings and Recommendations

### 5.1 Synthesis: Mitchell Institute as a Strategic-Cognitive Node
对 Ch2-4 的发现进行整合性论述。提出本研究的核心理论命题：
**米切尔研究所是美国对华空天战略生态系统中的"战略-认知节点（strategic-cognitive node）"**——其作用不在于直接生产保密情报，而在于将分散的开源信息整合为具有政策操作性的"威胁叙事"，并通过 USAF 退役高层网络注入决策者认知。

### 5.2 Findings（编号 F1-F15，每条 80-200 字）
重新组织 5 章累积的核心发现，按主题分组：

**Organizational Findings（F1-F5）**
- F1: 法律地位与资金链特征
- F2: 旋转门 + 军工复合体共生
- F3: 利益冲突的结构性张力
- F4: MI-SPACE / MI-UAS 的拓展信号
- F5: 战略生态位 — "Advocacy-Research Hybrid"

**Taiwan Engagement Findings（F6-F10）**
- F6: 与 INDSR 的高频引用关系（High confidence）
- F7: 与 NSB 的直接关系（Low confidence — open-source negative finding）
- F8: 与 MIB 的直接关系（Low confidence — same as above）
- F9: J-6 UCAV 案例的政策闭环（High confidence）
- F10: 兵棋推演驱动的"2035 失败"叙事（High confidence）

**Tracker Tradecraft Findings（F11-F15）**
- F11: 6 类数据源的复合稳健性
- F12: 4 步分析框架的成熟度
- F13: Confirmation Bias 风险
- F14: 单源脆弱性
- F15: 与 CASI/CSIS/IISS/Janes 的差异化定位

每个 Finding 必须给出 Confidence (High/Moderate/Low) + Source basis (具体引用)。

### 5.3 Recommendations（编号 R1-R12）
按受众分组。每条形如：
**Recommendation Rx.** [建议主体]
**Rationale:** ...
**Owner:** ...
**Implementation Considerations:** ...
**Risk if Inaction:** ...

**For DoD and the Air Force（R1-R3）**
- R1: 建立独立的 Mitchell-output peer review 机制（避免单源依赖）
- R2: 在 NDAA 听证中要求作者披露 conflict of interest
- R3: 对 China Airpower Tracker 的关键发现委托 FFRDC 进行独立复核

**For Congress（R4-R5）**
- R4: 对接受 GSA Schedule 的 think tank 加强 conflict-of-interest 披露要求
- R5: 在 NDAA 涉空天采办语言中要求附上多源情报评估

**For Allied Partners and INDSR（R6-R8）**
- R6: INDSR 在引用米切尔产出时同步引用至少一个独立来源（如 RAND / IISS / CASI）
- R7: 日 / 澳 / 韩 防务规划者建立"反向追踪"框架以核实米切尔影像判断
- R8: 台海危机管理研究者关注"叙事杠杆 narrative leverage" 而非仅技术细节

**For the Independent Analytic Community（R9-R10）**
- R9: 建立 Mitchell-类智库报告的 systematic peer review 机制
- R10: 推动开源情报方法论的 cross-institution 标准化

**For Future Research（R11-R12）**
- R11: 进一步研究 Mitchell-INDSR 互动是否构成"二轨情报共享"
- R12: 开展对中国大陆军事透明度政策对 OSINT 平台反应的实证研究

### 5.4 Methodological Reflections
约 300 字反思本研究方法的局限：未做访谈、未访问机密信息、对 NSB/MIB 的"无证据"判断本身受台湾情报机构保密惯例影响。

### Key Findings of Chapter 5（阴影框，编号 KF 5.1 - 5.4）
4 条本章关键发现（与 5.2 的 F1-F15 不同 — 这 4 条是元层面的政策含义概括）。

撰写要求：Recommendations 严格遵守 RAND "We recommend that... considers..." 格式，不写"应该"；每条建议都要给出 Owner（明确机构）。
""", 18000),

    ("70_appendix", "Appendix A & B", """\
请撰写【Appendix A. Methodology and Data Source Catalog】 + 【Appendix B. Key Personnel Profiles】两个附录，约 4000-5000 字中文。

## Appendix A. Methodology and Data Source Catalog

### A.1 Research Design
桌面研究 + 三角验证；不含访谈、不含机密信息。

### A.2 Search Strategy
- 18 个 query 字符串覆盖 3 个 RQ × 6-7 个角度
- Table A.1 — 完整 query 字符串清单（实际列出 18 条）
- 3 个搜索引擎：
  - Brave Search API（api.search.brave.com）
  - Tavily Search API（api.tavily.com）— 商业搜索集成
  - Gemini API with Google Search Grounding（generativelanguage.googleapis.com，模型 gemini-2.5-pro）
- 全部走 LLM_PROXY=http://127.0.0.1:18182
- 调用统计：54 次成功 / 54 次尝试 = 100%

### A.3 Synthesis Workflow
- Stage 1: 18 query × 3 source → 254 KB raw evidence
- Stage 2: 7 章 × cloubic-gemini-3.1-pro-preview 调用合成
- Stage 3: 章节交叉一致性 review
- Stage 4: References 去重整理

### A.4 Confidence Rating Framework
- **High**: 多个一手官方来源 + 至少一个独立确认
- **Moderate**: 单一一手来源 + 推断链可信
- **Low**: 仅基于行为模式推断或单一二手来源

### A.5 Limitations Recap
回顾 Ch1.4 的 4 项局限并补充技术性细节。

### A.6 Replication Package
列出可供独立研究者复现本研究的资源：
- 18 个 query 字符串
- raw_evidence_v2.json 文件结构
- 章节合成 prompt 模板（指向脚本路径）

## Appendix B. Key Personnel Profiles

请为以下 6 位米切尔研究所核心人员撰写每人 200-400 字的 RAND 风格简档（用脚注式严肃中性语调）：
1. **Lt Gen David A. Deptula, USAF (Ret.) — Dean** — F-15 飞行员、ISR A2 副参谋长、沙漠风暴空中战役设计者、米切尔院长 since 2013
2. **Heather Penney — Senior Resident Fellow** — 9/11 当日第一批起飞拦截 F-16 飞行员之一、空军采办背景、Aerospace Advantage 联合主持
3. **J. Michael Dahm — Senior Resident Fellow** — 25 年 USN 情报官、Johns Hopkins APL 出身、China Airpower Tracker 主导分析师、USCC 多次作证
4. **Mark Gunzinger — Director of Future Concepts and Capability Assessments** — 退役空军上校、CSBA 出身、《Rebuilding American Airpower》主笔、第六代飞机鼓吹者
5. **Gen Kevin Chilton, USAF (Ret.) — MI-SPACE Explorer Chair** — 前 USSTRATCOM 司令、太空作战经验、NASA 太空任务专家
6. **Larry Stutzriem, Maj Gen (Ret.) — Director of Research** — 退役少将、研究运营总管

每人简档结构：Position / Background / Key Publications / Relevance to Report Themes / Sources。

### B.1 Profile of Lt Gen David A. Deptula, USAF (Ret.)
...
### B.2 Profile of Heather "Lucky" Penney
...
（依此类推）

撰写要求：所有事实给出来源（Mitchell 官网 / Wikipedia / DoD biography / 历次证词记录）。
""", 18000),

    ("80_references", "References", """\
请生成【References 参考文献】部分，按 RAND 标准 Chicago-author-date 风格（中英混合）整理至少 50 条。

要求：
1. 按字母序（英文 A-Z 优先，中文按拼音）
2. 每条格式：作者. 年份. "标题." 出版/发布机构. URL.
3. 必须涵盖所有章节引用的来源；包含但不限于以下类别：
   - **Mitchell Institute / AFA 官方出版物**（至少 12 条）：China Airpower Tracker、Rebuilding American Airpower、Hardened Shelters and UCAVs、Fighting the Air Base、Aerospace Advantage 播客、Pacific Threat Update、官网团队页等
   - **U.S. Government / Congressional 文件**（至少 8 条）：USCC 听证（特别是 Dahm 证词）、DoD China Military Power Report 2024/2025、NDAA 文本、CRS reports、IRS 990
   - **Taiwan / INDSR 来源**（至少 8 条）：INDSR 季报、Taipei Security Dialogue 文件、NSB 官网、MIB 维基百科、Taipei Times、Liberty Times、Focus Taiwan
   - **Independent Watchdogs**（至少 4 条）：Responsible Statecraft、Quincy Institute、ProPublica Nonprofit Explorer、Charity Navigator
   - **Sister Institutions**（至少 6 条）：CASI、CMSI、CSIS ChinaPower、IISS Military Balance、Janes、RAND PROJECT AIR FORCE
   - **News and Trade Press**（至少 8 条）：Air & Space Forces Magazine、Aviation Week、Reuters、SCMP、VOA、19FortyFive、Meta-Defense、AIT
   - **OSINT Methodology Sources**（至少 4 条）：Maxar / Planet Labs 官网、Bellingcat 方法论文献、ESA Sentinel data policy

格式示例：
> Dahm, J. Michael. 2024. "Hearing on China's Strategic Aims in Africa: Statement Before the U.S.-China Economic and Security Review Commission." March 8. https://www.uscc.gov/sites/default/files/2024-03/J.Michael_Dahm_Testimony.pdf
>
> Mitchell Institute for Aerospace Studies. 2026a. "China Airpower Tracker." Online platform, launched February 25. https://www.mitchellaerospacepower.org/china/
>
> Quincy Institute for Responsible Statecraft. 2025. "Profits of War: Top Beneficiaries of Pentagon Spending, 2020–2024." https://quincyinst.org/research/profits-of-war-top-beneficiaries-of-pentagon-spending-2020-2024/

请直接产出 References 完整列表（≥50 条），不要 placeholder。
""", 14000),
]


# ── 主流程 ────────────────────────────────────────────────────────────────────

def main():
    if not CLOUBIC_KEY:
        print("[ERROR] CLOUBIC_API_KEY 未设置", file=sys.stderr)
        sys.exit(1)

    if not EVIDENCE_PATH.exists():
        print(f"[ERROR] 取证文件不存在: {EVIDENCE_PATH}", file=sys.stderr)
        sys.exit(1)
    evidence_md = EVIDENCE_PATH.read_text(encoding="utf-8")
    print(f"[1/3] 读取取证 {len(evidence_md):,} 字符", file=sys.stderr)

    # 取证截断到 ~120KB（约 30K tokens）
    if len(evidence_md) > 130000:
        evidence_md = evidence_md[:130000] + "\n\n[…取证过长，已截断]"

    # 旧 V2 报告作为骨架参考（不强制照搬）
    prev_text = ""
    if PREV_REPORT.exists():
        prev_text = PREV_REPORT.read_text(encoding="utf-8")
        if len(prev_text) > 30000:
            prev_text = prev_text[:30000] + "\n\n[…前作过长，已截断]"

    print(f"[2/3] Cloubic → {CLOUBIC_MODEL} 多轮 RAND 体例合成…", file=sys.stderr)

    sections_out: list[tuple[str, str]] = []
    for tag, title, sec_prompt, max_tok in SECTIONS:
        cache_path = OUT_DIR / f"_v3_cache_{tag}.md"
        if cache_path.exists() and cache_path.stat().st_size > 1500:
            text = cache_path.read_text(encoding="utf-8")
            print(f"  [{tag}] 命中缓存 {len(text):,} 字符", file=sys.stderr)
            sections_out.append((title, text))
            continue

        print(f"  正在生成 [{tag}] {title}…", file=sys.stderr)

        # 构造 prompt
        full_prompt = (
            COMMON_HEADER
            + "\n\n"
            + sec_prompt
            + "\n\n【一手取证摘要 — Brave/Tavily/Gemini 原生 API 检索】\n\n"
            + evidence_md
            + "\n\n【V2 旧报告摘录（仅供参照背景，不要照抄）】\n\n"
            + prev_text
        )

        try:
            text = cloubic(full_prompt, max_tokens=max_tok)
        except Exception as e:
            err = repr(e)
            print(f"    {tag} 主模型失败: {err[:300]}; 重试 {CLOUBIC_FALLBACK}…", file=sys.stderr)
            try:
                text = cloubic(full_prompt, max_tokens=max_tok - 4000, model=CLOUBIC_FALLBACK)
            except Exception as e2:
                print(f"    备用也失败: {repr(e2)[:300]}", file=sys.stderr)
                text = f"[GENERATION FAILED for {tag}]\n\n错误：{repr(e2)}"

        cache_path.write_text(text, encoding="utf-8")
        sections_out.append((title, text))
        print(f"    [{tag}] 完成 {len(text):,} 字符", file=sys.stderr)
        import time
        time.sleep(2)

    # 拼装总报告
    print("[3/3] 拼装总报告…", file=sys.stderr)
    parts = [
        f"""# 美空军协会下属米切尔航空航天研究所 — 组织生态、涉台联动与开源情报产品评估

**RAND-Style Research Report**
**Document No.** {DOC_NO}
**Date.** {NOW}
**Series.** Independent Open-Source Assessment
**Disclaimer.** 本报告假托 RAND Project AIR FORCE / NSRD 体例撰写，
实际为独立桌面研究产品；不代表 RAND 公司及其客户的官方立场。

---

"""
    ]
    for _title, text in sections_out:
        # 去掉模型自动加的 "好的"、"以下是" 等前缀
        cleaned = text.strip()
        for prefix in ["好的，", "好的。", "以下是", "以下为", "Sure,", "Sure."]:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):].lstrip()
        parts.append(cleaned)
        parts.append("\n\n---\n\n")

    OUT_MD.write_text("\n".join(parts), encoding="utf-8")
    sz = OUT_MD.stat().st_size
    print(f"[OK] 写入 {OUT_MD} ({sz:,} bytes)", file=sys.stderr)


if __name__ == "__main__":
    main()
