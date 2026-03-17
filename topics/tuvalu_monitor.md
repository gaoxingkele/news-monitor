---
name: 图瓦卢动态监测
countries: [tv]
watch_countries: [tw, cn, us]
search_global: true
skip_sources: [newsdata_io, serpapi_google]
languages: [en, zh]
time_range_hours: 168
time_mode: last_week
max_articles: 20
enabled: true
---

# 图瓦卢动态监测

⚑ 台湾邦交国；全球最小国家之一；海平面上升存亡危机；与澳大利亚Falepili联盟；太平洋岛国论坛

涵盖12个主题维度：外交政治 / 经贸投资 / 港口航运 / 矿产能源 / 教育文化 /
公卫医疗 / NGO论坛展会 / 体育青年 / 环保气候碳权 / 军事安全 / LGBT政策 / 当地华人社区

查询语言：英语 + 中文 + 英文（三语并行，SerpAPI/NewsData 各语言独立命中）
台湾侧深挖：mofa.gov.tw / icdf.org.tw / cna.com.tw（site: 查询，SerpAPI 有效，NewsData 跳过）

## 搜索查询

### ── 关系线1：图瓦卢 × 中国 ────────────────────────────────────────

- Tuvalu China investment trade agreement diplomacy
- Tuvalu China port mining energy infrastructure project
- Tuvalu Chinese company infrastructure contract construction
- 图瓦卢 中国 投资 贸易 合作 外交 协议
- 图瓦卢 中国 港口 矿产 能源 基础设施 企业
- Tuvalu China bilateral relations cooperation security

### ── 关系线2：图瓦卢 × 美国 ────────────────────────────────────────

- Tuvalu United States agreement security cooperation defense
- Tuvalu US USAID aid trade agreement sanctions
- 图瓦卢 美国 协议 安全 贸易 关税 援助 合作
- Tuvalu US Pacific strategy security competition China

### ── 关系线3：图瓦卢 × 台湾 ────────────────────────────────────────

- Taiwan Tuvalu diplomacy visit minister cooperation
- Taiwan Tuvalu ICDF scholarship education health cooperation
- 图瓦卢 台湾 外交 访问 合作 奖学金 医疗 部长
- Taiwan Tuvalu carbon credits reforestation REDD forest hectares
- 图瓦卢 台湾 碳权 碳信用 造林 公顷 森林 合作

### ── 关系线3附：台湾侧主动发布（.tw 域名深挖）────────────────────────────
# site: 查询在 SerpAPI/Google 生效；NewsData.io 不支持 site: 语法，返回空（无副作用）
# 覆盖：台湾外交部(MOFA) / ICDF国际合作基金 / 中央社(CNA)

- site:mofa.gov.tw "Tuvalu"
- site:icdf.org.tw "Tuvalu"
- site:cna.com.tw "Tuvalu"
- 图瓦卢 台湾 外交部 ICDF 声明 合作 公告 计划

### ── 跨议题（三条关系线共用）────────────────────────────────────────

- Tuvalu forum summit NGO organization international event
- Tuvalu climate change carbon environment agreement policy
- Tuvalu sports cultural exchange youth cooperation
- Tuvalu public health medical cooperation donation hospital AI
- Tuvalu military security cooperation defense agreement
- Tuvalu Chinese community business crime security immigration
- 图瓦卢 论坛 峰会 体育 青年 环保 NGO 文化交流
- 图瓦卢 军事 安全 公卫 医疗 华人 华侨 社区

### ── 对华舆情与风险信号 ────────────────────────────────────────

- Tuvalu China protest xenophobia rejection invasion Chinese company conflict
- Tuvalu Chinese community crime insecurity persecution historical apology
- 图瓦卢 中国 抗议 排斥 仇外 冲突 安全 风险 华人 迫害

### ── 国别专项补充查询 ────────────────────────────────────────

- Tuvalu Taiwan embassy recognition diplomatic cooperation aid
- Tuvalu China pressure diplomatic switch recognition Pacific
- Tuvalu Australia Falepili Union climate sea level sinking
- Tuvalu .tv domain revenue internet digital sovereignty

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

1. 图瓦卢与台湾（外交 / 教育文化 / 公卫 / 体育 / 环保碳权 / ICDF）
2. 图瓦卢与中国（外交经贸 / 港口矿能 / 中资企业 / 华人社区）
3. 图瓦卢与美国（外交安全 / 经贸关税 / USAID / 军事）
4. 对华舆情（排华情绪 / 中资企业冲突 / 华人安全 / 历史迫害 / 社区摩擦）
