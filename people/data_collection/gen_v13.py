"""v1.3 报告生成器 —— 8篇独立生成 + 干净拼装，一次到位。"""
import httpx, json, os, sys, time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from people.data_collection.config import bootstrap, get_env, EXTRACTED_DIR

bootstrap()

GROK_KEY = get_env('GROK_API_KEY')
PROXY = get_env('LLM_PROXY')
_MODULE_DIR = Path(__file__).resolve().parent
OUT_DIR = _MODULE_DIR.parent / '_v13_parts'
OUT_DIR.mkdir(exist_ok=True)

# ── 加载全部素材 ──
ext_dir = EXTRACTED_DIR
all_facts = []
_skip = {'perplexity_fixes.json', 'perplexity_taiwan_gov.json', 'network_analysis.json', 'T0_taiwan_gov_raw.json'}
for f in sorted(ext_dir.glob('*.json')):
    if f.name in _skip:
        continue
    data = json.loads(f.read_text(encoding='utf-8'))
    if isinstance(data, list):
        all_facts.extend(d for d in data if isinstance(d, dict))

pfix = json.loads((ext_dir / 'perplexity_fixes.json').read_text(encoding='utf-8'))
ptw = json.loads((ext_dir / 'perplexity_taiwan_gov.json').read_text(encoding='utf-8'))
netw = json.loads((ext_dir / 'network_analysis.json').read_text(encoding='utf-8'))

# v1.0 原文
from docx import Document
doc = Document('people/蒋万安_政治人物分析报告_v1.0.docx')
v10 = '\n'.join(p.text.strip() for p in doc.paragraphs if p.text.strip())

def filter_facts(modules):
    return [f for f in all_facts if any(m in f.get('v6_module', '') for m in modules)]

def fmt_facts(facts, limit=50):
    lines = []
    for i, f in enumerate(facts[:limit], 1):
        lines.append(f"[F{i}] {f.get('content','')}\n  等级:{f.get('grade','C')} 来源:{f.get('source_name','')} URL:{f.get('source_url','')}")
    return '\n'.join(lines) if lines else '（无专项事实）'

def call_grok(system, user, max_tokens=12000):
    resp = httpx.Client(proxy=PROXY, timeout=httpx.Timeout(600.0), trust_env=False).post(
        'https://api.x.ai/v1/chat/completions',
        headers={'Authorization': f'Bearer {GROK_KEY}', 'Content-Type': 'application/json'},
        json={'model': 'grok-4.20-0309-reasoning',
              'messages': [{'role':'system','content':system},{'role':'user','content':user}],
              'temperature': 0.25, 'max_tokens': max_tokens})
    data = resp.json()
    return data['choices'][0]['message']['content'].strip()

# ── 共用 system prompt ──
SYSTEM = """你是厦门大学台湾研究院资深研究员，撰写 OSINT V6.0 蒋万安全景分析报告 v1.3。

写作规范：
- 连贯学术散文段落，每段150-300字，禁止项目符号列表
- 每段「事实铺陈→分析推理→战略含义」三层递进
- 大陆学术智库战略评估语体
- 证据标注融入行文：[A/B/C级, 来源名, 获取日期]
- E级推断标注学术框架：[E-Hermann] [E-George] [E-MBTI]等
- 立场演变标注P0-P5时期代号
- 跨篇引用：参见第X篇§X.X
- 仅结构化数据对比用表格

反幻觉规则：
- 所有具体数字必须来自下方【事实块】或【Perplexity来源】
- 无法溯源的数据标注【待核实】
- 宁可留信息缺口不可编造
- B级来源（维基百科/权威媒体）可直接使用，标注来源名即可

V6 16模块显性化规则（v1.4核心升级）：
- 每篇内必须为对应的V6模块设置显性子标题，格式：#### 【模块N：模块名称】
- 即使某模块信息不足，也必须保留标题并标注【信息缺口：XXX】
- 第一篇含模块一/二/六/七/十，第二篇含模块八，第三篇含模块三/四/五/九/十四
- 第六篇含模块十一/十二/十三/十五，第八篇含模块十六
"""

