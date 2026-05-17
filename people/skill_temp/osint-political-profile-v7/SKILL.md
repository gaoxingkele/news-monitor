---
name: osint-political-profile
description: >
  Taiwan political figure OSINT panoramic profiling. V7 Framework:
  16-module fact collection with automated pipeline, five behavioral modeling frameworks
  (Hermann LTA, George OpCode, Winter Motive, Barber, MBTI), networkx social network analysis,
  multi-LLM cross-validation peer review, iterative deepening protocol.
  Outputs Chinese academic prose reports (大陆战略智库语体).
  MANDATORY TRIGGERS: analyzing/profiling political figures in cross-strait context;
  mentions of OSINT, 开源情报, 政治人物分析, 全景分析; assessing behavioral patterns or
  alliance networks of politicians; cross-strait positioning or triangular dynamics;
  applying Hermann/George/Winter/Barber/MBTI to political figures; any of the 16 modules.
---

# OSINT 台湾政治人物全景分析框架 V7.0

> 基于蒋万安 v1.0→v1.6 六轮迭代实战经验，从 V6 升级而来。
> V7 = V6全景覆盖 + 自动化采集流水线 + 多LLM交叉校验 + 迭代深化协议 + 台湾一手数据源标准化

## V6→V7 核心升级

| 升级项 | V6 状态 | V7 改进 |
|--------|---------|---------|
| 数据采集 | 手动搜索+人工整理 | 自动化流水线：5引擎并发搜索→LLM结构化提取→JSON持久化 |
| 台湾一手数据 | 未标准化 | 6类必采数据源（中选会/公督盟/监察院/立法院/自由时报开票/户政系统） |
| 质量控制 | 单人审阅 | 4路多LLM专家评审（Perplexity+Claude+Gemini+Grok，角色分离） |
| 版本迭代 | 无协议 | 标准化三阶段迭代协议（v1.0基线→v1.x补数据→v1.x+评审修正） |
| 网络分析 | 定性描述 | networkx量化指标（度/中介/接近中心性、k-core、结构洞、桥接节点） |
| 25项内政政策 | 易遗漏 | 显性检查清单，缺失项必须标注【信息缺口】 |
| 模块编号 | 自检表与正文不一致 | 统一编号体系，正文标题严格对齐16模块 |
| 证据溯源 | URL仅列首页 | 每条事实绑定具体URL+段落引用 |
| Hermann编码 | 不透明 | 每维度≥3条独立行为证据+编码透明度标注 |

## 框架总体架构

| 层次 | 名称 | 功能 | 参考文件 |
|------|------|------|----------|
| Part A | 方法论基础设施 | 证据分级A-E、时间分期P0-P5、缺口处理 | `references/methodology.md` |
| Part B | 事实采集层（16模块） | 系统性信息采集，全景覆盖 | `references/modules.md` |
| Part C | 行为建模层 | 五框架人格建模+MBTI交叉验证 | `references/modeling.md` |
| Part D | 网络分析+情景推演 | SNA图谱+时间线+多情景矩阵 | `references/network-scenarios.md` |
| Part E | 自动化流水线 | 搜索→提取→评审→报告生成 | `references/pipeline.md` |
| Part F | 报告文档结构 | 八篇标准+写作规范 | 本文件 Phase 5 |
| Part G | 质量控制与交付 | 覆盖率自检+迭代协议+交付物标准 | `references/quality-tools.md` |

**按需加载**：不要一次读取所有参考文件，根据当前分析阶段逐步加载。

## 核心原则

1. **事实先行**：每条信息标注证据等级(A-E)+可追溯来源+获取日期。分析永远不能跑在证据前面。
2. **全模块覆盖**：16个模块必须在最终报告中出现，即使只有缺口标注。静默省略是最大的敌人。
3. **层叠不替换**：V2采集→V3建模→V4 MBTI→V5来源完整性→V6全景交付→V7流水线，每层叠加。
4. **交叉验证优于单框架**：Hermann/George/Winter/Barber/MBTI任何一个框架的结论都不能独立成为最终判断。
5. **大陆学术智库语体**：连贯散文段落（150-300字），每段遵循「事实铺陈→分析推理→战略含义」三层递进，禁止正文使用项目符号列表。
6. **迭代深化**：v1.0→v1.x不是一步到位，而是通过标准化迭代协议逐步补齐。

