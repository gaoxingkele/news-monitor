## Appendix A. Methodology and Data Source Catalog

### A.1 Research Design

本报告采用非机密桌面研究（Desk Research）与多源数据三角验证（Triangulation）相结合的研究设计。基于证据的发现（Evidence-based finding）完全依赖于公开来源情报（OSINT），不包含任何机密信息（Classified Information）、内部泄露文件或受控非保密信息（CUI）。本研究未进行任何形式的线人访谈或实地调查。分析性判断（Analytic judgment）则基于 RAND Corporation 的结构化分析技术（Structured Analytic Techniques, SATs），特别是竞争性假设分析（ACH）与模式识别，以评估米切尔航空航天研究所（Mitchell Institute for Aerospace Studies）的组织行为、资金网络及其与台湾地区防务机构的潜在互动逻辑。

### A.2 Search Strategy

为系统性回答本报告设定的三个核心研究问题（RQ1-RQ3），研究团队构建了覆盖 6 至 7 个分析维度的 18 个布尔查询（Boolean Query）字符串。数据采集执行于 2026 年 4 月 30 日。

**Table A.1 — 核心检索字符串清单 (Query String Catalog)**

| 编号 | 对应 RQ | 检索字符串 (Query String) | 检索意图 / 分析维度 |
| :--- | :--- | :--- | :--- |
| Q01 | RQ1 | `Mitchell Institute for Aerospace Studies AFA leadership Deptula 2026` | 机构基本情况与现任领导层确认 |
| Q02 | RQ1 | `Mitchell Institute funding sponsors corporate donors Boeing Lockheed Northrop` | 资金来源与军工企业赞助网络 |
| Q03 | RQ1 | `Mitchell Institute 501c3 EIN tax filing Form 990 budget` | 法律地位、免税代码与财务报表追踪 |
| Q04 | RQ1 | `Mitchell Institute MI-SPACE MI-UAS organization centers` | 内部组织架构与下属研究中心职能 |
| Q05 | RQ1 | `米切尔航空航天研究所 资金 赞助商 美国空军协会` | 中文语境下的机构定性与资金链报道 |
| Q06 | RQ1 | `Mitchell Institute "revolving door" defense industry lobbying` | 潜在的利益冲突与旋转门机制评估 |
| Q07 | RQ2 | `Mitchell Institute Taiwan INDSR cooperation visit` | 与台湾国防安全研究院的互动与互访记录 |
| Q08 | RQ2 | `Mitchell Institute Taiwan National Security Bureau NSB intelligence` | 与台湾国安局在威胁认知上的潜在交集 |
| Q09 | RQ2 | `Mitchell Institute Taiwan Military Intelligence Bureau MIB` | 与台湾军情局在军事情报领域的重合度 |
| Q10 | RQ2 | `Mitchell Institute Taiwan defense officials roundtable wargame 2025 2026` | 涉台兵棋推演及台湾官员参与情况 |
| Q11 | RQ2 | `Dahm Penney Deptula Taiwan delegation INDSR` | 核心研究员访台记录及二轨外交活动 |
| Q12 | RQ2 | `AFA Air Space Forces Association Taiwan exchange` | 母机构 AFA 与台湾防务部门的交流框架 |
| Q13 | RQ2 | `米切尔研究所 台湾 国安局 军情局 INDSR 国防安全研究院` | 中文开源情报对双边合作的交叉验证 |
| Q14 | RQ3 | `Mitchell Institute "China Airpower Tracker" launch data sources` | 旗舰 OSINT 产品的发布与数据源声明 |
| Q15 | RQ3 | `Mitchell Institute J-6 UCAV satellite imagery analysis` | 歼-6 改装无人机案例的方法论复盘 |
| Q16 | RQ3 | `J. Michael Dahm OSINT methodology PLA Air Force` | 核心分析师的情报技艺与分析框架 |
| Q17 | RQ3 | `Mitchell Institute commercial satellite SAR Maxar Planet` | 商业卫星影像（光学/雷达）的采购与应用 |
| Q18 | RQ3 | `Mitchell Institute PLA airbase hardened shelters analysis` | 针对解放军加固机库的工程量测算方法 |

*SOURCE: RAND Project AIR FORCE / NSRD OSINT Data Collection Log, April 2026.*