# ── 逐篇生成 ──
sections_config = [
    {
        'num': 1,
        'title': '第一篇　基本情况与政治履历',
        'modules': ['B模块一', 'B模块二', 'B模块十', 'B模块六', 'B模块七'],
        'subsections': """### §1.1 基本信息表
### §1.2 家庭背景与政治启蒙（必须完整展开章孝严非婚生认祖全过程：章亚若1942年桂林死亡争议→双胞胎出生→2002年寻亲→2005年改姓蒋。引用Perplexity历史来源的具体细节。P0分为P0-a蒋经国在世1978-1988.1.13与P0-b后蒋经国时代1988.1.14-2004）
### §1.3 从政前经历与政治网络早期建立
### §1.4 政治履历阶段分析（P0-a/P0-b/P3/P4/P5各阶段关键事件）
### §1.5 关键转折点（含228参与记录≥3个具体年份+发言内容）
### §1.6 海外经历深度追踪
### §1.7 立法与治理绩效评估（含公督盟评鉴数据）
### §1.8 选举与竞选分析（含2022年12行政区得票数据）""",
        'extra': f"\nPerplexity历史来源：\n{pfix['B1_228_white_terror']['content']}\n{pfix['B3_chiang_ching_kuo_death']['content']}\n\nPerplexity中选会12区得票数据（必须融入§1.8）：\n{ptw.get('cec_12district',{}).get('content','')}\n\nPerplexity立法院数据（融入§1.7）：\n{ptw.get('ly_performance',{}).get('content','')}\n\nPerplexity公督盟评鉴（融入§1.7）：\n{ptw.get('ccw_rating',{}).get('content','')}\n",
    },
    {
        'num': 2,
        'title': '第二篇　派系属性与权力网络',
        'modules': ['B模块八'],
        'subsections': """### §2.1 党内派系定位
### §2.2 核心幕僚与决策圈
### §2.3 地方派系与红黑背景（含台北市议会国民党团次级团体）
### §2.4 家族婚姻网络
### §2.5 国际与跨境网络
### §2.6 权力资源图谱（含与朱立伦/侯友宜/卢秀燕/韩国瑜/郑丽文/马英九/连战/洪秀柱/张亚中关系）
### §2.7 权力网络深度图谱（含与民进党关系/其他党派/宗教团体/军界影响度）
### §2.8 网络结构化分析（必须输出networkx量化指标表格：度中心性/中介中心性/接近中心性具体数值，识别结构洞与桥接节点）""",
        'extra': f"\nnetworkx量化分析结果（必须以表格形式融入§2.8）：\n节点数:{netw['summary']['nodes']} 边数:{netw['summary']['edges']} 密度:{netw['summary']['density']}\n度中心性:{json.dumps(netw['degree_centrality'], ensure_ascii=False)}\n中介中心性:{json.dumps(netw['betweenness_centrality'], ensure_ascii=False)}\n接近中心性:{json.dumps(netw['closeness_centrality'], ensure_ascii=False)}\nK-core:{json.dumps(netw['k_core'], ensure_ascii=False)}\n桥接边:{netw['bridges']}\n",
    },
    {
        'num': 3,
        'title': '第三篇　政治立场与意识形态特征',
        'modules': ['B模块三', 'B模块四', 'B模块五', 'B模块九', 'B模块十四', 'IR学术'],
        'subsections': """### §3.1 核心价值与宪政立场
### §3.2 国家认同与历史观（含戒严时期蒋经国角色、白色恐怖促转会《任务推动及调查结果报告书》2021年数据：受裁判人29407人死刑13.12%、228与白色恐怖在转型正义法律处理上的区别）
### §3.3 两岸定位与政策立场（必须注释九二共识历史争议：苏起2000年创词；必须纳入2019年1月3日蒋万安在《年代向钱看》四度表态支持蔡英文四个必须、反对一国两制原话；双城论坛前后立场对照≥3案例）
### §3.4 内政政策立场图谱（核心议题）
### §3.5 国防外交与国际定位（必须用Glaser战略模糊/清晰理论框架，将「亲美和中固台」拆解为政策工具矩阵：TRA条款/军售F-16V+AGM-84H/NDAA 2026台湾安全合作倡议10亿美元/汉光演习/CPTPP/IPEF/台美21世纪贸易倡议/AIT机制。引用Kastner制度化信号、Bush综合威慑概念）
### §3.6 三角联动动态分析（≥3组完整三角链：美方行动→蒋万安表态→北京反应。引用Glaser/Kastner/Bush学术文献。蒋万安在国民党两岸光谱中处于中间偏温和位置，不是深蓝统派——2019反一国两制为关键证据）""",
        'extra': f"\nPerplexity IR学术来源：\n{pfix['A1_triangle_policy_tools']['content']}\n\nPerplexity历史来源：\n{pfix['B1_228_white_terror']['content']}\n{pfix['B2_92consensus']['content']}\n",
    },
    {
        'num': 4,
        'title': '第四篇　行为模式与决策风格深层分析',
        'modules': [],
        'subsections': """### §4.1 Hermann领导特质分析（七维度每个须≥3条独立行为案例：具体时间+场合+行为描述）
### §4.2 George操作码
### §4.3 Winter动机编码（须与同期竞争对手做横向基线对比）
### §4.4 Barber类型学""",
        'extra': '',
    },
    {
        'num': 5,
        'title': '第五篇　人格特征与认知模式研判',
        'modules': [],
        'subsections': """### §5.1 MBTI四维度判定（须用独立行为证据，不可循环论证）
### §5.2 认知功能栈分析（须提供Te/Ni具体行为场景）
### §5.3 压力反应预测（Grip Theory）
### §5.4 五框架交叉验证综合画像（须消除循环论证：MBTI判定须基于认知功能观察而非直接从权力谋划推导）""",
        'extra': '',
    },
    {
        'num': 6,
        'title': '第六篇　综合研判与前瞻推演',
        'modules': ['B模块十一', 'B模块十二', 'B模块十三', 'B模块十五'],
        'subsections': """### §6.1 政治人物类型判断
### §6.2 风险等级判断
### §6.3 对区域关系的影响
### §6.4 多情景前瞻推演（必须包含：情景A台北施政优异2028参选；情景B两岸紧张蒋家符号被攻击；情景C市政危机；情景D 2026九合一选举（前置条件）；情景E台海高强度军事冲突RAND/CSIS级。概率评估须说明方法论依据，不可拍脑袋）
### §6.5 个人发展前景
### §6.6 重点跟踪建议
### §6.7 家族财务与利益冲突评估（含监察院财产申报数据）
### §6.9 媒体叙事与公众认知分析""",
        'extra': f"\nPerplexity财产申报数据（融入§6.7）：\n{ptw.get('asset_declaration',{}).get('content','')}\n\nPerplexity政治献金数据（融入§6.7）：\n{ptw.get('political_donation',{}).get('content','')}\n",
    },
    {
        'num': 7,
        'title': '第七篇　分析局限性与方法论声明',
        'modules': [],
        'subsections': """### §7.1 信息来源的局限性
### §7.2 行为建模不确定性
### §7.3 立场演变监测局限
### §7.4 两岸关系分析局限
### §7.5 财务与利益冲突信息局限
### §7.6 V6覆盖率自检表（必须量化16模块覆盖率：模块名/覆盖状态完成或部分或缺失/信息完整度百分比/主要缺口，用表格）""",
        'extra': '',
    },
    {
        'num': 8,
        'title': '第八篇　综合交付物',
        'modules': ['B模块十六'],
        'subsections': """### §8.1 核心事实摘要（20-50条，每条含证据等级+来源）
### §8.2 政策立场矩阵（政策域/立场/原话/证据/时期/一致性，用表格）
### §8.3 盟友对手关键组织网络清单（用表格）
### §8.4 数据源索引（列出所有引用来源的完整URL）
### §8.5 信息需求清单（列出仍待采集的缺口项）
### §8.6 整合时间轴（按年份列出关键事件）
### §8.7 争议事实核查矩阵（必须用四栏表格：指控|证据|反证|结论，≥5事件，含虐童案/台智光案/大巨蛋等近期市政争议）""",
        'extra': '',
    },
]