## 工作流程

### Phase 1: 目标确认与环境准备

当用户指定分析目标时：

1. **确认范围**：目标全名、当前职务、分析聚焦时期、优先模块
2. 读取 `references/methodology.md` 了解证据分级(A-E)和时间分期(P0-P5)
3. 评估可用资源：已有文档、需要网络搜索、现有报告版本
4. 在 `data_collection/tasks/` 下创建该人物的搜索任务定义文件

### Phase 2: 自动化数据采集（Part B + Part E）

读取 `references/pipeline.md` 了解完整流水线。核心步骤：

#### 2.1 多引擎搜索采集

使用 `data_collection/search_dispatcher.py` 并发调用5个搜索引擎：

| 引擎 | 用途 | 环境变量 |
|------|------|----------|
| Brave Search | 网页搜索主力 | `BRAVEAPI` |
| Tavily Search | 网页搜索补充 | `tavilyapi` |
| Grok Web Search | xAI网页搜索 | `GROK_API_KEY` |
| Grok X Search | X/Twitter社交媒体 | `GROK_API_KEY` |
| Gemini Search | Google Gemini搜索 | `GEMINI_API_KEY` |

执行：`python -m people.data_collection.run_collect --person <NAME> --tier 0`

#### 2.2 台湾一手数据源（V7必采）

使用 `data_collection/perplexity_fetcher.py` 通过Perplexity sonar-pro获取台湾政府数据：

| 数据源 | 级别 | 必采内容 |
|--------|------|----------|
| 中央选举委员会(中选会) | A级 | 历次选举各行政区得票数+得票率 |
| 公民监督国会联盟(公督盟) | A级 | 各会期评鉴结果+量化指标(出席率/质询率/提案数) |
| 监察院阳光法案平台 | A级 | 财产申报(不动产/存款/有价证券/汽车) |
| 立法院公报系统 | A级 | 主提案数/共同提案数/质询记录 |
| 政治献金公开查阅平台 | A级 | 总收入/个人捐款/企业捐款/支出 |
| 台湾户政系统/官方简历 | A级 | 出生/学历/职历基本事实 |

#### 2.3 LLM结构化事实提取

使用 `data_collection/extractor.py` 从搜索结果中提取可核验事实：
- 默认用 Grok-fast，备选 Claude/Gemini/Qwen
- 每条事实标注：content + evidence_grade(A/B/C/D) + source_url + source_name + date_of_event + raw_quote
- 输出到 `data_collection/extracted/` 目录

#### 2.4 网络图谱构建

使用 `data_collection/network_analysis.py`：
- 从提取事实中构建有向图（networkx DiGraph）
- 计算量化指标：度中心性、中介中心性、接近中心性、k-core、结构洞约束系数、桥接边
- 输出JSON到 `extracted/network_analysis.json`

### Phase 3: 行为建模（Part C）

读取 `references/modeling.md`。按以下顺序应用五大框架：

1. **Hermann LTA** — 七维度(BACE/CC/NP/DIS/IGB/SC/TASK)，1-7分制，每维度≥3条独立行为证据，编码透明度标注
2. **George操作码** — 哲学信念(P-1~P-5)+工具信念(I-1~I-5)
3. **Winter动机编码** — 权力/成就/亲和三维度+组合预测
4. **Barber类型学** — Active/Passive × Positive/Negative
5. **MBTI认知功能** — 四字母初判→八功能栈→与其他四框架交叉验证矩阵

**关键规则**：
- 每个MBTI结论标注[E-MBTI]并至少与一个其他框架交叉验证
- Hermann编码必须标注透明度（行为案例数量+来源等级+编码者一致性）
- 最终综合画像标注[E-Composite]

### Phase 4: 多LLM专家评审（V7核心升级）

使用 `peer_review/run_review.py`。4路专家通道并行评审：

| 专家 | 角色 | LLM | 评审重点 |
|------|------|-----|----------|
| A | 国际关系专家 | Perplexity sonar-pro | 三角联动、IR学术框架、国际定位 |
| B | 台湾历史学家 | Claude Sonnet | 历史叙事准确性、家族背景、转型正义 |
| C | 台湾问题研究专家 | Gemini Pro | 选举数据、立法绩效、内政政策 |
| D | 情报收集专家 | Grok Fast | 网络图谱、利益冲突、信息缺口 |

