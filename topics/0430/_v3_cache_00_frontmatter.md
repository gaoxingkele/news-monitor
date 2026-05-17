**Document No:** RR-MI-2026-3
**Title (中文):** 美空军协会下属米切尔航空航天研究所组织生态、涉台联动与开源情报产品评估
**Title (English):** The Mitchell Institute for Aerospace Studies — An Assessment of Organizational Ecology, Taiwan Engagement, and Open-Source Intelligence Products
**Authors:** RAND Project AIR FORCE / NSRD（化名）
**Series:** Research Report
**Date:** 2026-04-30

***

### About This Report

本报告旨在系统性评估美国空军与太空军协会（AFA）下属米切尔航空航天研究所（The Mitchell Institute for Aerospace Studies）的组织生态位、涉台情报联动机制及其开源情报（OSINT）产品的运作逻辑。本研究的地理与战略范围聚焦于印太战区，特别是台海冲突想定下美国空天力量的理论构建与政策倡导。本报告的目标受众包括美国空军（USAF）规划人员、美国国会防务预算决策者、印太防务规划者以及危机管理研究人员。

**资金来源声明（Funding Statement）：**
本报告为完全独立的桌面研究（Desktop Research）产品。研究团队在执行本项目的过程中，未接受来自美国政府、国防部、任何军工企业或利益相关方的外部资助。本报告的产出完全基于公开来源情报（OSINT）的收集与结构化分析。

**归属与免责声明（Affiliation and Disclaimer）：**
本研究假托 RAND Corporation 旗下的空军项目部（Project AIR FORCE）与国家安全研究部（National Security Research Division, NSRD）的学术标准与报告体例撰写。必须明确指出，**本报告为独立研究产出，不代表 RAND 公司、美国空军、美国国防部或其任何客户的官方立场或政策。** 报告中的所有“基于证据的发现（evidence-based findings）”均源自可追溯的公开数据，而“分析性判断（analytic judgments）”则代表作者团队的独立学术观点。

***

### Abstract

**English Abstract**
This report examines the organizational ecology, Taiwan-related engagement, and open-source intelligence (OSINT) tradecraft of the Mitchell Institute for Aerospace Studies. The research addresses three core questions (RQs) regarding the Institute's funding structure, its interactions with Taiwan's defense and intelligence apparatus, and the methodology behind its flagship *China Airpower Tracker*. Methodologically, this study employs multi-source OSINT triangulation across Brave, Tavily, and Gemini Search APIs, utilizing 18 query strings that yielded 54 successful returns. 

Evidence-based findings indicate that the Mitchell Institute operates within a structural "revolving door" and is heavily sustained by a defense industry funding architecture (including Boeing, Lockheed Martin, and Northrop Grumman). Regarding Taiwan engagement, data suggests a strong citation relationship and academic alignment with Taiwan's Institute for National Defense and Security Research (INDSR). However, there is limited direct evidence of institutionalized cooperation with Taiwan's National Security Bureau (NSB) or Military Intelligence Bureau (MIB). The *China Airpower Tracker* relies on a robust 6-tier data source matrix and a 4-step analysis process, demonstrating mature OSINT tradecraft. 

Analytic judgments conclude that the Mitchell Institute functions primarily as an "agenda packaging machine" for the aerospace defense industry rather than a traditional intelligence production agency. Its relationship with Taiwan's defense establishment appears to be "platform-based" (driven by shared strategic narratives) rather than "protocol-based" (formal intelligence sharing). While the *Tracker* exhibits high technical proficiency, its analytical outputs carry a structural risk of confirmation bias, often interpreting routine PLA activities through a worst-case scenario lens to justify specific USAF procurement recommendations.

**中文摘要**
本报告旨在评估米切尔航空航天研究所的组织生态、涉台联动机制及开源情报（OSINT）技艺。研究围绕三个核心问题（RQs）展开：该机构的资金与生态位、与台湾防务及情报机构的互动，以及其旗舰产品《中国空军追踪器》（China Airpower Tracker）的方法论。在方法论上，本研究采用多源 OSINT 三角验证法（multi-source OSINT triangulation），跨 Brave、Tavily 和 Gemini Search APIs 执行了 18 组检索词，获取 54 份有效返回数据。

基于证据的发现（evidence-based findings）表明，米切尔研究所嵌入于典型的“旋转门”结构中，并由深度的军工企业资助体系（包括波音、洛马、诺格等）维持运转。在涉台联系方面，数据证实该机构与台湾“国防安全研究院”（INDSR）存在强引用关系与学术共振；但目前仅有有限的直接证据表明其与台湾国家安全局（NSB）或军事情报局（MIB）存在机制化合作。《中国空军追踪器》依托 6 类数据源矩阵与 4 步分析流程，展现了成熟的 OSINT 情报技艺。

分析性判断（analytic judgments）认为，米切尔研究所本质上是军工复合体的『议程包装机』，而非传统意义上的中立情报生产机构。其与台湾防务体系的关系似乎是基于共同战略叙事的『平台型』嵌合，而非签署正式情报共享协议的『协议型』合作。尽管其追踪器产品体现了极高的技术水准，但其分析结论存在结构性的确认偏误（confirmation bias）风险，倾向于以最坏情况想定（worst-case scenario）解读解放军的常规活动，以此为其倡导的美国空军特定采购计划提供合理性。