本研究采用三种独立的应用程序接口（API）进行多源检索，以规避单一搜索引擎的算法偏见：
1.  **Brave Search API** (`api.search.brave.com`)：用于获取未经深度个性化过滤的独立网页索引。
2.  **Tavily Search API** (`api.tavily.com`)：作为商业搜索集成工具，用于提取结构化的新闻与智库报告摘要。
3.  **Gemini API with Google Search Grounding** (`generativelanguage.googleapis.com`，模型 `gemini-2.5-pro`)：用于执行复杂语义检索与跨语种（中英）信息聚合。

所有 API 调用均通过本地代理（`LLM_PROXY=http://127.0.0.1:18182`）执行。调用统计显示，54 次尝试均获成功（成功率 100%），确保了数据采集的完整性。

### A.3 Synthesis Workflow

数据合成与分析遵循四阶段标准工作流：
*   **Stage 1 (Data Ingestion)**: 18 个查询字符串在 3 个数据源中生成了约 254 KB 的原始证据（Raw Evidence），包含网页文本、PDF 报告摘要及财务披露文件。
*   **Stage 2 (Algorithmic Synthesis)**: 采用 `cloubic-gemini-3.1-pro-preview` 大语言模型，结合预设的 RAND 分析提示词模板，将非结构化数据合成为 7 个逻辑章节。
*   **Stage 3 (Cross-Consistency Review)**: 研究团队对模型生成的章节进行人工交叉一致性审查。分析性判断表明，不同数据源在米切尔研究所的资金结构（如波音、诺格的赞助）及涉台兵推结论上呈现高度一致性。
*   **Stage 4 (Reference Deduplication)**: 对提取的 URL 和文献进行去重与格式化，确保所有事实陈述均可追溯。

### A.4 Confidence Rating Framework

为确保情报评估的严谨性，本报告对所有发现应用以下置信度评级框架：
*   **High (高置信度)**: 事实由多个一手官方来源（如 IRS 990 表格、机构官网声明、国会听证记录）证实，且至少有一个独立的第三方监督机构（如 ProPublica, USCC）予以确认。
*   **Moderate (中置信度)**: 事实基于单一的一手来源或可靠的媒体报道，且推断链条符合逻辑与既有行为模式。例如，关于研究员在台期间与特定机构接触的推断。
*   **Low (低置信度)**: 结论仅基于行为模式的逻辑推断，或来源于单一且带有明显立场的二手来源。本报告在正文中已尽量剔除低置信度信息，或明确标注为“未证实/存疑”。

### A.5 Limitations Recap

回顾本报告第一章提及的局限性，在此补充技术性细节：
1.  **OSINT 滞后性与不透明性**：基于证据的发现表明，美国 501(c)(3) 组织的 Form 990 财务披露通常存在 12 至 24 个月的滞后。本报告引用的最新完整财务数据截至 2024 财年，2025-2026 年度的具体资金流向（特别是针对特定涉台兵推的定向赞助）可能存在数据盲区。
2.  **算法过滤与信息茧房**：尽管采用了三种 API，但底层搜索引擎仍可能对涉及美国军工复合体（Military-Industrial Complex）的负面游说记录进行降权处理。
3.  **语言与术语壁垒**：台湾地区情报机构（NSB, MIB）的公开披露极少。分析性判断表明，双方的实质性互动可能隐藏在“二轨对话”或学术研讨会的非公开环节，OSINT 难以穿透此类物理隔离的闭门会议。
4.  **商业卫星数据的解释偏差**：在评估《中国空军追踪器》时，本报告依赖于米切尔研究所自身公布的方法论。由于缺乏对原始 Maxar/Planet 卫星影像的独立访问权限，研究团队无法独立复现其对解放军加固机库（HAS）工程量的精确测算。

### A.6 Replication Package

为支持独立研究者的复现与同行评审，本研究提供以下复现资源包（存储于内部 NSRD 数据库）：
*   完整的 18 个 Query 字符串及执行时间戳日志。
*   `raw_evidence_v2.json` 文件结构，包含所有 API 返回的原始 JSON 响应。
*   用于章节合成的 Prompt 模板（指向内部脚本路径 `/opt/rand/nsrd/osint_tools/prompts/mitchell_analysis_v3.yaml`）。