每位专家产出结构化评审报告，包含：错误指出+缺口识别+补充建议+事实校正。

**设计原理**：使用不同厂商的模型，利用模型间的认知差异实现交叉校验，避免单一模型幻觉传播。

### Phase 5: 报告生成

使用 `data_collection/gen_v13.py`（或后续版本）按八篇结构分段调用LLM生成。

**八篇标准结构**：

```
封面（标题、版本、框架声明、数据采集声明、事实基础）

第一篇　基本情况与政治履历
  §1.1 基本信息表                    ← 模块一
  §1.2 家庭背景与政治启蒙            ← 模块二(部分)
  §1.3 从政前经历与政治网络早期建立
  §1.4 政治履历阶段分析(P0-P5)      ← 模块二(部分)
  §1.5 关键转折点
  §1.6 海外经历深度追踪              ← 模块十
  §1.7 立法与治理绩效评估            ← 模块六
  §1.8 选举与竞选分析                ← 模块七

第二篇　派系属性与权力网络           ← 模块八
  §2.1 党内派系定位
  §2.2 核心幕僚与决策圈
  §2.3 地方派系与红黑背景
  §2.4 家族婚姻网络
  §2.5 国际与跨境网络
  §2.6 权力资源图谱（逐组展开关键关系）
  §2.7 权力网络深度图谱
  §2.8 网络结构化分析（networkx量化指标表格）

第三篇　政治立场与意识形态特征
  §3.1 核心价值与宪政立场            ← 模块三
  §3.2 国家认同与历史观
  §3.3 两岸定位与政策立场            ← 模块九（≥3案例前后对照）
  §3.4 内政政策立场图谱              ← 模块四（25子领域检查清单）
  §3.5 国防外交与国际定位            ← 模块五
  §3.6 三角联动动态分析              ← 模块十四（≥3组完整三角链）

第四篇　行为模式与决策风格深层分析
  §4.1 Hermann LTA（七维度，每维度≥3案例+编码透明度）
  §4.2 George操作码
  §4.3 Winter动机编码（含横向基线对比）
  §4.4 Barber类型学

第五篇　人格特征与认知模式研判
  §5.1 MBTI四维度判定（独立行为证据，禁止循环论证）
  §5.2 认知功能栈分析（Te/Ni等具体行为场景）
  §5.3 压力反应预测（Grip Theory）
  §5.4 五框架交叉验证综合画像

第六篇　综合研判与前瞻推演
  §6.1 政治人物类型判断              ← 模块十五(部分)
  §6.2 风险等级判断
  §6.3 对区域关系的影响
  §6.4 多情景前瞻推演                ← 模块十五（≥5情景含概率+方法论）
  §6.5 个人发展前景
  §6.6 重点跟踪建议
  §6.7 家族财务与利益冲突评估        ← 模块十一
  §6.8 争议与法律风险评估            ← 模块十二
  §6.9 媒体叙事与公众认知分析        ← 模块十三

第七篇　分析局限性与方法论声明
  §7.1-7.5 各类局限性说明
  §7.6 V7覆盖率自检表（16模块×4列：覆盖状态/完整度%/主要缺口/下一步）

第八篇　综合交付物                   ← 模块十六
  §8.1 核心事实摘要（20-50条，每条含证据等级+具体来源URL）
  §8.2 政策立场矩阵（政策域/立场/原话/证据/时期/一致性）
  §8.3 盟友对手关键组织网络清单
  §8.4 数据源索引（绑定到具体事实编号）
  §8.5 信息需求清单
  §8.6 整合时间轴
  §8.7 争议事实核查矩阵（指控|证据|反证|结论，≥5事件）

学术参考文献
```

### Phase 6: 迭代深化协议（V7新增）

标准化三阶段迭代，每阶段有明确的准入/准出条件：

#### 阶段一：v1.0 基线报告
- **输入**：Tier-0搜索结果 + 基础事实提取
- **产出**：八篇框架完整但内容可能单薄的基线报告
- **准出**：16模块均有章节位置，覆盖率≥40%

