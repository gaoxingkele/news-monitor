---
name: 圭亚那动态监测
countries: [gy]
watch_countries: [tw, cn, us]
search_global: true
skip_sources: [newsdata_io, serpapi_google]
languages: [en, es, zh]
time_range_hours: 168
time_mode: last_week
max_articles: 20
enabled: true
---

# 圭亚那动态监测

重点关注：2015年起海上石油大发现（埃克森美孚），中国与美国竞争能源影响力，领土争端

涵盖12个主题维度：外交政治 / 经贸投资 / 港口航运 / 矿产能源 / 教育文化 /
公卫医疗 / NGO论坛展会 / 体育青年 / 环保气候碳权 / 军事安全 / LGBT政策 / 当地华人社区

查询语言：英语 + 中文 + 英文（三语并行，SerpAPI/NewsData 各语言独立命中）
台湾侧深挖：mofa.gov.tw / icdf.org.tw / cna.com.tw（site: 查询，SerpAPI 有效，NewsData 跳过）

## 搜索查询

### ── 关系线1：圭亚那 × 中国 ────────────────────────────────────────

- Guyana China investment trade agreement diplomacy
- Guyana China port mining energy infrastructure project
- Guyana Chinese company infrastructure contract construction
- 圭亚那 中国 投资 贸易 合作 外交 协议
- 圭亚那 中国 港口 矿产 能源 基础设施 企业
- Guyana China bilateral relations cooperation security

### ── 关系线2：圭亚那 × 美国 ────────────────────────────────────────

- Guyana United States agreement security cooperation defense
- Guyana US USAID aid trade agreement sanctions
- 圭亚那 美国 协议 安全 贸易 关税 援助 合作
- Guyana US Pacific strategy security competition China

### ── 关系线3：圭亚那 × 台湾 ────────────────────────────────────────

- Taiwan Guyana diplomacy visit minister cooperation
- Taiwan Guyana ICDF scholarship education health cooperation
- 圭亚那 台湾 外交 访问 合作 奖学金 医疗 部长
- Taiwan Guyana carbon credits reforestation REDD forest hectares
- 圭亚那 台湾 碳权 碳信用 造林 公顷 森林 合作

### ── 关系线3附：台湾侧主动发布（.tw 域名深挖）────────────────────────────
# site: 查询在 SerpAPI/Google 生效；NewsData.io 不支持 site: 语法，返回空（无副作用）
# 覆盖：台湾外交部(MOFA) / ICDF国际合作基金 / 中央社(CNA)

- site:mofa.gov.tw "Guyana"
- site:icdf.org.tw "Guyana"
- site:cna.com.tw "Guyana"
- 圭亚那 台湾 外交部 ICDF 声明 合作 公告 计划

### ── 跨议题（三条关系线共用）────────────────────────────────────────

- Guyana forum summit NGO organization international event
- Guyana climate change carbon environment agreement policy
- Guyana sports cultural exchange youth cooperation
- Guyana public health medical cooperation donation hospital AI
- Guyana military security cooperation defense agreement
- Guyana Chinese community business crime security immigration
- 圭亚那 论坛 峰会 体育 青年 环保 NGO 文化交流
- 圭亚那 军事 安全 公卫 医疗 华人 华侨 社区

### ── 对华舆情与风险信号 ────────────────────────────────────────

- Guyana China protest xenophobia rejection invasion Chinese company conflict
- Guyana Chinese community crime insecurity persecution historical apology
- 圭亚那 中国 抗议 排斥 仇外 冲突 安全 风险 华人 迫害

### ── 国别专项补充查询 ────────────────────────────────────────

- Guyana oil ExxonMobil China investment energy competition
- Guyana Venezuela border dispute US China

## 排除关键词

- sports results
- standings
- entertainment
- celebrity
- baseball
- WBC
- football results
- poll

## 检测结果分类

1. 圭亚那与台湾（外交 / 教育文化 / 公卫 / 体育 / 环保碳权 / ICDF）
2. 圭亚那与中国（外交经贸 / 港口矿能 / 中资企业 / 华人社区）
3. 圭亚那与美国（外交安全 / 经贸关税 / USAID / 军事）
4. 对华舆情（排华情绪 / 中资企业冲突 / 华人安全 / 历史迫害 / 社区摩擦）
