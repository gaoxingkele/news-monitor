---
name: 巴西动态监测
countries: [br]
watch_countries: [tw, cn, us]
search_global: true
skip_sources: [newsdata_io, serpapi_google]
languages: [pt, es, en, zh]
time_range_hours: 168
time_mode: last_week
max_articles: 20
enabled: true
---

# 巴西动态监测

重点关注：BRI成员国讨论、华为5G争议、中国最大贸易伙伴（大豆/铁矿石）、庞大华人社区

涵盖12个主题维度：外交政治 / 经贸投资 / 港口航运 / 矿产能源 / 教育文化 /
公卫医疗 / NGO论坛展会 / 体育青年 / 环保气候碳权 / 军事安全 / LGBT政策 / 当地华人社区

查询语言：葡语 + 中文 + 英文（三语并行，SerpAPI/NewsData 各语言独立命中）
台湾侧深挖：mofa.gov.tw / icdf.org.tw / cna.com.tw（site: 查询，SerpAPI 有效，NewsData 跳过）

## 搜索查询

### ── 关系线1：巴西 × 中国 ────────────────────────────────────────

- China Brazil investimento comércio acordo diplomacia
- China Brazil porto mineração energia infraestrutura
- Brazil empresa chinesa infraestrutura projeto contrato
- 巴西 中国 投资 贸易 合作 外交 协议
- 巴西 中国 港口 矿产 能源 基础设施 企业
- Brazil China trade investment agreement diplomacy

### ── 关系线2：巴西 × 美国 ────────────────────────────────────────

- "Estados Unidos" Brazil acordo segurança cooperação defesa
- Brazil EUA tarifa comércio segurança acordo
- 巴西 美国 协议 安全 贸易 关税 援助 合作
- Brazil "United States" USAID agreement security trade tariff

### ── 关系线3：巴西 × 台湾 ────────────────────────────────────────

- Taiwan Brazil diplomacia visita ministro cooperação
- Taiwan Brazil ICDF bolsas educação saúde cooperação
- 巴西 台湾 外交 访问 合作 奖学金 医疗 部长
- Taiwan Brazil carbon credits reforestation REDD forest hectares
- 巴西 台湾 碳权 碳信用 造林 公顷 森林 合作

### ── 关系线3附：台湾侧主动发布（.tw 域名深挖）────────────────────────────
# site: 查询在 SerpAPI/Google 生效；NewsData.io 不支持 site: 语法，返回空（无副作用）
# 覆盖：台湾外交部(MOFA) / ICDF国际合作基金 / 中央社(CNA)

- site:mofa.gov.tw "Brazil"
- site:icdf.org.tw "Brazil"
- site:cna.com.tw "Brazil"
- 巴西 台湾 外交部 ICDF 声明 合作 公告 计划

### ── 跨议题（三条关系线共用）────────────────────────────────────────

- Brazil fórum cúpula ONG organização evento internacional
- Brazil mudança climática carbono meio ambiente acordo política
- Brazil esporte intercâmbio cultural juventude cooperação
- Brazil saúde pública cooperação médica doação hospital IA
- Brazil cooperação militar segurança defesa armamento acordo
- Brazil comunidade chinesa empresa crime segurança imigração
- 巴西 论坛 峰会 体育 青年 环保 NGO 文化交流
- 巴西 军事 安全 公卫 医疗 华人 华侨 社区

### ── 对华舆情与风险信号 ────────────────────────────────────────

- Brazil China protesto xenofobia rejeição invasão empresa chinesa conflito
- Brazil comunidade chinesa crime insegurança perseguição histórica desculpa
- 巴西 中国 抗议 排斥 仇外 冲突 安全 风险 华人 迫害

### ── 国别专项补充查询 ────────────────────────────────────────

- China Brasil mineração ferro soja comércio energia
- Brasil China Huawei 5G tecnologia investimento
- Brasil EE.UU. China multipolaridade política exterior

## 排除关键词

- resultados
- classificação
- gol
- entretenimento
- celebridade
- espetáculo
- futebol
- football
- beisebol
- WBC
- pesquisa
- sondagem

## 检测结果分类

1. 巴西与台湾（外交 / 教育文化 / 公卫 / 体育 / 环保碳权 / ICDF）
2. 巴西与中国（外交经贸 / 港口矿能 / 中资企业 / 华人社区）
3. 巴西与美国（外交安全 / 经贸关税 / USAID / 军事）
4. 对华舆情（排华情绪 / 中资企业冲突 / 华人安全 / 历史迫害 / 社区摩擦）