#### 阶段二：v1.x 数据补齐（可能多轮）
- **输入**：v1.0 + Tier-1搜索 + 台湾一手数据 + networkx分析
- **每轮操作**：
  - 对照覆盖率自检表，识别最大缺口
  - 针对性执行搜索任务补数据
  - Perplexity获取台湾政府数据
  - 更新报告，版本号+0.1
- **准出**：覆盖率≥70%，台湾一手数据6类≥4类完成

#### 阶段三：v1.x 评审修正
- **输入**：数据补齐后的报告
- **操作**：4路专家并行评审→汇总修正→最终版
- **准出**：
  - 所有A/B级事实错误已修正
  - Hermann编码透明度标注完成
  - 三角联动≥3组完整案例
  - 两岸专项≥3组前后对照
  - 争议矩阵≥5事件
  - 版本号升至v1.x final

### Phase 7: 导出

使用 `export_report.py` 从最终MD导出：
```
python people/export_report.py --input people/output/<人物>/最终版.md
```
产出 DOCX + PDF。

## 写作规范

### 正文语体

- 连贯学术散文段落，每段150-300字，禁止项目符号列表
- 每段遵循「事实铺陈→分析推理→战略含义」三层递进
- 大陆学术智库战略评估语体
- 证据标注融入行文：[A/B/C级, 来源名, 获取日期]
- E级推断标注学术框架：[E-Hermann] [E-George] [E-MBTI] [E-Composite]
- 立场演变标注时期代号(P0-P5)
- 跨篇引用：参见第X篇§X.X

### 表格使用

仅在以下场景使用表格：
- 基本信息(§1.1)
- 选举数据(§1.8)
- networkx量化指标(§2.8)
- 政策立场矩阵(§8.2)
- 网络清单(§8.3)
- 覆盖率自检(§7.6)
- 争议矩阵(§8.7)
- 行为框架评分汇总

### 反幻觉规则

1. 所有具体数字必须来自采集事实或台湾一手数据源
2. 无法溯源的数据标注【待核实】
3. 宁可留信息缺口不可编造
4. B级来源（维基百科/权威媒体）可直接使用，标注来源名
5. 不同LLM产出的同一事实需交叉验证，冲突时以A/B级来源为准

## 16模块→报告章节映射速查

| 模块 | 名称 | 报告位置 |
|------|------|----------|
| 1 | 身份与履历基础 | 第一篇 §1.1-1.5 |
| 2 | 政治生涯与党派动态 | 第一篇 §1.4-1.5 + 第二篇 §2.1 |
| 3 | 核心价值与宪政立场 | 第三篇 §3.1-3.2 |
| 4 | 内政政策立场图谱(25子领域) | 第三篇 §3.4 |
| 5 | 国防外交与国际定位 | 第三篇 §3.5 |
| 6 | 立法与治理绩效 | 第一篇 §1.7 |
| 7 | 选举与竞选分析 | 第一篇 §1.8 |
| 8 | 权力网络与资源图谱 | 第二篇 §2.1-2.8 |
| 9 | 两岸定位专项 | 第三篇 §3.3 |
| 10 | 海外经历深度追踪 | 第一篇 §1.6 |
| 11 | 家族财务与利益冲突 | 第六篇 §6.7 |
| 12 | 争议法律与风险评估 | 第六篇 §6.8 |
| 13 | 媒体叙事与公众认知 | 第六篇 §6.9 |
| 14 | 三角联动动态分析 | 第三篇 §3.6 |
| 15 | 前瞻分析与情景推演 | 第六篇 §6.1-6.6 |
| 16 | 综合交付物(7项) | 第八篇 §8.1-8.7 |

## 文件路径约定

```
people/
├── data_collection/
│   ├── tasks/<person_slug>.py      # 搜索任务定义
│   ├── raw/<task_id>.json          # 原始搜索结果
│   ├── extracted/<task_id>.json    # 提取的结构化事实
│   └── reports/                    # 采集汇总
├── peer_review/
│   ├── raw_responses/              # 专家原始评审
│   └── reports/                    # 评审汇总
├── output/<人物名>/
│   ├── v1.0.docx                   # 基线报告
│   ├── v1.x.md                     # 迭代版本
│   └── v1.x_final.{md,docx,pdf}   # 最终版
└── export_report.py                # 导出工具
```
