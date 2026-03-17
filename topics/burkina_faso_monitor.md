---
name: 布基纳法索动态监测
countries: [bf]
watch_countries: [tw, cn, us]
search_global: true
skip_sources: [newsdata_io, serpapi_google]
languages: [fr, en, zh]
time_range_hours: 168
time_mode: last_week
max_articles: 20
enabled: true
---

# 布基纳法索动态监测

2018年与台湾断交转与中国建交；2022年军事政变；瓦格纳/俄罗斯/中国影响扩张；法国/美国基地撤出

涵盖12个主题维度：外交政治 / 经贸投资 / 港口航运 / 矿产能源 / 教育文化 /
公卫医疗 / NGO论坛展会 / 体育青年 / 环保气候碳权 / 军事安全 / LGBT政策 / 当地华人社区

查询语言：法语 + 中文 + 英文（三语并行，SerpAPI/NewsData 各语言独立命中）
台湾侧深挖：mofa.gov.tw / icdf.org.tw / cna.com.tw（site: 查询，SerpAPI 有效，NewsData 跳过）

## 搜索查询

### ── 关系线1：布基纳法索 × 中国 ────────────────────────────────────────

- Chine Burkina Faso investissement commerce accord diplomatie
- Chine Burkina Faso port exploitation minerais énergie infrastructure
- Burkina Faso entreprise chinoise infrastructure projet contrat
- 布基纳法索 中国 投资 贸易 合作 外交 协议
- 布基纳法索 中国 港口 矿产 能源 基础设施 企业
- Burkina Faso China trade investment agreement diplomacy

### ── 关系线2：布基纳法索 × 美国 ────────────────────────────────────────

- "États-Unis" Burkina Faso accord sécurité coopération défense
- Burkina Faso USA aide sanctions accord commerce
- 布基纳法索 美国 协议 安全 贸易 关税 援助 合作
- Burkina Faso "United States" USAID agreement security cooperation

### ── 关系线3：布基纳法索 × 台湾 ────────────────────────────────────────

- Taïwan Burkina Faso diplomatie visite ministre coopération
- Taïwan Burkina Faso ICDF bourses éducation santé coopération
- 布基纳法索 台湾 外交 访问 合作 奖学金 医疗 部长
- Taiwan Burkina Faso carbon credits reforestation REDD forest hectares
- 布基纳法索 台湾 碳权 碳信用 造林 公顷 森林 合作

### ── 关系线3附：台湾侧主动发布（.tw 域名深挖）────────────────────────────
# site: 查询在 SerpAPI/Google 生效；NewsData.io 不支持 site: 语法，返回空（无副作用）
# 覆盖：台湾外交部(MOFA) / ICDF国际合作基金 / 中央社(CNA)

- site:mofa.gov.tw "Burkina Faso"
- site:icdf.org.tw "Burkina Faso"
- site:cna.com.tw "Burkina Faso"
- 布基纳法索 台湾 外交部 ICDF 声明 合作 公告 计划

### ── 跨议题（三条关系线共用）────────────────────────────────────────

- Burkina Faso forum sommet ONG organisation événement international
- Burkina Faso changement climatique carbone environnement accord politique
- Burkina Faso sport échange culturel jeunesse coopération
- Burkina Faso santé publique coopération médicale don hôpital IA
- Burkina Faso coopération militaire sécurité défense armement accord
- Burkina Faso communauté chinoise entreprise crime sécurité immigration
- 布基纳法索 论坛 峰会 体育 青年 环保 NGO 文化交流
- 布基纳法索 军事 安全 公卫 医疗 华人 华侨 社区

### ── 对华舆情与风险信号 ────────────────────────────────────────

- Burkina Faso Chine protestation xénophobie rejet invasion entreprise chinoise conflit
- Burkina Faso communauté chinoise crime insécurité persécution historique excuse
- 布基纳法索 中国 抗议 排斥 仇外 冲突 安全 风险 华人 迫害

### ── 国别专项补充查询 ────────────────────────────────────────

- Burkina Faso AES Alliance Sahel Russie Wagner Chine sécurité
- Burkina Faso France États-Unis base militaire retrait
- Burkina Faso Taïwan rupture Chine reconnaissance conséquences

## 排除关键词

- résultats
- classement
- but
- divertissement
- célébrité
- football
- baseball
- WBC
- sondage
- enquête

## 检测结果分类

1. 布基纳法索与台湾（外交 / 教育文化 / 公卫 / 体育 / 环保碳权 / ICDF）
2. 布基纳法索与中国（外交经贸 / 港口矿能 / 中资企业 / 华人社区）
3. 布基纳法索与美国（外交安全 / 经贸关税 / USAID / 军事）
4. 对华舆情（排华情绪 / 中资企业冲突 / 华人安全 / 历史迫害 / 社区摩擦）