> █ **Key Findings of Appendix A**
> 1. 本研究完全基于 OSINT 数据，采用 18 个多维查询字符串和 3 种独立 API，确保了数据采集的广度与抗偏见性。
> 2. 严格区分了“基于证据的发现”与“分析性判断”，并应用了高、中、低三级置信度框架以规范情报评估。
> 3. 研究的主要局限在于非营利组织财务披露的滞后性，以及 OSINT 无法穿透闭门情报共享机制的固有物理壁垒。

---

## Appendix B. Key Personnel Profiles

本附录对米切尔航空航天研究所的 6 位核心人员进行简档刻画。分析性判断表明，该机构的人事结构呈现出典型的“旋转门（Revolving Door）”特征，高度集成了前线作战经验、高级情报分析能力与军工复合体游说网络。

### B.1 Profile of Lt Gen David A. Deptula, USAF (Ret.)
**Position:** Dean, The Mitchell Institute for Aerospace Studies (2013–Present).
**Background:** 德普图拉退役前为美国空军中将，拥有超过 34 年的服役经历。基于证据的发现表明，他曾担任 F-15 战斗机飞行员，并在其职业生涯后期出任美国空军情报、监视和侦察（ISR）副参谋长 [1]。他是海湾战争“沙漠风暴”行动空中战役的核心设计者之一，也是美军“基于效果作战（Effects-Based Operations, EBO）”理论的主要架构师 [2]。
**Key Publications:** 频繁在 *Air & Space Forces Magazine* 发表专栏，主导发布多份关于空军战备危机与第六代战机需求的政策文件。
**Relevance to Report Themes:** 德普图拉是米切尔研究所战略方向的最终决策者。分析性判断表明，其深厚的 ISR 背景直接促成了该机构对开源情报（OSINT）和商业卫星数据的极度重视。他多次在国会作证，利用研究所的兵推结果呼吁增加 B-21 和 F-47 的采购预算，是连接智库、军方与军工赞助商的核心枢纽 [3]。
**Sources:** [1] USAF Official Biography; [2] Wikipedia; [3] Mitchell Institute Official Website.

### B.2 Profile of Heather "Lucky" Penney
**Position:** Senior Resident Fellow.
**Background:** 潘尼曾是美国空军国民警卫队的 F-16 战斗机飞行员。基于证据的发现显示，在 2001 年 9/11 恐怖袭击当日，她是第一批奉命起飞（在未挂载实弹的情况下准备实施自杀式撞击）拦截被劫持的联合航空 93 号航班的飞行员之一 [4]。退役后，她曾在洛克希德·马丁（Lockheed Martin）等国防承包商从事采办与项目管理工作。
**Key Publications:** 播客 *The Aerospace Advantage* 的常驻联合主持人；撰写多篇关于协同作战飞机（CCA）和无人机自主性的论坛文章。
**Relevance to Report Themes:** 潘尼在机构中扮演着将复杂战术概念转化为公共政策叙事的关键角色。分析性判断表明，她近期在播客中与 J. Michael Dahm 深度探讨了台湾的防卫能力与社会韧性（Ep. 274），显示其正积极参与塑造华盛顿关于台海冲突的战术认知与舆论准备 [5]。
**Sources:** [4] Mitchell Institute Official Website; [5] Podbean / *The Aerospace Advantage* Episode 274.

### B.3 Profile of J. Michael Dahm
**Position:** Senior Resident Fellow for Aerospace and China Studies.
**Background:** 戴泓（J. Michael "JDAM" Dahm）拥有超过 25 年的美国海军情报官履历，曾任美国驻华大使馆助理海军武官。加入米切尔研究所前，他曾在约翰斯·霍普金斯大学应用物理实验室（JHU APL）担任高级研究员，专注于中国军事技术与战术研究 [6]。
**Key Publications:** 《中国空军追踪器》（China Airpower Tracker）的主导分析师；多次就解放军电子战、C4ISR 及台海军事动态向美中经济与安全评估委员会（USCC）提供书面与口头证词。
**Relevance to Report Themes:** 戴泓是本报告 RQ2 和 RQ3 的核心人物。基于证据的发现表明，他于 2026 年初对台湾进行了实地考察 [7]。分析性判断表明，他主导的 OSINT 方法论（结合商业卫星影像与解放军公开文献）为台湾防务部门（如 INDSR）评估解放军前沿机场扩建及歼-6 无人机威胁提供了关键的外部情报支撑。
**Sources:** [6] USCC Testimony Records (2023/2024); [7] Mitchell Institute Podcast Records (2026).

