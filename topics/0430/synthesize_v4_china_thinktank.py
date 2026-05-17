"""V4 — 中国智库风格简化版深度报告。

风格基准：参照 CICIR / CIIS / SIIS / 清华战略与安全研究中心（SCSS）/ 复旦美研中心
的政策报告与战略研判文章。

特征：
  - 章节标题用中文（四字格 / 对仗式）
  - 直接陈述，少用条件式
  - 客观、理性、精炼，突出重点
  - 末尾必有"对我启示"或"政策建议"
  - 篇幅控制在 15000-20000 字
  - 引用用 [1] 上标式
"""
from __future__ import annotations

import io
import os
import socket
import sys
import time
from datetime import datetime
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# 修复本地代理把 api.cloubic.com 劫持为 fake-IP 的 SSL 问题
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

CLOUBIC_KEY = os.environ.get("CLOUBIC_API_KEY", "")
CLOUBIC_URL = os.environ.get("CLOUBIC_BASE_URL", "https://api.cloubic.com/v1/chat/completions")
CLOUBIC_MODEL = "gemini-3.1-pro-preview"
CLOUBIC_FALLBACK = "gemini-3-pro-preview"

OUT_DIR = _HERE.parent
EVIDENCE_PATH = OUT_DIR / "raw_evidence_v2.md"
PREV_REPORT_V3 = OUT_DIR / "米切尔研究所_RAND体例分析_v3.md"
OUT_MD = OUT_DIR / "米切尔研究所_战略研判_v4.md"
NOW = datetime.now().strftime("%Y年%m月")