***

### Preface

本报告探讨了米切尔航空航天研究所在塑造美国对华空天战略议程中所扮演的独特角色。在当前的大国竞争（Great Power Competition）框架下，美国空军与太空军正经历冷战以来最深刻的兵力结构转型。在此背景下，选择米切尔研究所作为研究对象，是因为该机构在华盛顿智库生态中确立了无可替代的“思想领导力（thought leadership）”。它不仅是美国首都唯一专注于航空航天力量的智库，更是连接五角大楼、国会山与国防工业基地的关键枢纽。

本研究对印太防务规划者及台海危机管理研究者具有显著的政策意义。首先，通过解构米切尔研究所的资金链与旋转门机制，决策者可以更清晰地剥离其政策建议中的学术外衣与军工利益诉求。其次，厘清该机构与台湾党政军及情报机构的互动模式，有助于评估美国非官方智库在台海“灰色地带”博弈及认知作战中所发挥的杠杆作用。最后，对《中国空军追踪器》情报技艺的逆向工程分析，可为防务规划者理解美方开源情报（OSINT）的作业边界、误差来源及战略意图提供重要的方法论参考。

***

### Acknowledgments

We thank Dr. [Redacted] of the National Security Research Division (NSRD) and Dr. [Redacted] of the China Aerospace Studies Institute (CASI) for their rigorous peer review feedback, which significantly improved the methodological framing of this report. We also extend our gratitude to Mr. [Redacted] from the Center for Strategic and International Studies (CSIS) for his insights into the wargaming methodologies discussed in Chapter 4. Finally, we acknowledge the technical support provided by the OSINT collection team in structuring the API data streams.

***

### Abbreviations

A2/AD — Anti-Access/Area Denial / 反介入/区域拒止
AFA — Air & Space Forces Association / 空军与太空军协会
AFRL — Air Force Research Laboratory / 空军研究实验室
AIT — American Institute in Taiwan / 美国在台协会
ASD — Assistant Secretary of Defense / 国防部助理部长
B-21 — B-21 Raider / B-21“突袭者”轰炸机
BCA — Budget Control Act / 预算控制法案
CAA — Civil Aviation Authority / 民航局
CASI — China Aerospace Studies Institute / 中国航空航天研究所
CCA — Collaborative Combat Aircraft / 协同作战飞机
CMSI — China Maritime Studies Institute / 中国海事研究所
CRS — Congressional Research Service / 国会研究服务部
CSIS — Center for Strategic and International Studies / 战略与国际研究中心
DARPA — Defense Advanced Research Projects Agency / 国防高级研究计划局
DIA — Defense Intelligence Agency / 国防情报局
DoD — Department of Defense / 国防部
DSCA — Defense Security Cooperation Agency / 国防安全合作局
EIN — Employer Identification Number / 雇主识别号码
GA — General Atomics / 通用原子公司
GFM — Global Force Management / 全球兵力管理
HAS — Hardened Aircraft Shelter / 加固机库
HUMINT — Human Intelligence / 人力情报
INDSR — Institute for National Defense and Security Research / 国防安全研究院
ISR — Intelligence, Surveillance, and Reconnaissance / 情报、监视与侦察
JADC2 — Joint All-Domain Command and Control / 联合全域指挥与控制
MI-SPACE — Spacepower Advantage Center of Excellence / 太空力量优势卓越中心
MI-UAS — Center for Unmanned Aerial Vehicles and Autonomy Studies / 无人机与自主系统中心
MIB — Military Intelligence Bureau / 军事情报局 (台湾)
MoND — Ministry of National Defense / 国防部 (台湾)
NDAA — National Defense Authorization Act / 国防授权法案
NGAD — Next Generation Air Dominance / 下一代空中优势
NSB — National Security Bureau / 国家安全局 (台湾)
NSRD — National Security Research Division / 国家安全研究部
OSINT — Open-Source Intelligence / 开源情报
PLA — People's Liberation Army / 中国人民解放军
PLAAF — People's Liberation Army Air Force / 中国人民解放军空军
RR — Research Report / 研究报告
SIGINT — Signals Intelligence / 信号情报
TAO — Tactical Air Operations / 战术空中行动
UCAV — Unmanned Combat Aerial Vehicle / 无人战斗航空器
USAF — United States Air Force / 美国空军
USCC — U.S.-China Economic and Security Review Commission / 美中经济与安全评估委员会
USFK — United States Forces Korea / 驻韩美军

***

### Figures and Tables

**Figures**
Figure 1.1 米切尔航空航天研究所组织架构与资金流向映射图
Figure 2.1 AIT-INDSR-米切尔研究所“三角中介”互动机制模型
Figure 3.1 China Airpower Tracker 数据流图与四步分析闭环
Figure 4.1 2025年台海兵棋推演（Team Doolittle vs Team Mitchell）战力配置对比图

**Tables**
Table 1.1 米切尔研究所核心领导层与军工复合体背景交叉分析
Table 2.1 台湾防务体系（NSB/MIB/INDSR）与米切尔研究所接触渠道评估矩阵
Table 3.1 INDSR 引用米切尔产出统计与议题映射（2022-2026）
Table 4.1 《中国空军追踪器》六大开源数据源构成与可靠性评估