print(f"Total facts: {len(all_facts)}")
now = datetime.now().strftime("%Y-%m-%d")

for sec in sections_config:
    facts = filter_facts(sec['modules'])
    facts_block = fmt_facts(facts)

    user = f"""撰写 **{sec['title']}**

章节结构：
{sec['subsections']}

v1.0原文（作为基础扩写）：
{v10}

新增采集事实（{len(facts)}条，可直接使用）：
{facts_block}
{sec['extra']}
输出要求：3000-6000字，以 **{sec['title']}** 开头，直接输出正文。"""

    print(f"\n[Part {sec['num']}] Generating ({len(facts)} facts)...", flush=True)
    t0 = time.time()
    text = call_grok(SYSTEM, user)
    elapsed = time.time() - t0
    print(f"  -> {len(text)} chars, {elapsed:.0f}s")

    out_file = OUT_DIR / f"part{sec['num']}.md"
    out_file.write_text(text, encoding='utf-8')

# ── 拼装 ──
header = f"""# 厦门大学台湾研究院
# 开源情报全景分析报告

**分析对象**：蒋万安
**报告版本**：V1.4 | **分析框架**：OSINT V6.0 全景分析体系
**编制日期**：{now} | **保密级别**：内部研究参考
**行为框架**：Hermann LTA · George操作码 · Winter动机编码 · Barber类型学 · MBTI认知功能
**数据采集**：Brave · Tavily · Grok Web/X · Gemini · Perplexity（IR学术+历史校正）
**事实基础**：{len(all_facts)} 条结构化事实 + Perplexity 权威来源交叉校验
**版本说明**：v1.4 = 153条结构化事实 + Perplexity台湾一手数据（中选会/监察院/公督盟/立法院）+ networkx网络量化 + IR学术框架 + 16模块V6显性化 + 四专家四轮评审修正

---

"""

