"""v1.1 报告生成器 —— 按 V6 Part F 八篇结构分段调用 LLM 重写。

流程：
1. 加载 v1.0 原文 + 全部提取事实
2. 按篇分组事实
3. 逐篇调用 LLM（Grok reasoning）重写
4. 拼装输出完整 v1.1 markdown
"""
from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from datetime import datetime

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from people.data_collection.config import bootstrap, get_env, EXTRACTED_DIR

logger = logging.getLogger("report_writer")

# ── 八篇结构定义 ──
SECTIONS = [
    {
        "id": "part1",
        "title": "第一篇　基本情况与政治履历",
        "v6_modules": ["B模块一", "B模块二", "B模块十", "B模块六", "B模块七"],
        "subsections": "§1.1基本信息 §1.2家庭背景与政治启蒙 §1.3从政前经历 §1.4政治履历阶段分析(P0-P5) §1.5关键转折点 §1.6海外经历 §1.7立法与治理绩效 §1.8选举与竞选分析",
        "expert_fixes": [
            "B专家：章孝严非婚生认祖全过程（章亚若→DNA→改姓）必须完整展开",
            "B专家：P0时期必须细分为P0-a(1978-1988蒋经国在世)与P0-b(1988-2004后蒋经国时代)",
            "B专家：228参与记录必须提供≥3个具体年份的活动+发言内容",
            "C专家：立法绩效必须有公督盟评鉴具体数据、提案数、出席率",
            "C专家：2022选举票源必须有12行政区得票率拆解",
        ],
    },
    {
        "id": "part2",
        "title": "第二篇　派系属性与权力网络",
        "v6_modules": ["B模块八"],
        "subsections": "§2.1党内派系定位 §2.2核心幕僚与决策圈 §2.3地方派系 §2.4家族婚姻网络 §2.5国际与跨境网络 §2.6权力资源图谱 §2.7权力网络深度图谱",
        "expert_fixes": [
            "A/B/C专家共同指出：必须输出网络结构化数据（节点-边/结构洞/中心性）",
            "C专家：台北市议会国民党团次级团体必须分析",
            "D凡博士：与朱立伦/侯友宜/卢秀燕/韩国瑜关系必须逐组展开",
            "D凡博士：与郑丽文/张亚中/马英九/连战/洪秀柱关系",
            "D凡博士：与民进党/其他党派/宗教团体关系",
            "D凡博士：军界影响度（黄复兴/退辅会/眷村）",
        ],
    },
    {
        "id": "part3",
        "title": "第三篇　政治立场与意识形态特征",
        "v6_modules": ["B模块三", "B模块四", "B模块五", "B模块九", "B模块十四", "IR学术"],
        "subsections": "§3.1核心价值与宪政立场 §3.2国家认同与历史观 §3.3两岸定位(九二共识/一国两制) §3.4内政政策立场图谱 §3.5国防外交与国际定位 §3.6两岸定位专项分析(访中前后对照≥3案例) §3.7三角联动动态分析(美中台≥3组对照)",
        "expert_fixes": [
            "A专家(v1.2核心升级)：'亲美和中固台'必须拆解到具体政策工具，使用IR学术框架：(1)Glaser的战略模糊/清晰辩论框架定位蒋万安立场；(2)将'亲美'拆解为TRA条款支持度/军售态度/NDAA涉台条款回应/AIT互动/CPTPP-IPEF立场；(3)将'和中'拆解为九二共识诠释弹性/双城论坛层级/访中频率/一国两制回应；(4)将'固台'拆解为汉光演习态度/后备动员/国防预算立场",
            "A专家(v1.2核心升级)：三角联动必须引用IR学术文献(Kastner/Christensen/Bush/Glaser等)构建分析框架，不是泛泛描述而是用学术概念工具",
            "A专家(v1.2核心升级)：增加RAND/CSIS级台海冲突情景推演变量（封锁/灰色地带/全面冲突三级），分析蒋万安在各级别下的预期行为",
            "A/B/C：三角联动必须≥3组案例（佩洛西/军售/AUKUS），每组给出美方行动→蒋万安表态→北京反应完整三角链",
            "A/B/C：两岸专项必须≥3案例前后对照（含双城论坛）",
            "C专家：2019-01-03'四个必须'反对一国两制原话必须纳入",
            "B专家：'九二共识'概念历史争议性必须注释（苏起2000年创词、1992年原始档案无共识记录）",
            "B专家：戒严时期蒋经国角色与白色恐怖数据必须纳入",
        ],
    },
    {
        "id": "part4",
        "title": "第四篇　行为模式与决策风格深层分析",
        "v6_modules": [],
        "subsections": "§4.1 Hermann LTA(七维度+≥3条独立行为证据) §4.2 George操作码 §4.3 Winter动机编码 §4.4 Barber类型学",
        "expert_fixes": [
            "B专家：Hermann每个维度必须提供≥3个具体行为案例（时间、场合、行为）",
            "C专家：Winter动机必须与同期竞争对手做横向基线对比",
        ],
    },
    {
        "id": "part5",
        "title": "第五篇　人格特征与认知模式研判",
        "v6_modules": [],
        "subsections": "§5.1 MBTI四维度判定 §5.2认知功能栈分析 §5.3压力反应预测(Grip Theory) §5.4五框架交叉验证综合画像",
        "expert_fixes": [
            "A/B/C共同指出：MBTI结论存在循环论证，必须用独立行为证据而非同源推断",
            "B专家：必须提供Te/Ni具体行为场景，消除循环论证",
        ],
    },
    {
        "id": "part6",
        "title": "第六篇　综合研判与前瞻推演",
        "v6_modules": ["B模块十一", "B模块十二", "B模块十三", "B模块十五"],
        "subsections": "§6.1政治类型判断 §6.2风险等级 §6.3区域影响 §6.4多情景推演(含2026九合一+台海冲突高强度情景) §6.5个人发展 §6.6跟踪建议 §6.7家族财务利益冲突 §6.9媒体叙事(注意：争议矩阵已移至第八篇§8.7)",
        "expert_fixes": [
            "A/C：情景概率必须有方法论依据，不能拍脑袋55%/30%/15%",
            "A专家：必须增加台海冲突高强度情景推演",
            "C专家：必须增加2026九合一选举为2028前置条件",
            "C专家：争议矩阵必须含虐童案/台智光案等近期市政争议",
            "C专家：财产申报必须有监察院具体数据",
        ],
    },
    {
        "id": "part7",
        "title": "第七篇　分析局限性与方法论声明",
        "v6_modules": [],
        "subsections": "§7.1信息来源局限 §7.2行为建模不确定性 §7.3立场演变监测局限 §7.4两岸关系分析局限 §7.5财务信息局限 §7.6 V6覆盖率自检表(B.0 16模块覆盖率量化)",
        "expert_fixes": [
            "A/B/C：必须量化16模块覆盖率（完成/部分/缺失 + 百分比）",
        ],
    },
    {
        "id": "part8",
        "title": "第八篇　综合交付物",
        "v6_modules": ["B模块十六"],
        "subsections": "§8.1核心事实摘要(20-50条) §8.2政策立场矩阵 §8.3盟友对手网络清单 §8.4数据源索引 §8.5信息需求清单 §8.6整合时间轴 §8.7争议事实核查矩阵(必须用四栏表格：指控|证据|反证|结论，≥5事件，含虐童案/台智光案)",
        "expert_fixes": [
            "A/B/C：交付物必须作为独立篇章完整出现",
            "B专家：必须增加整合时间轴§8.6",
        ],
    },
]


