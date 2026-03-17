---
name: 秘鲁动态监测
countries: [pe]
watch_countries: [tw, cn, us]
search_global: true
skip_sources: [newsdata_io, serpapi_google]
languages: [es, en, zh, pt]
time_range_hours: 168
time_mode: last_week
max_articles: 20
enabled: true
---

# 秘鲁动态监测

重点关注：钱凯港（中国国有企业建设，2024年开港）、中国矿业投资（铜/银/锌）

涵盖12个主题维度：外交政治 / 经贸投资 / 港口航运 / 矿产能源 / 教育文化 /
公卫医疗 / NGO论坛展会 / 体育青年 / 环保气候碳权 / 军事安全 / LGBT政策 / 当地华人社区

查询语言：西班牙语 + 中文 + 英文（三语并行，SerpAPI/NewsData 各语言独立命中）
台湾侧深挖：mofa.gov.tw / icdf.org.tw / cna.com.tw（site: 查询，SerpAPI 有效，NewsData 跳过）

## 搜索查询

### ── 关系线1：秘鲁 × 中国 ────────────────────────────────────────

- China Peru inversión comercio acuerdo diplomacia
- China Peru puerto minería energía infraestructura
- Peru empresa china infraestructura proyecto contrato
- 秘鲁 中国 投资 贸易 合作 外交 协议
- 秘鲁 中国 港口 矿产 能源 基础设施 企业
- Peru China trade investment agreement diplomacy

### ── 关系线2：秘鲁 × 美国 ────────────────────────────────────────

- "Estados Unidos" Peru acuerdo seguridad cooperación defensa
- Peru EE.UU. arancel tarifa comercio suministro cadena
- 秘鲁 美国 协议 安全 贸易 关税 援助 合作
- Peru "United States" USAID agreement security trade tariff

### ── 关系线3：秘鲁 × 台湾 ────────────────────────────────────────

- Taiwan Peru diplomacia visita ministro congreso cooperación
- Taiwan Peru ICDF becas educación salud cooperación
- 秘鲁 台湾 外交 访问 合作 奖学金 医疗 部长
- Taiwan Peru carbon credits reforestation REDD forest hectares
- 秘鲁 台湾 碳权 碳信用 造林 公顷 森林 合作

### ── 关系线3附：台湾侧主动发布（.tw 域名深挖）────────────────────────────
# site: 查询在 SerpAPI/Google 生效；NewsData.io 不支持 site: 语法，返回空（无副作用）
# 覆盖：台湾外交部(MOFA) / ICDF国际合作基金 / 中央社(CNA)

- site:mofa.gov.tw "Peru"
- site:icdf.org.tw "Peru"
- site:cna.com.tw "Peru"
- 秘鲁 台湾 外交部 ICDF 声明 合作 公告 计划

### ── 跨议题（三条关系线共用）────────────────────────────────────────

- Peru foro cumbre ONG organización evento internacional
- Peru cambio climático carbono medio ambiente acuerdo política
- Peru deporte intercambio cultural juventud cooperación
- Peru salud pública cooperación médica donación hospital IA
- Peru cooperación militar seguridad defensa armamento acuerdo
- Peru comunidad china empresa crimen seguridad inmigrante
- 秘鲁 论坛 峰会 体育 青年 环保 NGO 文化交流
- 秘鲁 军事 安全 公卫 医疗 华人 华侨 社区

### ── 对华舆情与风险信号 ────────────────────────────────────────

- Peru China protesta xenofobia rechazo invasión empresa china conflicto
- Peru comunidad china crimen inseguridad persecución histórica disculpa
- 秘鲁 中国 抗议 排斥 仇外 冲突 安全 风险 华人 迫害

### ── 国别专项补充查询 ────────────────────────────────────────

- Peru Chancay puerto China COSCO megaproyecto
- Peru cobre plata zinc minería China empresa inversión

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

1. 秘鲁与台湾（外交 / 教育文化 / 公卫 / 体育 / 环保碳权 / ICDF）
2. 秘鲁与中国（外交经贸 / 港口矿能 / 中资企业 / 华人社区）
3. 秘鲁与美国（外交安全 / 经贸关税 / USAID / 军事）
4. 对华舆情（排华情绪 / 中资企业冲突 / 华人安全 / 历史迫害 / 社区摩擦）