parts = [header]
for i in range(1, 9):
    pf = OUT_DIR / f"part{i}.md"
    if pf.exists():
        parts.append(pf.read_text(encoding='utf-8'))
        parts.append('\n\n')

# 学术参考文献
parts.append("""
## 学术参考文献

Hermann, M.G. (1980). Explaining Foreign Policy Behavior Using the Personal Characteristics of Political Leaders. *International Studies Quarterly*, 24(1), 7-46.
George, A.L. (1969). The Operational Code: A Neglected Approach to the Study of Political Leaders and Decision-Making. *International Studies Quarterly*, 13(2), 190-222.
Winter, D.G. (1992). Personality and Foreign Policy: Historical Overview of Research. In E. Singer & V. Hudson (Eds.), *Political Psychology and Foreign Policy*. Westview Press.
Barber, J.D. (1972). *The Presidential Character: Predicting Performance in the White House*. Prentice-Hall.
Glaser, C.L. (2023). Washington's Dangerous New Consensus on China. *Foreign Affairs*.
Kastner, S.L. (2009). *Political Conflict and Economic Interdependence Across the Taiwan Strait and Beyond*. Stanford University Press.
Bush, R.C. (2005). *Untying the Knot: Making Peace in the Taiwan Strait*. Brookings Institution Press.
Christensen, T.J. (2015). *The China Challenge: Shaping the Choices of a Rising Power*. W.W. Norton.
促进转型正义委员会 (2021).《任务推动及调查结果报告书》.
""")

final = '\n'.join(parts)
Path('people/蒋万安_政治人物分析报告_v1.4.md').write_text(final, encoding='utf-8')
print(f"\n=== v1.3 DONE: {len(final)} chars ===")
