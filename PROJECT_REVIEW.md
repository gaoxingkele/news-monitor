# News Monitor — 项目回顾与演进路线

**最后更新：2026-03-17**

---

## 一、项目概述

全球新闻监控与舆情分析系统，两条功能线并行运作：

| 功能线 | 入口脚本 | 场景 | 输出 |
|--------|---------|------|------|
| 国别动态监测 | `fetch_topic.py` | 35 国每周定期监测 | MD + PDF + 飞书推送 |
| 主题事件舆情 | `fetch_event.py` + `analyze_event.py` | 临时性事件深度分析 | MD + DOCX + 2000 字分析报告 |

**核心技术栈：** Python 3.12 / asyncio + httpx / Grok API (2M context) / SQLite / APScheduler

---

## 二、改进历史

### Phase 1：国别监测基础架构（2026-03 初）

- 搭建 pipeline.py 核心流水线：fetch → dedup → translate → filter → push
- 接入 6 个数据源：Brave、Gemini、Grok Web、Grok X、Tavily、NewsAPI.ai
- SQLite 双层去重（SHA256 指纹 + SequenceMatcher 标题模糊匹配）
- LLM 翻译（qwen 主力 + fallback chain）
- 五条关系线相关性筛选（中国/台湾/美国/对华舆情/地缘政治）
- PDF 报告生成（pandoc/weasyprint/fpdf2 三级降级）
- 飞书 webhook 卡片推送
- 35 国查询配置文件（每国 30-34 条查询，6 个板块）

### Phase 2：国别监测优化（2026-03 中旬）

- Grok 批量搜索：按 section 合并查询，API 调用量降低 ~60%
- 多国顺序执行：`python fetch_topic.py 智利 墨西哥 巴西`
- MERGE_WITH 支持：跨运行合并结果，增量更新
- 主题聚类报告：同事件多源报道合并展示
- 推文专区：Grok X 推文单独聚类，提取作者和原文摘要

### Phase 3：主题事件舆情分析（2026-03-17，本次里程碑）

**新增文件：**
| 文件 | 行数 | 功能 |
|------|------|------|
| `fetch_event.py` | 1205 | 事件舆情抓取（5 阶段 + checkpoint） |
| `analyze_event.py` | 508 | 深度分析（语义聚类 + 2000 字报告） |
| `sentiment_classifier.py` | 368 | 舆情态度四分类器 |
| `docx_reporter.py` | 248 | Word 报告生成 |
| `topics/boao_forum_2026.md` | 120 | 博鳌论坛查询模板 |

**关键改进：**
1. **Checkpoint 断点续传** — 每阶段保存 JSON，`--resume` 恢复，断电不丢数据
2. **智能 API 分批** — 按 output token 预算估算 max_batch，不固定批量
3. **JSON 容错解析** — 4 层修复策略（直解→去 markdown→截断修复→逐对象提取）
4. **双通道日志** — terminal + 文件同步输出，后台运行也能实时看进度
5. **语义聚类** — Grok reasoning 按议题/事件深度聚类（非标题相似度）
6. **综合摘要** — LLM 生成 300-400 字舆情总览
7. **深度报告** — 2000 字结构化分析（总览/核心议题/风险机遇/研判建议）
8. **后处理降噪** — 关键词过滤 + 域名黑名单（排除中国大陆媒体）

### Phase 3.1：国别监测 checkpoint（2026-03-17）

- `fetch_topic.py` 加入三阶段 checkpoint（fetch_dedup / translated / filtered）
- 支持 `--resume` 断点续传，与事件监测保持一致

---

## 三、现有功能清单

### 3.1 数据采集
- [x] Brave Search API（优先级 1，每查询 20 条）
- [x] Gemini Search（grounding，优先级 4）
- [x] Grok Web Search（grok-4-1-fast-non-reasoning，批量按 section）
- [x] Grok X Search（Twitter/X 社交媒体帖文）
- [x] Tavily Search（补充源，每查询 5 条）
- [x] NewsAPI.ai / Perplexity / SerpAPI / NewsData.io / WorldNews（pipeline.py 可用，fetch_topic 未启用）
- [x] 中国内容域名黑名单（~40 个域名自动过滤）
- [x] 多语言搜索：中/英/西/法/德/日/韩/阿拉伯 等