def _load_all_facts() -> list[dict]:
    """加载全部提取的结构化事实。"""
    facts = []
    for f in sorted(EXTRACTED_DIR.glob("*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        for item in data:
            item["_source_file"] = f.name
        facts.extend(data)
    return facts


def _load_v10_text(docx_path: Path) -> str:
    from docx import Document
    doc = Document(str(docx_path))
    parts = []
    for p in doc.paragraphs:
        if p.text and p.text.strip():
            parts.append(p.text.strip())
    return "\n".join(parts)


def _filter_facts(facts: list[dict], v6_modules: list[str]) -> list[dict]:
    """按 V6 模块前缀过滤事实。"""
    if not v6_modules:
        return []
    matched = []
    for f in facts:
        vm = f.get("v6_module", "")
        for prefix in v6_modules:
            if prefix in vm:
                matched.append(f)
                break
    return matched


def _format_facts_block(facts: list[dict]) -> str:
    """将事实列表格式化为 LLM 可读的文本块。"""
    if not facts:
        return "（无新增事实数据）"
    lines = []
    for i, f in enumerate(facts, 1):
        lines.append(
            f"[F{i}] {f.get('content', '')}\n"
            f"    证据等级: {f.get('grade', 'C')} | 来源: {f.get('source_name', '')} | "
            f"URL: {f.get('source_url', '')} | 事件日期: {f.get('date_of_event', '')}\n"
            f"    原文引用: {f.get('raw_quote', '')[:200]}"
        )
    return "\n".join(lines)


SYSTEM_PROMPT = """\
你是厦门大学台湾研究院的资深研究员，正在依据 OSINT V6.0 全景分析框架撰写政治人物分析报告 v1.2 版本。

# 写作规范（厦大战略评估体）
1. 全文以连贯的学术散文段落呈现，每段 150-300 字以上，禁止使用项目符号列表
2. 每段遵循"事实铺陈→分析推理→战略含义"三层递进
3. 采用大陆学术智库的战略评估语体
4. 证据等级标注融入行文（如"根据A级来源……"），不打断阅读节奏
5. 立场演变须标注 P0-P5 时期代号
6. 跨篇引用使用"参见第X篇§X.X"格式
7. 仅在结构化数据对比时使用表格（如选票数据、政策矩阵），正文分析不使用表格

# 反幻觉规则（v1.2 核心升级）
- **严禁编造任何具体数字**（百分比、票数、金额、人数、日期）
- 所有具体数据必须直接来自下方提供的【新增采集事实】块
- 如果某个具体数据点在事实块中找不到，必须标注【待核实：XXX数据未在开源采集中确认】
- 宁可留信息缺口，不可编造数据
- 每条事实标注格式：[证据等级, 来源名, 获取日期]；若无获取日期则标注[证据等级, 来源名]

# V6 结构要求
- 全部 16 模块必须在文档中获得显性章节位置（即使只能标"信息缺口"）
- 第八篇交付物必须包含：核心事实摘要、政策立场矩阵、盟友对手网络清单、争议事实核查矩阵（指控-证据-反证-结论四栏）、数据源索引、信息需求清单、整合时间轴
- 争议矩阵必须用四栏表格格式（指控 | 证据 | 反证 | 结论），不得用纯文本段落
"""


def _call_llm(system: str, user: str, provider: str = "grok") -> str:
    """调用 LLM 生成报告段落。"""
    bootstrap()

    if provider == "grok":
        api_key = get_env("GROK_API_KEY")
        base_url = "https://api.x.ai/v1/chat/completions"
        model = "grok-4.20-0309-reasoning"
        proxy = get_env("LLM_PROXY")
    elif provider == "claude":
        api_key = get_env("CLOUBIC_API_KEY")
        base_url = get_env("CLOUBIC_BASE_URL")
        model = "claude-opus-4-6"
        proxy = ""
    else:
        api_key = get_env("CLOUBIC_API_KEY")
        base_url = get_env("CLOUBIC_BASE_URL")
        model = "gemini-3.1-pro-preview"
        proxy = ""

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.3,
        "max_tokens": 16000,
    }
    kwargs = {"timeout": httpx.Timeout(600.0), "follow_redirects": True, "trust_env": False}
    if proxy:
        kwargs["proxy"] = proxy

    with httpx.Client(**kwargs) as client:
        resp = client.post(base_url, headers=headers, json=payload)

    if resp.status_code != 200:
        logger.error("LLM error: %d %s", resp.status_code, resp.text[:300])
        return f"[生成失败: HTTP {resp.status_code}]"

    data = resp.json()
    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    if isinstance(content, list):
        content = "\n".join(b.get("text", "") for b in content if isinstance(b, dict))
    return content.strip()


def generate_v11(
    v10_docx: Path,
    output_path: Path,
    provider: str = "grok",
) -> None:
    bootstrap()

    v10_text = _load_v10_text(v10_docx)
    all_facts = _load_all_facts()
    logger.info("loaded v1.0 (%d chars) + %d facts", len(v10_text), len(all_facts))

    now = datetime.now().strftime("%Y-%m-%d")

    report_parts: list[str] = []

    # 封面
    report_parts.append(f"""# 厦门大学台湾研究院
# 开源情报全景分析报告

**分析对象**：蒋万安
**报告版本**：V1.2 | **分析框架**：OSINT V6.0 全景分析体系
**编制日期**：{now} | **保密级别**：内部研究参考
**行为框架**：Hermann LTA · George操作码 · Winter动机编码 · Barber类型学 · MBTI认知功能
**数据采集**：Brave Search · Tavily · Grok Web/X Search · Gemini Search · LLM 结构化提取
**v1.0→v1.2 变更**：基于四专家两轮评审，补充 {len(all_facts)} 条结构化事实（含 IR 学术框架），反幻觉机制过滤未溯源数据，修复 V6 合规性缺陷

---
""")

    # 逐篇生成
    for sec in SECTIONS:
        section_facts = _filter_facts(all_facts, sec["v6_modules"])
        # 对无模块映射的篇（Part 4/5/7），也收集通用事实
        facts_block = _format_facts_block(section_facts)

        user_prompt = f"""请撰写报告的 **{sec['title']}**。

## 本篇章节结构
{sec['subsections']}

## 专家评审指出的必修缺陷（v1.1 必须修复）
{"".join(f"- {fix}" + chr(10) for fix in sec['expert_fixes'])}

## v1.0 原文（作为基础，需要扩写和修正）
{v10_text}

## 新增采集事实（必须融入正文，标注具体来源）
{facts_block}

## 输出要求
- 按上述章节结构输出，每个 § 用三级标题 (###)
- 融入新增事实时标注 [A/B/C级，来源名，日期]
- 信息缺口处标注 【信息缺口：XXX】
- 2000-5000 字
- 直接输出正文，不要前言/说明"""

        logger.info("=== Generating %s (%d facts, provider=%s) ===", sec["id"], len(section_facts), provider)
        text = _call_llm(SYSTEM_PROMPT, user_prompt, provider=provider)
        report_parts.append(f"\n{text}\n\n---\n")
        logger.info("  → %d chars", len(text))

    # 拼装输出
    output_path.parent.mkdir(parents=True, exist_ok=True)
    full_report = "\n".join(report_parts)
    output_path.write_text(full_report, encoding="utf-8")
    logger.info("v1.1 report → %s (%d chars)", output_path, len(full_report))


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    ap = argparse.ArgumentParser()
    ap.add_argument("--v10", required=True, help="v1.0 docx 路径")
    ap.add_argument("--output", required=True, help="v1.1 markdown 输出路径")
    ap.add_argument("--provider", default="grok", help="LLM 通道: grok/claude/gemini")
    args = ap.parse_args()

    generate_v11(Path(args.v10).resolve(), Path(args.output).resolve(), provider=args.provider)
