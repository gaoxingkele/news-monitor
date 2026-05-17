---
name: {{国家}}动态监测
countries: [{{country_code}}]
# watch_countries: 除本地外额外抓取的国家视角（与 countries 合并为一次请求）
watch_countries: [tw, cn, us]
# search_global: true → 额外再跑一次全网搜索（不限国家）
search_global: true
# skip_sources: 本 topic 跳过的数据源
skip_sources: [newsapi_ai]
# es: 西班牙语（本地主语）  en: 英语（国际报道）
# zh: 简繁中文（中文媒体，API 不区分）  pt: 葡语（巴西/区域媒体）
languages: [es, en, zh, pt]
time_range_hours: 168
time_mode: last_week
max_articles: 20
enabled: true
---

# {{国家}}动态监测

监测{{国家}}与中国、美国、台湾三条关系线上的"新动作 / 新进展 / 新表态"。
只收官方/半官方/主流媒体报道的可核验事实，不收纯背景科普与历史综述。

关注12个主题维度（任一维度有新进展即收录）：
外交政治 / 经贸投资 / 港口航运 / 矿产能源 / 教育文化 /
公共卫生医疗 / NGO论坛展会 / 体育青年 / 环保气候碳权 /
军事安全 / LGBT政策 / 当地华人社区

查询语言：本地语 + 中文 + 英文（三语并行，SerpAPI/NewsData 各语言独立命中）
台湾侧深挖：mofa.gov.tw / icdf.org.tw / cna.com.tw（site: 查询，SerpAPI 有效，NewsData 跳过）

## 搜索查询

### ── 关系线1：{{国家}} × 中国 ────────────────────────────────────────

# 经贸 / 外交（西班牙语）
- China {{Country}} inversión comercio acuerdo diplomacia
# 港口 / 矿产 / 能源（西班牙语）
- China {{Country}} puerto minería energía litio cobre
# 中资企业 / 基础设施（西班牙语）
- {{Country}} empresa china infraestructura proyecto contrato
# 经贸 / 外交（中文）
- {{国家}} 中国 投资 贸易 合作 外交 协议
# 港口 / 矿产 / 能源（中文）
- {{国家}} 中国 港口 矿产 能源 基础设施 企业
# 经贸 / 外交（英文）
- {{Country}} China trade investment agreement diplomacy

### ── 关系线2：{{国家}} × 美国 ────────────────────────────────────────

# 外交 / 安全 / 协议（西班牙语）
- "Estados Unidos" {{Country}} acuerdo seguridad cooperación defensa
# 关税 / 贸易 / 供应链（西班牙语）
- {{Country}} EE.UU. arancel tarifa comercio suministro cadena
# 外交 / 安全 / 援助（中文）
- {{国家}} 美国 协议 安全 贸易 关税 援助 合作
# 外交 / 安全 / 援助（英文）
- {{Country}} "United States" USAID agreement security trade tariff

### ── 关系线3：{{国家}} × 台湾 ────────────────────────────────────────

# 外交访问 / 部长 / 国会（西班牙语）
- Taiwan {{Country}} diplomacia visita ministro congreso cooperación
# ICDF / 教育 / 医疗 / 奖学金（西班牙语）
- Taiwan {{Country}} ICDF becas educación salud cooperación
# 外交 / 合作 / 奖学金（中文）
- {{国家}} 台湾 外交 访问 合作 奖学金 医疗 部长
# 碳权 / 造林 / 碳信用（三语均可命中，台湾重点项目）
- Taiwan {{Country}} carbon credits reforestation REDD forest hectares
- {{国家}} 台湾 碳权 碳信用 造林 公顷 森林 合作

### ── 关系线3附：台湾侧主动发布（.tw 域名深挖）────────────────────────────

# site: 查询在 SerpAPI/Google 生效；NewsData.io 不支持 site: 语法，返回空（无副作用）
# 覆盖：台湾外交部(MOFA) / ICDF国际合作基金 / 中央社(CNA)
- site:mofa.gov.tw "{{Country}}"
- site:icdf.org.tw "{{Country}}"
- site:cna.com.tw "{{Country}}"
- {{国家}} 台湾 外交部 ICDF 声明 合作 公告 计划

### ── 跨议题（三条关系线共用）────────────────────────────────────────

# NGO / 论坛 / 峰会 / 展会（西班牙语）
- {{Country}} foro cumbre ONG organización evento exhibición internacional
# 环保 / 气候 / 碳（西班牙语）
- {{Country}} cambio climático carbono medio ambiente acuerdo política
# 体育 / 青年 / 文化交流（西班牙语）
- {{Country}} deporte intercambio cultural juventud cooperación
# 公共卫生 / 医疗合作（西班牙语）
- {{Country}} salud pública cooperación médica donación hospital IA
# 军事 / 安全（西班牙语）
- {{Country}} cooperación militar seguridad defensa armamento acuerdo
# 当地华人社区（西班牙语）
- {{Country}} comunidad china empresa crimen seguridad inmigrante
# NGO / 论坛 / 环保 / 体育 / 青年（中文）
- {{国家}} 论坛 峰会 体育 青年 环保 NGO 文化交流
# 军事 / 安全 / 公卫 / 华人（中文）
- {{国家}} 军事 安全 公卫 医疗 华人 华侨 社区

## 排除关键词

# 体育赛事结果（保留"体育外交/合作"类新闻，只排过滤纯赛事噪音）
- resultados
- clasificación
- gol
- marcador
- campeonato liga torneo
# 娱乐/明星
- entretenimiento
- farándula
- espectáculo
- telenovela
# 棒球专项噪音（世界棒球经典赛造成大量歧义结果）
- beisbol
- baseball
- WBC
# 足球纯赛事
- fútbol
- football
# 民调/排名（非外交议题）
- encuesta
- sondeo

## 检测结果分类

LLM 翻译时自动对每篇文章分配以下 category（取最高优先级）：

| 优先级 | category 值 | 含义 |
|--------|-------------|------|
| 1（最高） | china   | 与中国有关 |
| 2       | taiwan  | 与台湾有关 |
| 3       | us      | 与美国有关 |
| 4（默认） | {{country_code}} | {{国家}}本地/其他 |

12个主题维度（摘要中标注，供人工审阅参考）：
外交政治 / 经贸投资 / 港口航运 / 矿产能源 / 教育文化 /
公卫医疗 / NGO论坛 / 体育青年 / 环保气候 / 军事安全 / LGBT / 华人社区
