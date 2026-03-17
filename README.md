# News Monitor — 全球新闻监控与舆情分析系统

多数据源新闻抓取 → 去重 → 翻译 → 智能分析 → 报告生成，支持两种工作模式：

- **国别动态监测**：35 国定期监测，五条关系线相关性筛选，飞书/钉钉推送
- **主题事件舆情**：针对特定事件搜索海外媒体，舆情四分类，语义聚类，生成 2000 字深度分析报告

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt
pip install python-docx  # Word 报告（可选）

# 配置 API Key
cp .env.example .env
# 编辑 .env 填入 BRAVEAPI, GROK_API_KEY, GEMINI_API_KEY 等

# 国别监测
python fetch_topic.py 智利
python fetch_topic.py 智利 墨西哥 巴西        # 多国
python fetch_topic.py 智利 --resume           # 断点续传
python fetch_topic.py 智利 --incremental      # 增量抓取

# 主题事件舆情
python fetch_event.py boao                    # 抓取+翻译+分类
python fetch_event.py boao --resume           # 断点续传
python analyze_event.py                       # 深度分析（2次API调用）

# 守护进程
python run.py                                 # 60分钟间隔自动执行
python run.py --once                          # 单次执行
```

## 架构

```
┌─────────────────────────────────────────────────────┐
│                   数据源（6个启用）                    │
│  Brave │ Gemini │ Grok Web │ Grok X │ Tavily │ ...  │
└────────────────────┬────────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────────┐
│              fetch_topic.py / fetch_event.py         │
│  Fetch → Dedup → Translate → Filter/Classify → Report│
│         ↕ checkpoint (断点续传)                       │
└────────────────────┬────────────────────────────────┘
                     ▼
┌──────────────┐  ┌──────────────┐  ┌─────────────────┐
│  国别报告     │  │  事件舆情报告  │  │  深度分析报告    │
│  MD + PDF    │  │  MD + DOCX   │  │  2000字 + 聚类   │
│  + 飞书推送   │  │  + JSON      │  │  analyze_event   │
└──────────────┘  └──────────────┘  └─────────────────┘
```

## 两条功能线

### 国别动态监测 (`fetch_topic.py`)

覆盖 35 个国家，每国 30+ 条搜索查询，6 个板块：

| 关系线 | 门槛 | 说明 |
|--------|------|------|
| 中国线 | 中 | 中资投资、双边外交、政策变动 |
| 台湾线 | 低 | 文化外交、教育奖学金、ICDF |
| 美国线 | 中高 | 峰会条约、关税制裁、军事安全 |
| 对华舆情 | 中 | 排华情绪、劳资冲突、华人安全 |
| 地缘政治 | 高 | 外交重组、多边权力平衡 |

### 主题事件舆情 (`fetch_event.py` + `analyze_event.py`)

针对特定事件的完整分析流水线：

1. **抓取** — 4 源并行，55+ 条多语言查询
2. **翻译** — Grok non-reasoning，只提交标题（节省 token）
3. **舆情分类** — Grok reasoning，四分类（正面/中性/负面/分析）
4. **语义聚类** — Grok reasoning，15-25 个主题群
5. **深度报告** — 2000 字结构化分析（总览/核心议题/风险机遇/研判建议）

## 关键特性

- **Checkpoint 断点续传** — 每阶段自动保存，`--resume` 恢复，断电不丢数据
- **智能 API 分批** — 按 output token 预算动态估算批量大小，最少 API 调用
- **JSON 容错解析** — 4 层修复策略应对 LLM 输出截断
- **媒体影响力分级** — 50+ 媒体分 3 级（国际主流/区域大媒体/智库专刊），报告按影响力排序
- **增量抓取** — `--incremental` 只抓取上次运行后的新文章
- **社交媒体处理** — Grok X 推文标题清洗，独立板块展示
- **时序趋势存储** — 每次运行保存舆情快照，支持跨时间对比

## 目录结构

```
fetch_topic.py                  # 国别监测入口
fetch_event.py                  # 主题事件舆情入口
analyze_event.py                # 深度分析（语义聚类+报告）
run.py                          # 守护进程入口
config.yaml                     # 全局配置
topics/                         # 搜索查询配置（35国 + 事件主题）
src/news_monitor/
  checkpoint.py                 # 统一断点续传模块
  media_tier.py                 # 媒体影响力分级
  trend.py                      # 时序趋势存储
  filter/
    relevance_filter.py         # 国别相关性筛选
    sentiment_classifier.py     # 事件舆情态度分类
  translation/llm_translator.py # LLM 批量翻译
  sources/                      # 数据源适配器
  output/                       # 报告生成（PDF/DOCX）
  push/                         # 推送渠道（飞书/钉钉/企微）
  db/                           # PostgreSQL DAO（可选）
output/
  reports/                      # 生成的报告
  checkpoints/                  # 断点续传数据
  trends/                       # 舆情趋势快照
  logs/                         # 运行日志
```

## 配置

复制 `.env.example` 为 `.env`，填入 API Key：

| 变量 | 用途 | 必填 |
|------|------|------|
| `BRAVEAPI` | Brave Search API | 是 |
| `GROK_API_KEY` | Grok 翻译/分类/搜索 | 是 |
| `GEMINI_API_KEY` | Gemini Search | 是 |
| `TAVILYAPI` | Tavily Search | 否 |
| `LLM_PROXY` | 海外 API 代理地址 | 视网络环境 |
| `QWEN_API_KEY` | 通义千问（翻译备选） | 否 |
| `DEEPSEEK_API_KEY` | DeepSeek（翻译备选） | 否 |
| `FEISHU_WEBHOOK_URL` | 飞书推送 | 否 |

## 技术栈

- Python 3.12 / asyncio + httpx
- Grok API (grok-4-1-fast-reasoning / non-reasoning, 2M context)
- SQLite（默认）/ PostgreSQL + pgvector（可选）
- APScheduler / python-docx / fpdf2
