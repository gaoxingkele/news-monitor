# people/peer_review —— OSINT V6 三专家评审子模块

本子模块是 `news-monitor` 项目的独立附加模块，用于对 `people/` 目录下按
OSINT V6.0 框架撰写的政治人物分析报告进行「挑错式」三专家评审。

## 设计原则

- **只读访问主项目**：读取 `.env` / `.env.cloubic` 中的 API Key 与代理配置，**不修改** `src/news_monitor/` 下任何代码
- **独立依赖最小化**：仅依赖 `httpx` 和 `python-docx`（主项目已内置）
- **三通道 LLM 互证**：避免单一模型偏见，每位专家由不同厂商的模型分别驱动

## 三专家配置

| ID | 专家 | 通道 | 模型 | 代理 |
|----|------|------|------|------|
| A | 国际关系专家 | Grok 直连（OpenAI 兼容） | `grok-4.20-0309-reasoning` | 走 `LLM_PROXY` |
| B | 台湾历史学家 | Cloubic Claude | `CLOUBIC_CLAUDE_MODEL` 首项（默认 `claude-opus-4-6`） | 无代理 |
| C | 台湾问题研究专家 | Cloubic Gemini | `CLOUBIC_GEMINI_REASONING_MODEL` 首项（默认 `gemini-3.1-pro-preview`） | 无代理 |

## 目录结构

```
people/peer_review/
├── __init__.py
├── README.md              ← 本文件
├── config.py              ← 三专家通道配置 + 环境变量加载
├── llm_clients.py         ← OpenAI 兼容 chat/completions 调用封装
├── prompts.py             ← 三专家角色 system prompt + 共享评审任务
├── run_review.py          ← 主入口
├── raw_responses/         ← 每位专家的原始评审文本
└── reports/               ← 汇总评审 markdown 报告
```

## 使用方式

```bash
# 评审蒋万安 v1.0
python -m people.peer_review.run_review \
    --report people/蒋万安_政治人物分析报告_v1.0.docx \
    --person 蒋万安 \
    --output people/peer_review/reports/蒋万安_v1.0_peer_review.md
```

## 输出结构

汇总报告包含：
1. 评审元信息（被评审报告、框架基线、评审时间、三通道模型）
2. 三位专家各自的完整评审意见（总体评价 / V6 合规性 / 专业缺陷 / 方法论问题 / 优先修改清单）

## 扩展

- 添加新专家：在 `config.py` 的 `build_channels()` 中追加 `ExpertChannel`，并在 `prompts.py` 中增加对应 system prompt
- 评审其他人物：直接替换 `--report` 和 `--person` 参数即可
