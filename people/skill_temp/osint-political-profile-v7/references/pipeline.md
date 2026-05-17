# Part E：自动化流水线（V7新增）

> 基于蒋万安 v1.0→v1.6 六轮迭代的实战经验，将手动流程标准化为可复用的自动化流水线。

## 架构总览

```
搜索采集 ──→ 结构化提取 ──→ 台湾一手数据 ──→ 网络图谱 ──→ 报告生成 ──→ 专家评审 ──→ 导出
(5引擎并发)   (LLM提取)     (Perplexity)    (networkx)   (LLM分段)    (4路并行)    (DOCX+PDF)
```

## E.1 搜索任务定义

为每个目标人物创建任务定义文件：`data_collection/tasks/<person_slug>.py`

任务数据模型（`models.py`中的`SearchTask`）：

```python
@dataclass
class SearchTask:
    task_id: str                       # 如 "T1-07"
    gap_id: int                        # 映射到执行计划编号
    title: str                         # 采集项简称
    queries_zh: list[str]              # 正体中文关键词组
    queries_en: list[str]              # 英文关键词组
    engines: list[str]                 # ["brave", "tavily", "grok_web", "grok_x", "gemini"]
    time_range_hours: int = 8760       # 搜索时间范围（默认1年）
    max_results_per_engine: int = 10
    extraction_schema: str = ""        # LLM提取时的schema描述
    v6_module: str = ""                # 映射V7模块编号
    tier: int = 1                      # 采集优先级 0/1/2/3
```

### Tier分层策略

| Tier | 时机 | 内容 | 目标 |
|------|------|------|------|
| 0 | v1.0基线 | 基本信息+维基百科+主流媒体综述 | 建立16模块框架骨架 |
| 1 | v1.x补数据 | 针对覆盖率自检表缺口的专项搜索 | 覆盖率提升至70%+ |
| 2 | v1.x深化 | 学术文献+IR框架+深度调查报道 | 行为建模支撑 |
| 3 | 持续跟踪 | 最新动态+时效性事件 | 报告更新维护 |

## E.2 多引擎搜索调度

使用 `search_dispatcher.py`，核心流程：

1. 根据任务定义的 `engines` 列表，异步并发调用多个搜索引擎
2. 每个引擎执行中文+英文关键词查询
3. 合并所有结果，按URL去重
4. 存档到 `data_collection/raw/<task_id>.json`

**执行命令**：
```bash
# Tier-0 全部任务
python -m people.data_collection.run_collect --person <NAME> --tier 0

# Tier-1 全部任务
python -m people.data_collection.run_collect --person <NAME> --tier 1

# 仅执行指定任务
python -m people.data_collection.run_collect --person <NAME> --tier 1 --only T1-07,T1-12

# 仅搜索不提取
python -m people.data_collection.run_collect --person <NAME> --tier 1 --search-only

# 仅提取（基于已有raw）
python -m people.data_collection.run_collect --person <NAME> --tier 1 --extract-only
```

## E.3 LLM结构化事实提取

使用 `extractor.py`，核心流程：

1. 读取 `raw/<task_id>.json` 中的搜索结果
2. 构建提取prompt（系统提示+用户提示）
3. 调用LLM提取结构化事实
4. 解析JSON响应，转换为 `ExtractedFact` 对象
5. 持久化到 `extracted/<task_id>.json`

**提取事实数据模型**：
```python
@dataclass
class ExtractedFact:
    fact_id: str           # "T1-07-F01"
    gap_id: int
    content: str           # 事实陈述（简体中文，50-150字）
    evidence_grade: str    # A/B/C/D
    source_url: str
    source_name: str       # 如"联合新闻网"
    date_obtained: str     # 提取日期
    date_of_event: str     # 事件发生日期
    v6_module: str         # 映射到16模块编号
    raw_quote: str         # 原文关键引用（正体中文，20-50字）
```

**LLM通道选择**：
| 通道 | 模型 | 适用场景 |
|------|------|---------|
| grok (默认) | grok-fast | 大批量快速提取 |
| claude | claude-sonnet | 高质量提取（复杂语境） |
| gemini | gemini-flash | 快速补充提取 |
| qwen (兜底) | qwen3-max | 默认备选 |

## E.4 台湾一手数据获取

使用 `perplexity_fetcher.py`，通过Perplexity sonar-pro获取台湾政府数据：

```bash
python -m people.data_collection.perplexity_fetcher --person <NAME>
```

Perplexity的优势：自带实时搜索+引用，适合获取台湾政府网站数据（中选会/公督盟/监察院等），返回结构化内容+citations列表。

