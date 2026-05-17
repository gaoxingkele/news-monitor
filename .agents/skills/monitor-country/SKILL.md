---
name: monitor-country
description: |
  对任意国别执行完整新闻监测流水线：抓取 → 去重 → 翻译(简体中文) → 相关性筛选(涉华利益) → 输出 MD + PDF 报告。
  涵盖12个主题维度：外交政治 / 经贸投资 / 港口航运 / 矿产能源 / 教育文化 /
  公卫医疗 / NGO论坛展会 / 体育青年 / 环保气候碳权 / 军事安全 / LGBT政策 / 当地华人社区。
  示例：/monitor-country 智利   /monitor-country Colombia   /monitor-country cl
argument-hint: <国名(中/英)或ISO国别码>
allowed-tools:
  - Bash(python:*)
  - Read
---

# 国别新闻监测任务

## 目标国别

**$ARGUMENTS**

---

## 执行步骤

### 第一步：验证国别是否有配置

在项目根目录运行以下命令，确认对应的 topic 存在：

```bash
python -c "
import sys; sys.path.insert(0,'src')
from news_monitor.topics.loader import load_topics_from_dir
topics = load_topics_from_dir('topics')
needle = '$ARGUMENTS'.lower()
matched = [t for t in topics if needle in t.get('name','').lower()]
if matched:
    t = matched[0]
    print(f'✓ 找到：{t[\"name\"]}')
    print(f'  国别代码：{t.get(\"countries\",[])}')
    print(f'  查询数量：{len(t.get(\"query_groups\",[]))} 条')
    print(f'  时间模式：{t.get(\"time_mode\",\"默认\")}')
    print(f'  监测语言：{t.get(\"languages\",[])}')
else:
    print('✗ 未找到匹配的国别配置')
    print('可用国别：')
    for t in sorted(topics, key=lambda x: x.get('name','')):
        print(f'  - {t[\"name\"]} {t.get(\"countries\",[])}')
"
```

若未找到，**列出所有可用国别让用户选择，不要继续执行后续步骤**。

---

### 第二步：运行完整监测流水线

确认国别存在后，在项目根目录运行：

```bash
python fetch_topic.py "$ARGUMENTS"
```

**实时展示所有输出**，包括：
- API 调用进度（NewsData / SerpAPI 每条查询的命中数）
- 去重统计
- 翻译批次进度
- 相关性过滤结果（保留 / 剔除 / 剔除原因）
- 生成的 MD 路径和 PDF 路径

---

### 第三步：汇总报告

流水线完成后，输出结构化摘要：

```
═══════════════════════════════════════════════════
  【$ARGUMENTS】监测任务完成
═══════════════════════════════════════════════════
  时间范围  ：[from_date] → [to_date]
  ─────────────────────────────────────
  原始抓取  ：[N] 篇（NewsData=[n1]，SerpAPI=[n2]）
  去重后    ：[N] 篇（已去除重复 [n] 篇）
  翻译完成  ：[N] 篇
  ─────────────────────────────────────
  相关性过滤：保留 [N] 篇，剔除 [n] 篇
  ─────────────────────────────────────
  分类统计  ：
    美国相关  [n] 篇
    台湾相关  [n] 篇
    中国相关  [n] 篇
    本地其他  [n] 篇
  ─────────────────────────────────────
  输出文件  ：
    MD  → [md_path]
    PDF → [pdf_path]
═══════════════════════════════════════════════════
```

---

## 查询策略说明（供参考）

每个国别的 `topics/*.md` 配置文件已按以下策略设计，共约 20–25 条独立查询：

| 关系线 | 语言 | 主题覆盖 |
|--------|------|---------|
| 目标国 × 中国 | ES + ZH + EN | 经贸外交 / 港口矿能 / 中资企业基础设施 |
| 目标国 × 美国 | ES + ZH + EN | 安全协议 / 关税供应链 / USAID军事 |
| 目标国 × 台湾 | ES + ZH + 专项 | 外交访问 / ICDF教育医疗奖学金 / **碳权造林** |
| 跨议题 | ES + ZH | NGO论坛 / 环保气候碳 / 体育文化青年 / 公卫医疗 / 军事安全 / 华人社区 |

**相关性筛选标准**（LLM 自动过滤）：
- ✅ 保留：涉及中国利益的内容（中国-目标国双边、台湾外交空间、美国影响中国布局、BRI/资源/港口、NGO针对中资项目等）
- ❌ 剔除：目标国纯内政（无外交维度）/ 娱乐体育赛事结果 / 通用金融市场报告 / 历史背景综述

---

## 注意事项

- **API 限速**：SerpAPI 查询间隔 0.5 秒，NewsData 查询间隔 1.5 秒，约 20–30 分钟完成
- **免费版 NewsData**：仅返回最近 48 小时内容，历史日期查询后客户端会过滤为 0 条（正常）
- **翻译失败重试**：DeepSeek 主用，Kimi 备用，批次失败自动切换，不影响整体运行
- **PDF 生成**：优先 pandoc（需已安装），备选 weasyprint，最终 fpdf2 兜底
