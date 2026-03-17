---
name: 哥伦比亚动态监测
countries: [co]
watch_countries: [tw, cn, us]
search_global: true
skip_sources: [newsdata_io, serpapi_google]
languages: [es, en, zh, pt]
time_range_hours: 168
time_mode: last_week
max_articles: 20
enabled: true
---

# 哥伦比亚动态监测

重点关注：布埃纳文图拉港口中国投资、彼得罗政府对华/对美立场、毒品战争与美国反制

涵盖12个主题维度：外交政治 / 经贸投资 / 港口航运 / 矿产能源 / 教育文化 /
公卫医疗 / NGO论坛展会 / 体育青年 / 环保气候碳权 / 军事安全 / LGBT政策 / 当地华人社区

查询语言：西班牙语 + 中文 + 英文（三语并行，SerpAPI/NewsData 各语言独立命中）
台湾侧深挖：mofa.gov.tw / icdf.org.tw / cna.com.tw（site: 查询，SerpAPI 有效，NewsData 跳过）

## 搜索查询

### ── 关系线1：哥伦比亚 × 中国 ────────────────────────────────────────

- China Colombia inversión comercio acuerdo diplomacia
- China Colombia puerto minería energía infraestructura
- Colombia empresa china infraestructura proyecto contrato
- 哥伦比亚 中国 投资 贸易 合作 外交 协议
- 哥伦比亚 中国 港口 矿产 能源 基础设施 企业
- Colombia China trade investment agreement diplomacy

### ── 关系线2：哥伦比亚 × 美国 ────────────────────────────────────────

- "Estados Unidos" Colombia acuerdo seguridad cooperación defensa
- Colombia EE.UU. arancel tarifa comercio suministro cadena
- 哥伦比亚 美国 协议 安全 贸易 关税 援助 合作
- Colombia "United States" USAID agreement security trade tariff

### ── 关系线3：哥伦比亚 × 台湾 ────────────────────────────────────────

- Taiwan Colombia diplomacia visita ministro congreso cooperación
- Taiwan Colombia ICDF becas educación salud cooperación
- 哥伦比亚 台湾 外交 访问 合作 奖学金 医疗 部长
- Taiwan Colombia carbon credits reforestation REDD forest hectares
- 哥伦比亚 台湾 碳权 碳信用 造林 公顷 森林 合作

### ── 关系线3附：台湾侧主动发布（.tw 域名深挖）────────────────────────────
# site: 查询在 SerpAPI/Google 生效；NewsData.io 不支持 site: 语法，返回空（无副作用）
# 覆盖：台湾外交部(MOFA) / ICDF国际合作基金 / 中央社(CNA)

- site:mofa.gov.tw "Colombia"
- site:icdf.org.tw "Colombia"
- site:cna.com.tw "Colombia"
- 哥伦比亚 台湾 外交部 ICDF 声明 合作 公告 计划

### ── 跨议题（三条关系线共用）────────────────────────────────────────

- Colombia foro cumbre ONG organización evento internacional
- Colombia cambio climático carbono medio ambiente acuerdo política
- Colombia deporte intercambio cultural juventud cooperación
- Colombia salud pública cooperación médica donación hospital IA
- Colombia cooperación militar seguridad defensa armamento acuerdo
- Colombia comunidad china empresa crimen seguridad inmigrante
- 哥伦比亚 论坛 峰会 体育 青年 环保 NGO 文化交流
- 哥伦比亚 军事 安全 公卫 医疗 华人 华侨 社区

### ── 对华舆情与风险信号 ────────────────────────────────────────

- Colombia China protesta xenofobia rechazo invasión empresa china conflicto
- Colombia comunidad china crimen inseguridad persecución histórica disculpa
- 哥伦比亚 中国 抗议 排斥 仇外 冲突 安全 风险 华人 迫害

### ── 国别专项补充查询 ────────────────────────────────────────

- Colombia Buenaventura puerto China empresa inversión
- Colombia Petro China EE.UU. política exterior diplomacia

## 排除关键词

- resultados
- clasificación
- gol
- marcador
- entretenimiento
- farándula
- espectáculo
- telenovela
- beisbol
- baseball
- WBC
- fútbol
- football
- encuesta
- sondeo

## 检测结果分类

1. 哥伦比亚与台湾（外交 / 教育文化 / 公卫 / 体育 / 环保碳权 / ICDF）
2. 哥伦比亚与中国（外交经贸 / 港口矿能 / 中资企业 / 华人社区）
3. 哥伦比亚与美国（外交安全 / 经贸关税 / USAID / 军事）
4. 对华舆情（排华情绪 / 中资企业冲突 / 华人安全 / 历史迫害 / 社区摩擦）
