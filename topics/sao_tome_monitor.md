---
name: 圣多美和普林西比动态监测
countries: [st]
watch_countries: [tw, cn, us]
search_global: true
skip_sources: [newsdata_io, serpapi_google]
languages: [pt, en, zh, fr]
time_range_hours: 168
time_mode: last_week
max_articles: 20
enabled: true
---

# 圣多美和普林西比动态监测

2016年与台湾断交转与中国建交；非洲唯一葡语岛国；石油开发；中非合作论坛

涵盖12个主题维度：外交政治 / 经贸投资 / 港口航运 / 矿产能源 / 教育文化 /
公卫医疗 / NGO论坛展会 / 体育青年 / 环保气候碳权 / 军事安全 / LGBT政策 / 当地华人社区

查询语言：葡语 + 中文 + 英文（三语并行，SerpAPI/NewsData 各语言独立命中）
台湾侧深挖：mofa.gov.tw / icdf.org.tw / cna.com.tw（site: 查询，SerpAPI 有效，NewsData 跳过）

## 搜索查询

### ── 关系线1：圣多美和普林西比 × 中国 ────────────────────────────────────────

- China Sao Tome and Principe investimento comércio acordo diplomacia
- China Sao Tome and Principe porto mineração energia infraestrutura
- Sao Tome and Principe empresa chinesa infraestrutura projeto contrato
- 圣多美和普林西比 中国 投资 贸易 合作 外交 协议
- 圣多美和普林西比 中国 港口 矿产 能源 基础设施 企业
- Sao Tome and Principe China trade investment agreement diplomacy

### ── 关系线2：圣多美和普林西比 × 美国 ────────────────────────────────────────

- "Estados Unidos" Sao Tome and Principe acordo segurança cooperação defesa
- Sao Tome and Principe EUA tarifa comércio segurança acordo
- 圣多美和普林西比 美国 协议 安全 贸易 关税 援助 合作
- Sao Tome and Principe "United States" USAID agreement security trade tariff

### ── 关系线3：圣多美和普林西比 × 台湾 ────────────────────────────────────────

- Taiwan Sao Tome and Principe diplomacia visita ministro cooperação
- Taiwan Sao Tome and Principe ICDF bolsas educação saúde cooperação
- 圣多美和普林西比 台湾 外交 访问 合作 奖学金 医疗 部长
- Taiwan Sao Tome and Principe carbon credits reforestation REDD forest hectares
- 圣多美和普林西比 台湾 碳权 碳信用 造林 公顷 森林 合作

### ── 关系线3附：台湾侧主动发布（.tw 域名深挖）────────────────────────────
# site: 查询在 SerpAPI/Google 生效；NewsData.io 不支持 site: 语法，返回空（无副作用）
# 覆盖：台湾外交部(MOFA) / ICDF国际合作基金 / 中央社(CNA)

- site:mofa.gov.tw "Sao Tome and Principe"
- site:icdf.org.tw "Sao Tome and Principe"
- site:cna.com.tw "Sao Tome and Principe"
- 圣多美和普林西比 台湾 外交部 ICDF 声明 合作 公告 计划

### ── 跨议题（三条关系线共用）────────────────────────────────────────

- Sao Tome and Principe fórum cúpula ONG organização evento internacional
- Sao Tome and Principe mudança climática carbono meio ambiente acordo política
- Sao Tome and Principe esporte intercâmbio cultural juventude cooperação
- Sao Tome and Principe saúde pública cooperação médica doação hospital IA
- Sao Tome and Principe cooperação militar segurança defesa armamento acordo
- Sao Tome and Principe comunidade chinesa empresa crime segurança imigração
- 圣多美和普林西比 论坛 峰会 体育 青年 环保 NGO 文化交流
- 圣多美和普林西比 军事 安全 公卫 医疗 华人 华侨 社区

### ── 对华舆情与风险信号 ────────────────────────────────────────

- Sao Tome and Principe China protesto xenofobia rejeição invasão empresa chinesa conflito
- Sao Tome and Principe comunidade chinesa crime insegurança perseguição histórica desculpa
- 圣多美和普林西比 中国 抗议 排斥 仇外 冲突 安全 风险 华人 迫害

### ── 国别专项补充查询 ────────────────────────────────────────

- São Tomé China petróleo cooperação investimento África
- São Tomé Taiwan ruptura consequências projetos

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

1. 圣多美和普林西比与台湾（外交 / 教育文化 / 公卫 / 体育 / 环保碳权 / ICDF）
2. 圣多美和普林西比与中国（外交经贸 / 港口矿能 / 中资企业 / 华人社区）
3. 圣多美和普林西比与美国（外交安全 / 经贸关税 / USAID / 军事）
4. 对华舆情（排华情绪 / 中资企业冲突 / 华人安全 / 历史迫害 / 社区摩擦）