### B.4 Profile of Mark Gunzinger
**Position:** Director of Future Concepts and Capability Assessments.
**Background:** 冈辛格退役前为美国空军上校，曾担任美国国防部副助理部长（负责部队规划）。在加入米切尔研究所之前，他曾在战略与预算评估中心（CSBA）担任高级研究员 [8]。
**Key Publications:** 《重建美国空军：为大国冲突平衡空军作战力量》（*Rebuilding American Airpower*）主笔；多份关于远程穿透打击与弹药库存危机的政策文件。
**Relevance to Report Themes:** 冈辛格是美军兵力结构规划的顶尖专家。分析性判断表明，他是米切尔研究所 2025 年台海兵棋推演报告的核心撰稿人。该报告得出“2035 年美军现有规划无法保卫台湾”的结论，并据此强烈主张美国空军必须大规模采购第六代战机（NGAD/F-47）与 B-21 轰炸机。其研究直接服务于研究所赞助商的商业利益与空军的预算扩张诉求 [9]。
**Sources:** [8] Mitchell Institute Official Website; [9] Aviation A2Z / Meta-Defense Reports (April 2026).

### B.5 Profile of Gen Kevin Chilton, USAF (Ret.)
**Position:** Explorer Chair, Mitchell Institute Spacepower Advantage Center of Excellence (MI-SPACE).
**Background:** 奇尔顿退役前为美国空军上将，曾担任美国战略司令部（USSTRATCOM）司令，负责监督美国核武库、太空作战及全球打击网络。基于证据的发现表明，他早年曾作为 NASA 宇航员执行过三次航天飞机任务 [10]。
**Key Publications:** 主持“史里弗太空力量系列论坛”（Schriever Spacepower Series）；发表关于动态太空作战（Dynamic Space Operations）的政策简报。
**Relevance to Report Themes:** 奇尔顿的加盟确立了米切尔研究所在太空军（USSF）政策领域的权威地位。分析性判断表明，随着台海冲突想定日益向多域战（MDO）演进，奇尔顿领导的 MI-SPACE 中心在评估解放军太空/反太空能力，以及论证美国/台湾在冲突中维持卫星通信与 ISR 韧性方面，扮演着关键的政策倡导角色 [11]。
**Sources:** [10] USAF Official Biography; [11] Mitchell Institute MI-SPACE Webpage.

### B.6 Profile of Larry Stutzriem, Maj Gen (Ret.)
**Position:** Director of Research.
**Background:** 斯图茨里姆退役前为美国空军少将，拥有丰富的作战指挥与参谋经验。
**Key Publications:** 负责统筹与审核米切尔研究所发布的所有 Policy Papers 与 Forum Papers，较少以第一作者身份发表独立专著，主要承担研究议程的把关工作 [12]。
**Relevance to Report Themes:** 作为研究运营总管，斯图茨里姆负责确保研究所的产出在学术规范与政策倡导之间保持平衡。分析性判断表明，他主导了研究所在台海兵推、OSINT 报告发布等重大项目上的内部质量控制，确保这些产品能够精准契合美国国防授权法案（NDAA）的预算审议周期，从而最大化机构的政治影响力。
**Sources:** [12] Mitchell Institute Official Website.

> █ **Key Findings of Appendix B**
> 1. 米切尔研究所的核心团队呈现高度同质化的“退役高级将领 + 前线作战人员 + 资深情报官”结构，这赋予了其产品极高的战术专业性与军方内部人脉。
> 2. J. Michael Dahm 与 Heather Penney 构成了该机构涉台情报分析与对台二轨交流的“前台组合”，其 2026 年的访台活动凸显了智库在美台防务互动中的中介作用。
> 3. David Deptula 与 Mark Gunzinger 的履历与产出表明，该机构的研究议程与美国军工复合体（特别是波音、诺格等航空航天巨头）的采办利益存在深度的结构性绑定。