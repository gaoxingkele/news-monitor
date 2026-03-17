---
name: 委内瑞拉动态监测
countries: [ve]
watch_countries: [tw, cn, us]
search_global: true
skip_sources: [newsdata_io, serpapi_google]
languages: [es, en, zh, pt]
time_range_hours: 168
time_mode: last_week
max_articles: 20
enabled: true
---

# 委内瑞拉动态监测

重点关注：中国石油贷款（以油还债）、美国制裁与中国规避、马杜罗政府外交立场

涵盖12个主题维度：外交政治 / 经贸投资 / 港口航运 / 矿产能源 / 教育文化 /
公卫医疗 / NGO论坛展会 / 体育青年 / 环保气候碳权 / 军事安全 / LGBT政策 / 当地华人社区

查询语言：西班牙语 + 中文 + 英文（三语并行，SerpAPI/NewsData 各语言独立命中）
台湾侧深挖：mofa.gov.tw / icdf.org.tw / cna.com.tw（site: 查询，SerpAPI 有效，NewsData 跳过）

## 搜索查询

### ── 关系线1：委内瑞拉 × 中国 ────────────────────────────────────────

- China Venezuela inversión comercio acuerdo diplomacia
- China Venezuela puerto minería energía infraestructura
- Venezuela empresa china infraestructura proyecto contrato
- 委内瑞拉 中国 投资 贸易 合作 外交 协议
- 委内瑞拉 中国 港口 矿产 能源 基础设施 企业
- Venezuela China trade investment agreement diplomacy

### ── 关系线2：委内瑞拉 × 美国 ────────────────────────────────────────

- "Estados Unidos" Venezuela acuerdo seguridad cooperación defensa
- Venezuela EE.UU. arancel tarifa comercio suministro cadena
- 委内瑞拉 美国 协议 安全 贸易 关税 援助 合作
- Venezuela "United States" USAID agreement security trade tariff

### ── 关系线3：委内瑞拉 × 台湾 ────────────────────────────────────────

- Taiwan Venezuela diplomacia visita ministro congreso cooperación
- Taiwan Venezuela ICDF becas educación salud cooperación
- 委内瑞拉 台湾 外交 访问 合作 奖学金 医疗 部长
- Taiwan Venezuela carbon credits reforestation REDD forest hectares
- 委内瑞拉 台湾 碳权 碳信用 造林 公顷 森林 合作

### ── 关系线3附：台湾侧主动发布（.tw 域名深挖）────────────────────────────
# site: 查询在 SerpAPI/Google 生效；NewsData.io 不支持 site: 语法，返回空（无副作用）
# 覆盖：台湾外交部(MOFA) / ICDF国际合作基金 / 中央社(CNA)

- site:mofa.gov.tw "Venezuela"
- site:icdf.org.tw "Venezuela"
- site:cna.com.tw "Venezuela"
- 委内瑞拉 台湾 外交部 ICDF 声明 合作 公告 计划

### ── 跨议题（三条关系线共用）────────────────────────────────────────

- Venezuela foro cumbre ONG organización evento internacional
- Venezuela cambio climático carbono medio ambiente acuerdo política
- Venezuela deporte intercambio cultural juventud cooperación
- Venezuela salud pública cooperación médica donación hospital IA
- Venezuela cooperación militar seguridad defensa armamento acuerdo
- Venezuela comunidad china empresa crimen seguridad inmigrante
- 委内瑞拉 论坛 峰会 体育 青年 环保 NGO 文化交流
- 委内瑞拉 军事 安全 公卫 医疗 华人 华侨 社区

### ── 对华舆情与风险信号 ────────────────────────────────────────

- Venezuela China protesta xenofobia rechazo invasión empresa china conflicto
- Venezuela comunidad china crimen inseguridad persecución histórica disculpa
- 委内瑞拉 中国 抗议 排斥 仇外 冲突 安全 风险 华人 迫害

### ── 国别专项补充查询 ────────────────────────────────────────

- Venezuela China petróleo deuda préstamo PDVSA acuerdo
- Venezuela sanciones EE.UU. China Maduro relaciones

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

1. 委内瑞拉与台湾（外交 / 教育文化 / 公卫 / 体育 / 环保碳权 / ICDF）
2. 委内瑞拉与中国（外交经贸 / 港口矿能 / 中资企业 / 华人社区）
3. 委内瑞拉与美国（外交安全 / 经贸关税 / USAID / 军事）
4. 对华舆情（排华情绪 / 中资企业冲突 / 华人安全 / 历史迫害 / 社区摩擦）