### 3.2 数据处理
- [x] URL 归一化去重 + SHA256 指纹去重
- [x] SequenceMatcher 标题模糊去重（阈值 0.85）
- [x] LLM 批量翻译（标题→简体中文，摘要本地截取）
- [x] 翻译 provider fallback chain（grok → qwen → deepseek → doubao → glm）
- [x] 中文文章自动跳过翻译

### 3.3 智能分析
- [x] 国别相关性筛选（五条关系线 + ALWAYS FILTER 规则）
- [x] 事件舆情四分类（positive / neutral / negative / analysis）
- [x] 核心态度提取（每篇一句话中文态度摘要）
- [x] 重要度评分（1-5 星）
- [x] 标题相似度聚类（greedy, threshold 0.45）
- [x] Grok reasoning 语义聚类（15-25 主题群）
- [x] 综合舆情摘要（300-400 字）
- [x] 深度分析报告（~2000 字，四段式结构）

### 3.4 输出与推送
- [x] Markdown 报告（结构化，关键词高亮）
- [x] PDF 报告（pandoc/weasyprint/fpdf2 三级降级）
- [x] Word 文档（python-docx，颜色编码，重要度标记）
- [x] JSON sidecar（便于后续合并和分析）
- [x] 飞书 webhook 卡片推送
- [x] 钉钉 / 企业微信（已实现，默认禁用）

### 3.5 运维
- [x] Checkpoint 断点续传（国别 3 阶段 / 事件 3 阶段）
- [x] `--resume` 命令行参数
- [x] 双通道日志（terminal + 文件）
- [x] APScheduler 守护进程模式（60 分钟间隔）
- [x] PostgreSQL 可选（连接池 + 自动迁移 + 向量搜索）
- [x] NER 实体提取 + 向量嵌入（PG 模式）

---

## 四、代码规模

