---
name: 梵蒂冈动态监测
countries: [va]
watch_countries: [tw, cn, us]
search_global: true
skip_sources: [newsdata_io, serpapi_google]
languages: [en, zh, it]
time_range_hours: 168
time_mode: last_week
max_articles: 20
enabled: true
---

# 梵蒂冈动态监测

⚑ 台湾在欧洲唯一邦交国；中梵临时协议（主教任命）持续谈判；教廷对华外交立场微妙；全球天主教影响力

涵盖12个主题维度：外交政治 / 经贸投资 / 港口航运 / 矿产能源 / 教育文化 /
公卫医疗 / NGO论坛展会 / 体育青年 / 环保气候碳权 / 军事安全 / LGBT政策 / 当地华人社区

查询语言：英语 + 中文 + 英文（三语并行，SerpAPI/NewsData 各语言独立命中）
台湾侧深挖：mofa.gov.tw / icdf.org.tw / cna.com.tw（site: 查询，SerpAPI 有效，NewsData 跳过）

## 搜索查询

### ── 关系线1：梵蒂冈 × 中国 ────────────────────────────────────────

- Vatican China investment trade agreement diplomacy
- Vatican China port mining energy infrastructure project
- Vatican Chinese company infrastructure contract construction
- 梵蒂冈 中国 投资 贸易 合作 外交 协议
- 梵蒂冈 中国 港口 矿产 能源 基础设施 企业
- Vatican China bilateral relations cooperation security

### ── 关系线2：梵蒂冈 × 美国 ────────────────────────────────────────

- Vatican United States agreement security cooperation defense
- Vatican US USAID aid trade agreement sanctions
- 梵蒂冈 美国 协议 安全 贸易 关税 援助 合作
- Vatican US Pacific strategy security competition China

### ── 关系线3：梵蒂冈 × 台湾 ────────────────────────────────────────

- Taiwan Vatican diplomacy visit minister cooperation
- Taiwan Vatican ICDF scholarship education health cooperation
- 梵蒂冈 台湾 外交 访问 合作 奖学金 医疗 部长
- Taiwan Vatican carbon credits reforestation REDD forest hectares
- 梵蒂冈 台湾 碳权 碳信用 造林 公顷 森林 合作

### ── 关系线3附：台湾侧主动发布（.tw 域名深挖）────────────────────────────
# site: 查询在 SerpAPI/Google 生效；NewsData.io 不支持 site: 语法，返回空（无副作用）
# 覆盖：台湾外交部(MOFA) / ICDF国际合作基金 / 中央社(CNA)

- site:mofa.gov.tw "Vatican"
- site:icdf.org.tw "Vatican"
- site:cna.com.tw "Vatican"
- 梵蒂冈 台湾 外交部 ICDF 声明 合作 公告 计划

### ── 跨议题（三条关系线共用）────────────────────────────────────────

- Vatican forum summit NGO organization international event
- Vatican climate change carbon environment agreement policy
- Vatican sports cultural exchange youth cooperation
- Vatican public health medical cooperation donation hospital AI
- Vatican military security cooperation defense agreement
- Vatican Chinese community business crime security immigration
- 梵蒂冈 论坛 峰会 体育 青年 环保 NGO 文化交流
- 梵蒂冈 军事 安全 公卫 医疗 华人 华侨 社区

### ── 对华舆情与风险信号 ────────────────────────────────────────

- Vatican China protest xenophobia rejection invasion Chinese company conflict
- Vatican Chinese community crime insecurity persecution historical apology
- 梵蒂冈 中国 抗议 排斥 仇外 冲突 安全 风险 华人 迫害

### ── 国别专项补充查询 ────────────────────────────────────────

- Vatican China provisional agreement bishop renewal 2024 2025
- Vatican Taiwan Holy See recognition diplomatic last Europe
- Vatican Pope Francis China policy religious persecution Uyghur
- Vaticano Cina accordo provvisorio vescovi Taiwan relazioni

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

1. 梵蒂冈与台湾（外交 / 教育文化 / 公卫 / 体育 / 环保碳权 / ICDF）
2. 梵蒂冈与中国（外交经贸 / 港口矿能 / 中资企业 / 华人社区）
3. 梵蒂冈与美国（外交安全 / 经贸关税 / USAID / 军事）
4. 对华舆情（排华情绪 / 中资企业冲突 / 华人安全 / 历史迫害 / 社区摩擦）