def cloubic(prompt: str, max_tokens: int = 16000, model: str | None = None) -> str:
    body = {
        "model": model or CLOUBIC_MODEL,
        "messages": [
            {"role": "system", "content": (
                "你是中国智库（中国现代国际关系研究院 CICIR / 中国国际问题研究院 CIIS / "
                "上海国际问题研究院 SIIS / 清华大学战略与安全研究中心 SCSS）的资深研究员。"
                "请按中国智库政策研究报告的标准体例撰写中文报告："
                "(1) 客观、理性、精炼，突出重点；"
                "(2) 直接陈述，避免英文条件式（may/could/suggests），"
                "    用『研判』『综合判断』『总体看』『值得关注』『需要警惕』等中文政策研究语汇；"
                "(3) 章节标题用中文（四字格、对仗式或主谓式），不用英文 'Chapter N'；"
                "(4) 关键英文术语在首次出现时附中英对照（如『开源情报（OSINT）』），后续用中文；"
                "(5) 区分『已确证』『综合判断』『据公开信息推断』三档置信度，但不要堆砌标签；"
                "(6) 涉及外国机构、人物、地名时用规范译名（如『米切尔航空航天研究所』『国防安全研究院』）；"
                "(7) 涉台用词规范：『台湾地区』『民进党当局』『台湾国安局』『台湾军情局』；"
                "(8) 不写客套语，不用『好的』『以下是』开头，直接进入内容；"
                "(9) 数据用阿拉伯数字，引用用 [1][2] 上标式；"
                "(10) 风格基准：政策研究文，不是新闻稿、不是宣传稿、不是学术论文。"
            )},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "max_tokens": max_tokens,
    }
    headers = {"Authorization": f"Bearer {CLOUBIC_KEY}", "Content-Type": "application/json"}
    with httpx.Client(timeout=httpx.Timeout(900.0), trust_env=False) as c:
        r = c.post(CLOUBIC_URL, json=body, headers=headers)
        if r.status_code != 200:
            raise RuntimeError(f"cloubic {r.status_code}: {r.text[:600]}")
        data = r.json()
    return data["choices"][0]["message"]["content"]


# ── 5 段式简化结构 ───────────────────────────────────────────────────────────

SECTIONS: list[tuple[str, str, int]] = [
    ("00_summary", """\
请撰写【内容摘要与核心研判】，约 1200-1500 字。结构：

## 内容摘要

(开篇 200 字左右段落) 介绍研究对象、背景、研究问题与本文研判的总体框架。

## 核心研判

以"判断 1 ─ 标题"形式列出 5 条核心研判，每条 150-200 字，必须包含：
- 判断 1：米切尔研究所性质 — 美国军工复合体的"议程包装机"
- 判断 2：与台湾"国防安全研究院"形成"二轨回音壁"机制
- 判断 3：与台湾国安局、军情局的直接联系尚无公开证据，但战略协同明显
- 判断 4：《中国空军追踪器》是开源情报武器化的新形态
- 判断 5：该机构对华空天战略议程的塑造能力被严重低估

## 主要建议

3 条精炼建议（每条 80-100 字），分别针对：
- 反向追踪与情报对冲
- 战略叙事反制
- 学术界与情报研究界的协同

要求：摘要语言精炼有力；研判每条要有数据/事实支撑；建议要具体可操作。
""", 6000),

    ("10_intro", """\
请撰写【一、研究背景与战略意义】，约 800-1000 字。

涵盖：
1. 当前美国对华空天战略竞争背景（2024-2026 趋势：印太战区前沿威慑、A2/AD、"2027 决胜年"等）
2. 美国国防智库在对华政策制定中的角色演变
3. 米切尔航空航天研究所为何值得专门研究（其在华盛顿对华政策圈的独特位置）
4. 本文研究问题（3 个）与方法（多源开源情报三角验证 + 政策研判）

章节标题用中文。开篇用一段类似"近年来，随着…"的政策研究开头。
""", 5000),

    ("20_organization", """\
请撰写【二、组织架构与资金脉络】，约 2500-3000 字。结构：

## 二、组织架构与资金脉络

### （一）法律地位与组织沿革

简要说明：501(c)(3) 性质、AFA 隶属、EIN 52-6043929、阿灵顿总部、2004 成立、2013 更名、Billy Mitchell 命名缘起的意识形态信号。约 400 字。

### （二）领导团队特征

用一段文字加一个简表呈现核心 6 人（Deptula 院长、Penney、Dahm、Gunzinger、Stutzriem、Chilton），重点突出"美军退役高层 + 情报背景"的旋转门特征。约 600 字。

表格用 markdown：
| 姓名 | 职务 | 军种背景 | 关键履历 |
| --- | --- | --- | --- |

### （三）资金链结构与利益绑定

分析三大资金来源：政府拨款（DoD/DARPA/AFRL/OSD/GSA Schedule）、企业赞助（波音、洛马、诺格、雷神、通用原子、L3Harris、BAE、普惠、SpaceX）、基金会与个人捐助。

重点指出"利益冲突"问题：推荐采购的武器（B-21、F-47、F-35、CCA）与赞助商的对应关系。约 800 字。

### （四）研究产品与传播渠道

简介产品矩阵：政策报告（Policy Paper）、论坛报告（Forum Paper）、《空天优势》（Aerospace Advantage）播客、空天国家（Aerospace Nation）圆桌、兵棋推演、《中国空军追踪器》。重点说明影响力放大机制（→ AFA 杂志 → 国会简报 → NDAA）。约 600 字。

### （五）战略生态位

一段总评（300-400 字）：米切尔在美国对华空天战略思想生产链中的位置 — 介于学院派（CASI/CMSI）、FFRDC（RAND）、行业期刊（Aviation Week）与政治倾向性智库（Hudson/AEI）之间的"倡导-研究混合体"。

要求：客观陈述事实，不渲染；引用[1]-[X]标注关键来源。
""", 12000),

    ("30_taiwan", """\
请撰写【三、涉台动向与情报联动】，约 3500-4500 字。结构：

## 三、涉台动向与情报联动

### （一）涉台议程的战略权重

说明米切尔近年涉台研究产品的频次与权重：从 2022 年关于台海前沿机场加固机库的研究[Daniel Rice 报告]，到 2024 年《抗击空军基地》（Fighting the Air Base）报告，到 2026 年初的《中国空军追踪器》及《重建美国空中力量》兵推报告。约 500 字。

### （二）与台湾"国防安全研究院"（INDSR）的学术嵌合

详细分析：
- INDSR 的法人结构（财团法人 + 立法院监督 + 经费几乎全来自台湾防务部门）
- INDSR 引用米切尔产出的频次与典型语境（重点引述 Penney、Dahm、Deptula 的论述）
- 是否有正式合作协议？现有公开材料中**未发现书面协议**，但有大量人员同框、引用共振
- 共同会议场域：Taipei Security Dialogue、Halifax Forum、Aspen Security 等

约 1000 字。

### （三）与台湾国安局、军情局的可见联系

这是最敏感的部分，请保持严谨：
- 现有公开材料中**未发现**米切尔研究所与台湾国安局（NSB）、军情局（MIB）的正式合作记录
- 但存在**间接通道**：(1) 美国在台协会（AIT）作为中介；(2) USCC 听证 Dahm 证词内容映射 NSB 关切；(3) Dahm 25 年美军海军情报官履历与 MIB 的"同业语言"
- AIT 处长格林（Raymond Greene）2026 年 1 月在 INDSR 演讲事件分析
- 据公开信息推断：米切尔与台湾国安系统是"平台型嵌合"而非"协议型合作"

明确指出：本文**不臆测**米切尔与台湾情报机构存在隐秘合作；同时指出"无证据"（absence of evidence）不等于"证据不存在"（evidence of absence）。约 1000 字。

### （四）典型案例：歼-6 改装无人机事件

详细复盘 2026 年 3 月米切尔（Dahm）发布的关于解放军在福建、广东 6 个机场部署 200+ 架歼-6 改装无人机的报告。
- 信息释放链：米切尔报告 → 路透 / SCMP / 美国之音国际媒体 → 台湾安全官员证实战术 → INDSR 评估"不对称作战形式" → AIT 表态 → 推动美对台军售（Switchblade、Altius 等无人系统）
- 这构成完整的"情报释放→台湾国安验证→对台军售"政策闭环

约 700 字。

### （五）2025 年兵棋推演与"2035 失败"叙事

复盘：2025 年 6 月米切尔组织 60 人非机密兵棋推演 → 2026 年 4 月 9 日发布《重建美国空中力量》报告 → 结论"以当前轨迹，到 2035 年美国空军将无法可靠阻止解放军入侵台湾"。

分析其政策杠杆效应：(1) 推动美国国会增加 F-35 / B-21 / NGAD 采购；(2) 借台湾媒体放大焦虑、推升立法院"国防自主"压力；(3) 为美对台军售制造"紧迫性"。

约 800 字。

要求：严格区分"已确证""综合判断""据公开信息推断"；涉及国安局、军情局部分必须严谨，不编造合作细节；引用 [X] 标注。
""", 16000),

    ("40_tracker", """\
请撰写【四、《中国空军追踪器》运作机制】，约 2500-3000 字。结构：

## 四、《中国空军追踪器》运作机制

### （一）项目概况

mitchellaerospacepower.org/china、2026 年 2 月 25 日上线、首席分析师 J. Michael Dahm（25 年美海军情报官履历）。该平台被定位为"评估解放军空军（PLAAF）能力进展与现状的权威在线工具"。

约 300 字。

### （二）数据采集六维矩阵

按 6 类数据源详述（每类 150-300 字）：
1. **商业卫星影像**：Maxar、Planet Labs、Capella、BlackSky、ICEYE、ESA Sentinel
2. **中方公开信息**：解放军报、中国空军、CCTV-7、81.cn、AVIC 年报、政府采购公告、地方政府环评公示
3. **行业期刊与航展**：Aviation Week、Janes、IISS、珠海航展资料
4. **中文社交媒体**：微博、抖音、超大军事论坛等军迷情报
5. **美方公开听证**：USCC 听证（特别是 Dahm 历次证词）、DoD 中国军力年度报告、CRS 报告
6. **学术伙伴产出**：CASI、CMSI、CSIS ChinaPower、IISS、CNA Corporation

每类要列举 1-2 个具体来源链接示例。

### （三）四步分析方法

**第一步：物理识别** — 影像中几何形状、机型轮廓比对
**第二步：工程量化** — HAS 数量、跑道长度、油料库容量计数
**第三步：战术意图反推** — 从基础设施变化推断作战意图（永久 HAS → 长期驻扎 + UCAV 消耗战预设）
**第四步：多源交叉验证** — 影像 + 官方采办公告 + 中文社媒 + 美方证词的四角验证

每步给出"福建/广东机场歼-6 UCAV"案例的具体应用。约 700 字。

### （四）作业优势与局限

**优势**：多模态数据矩阵稳健、可视化降低受众理解门槛、与 CASI / CSIS / IISS / Janes 形成差异化定位

**局限**：
- 确认偏误（confirmation bias）：选择性发布有利于"威胁严重"叙事的影像
- 影像解读过度自信：单凭外部影像难以确认机库内部用途；无法识别假目标 / 充气模型；装备完好率等"软"指标不可见
- 单源脆弱性：缺乏 SIGINT / HUMINT 交叉验证
- 复现性问题：内部数据加工流程、AI 识别算法未公开

约 600 字。

### （五）战略意图研判

研判该平台的核心战略功能：
- 对内：为美国空军预算辩论提供"科学依据"
- 对外：执行"透明化威慑"（Deterrence through Transparency）— 反向施压中国军事透明度
- 对盟：为印太盟友（日、澳、台）国防采办决策提供"统一情报底座"
- 对认知作战：在国际舆论场塑造"解放军威胁严重化"叙事

约 400 字。

要求：客观分析数据源与方法论；优势与局限并陈；战略意图部分用研判口吻。
""", 14000),

    ("50_assessment", """\
请撰写【五、综合研判与对我启示】，约 2500-3000 字。这是中国智库报告的核心收尾章节。

## 五、综合研判与对我启示

### （一）性质判断

提出三层判断：
1. **机构性质**：米切尔研究所并非传统意义上的中立情报生产机构，而是美国军工复合体的"议程包装机"和"思想孵化器"
2. **运作模式**：以高质量的开源情报作业为表，以争取空军军费、推动特定武器采购为里
3. **战略定位**：在美国对华空天战略思想生产链中扮演"战略-认知节点"角色，将技术数据转化为可操作的政策叙事

约 500 字。

### （二）影响评估

从三个维度评估其对中方的潜在影响：

**1. 对我军事透明度的"被动施压"**
《中国空军追踪器》通过商业卫星影像将解放军部署变化置于全球审视之下，对我方军事行动的隐蔽性、伪装措施、战略欺骗能力提出新挑战。

**2. 对台海冲突的"叙事杠杆"作用**
通过 J-6 UCAV、加固机库、机场扩建等具体案例的释放，配合台湾"国防安全研究院"、AIT 的协同放大，形成"威胁认知 → 资源调配 → 军售推动"政策闭环，间接推升民进党当局"以武拒统"的国际化论据。

**3. 对中方海外形象的"持续聚光灯"**
在国际智库圈、专业军事媒体形成关于解放军的"基线认知"，挤压第三国（特别是欧洲、东盟、拉美）独立研判的空间。

每点 300-400 字。

### （三）政策建议

按"对我"角度给出 6-8 条具体建议：

1. **建立反向追踪机制**：组织专门团队对米切尔产品进行系统性"逆向工程"分析，研判其数据来源、分析框架与议程偏向，形成定期评估报告
2. **构建对等开源情报平台**：利用我方商业航天能力（如长光卫星、四维世景等）建立针对美军及盟友在印太基地（关岛、冲绳、菲律宾、苏比克）的公开追踪平台，形成对冲
3. **强化战略叙事反制**：在国际学术期刊、安全论坛（如香山论坛、博鳌亚洲论坛安全分论坛）系统性揭露其"利益冲突"本质（赞助商与采购建议的对应）
4. **加强反侦察与战略欺骗**：评估《追踪器》披露内容反推我方反间反侦保密漏洞；在非敏感区域有规划地暴露假目标，消耗其分析资源
5. **关注"二轨情报链"动向**：密切监测 INDSR、GTI 等机构与米切尔的人员往来与资金流向；对涉嫌向美方泄露我方军情的台湾学者、前军方人员依法反制
6. **推动学术界系统研究**：支持国内国际关系学界、军事学界对美国"思想型智库"运作机制的系统性研究，培养这一领域的研究专家
7. **加强对美军工旋转门追踪**：建立美国国防领域"旋转门"现象数据库，量化展示个人、资金、政策建议的流动路径
8. **关注 MI-SPACE / MI-UAS 拓展**：太空力量优势中心和无人机与自主系统中心是该机构未来 3-5 年的扩张方向，需提前布局应对

每条 80-150 字。

### （四）展望与未尽课题

约 300-400 字。指出 5 个未尽问题：
- 米切尔与台湾国安局是否存在未披露的非正式渠道？
- Dahm 是否曾访台？具体行程？
- 《追踪器》底层 AI 识别算法的承包商身份？
- 米切尔是否参与日韩澳"印太共同 OSINT 平台"建设？
- 米切尔是否将拓展至东南亚、印度方向？

要求：性质判断要鲜明；影响评估要具体；政策建议要可操作；用中国智库标准的政策研究语汇。
""", 14000),

    ("60_refs", """\
请生成【参考文献】，按编号顺序整理 30-40 条权威来源。

要求：
1. 编号 [1]-[40]
2. 中英文混排，按"机构.年份.《标题》.URL"格式
3. 涵盖类别：
   - 米切尔研究所 / AFA 官方出版物（≥10 条）
   - 美国政府文件（USCC 听证、DoD 报告、CRS、IRS 990）（≥6 条）
   - 台湾相关来源（INDSR、AIT、Taipei Times、Liberty Times、Focus Taiwan）（≥6 条）
   - 独立批评机构（Responsible Statecraft、Quincy Institute、ProPublica）（≥3 条）
   - 兄弟智库（CASI、CMSI、CSIS、IISS、RAND、Stimson）（≥4 条）
   - 中文研究文献与新闻（联合早报、参考消息、环球时报、澎湃国际等）（≥4 条）
   - OSINT 方法论与卫星数据来源（Maxar、Planet Labs、ESA、Bellingcat）（≥3 条）

格式示例：
> [1] Mitchell Institute for Aerospace Studies. 2026.《中国空军追踪器》(China Airpower Tracker). https://www.mitchellaerospacepower.org/china/
> [2] Dahm, J. Michael. 2024.《关于中国战略目标的证词》（向美中经济与安全审查委员会提交）. https://www.uscc.gov/sites/default/files/2024-03/J.Michael_Dahm_Testimony.pdf
> [3] Quincy Institute for Responsible Statecraft. 2025. "Profits of War: Top Beneficiaries of Pentagon Spending, 2020–2024." https://quincyinst.org/research/profits-of-war-top-beneficiaries-of-pentagon-spending-2020-2024/

直接产出完整列表，不要 placeholder。
""", 8000),
]


def main():
    if not CLOUBIC_KEY:
        print("[ERROR] CLOUBIC_API_KEY 未设置", file=sys.stderr)
        sys.exit(1)

    if not EVIDENCE_PATH.exists():
        print(f"[ERROR] 取证文件不存在: {EVIDENCE_PATH}", file=sys.stderr)
        sys.exit(1)
    evidence_md = EVIDENCE_PATH.read_text(encoding="utf-8")
    print(f"[1/3] 读取取证 {len(evidence_md):,} 字符", file=sys.stderr)

    # 截断到 ~110KB（约 28K tokens）
    if len(evidence_md) > 110000:
        evidence_md = evidence_md[:110000] + "\n\n[…取证过长，已截断]"

    # 读 V3 作骨架参考
    prev_text = ""
    if PREV_REPORT_V3.exists():
        prev_text = PREV_REPORT_V3.read_text(encoding="utf-8")
        if len(prev_text) > 25000:
            prev_text = prev_text[:25000] + "\n\n[…前作过长，已截断]"

    print(f"[2/3] Cloubic → {CLOUBIC_MODEL} 中国智库风格合成…", file=sys.stderr)

    sections_out: list[str] = []
    for tag, sec_prompt, max_tok in SECTIONS:
        cache_path = OUT_DIR / f"_v4_cache_{tag}.md"
        if cache_path.exists() and cache_path.stat().st_size > 1500:
            text = cache_path.read_text(encoding="utf-8")
            print(f"  [{tag}] 命中缓存 {len(text):,} 字符", file=sys.stderr)
            sections_out.append(text)
            continue

        print(f"  正在生成 [{tag}]…", file=sys.stderr)
        full_prompt = (
            sec_prompt
            + "\n\n【一手取证摘要 — Brave/Tavily/Gemini 原生 API 检索】\n\n"
            + evidence_md
            + "\n\n【V3 RAND 体例报告骨架（仅作背景参照，请用中国智库风格重写）】\n\n"
            + prev_text
        )
        try:
            text = cloubic(full_prompt, max_tokens=max_tok)
        except Exception as e:
            print(f"    主模型失败: {repr(e)[:200]}; 重试 {CLOUBIC_FALLBACK}…", file=sys.stderr)
            try:
                text = cloubic(full_prompt, max_tokens=max_tok - 4000, model=CLOUBIC_FALLBACK)
            except Exception as e2:
                print(f"    备用也失败: {repr(e2)[:200]}", file=sys.stderr)
                text = f"[GENERATION FAILED for {tag}]\n\n错误：{repr(e2)}"
        cache_path.write_text(text, encoding="utf-8")
        sections_out.append(text)
        print(f"    [{tag}] 完成 {len(text):,} 字符", file=sys.stderr)
        time.sleep(2)

    # 拼装总报告
    print("[3/3] 拼装报告…", file=sys.stderr)
    header = f"""# 米切尔航空航天研究所深度研判：组织生态、涉台动向与对华开源情报作业

**报告类型**：战略研判 · 政策研究
**编号**：MISJ-2026-04
**完成时间**：{NOW}
**研究方法**：多源开源情报（OSINT）三角验证 + 政策研判

---

"""
    parts = [header]
    for text in sections_out:
        cleaned = text.strip()
        for prefix in ["好的，", "好的。", "以下是", "以下为", "Sure,", "Sure."]:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):].lstrip()
        parts.append(cleaned)
        parts.append("\n")

    OUT_MD.write_text("\n".join(parts), encoding="utf-8")
    sz = OUT_MD.stat().st_size
    print(f"[OK] 写入 {OUT_MD} ({sz:,} bytes)", file=sys.stderr)


if __name__ == "__main__":
    main()