| 模块 | 文件数 | 总行数 |
|------|--------|--------|
| 入口脚本 | 4 (run/fetch_topic/fetch_event/analyze) | ~2,800 |
| 数据源 | 11 (sources/*.py) | ~2,000 |
| 翻译/筛选/分类 | 3 | ~1,060 |
| 报告输出 | 2 | ~1,130 |
| 数据库/去重/推送 | 12 | ~1,500 |
| 配置/模型/调度 | 5 | ~600 |
| **合计** | **~37** | **~9,000** |
| 国别查询文件 | 35 | ~3,500 |
| 事件查询文件 | 1 | 120 |

---

## 五、升级优化建议

### 优先级 P0（近期可做，收益高）

#### 1. 搜索查询精确化
**现状：** 宽泛关键词组合（如 `Boao Forum 2026 technology AI`）拉回大量无关文章，后处理降噪删掉 25%。
**建议：** 事件查询强制使用引号精确匹配（`"Boao Forum" 2026`），国别查询保持现有模式。在 topic MD 文件中区分 `exact_match: true` 的查询和模糊查询。
**预期效果：** 无关文章减少 50%+，翻译/分类 token 节省。

#### 2. 抓取阶段就过滤域名
**现状：** 域名黑名单在 `_dedup_merge()` 中过滤，已经浪费了翻译和分类的 API 调用。
**建议：** 在各 source 的 `fetch_articles()` 返回时立即过滤，或在去重前增加 `_filter_blocked_domains()` 步骤。
**预期效果：** 每次运行减少 200+ 篇无效文章的处理开销。

#### 3. 统一 checkpoint 模块
**现状：** `fetch_topic.py` 和 `fetch_event.py` 各自实现了 checkpoint 逻辑，代码重复。
**建议：** 抽取为 `src/news_monitor/checkpoint.py` 共享模块，接口：`save(key, stage, articles, extra)` / `load(key, stage)` / `find_latest(key)`。
**预期效果：** 消除重复代码 ~80 行，未来新脚本自动获得 checkpoint 能力。

### 优先级 P1（中期，架构优化）

#### 4. 媒体影响力分级
**现状：** Reuters 一篇和不知名博客一篇在报告中权重相同。
**建议：** 建立媒体影响力数据库（tier 1: Reuters/BBC/CNN/SCMP / tier 2: 区域大媒体 / tier 3: 其他），报告排序和深度分析中加权。可用静态 JSON 配置 + LLM 辅助补全。
**预期效果：** 报告可读性大幅提升，重要媒体报道不被淹没。

#### 5. 时序趋势分析
**现状：** 每次运行是独立快照，无法看舆情变化趋势。
**建议：** 在 SQLite/PG 中持久化每次运行的舆情分布数据（时间戳 + 分类计数 + 关键词频率），新增 `trend_report.py` 生成趋势图（matplotlib/plotly）。
**预期效果：** 支持"会前→会中→会后"舆情变化追踪，对重大事件极有价值。

#### 6. 增量抓取模式
**现状：** 每次运行都全量抓取 55 条查询，即使大部分结果和上次相同。
**建议：** 记录上次运行的最新文章时间戳，仅抓取该时间之后的新文章。Brave/Gemini 支持 `freshness` 参数。
**预期效果：** 定期运行时 API 调用量降低 60-70%。

#### 7. 社交媒体专项处理
**现状：** Grok X 返回的推文标题往往是搜索查询本身，不是实际推文内容。
**建议：** Grok X 结果单独处理：提取实际推文文本、作者、互动数据；在报告中以"社交媒体舆情"独立板块展示，按影响力（粉丝数/转发量）排序。
**预期效果：** 社交媒体数据从噪音变为有价值的舆情信号。

### 优先级 P2（长期，功能扩展）

#### 8. Web UI 可视化看板
**现状：** 纯命令行 + 文件输出，非技术人员难以使用。
**建议：** 基于 Streamlit 或 FastAPI+Vue 搭建轻量看板：舆情分布饼图、时序趋势线、关键词词云、文章列表可筛选。
**预期效果：** 非技术团队可以自助查看和筛选舆情数据。

#### 9. 多事件对比分析
**现状：** `analyze_event.py` 只处理单个事件。
**建议：** 支持多事件 JSON 输入，生成对比报告（如"博鳌论坛 vs 达沃斯论坛"舆情对比）。
**预期效果：** 竞品事件舆情对标分析。

#### 10. 自动告警机制
**现状：** 需手动运行、手动查看报告。
**建议：** 在 pipeline 中加入告警规则引擎：当负面报道突增（超过阈值）、出现特定关键词（如"制裁""抵制"）、重要媒体首次报道时，自动推送飞书/钉钉告警。
**预期效果：** 重大舆情事件第一时间响应。

#### 11. 知识图谱可视化
**现状：** NER + 实体关系已在 PG 模式实现，但无可视化。
**建议：** 导出实体关系为 Neo4j 或 D3.js 网络图，展示国家-组织-人物-事件的关联网络。
**预期效果：** 直观呈现地缘政治关系脉络。

#### 12. RAG 问答接口
**现状：** 向量嵌入已存入 PG (pgvector)，但无查询接口。
**建议：** 基于已有 embedding + PG HNSW 索引，搭建 RAG 接口：用户提问 → 向量检索相关文章 → LLM 生成带引用的回答。
**预期效果：** "某国最近和中国有什么合作？"之类的问题可以即时回答。

---

## 六、运行指南速查

```bash
# ── 国别监测 ──
python fetch_topic.py 智利                    # 单国
python fetch_topic.py 智利 墨西哥 巴西         # 多国顺序
python fetch_topic.py 智利 --resume           # 断点续传
FETCH_SOURCES=brave,gemini python fetch_topic.py 智利  # 指定数据源
MERGE_WITH=output/reports/xxx.json python fetch_topic.py 智利  # 合并上次结果

# ── 事件舆情 ──
python fetch_event.py boao                    # 全量抓取+分析
python fetch_event.py boao --resume           # 断点续传
python analyze_event.py output/reports/xxx.json  # 深度分析（2次API）

# ── 守护进程 ──
python run.py                                 # 60分钟间隔自动执行
python run.py --once                          # 单次执行
```
