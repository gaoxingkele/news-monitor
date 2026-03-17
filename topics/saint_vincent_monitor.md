---
name: 圣文森特和格林纳丁斯动态监测
countries: [vc]
watch_countries: [tw, cn, us]
search_global: true
skip_sources: [newsdata_io, serpapi_google]
languages: [en, zh]
time_range_hours: 168
time_mode: last_week
max_articles: 20
enabled: true
---

# 圣文森特和格林纳丁斯动态监测

⚑ 台湾邦交国；加勒比小岛国；火山灾害（2021年苏弗里耶尔火山爆发）；ALBA成员；气候脆弱

涵盖12个主题维度：外交政治 / 经贸投资 / 港口航运 / 矿产能源 / 教育文化 /
公卫医疗 / NGO论坛展会 / 体育青年 / 环保气候碳权 / 军事安全 / LGBT政策 / 当地华人社区

查询语言：英语 + 中文 + 英文（三语并行，SerpAPI/NewsData 各语言独立命中）
台湾侧深挖：mofa.gov.tw / icdf.org.tw / cna.com.tw（site: 查询，SerpAPI 有效，NewsData 跳过）

## 搜索查询

### ── 关系线1：圣文森特和格林纳丁斯 × 中国 ────────────────────────────────────────

- Saint Vincent and the Grenadines China investment trade agreement diplomacy
- Saint Vincent and the Grenadines China port mining energy infrastructure project
- Saint Vincent and the Grenadines Chinese company infrastructure contract construction
- 圣文森特和格林纳丁斯 中国 投资 贸易 合作 外交 协议
- 圣文森特和格林纳丁斯 中国 港口 矿产 能源 基础设施 企业
- Saint Vincent and the Grenadines China bilateral relations cooperation security

### ── 关系线2：圣文森特和格林纳丁斯 × 美国 ────────────────────────────────────────

- Saint Vincent and the Grenadines United States agreement security cooperation defense
- Saint Vincent and the Grenadines US USAID aid trade agreement sanctions
- 圣文森特和格林纳丁斯 美国 协议 安全 贸易 关税 援助 合作
- Saint Vincent and the Grenadines US Pacific strategy security competition China

### ── 关系线3：圣文森特和格林纳丁斯 × 台湾 ────────────────────────────────────────

- Taiwan Saint Vincent and the Grenadines diplomacy visit minister cooperation
- Taiwan Saint Vincent and the Grenadines ICDF scholarship education health cooperation
- 圣文森特和格林纳丁斯 台湾 外交 访问 合作 奖学金 医疗 部长
- Taiwan Saint Vincent and the Grenadines carbon credits reforestation REDD forest hectares
- 圣文森特和格林纳丁斯 台湾 碳权 碳信用 造林 公顷 森林 合作

### ── 关系线3附：台湾侧主动发布（.tw 域名深挖）────────────────────────────
# site: 查询在 SerpAPI/Google 生效；NewsData.io 不支持 site: 语法，返回空（无副作用）
# 覆盖：台湾外交部(MOFA) / ICDF国际合作基金 / 中央社(CNA)

- site:mofa.gov.tw "Saint Vincent and the Grenadines"
- site:icdf.org.tw "Saint Vincent and the Grenadines"
- site:cna.com.tw "Saint Vincent and the Grenadines"
- 圣文森特和格林纳丁斯 台湾 外交部 ICDF 声明 合作 公告 计划

### ── 跨议题（三条关系线共用）────────────────────────────────────────

- Saint Vincent and the Grenadines forum summit NGO organization international event
- Saint Vincent and the Grenadines climate change carbon environment agreement policy
- Saint Vincent and the Grenadines sports cultural exchange youth cooperation
- Saint Vincent and the Grenadines public health medical cooperation donation hospital AI
- Saint Vincent and the Grenadines military security cooperation defense agreement
- Saint Vincent and the Grenadines Chinese community business crime security immigration
- 圣文森特和格林纳丁斯 论坛 峰会 体育 青年 环保 NGO 文化交流
- 圣文森特和格林纳丁斯 军事 安全 公卫 医疗 华人 华侨 社区

### ── 对华舆情与风险信号 ────────────────────────────────────────

- Saint Vincent and the Grenadines China protest xenophobia rejection invasion Chinese company conflict
- Saint Vincent and the Grenadines Chinese community crime insecurity persecution historical apology
- 圣文森特和格林纳丁斯 中国 抗议 排斥 仇外 冲突 安全 风险 华人 迫害

### ── 国别专项补充查询 ────────────────────────────────────────

- "Saint Vincent" Taiwan embassy recognition diplomatic cooperation aid
- "Saint Vincent" ALBA CARICOM Caribbean cooperation China Taiwan
- "Saint Vincent" volcano Soufriere disaster reconstruction aid

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

1. 圣文森特和格林纳丁斯与台湾（外交 / 教育文化 / 公卫 / 体育 / 环保碳权 / ICDF）
2. 圣文森特和格林纳丁斯与中国（外交经贸 / 港口矿能 / 中资企业 / 华人社区）
3. 圣文森特和格林纳丁斯与美国（外交安全 / 经贸关税 / USAID / 军事）
4. 对华舆情（排华情绪 / 中资企业冲突 / 华人安全 / 历史迫害 / 社区摩擦）