**自定义查询**：为新人物定义查询集时，参考蒋万安的5个标准查询（选举数据/政治献金/立法绩效/公督盟评鉴/财产申报），根据人物类型调整。

## E.5 网络图谱构建

使用 `network_analysis.py`：

```bash
python -m people.data_collection.network_analysis
```

**图谱构建步骤**：
1. 定义核心节点（目标人物）
2. 从提取事实中识别关系实体
3. 手工补充已知关系（党内/家族/国际）
4. 赋予边权重(0-1)和证据等级
5. 构建networkx DiGraph
6. 计算量化指标
7. 输出JSON

**注意**：当前版本边数据为半手工编码。未来可考虑LLM自动从事实中提取关系三元组。

## E.6 报告生成

使用 `gen_v13.py`（或后续版本），核心流程：

1. 加载全部提取事实（`extracted/*.json`）
2. 加载Perplexity台湾一手数据
3. 加载networkx网络分析结果
4. 加载v1.0基线报告（如有）
5. 按八篇结构逐篇调用LLM生成
6. 拼装封面+八篇+参考文献
7. 输出完整markdown

**LLM写作通道**：推荐使用reasoning模型（如grok-reasoning）做报告撰写，非reasoning模型用于事实提取。

## E.7 多LLM专家评审

使用 `peer_review/run_review.py`：

```bash
python -m people.peer_review.run_review \
    --report people/output/<NAME>/v1.x.md \
    --person <NAME> \
    --output people/peer_review/reports/<NAME>_review.md
```

**4路专家通道**：

| 专家 | 角色 | LLM | 评审重点 |
|------|------|-----|---------|
| A | 国际关系专家 | Perplexity sonar-pro | 三角联动、IR学术框架、国际定位 |
| B | 台湾历史学家 | Claude Sonnet | 历史叙事准确性、家族背景、转型正义 |
| C | 台湾问题研究专家 | Gemini Pro | 选举数据、立法绩效、内政政策 |
| D | 情报收集专家 | Grok Fast | 网络图谱、利益冲突、信息缺口 |

**评审输出格式**（每位专家）：
1. 事实错误指出（具体条目+正确信息+来源）
2. 信息缺口识别（缺什么+为什么重要+建议搜索方向）
3. 分析质量评估（框架应用是否恰当+推理链是否成立）
4. 补充建议（建议增加的内容+优先级）

## E.8 迭代深化协议

### 版本号约定

| 版本 | 含义 |
|------|------|
| v1.0 | Tier-0基线报告，16模块框架完整但内容单薄 |
| v1.1-v1.3 | 数据补齐阶段，每轮+0.1 |
| v1.4-v1.5 | 专家评审修正+台湾一手数据补齐 |
| v1.6+ | 最终版（台湾IP直采数据+Hermann编码透明度+全面校验） |

### 每轮迭代的标准操作

```
1. 运行覆盖率自检 → 识别最大缺口模块
2. 定义针对性搜索任务 → 执行采集+提取
3. 更新报告（融入新事实）→ 版本号+0.1
4. 重新运行覆盖率自检 → 评估改善幅度
5. 若覆盖率≥70%且台湾一手数据≥4/6 → 进入评审阶段
6. 否则 → 重复步骤1-4
```

### 准出条件

报告可标记为"final"的条件：
- [ ] 16模块均有章节位置（无静默省略）
- [ ] 覆盖率自检平均≥70%
- [ ] 台湾一手数据6类中≥4类完成
- [ ] Hermann编码透明度标注完成
- [ ] 三角联动≥3组完整案例
- [ ] 两岸专项≥3组前后对照
- [ ] 争议矩阵≥5事件
- [ ] 核心事实摘要20-50条
- [ ] 4路专家评审至少完成3路
- [ ] 所有A/B级事实错误已修正

## E.9 环境变量清单

| 变量 | 用途 | 必需 |
|------|------|------|
| `GROK_API_KEY` | Grok API (搜索+提取+评审) | 是 |
| `BRAVEAPI` | Brave Search API | 是 |
| `tavilyapi` | Tavily Search API | 是 |
| `GEMINI_API_KEY` | Gemini Search API | 是 |
| `PERPLEXITY_API_KEY` | Perplexity API (台湾数据+评审) | 是 |
| `CLOUBIC_API_KEY` | Cloubic中转 (Claude/Gemini/Qwen) | 是 |
| `CLOUBIC_BASE_URL` | Cloubic API地址 | 否(有默认值) |
| `LLM_PROXY` | 海外API代理 | 视网络环境 |
