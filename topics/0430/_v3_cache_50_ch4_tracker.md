## Chapter 4. The China Airpower Tracker: Sources, Methods, and Tradecraft

### 4.1 Project Overview

基于证据的发现（Evidence-based finding）显示，米切尔航空航天研究所（The Mitchell Institute for Aerospace Studies）于2026年2月25日正式上线了其旗舰开源情报（OSINT）产品——《中国空军追踪器》（China Airpower Tracker）[1]。该项目（URL: mitchellaerospacepower.org/china）被官方定义为一个动态的、基于高分辨率影像的战术与战略情报评估平台，旨在系统性追踪中国人民解放军空军（PLAAF）及海军航空兵（PLANAF）的兵力结构演进、基地基础设施建设及装备现代化轨迹[2]。

分析性判断（Analytic judgment）表明，该项目的核心驱动力高度依赖其首席分析师 J. Michael Dahm 的个人履历与情报技艺。Dahm 拥有25年美国海军情报官服役经验，曾任美国驻华大使馆助理海军武官，其深厚的体制内情报分析背景为该开源项目注入了准军方标准的方法论[3]。

**Table 4.1 — Tracker 项目基本信息表**

| 维度 (Dimension) | 描述 (Description) |
| :--- | :--- |
| **项目名称** | China Airpower Tracker (中国空军追踪器) |
| **上线日期** | 2026-02-25 |
| **首席分析师** | J. Michael Dahm (前 USN 资深情报官) |
| **核心目标** | 追踪 PLAAF/PLANAF 基地扩建、机型迭代与战术意图 |
| **数据基础** | 多模态商业卫星影像 + 跨域开源情报 (OSINT) |
| **目标受众** | 美国国会、DoD 决策层、印太盟友防务部门、防务工业界 |

*SOURCE: RAND NSRD compilation based on Mitchell Institute public announcements, 2026.*

### 4.2 Six Categories of Data Sources

《中国空军追踪器》的底层数据架构并未依赖单一维度的信息，而是构建了一个由六大类开源数据交织而成的多模态矩阵。以下对各类数据源的构成与情报价值进行解构。

#### 4.2.1 Commercial Satellite Imagery
商业卫星影像是该追踪器最核心的物理证据层。基于证据的发现表明，该项目广泛采购或订阅了多家顶级商业卫星供应商的数据服务[4]。在光学影像方面，Maxar Technologies 的 WorldView 星座（提供高达 0.3 米分辨率的图像）和 Planet Labs 的 SkySat 与 PlanetScope 星座被用于精确测量飞机几何尺寸及跑道扩建细节。在合成孔径雷达（SAR）方面，Capella Space 和 ICEYE 的数据被用于全天候、穿透云层及伪装网的侦察，特别是利用相干变化检测（CCD）技术识别地下设施的挖掘活动。此外，欧洲空间局（ESA）免费提供的 Sentinel-1/2 数据被用作广域基线监测，以触发高分辨率卫星的定向拍摄[5]。

**Table 4.2 — 主要商业卫星供应商及其分辨率/重访率**

| 供应商 (Provider) | 传感器类型 (Sensor) | 最高分辨率 (Max Resolution) | 重访率特征 (Revisit Capability) |
| :--- | :--- | :--- | :--- |
| **Maxar** | 光学 (Optical) | 0.3m | 每日 1-2 次 (高精度测绘) |
| **Planet Labs** | 光学 (Optical) | 0.5m (SkySat) / 3m | 每日多次 (高频次动态监测) |
| **Capella Space** | 雷达 (SAR) | 0.5m | 全天候/穿透云层 |
| **ICEYE** | 雷达 (SAR) | 1m 以下 | 每日多次 (SAR 动态追踪) |
| **ESA Sentinel** | 光学/SAR | 10m | 免费开源，5-6天周期 (基线比对) |

*SOURCE: RAND NSRD analysis of commercial satellite market capabilities, 2026.*

#### 4.2.2 PRC Official and Semi-Official Sources
物理影像仅能揭示“存在什么”，而中国官方与半官方信息则被用于解释“编制归属”与“战略意图”。该项目系统性地抓取并翻译了《解放军报》、《中国空军》杂志、中国军网（81.cn）以及 CCTV-7 国防军事频道的公开报道[6]。分析性判断认为，通过对 CCTV-7 画面中战机垂尾编号、飞行员臂章的视觉提取（Visual Extraction），结合卫星影像，分析师能够确认特定基地的驻扎部队番号。此外，中国政府采购网及全军武器装备采购信息网的公开招投标公告，以及地方政府生态环境局的“机场扩建项目环境影响评价公示”，为追踪器提前数月掌握基地油库容量增加值及地下弹药库工程量提供了关键的文本证据[7]。

#### 4.2.3 Trade Publications and Air Show Materials
行业期刊与防务展会资料构成了追踪器的技术参数基准层。基于证据的发现显示，该项目大量引用了《Aviation Week》、Janes 防务周刊、Forecast International 的市场预测以及国际战略研究所（IISS）的《Military Balance》数据[8]。同时，中国国内举办的防务展（特别是 ZHUHAI Airshow 珠海航展）是获取中国无人机（UAV）、空空导弹及雷达系统公开参数的关键节点。分析师通过系统性收集展板数据、宣传册及现场高清照片，建立了解放军新型航空装备的目标特征库（Target Signature Library），用于辅助卫星影像中的几何比对[9]。

#### 4.2.4 Chinese Social Media and Mil-Forum Imagery
中文社交媒体与军事论坛构成了高时效性的线索层。微博、抖音、超大军事论坛（CJDBY）、铁血社区以及豆瓣军迷小组等平台上的“爬墙党”（军事爱好者）拍摄的飞机起降照片，往往比商业卫星更早揭示新机型的试飞动态或部队换装进度[10]。然而，分析性判断指出，此类数据伴随着极高的虚假信息风险。为此，追踪器团队采用了一套严格的真实性筛选机制，包括地理定位（Geolocation，通过背景山脉、建筑轮廓比对）和时间验证（Chronolocation，通过光影角度、历史天气数据比对），以剔除伪造图像或旧图重发的干扰[11]。

#### 4.2.5 U.S. Congressional and Allied Government Reporting
美国国会及盟国政府的公开报告为追踪器提供了宏观的政策与战略框架。美中经济与安全评估委员会（USCC）的历次听证记录（包括 Dahm 本人的证词）、美国国防部（DoD）发布的年度《中国军力报告》（2024/2025/2026 China Military Power Report）、国会研究服务部（CRS）的背景简报以及政府问责局（GAO）的评估，均被整合入追踪器的分析语境中[12]。这些文件不仅用于交叉验证解放军的整体战略意图，也确保了追踪器的产出能够与华盛顿的主流政策话语体系保持无缝对接。

#### 4.2.6 Academic and Sister Institution Outputs
《中国空军追踪器》并非在学术真空中运作，而是深度嵌入了美国涉华军事研究的智库生态圈。基于证据的发现表明，美国空军大学中国航空航天研究所（CASI）是该项目的关键合作伙伴，提供了关于解放军空军条令与组织架构的深度文献支持[13]。此外，美国海军战争学院中国海事研究所（CMSI）、战略与国际研究中心（CSIS）的 ChinaPower 项目、IISS 以及 CNA Corporation 的公开研究成果，均作为平行数据源被纳入追踪器的交叉验证网络中，形成了一个非正式的情报共享与互校机制[14]。

### 4.3 Analytical Methodology: A Four-Stage Framework

分析性判断表明，《中国空军追踪器》的底层方法论超越了简单的图像标注，形成了一套严密的“四步闭环流程”（Four-Stage Framework）。该框架旨在将微观的像素变化转化为宏观的战术与战略评估。

**Stage 1: Physical Identification（物理识别）**
第一阶段侧重于从卫星影像中提取目标的几何与光谱特征。分析师通过测量机身长度、翼展、后掠角等参数，与已知的中国战机数据库进行比对。例如，在识别退役改装无人机时，分析师能够在 Maxar 的高分辨率影像中，通过识别歼-6（J-6）特有的短粗机身比例与大后掠翼特征，将其与歼-7 或现代战机区分开来[15]。此外，跑道的长度、方向以及滑行道的布局模式，也是识别基地起降能力的关键物理指标。

**Stage 2: Engineering Quantification（工程量计数）**
第二阶段将定性识别转化为定量数据。分析师对基地基础设施进行精确的工程量测算，包括加固机库（HAS）的数量与尺寸、露天停机坪的面积、油料库的储量估算以及地下弹药存储区的挖掘土方量。

**Figure 4.1 — HAS 计数与分类方法示意图 (Conceptual Layout)**

```text
[Satellite Imagery Grid - Base X]
|-- Zone A: Flight Line
|   |-- Open Tarmac: 12x J-16 (Identified via geometry)
|-- Zone B: Hardened Aircraft Shelters (HAS)
|   |-- Type 1 (Standard): 24 units (Dimensions: 20m x 15m) -> Fighter capacity
|   |-- Type 2 (Large): 4 units (Dimensions: 40m x 30m) -> Bomber/AWACS capacity
|-- Zone C: Support Infrastructure
|   |-- Fuel Farm: 6x tanks (Radius 10m) -> Est. capacity X million liters
|   |-- Munitions Storage: Earth-covered magazines (ECM), 8 units
```
*SOURCE: RAND NSRD conceptualization of Mitchell Institute methodology, 2026.*

**Stage 3: Tactical Intent Inference（战术意图反推）**
第三阶段是该方法论的核心增值环节。分析师试图从基础设施的物理变化中推断解放军的作战意图。例如，分析性判断认为，如果一个靠近台湾海峡的前沿基地不仅扩建了停机坪，还大规模建设了高抗力的永久性 HAS 和地下弹药库，这可能（suggests）表明该基地不再仅仅是作为“临时部署跳板”，而是被预设为长期驻扎的堡垒，甚至可能用于在冲突初期支撑大规模的 UCAV 消耗战[16]。

**Stage 4: Multi-Source Cross-Validation（多源交叉验证）**
第四阶段旨在降低单一来源的误判风险。追踪器采用“四角验证”法：将卫星影像得出的物理结论，与官方采办公告中的工程招标数据、中文社交媒体上流出的地面照片，以及美方国会听证会上的宏观评估进行交叉比对。只有当多源数据形成逻辑闭环时，该项情报评估才会被正式发布至追踪器平台[17]。

### 4.4 Tradecraft Assessment: Strengths

采用 RAND 标志性的情报技艺（Tradecraft）评估框架，本节首先分析《中国空军追踪器》在方法论与产品呈现上的显著优势。

首先，**多模态数据矩阵的稳健性**是其核心优势。基于证据的发现表明，通过融合商业光学、SAR 影像与开源文本数据，该项目在一定程度上克服了传统单一光学卫星受制于云层遮挡和夜间盲区的物理限制[18]。

其次，**可视化呈现显著降低了非专业受众的理解门槛**。追踪器通过交互式地图、时间序列滑块（Time-series sliders）和直观的图表，将晦涩的工程量数据转化为国会议员、政策制定者及媒体能够迅速消化的“威胁热力图”。这种设计极大地增强了其政策游说与公共传播的效力[19]。

第三，**相对透明的数据源标注**。与部分拒绝披露来源的闭门情报产品不同，追踪器在多数非敏感案例中公开了其卫星影像的提供商（如标注 Maxar 或 Planet）及拍摄日期，这为第三方学术机构进行有限度的复核提供了可能。

最后，该项目在华盛顿智库圈中确立了**清晰的差异化定位**。如 Table 4.3 所示，它填补了宏观学术研究与微观商业数据之间的空白。

**Table 4.3 — Tracker vs CASI / CSIS / IISS / Janes 比较矩阵**

| 机构/项目 | 核心定位 (Core Focus) | 数据呈现形式 (Format) | 战术颗粒度 (Tactical Granularity) |
| :--- | :--- | :--- | :--- |
| **Mitchell Tracker** | 设施追踪与战术意图反推 | 交互式 GIS 仪表盘 | 极高 (单体机库/机型计数) |
| **CASI (Air Univ.)** | 组织架构与条令研究 | 学术报告/翻译文献 | 中等 (侧重编制与人事) |
| **CSIS ChinaPower** | 宏观军力与国力趋势 | 数据可视化图表 | 中低 (侧重战区级/国家级) |
| **IISS Mil-Balance** | 全球军力基线统计 | 年度出版物/数据库 | 中等 (侧重装备总数) |
| **Janes** | 装备技术参数与军贸 | 商业订阅数据库 | 高 (侧重单体装备性能) |

*SOURCE: RAND NSRD analytic assessment, 2026.*

### 4.5 Tradecraft Assessment: Limitations and Risks

在评估其局限性与风险时，必须严格区分基于客观事实的证据与基于情报学理的分析性判断。尽管该项目在 OSINT 领域表现出较高的专业度，但其情报技艺仍存在若干结构性脆弱点。

#### 4.5.1 Confirmation Bias 确认偏误
**基于证据的发现（Evidence-based finding）：** 米切尔研究所的资金来源结构中，包含了波音、洛克希德·马丁、诺斯罗普·格鲁曼等主要美国防务承包商的赞助[20]。同时，该机构的公开使命是倡导强大的美国航空航天力量。
**分析性判断（Analytic judgment）：** 这种机构属性与资金结构可能（may）在无意识中引导分析师产生确认偏误（Confirmation Bias）。在面对模糊的卫星影像或不确定的开源数据时，分析团队可能存在一种系统性的激励，倾向于优先选择和发布那些支持“威胁严重”或“解放军扩张迅速”叙事的证据。这种“威胁通胀”（Threat Inflation）的潜在倾向，可能导致对解放军常规设施翻新或防御性升级的过度解读[21]。

#### 4.5.2 Imagery Interpretation Overconfidence 影像判读的过度自信
**基于证据的发现（Evidence-based finding）：** 商业卫星影像，无论分辨率多高，本质上只能捕捉目标的外部物理特征，无法穿透加固机库的顶部观察内部活动[22]。
**分析性判断（Analytic judgment）：** 追踪器在从“物理识别”向“战术意图反推”跨越时，可能表现出过度自信。单凭外部影像难以确认机库内部的真实用途（例如，新建的 HAS 内部可能是空的，或者用于存放非航空物资）。此外，该方法论对解放军的伪装、隐蔽与欺骗（CC&D）措施（如高仿真充气模型、假跑道、电磁诱饵）的抵抗力有限。更重要的是，装备完好率、后勤保障深度、人员训练熟练度等决定战斗力的“软”维度，是无法从卫星影像中提取的[23]。

#### 4.5.3 Single-Source Vulnerability 单一来源脆弱性
**基于证据的发现（Evidence-based finding）：** 尽管追踪器声称采用多源验证，但在某些高时效性或偏远地区的案例中，其判断仅依赖于单一商业卫星供应商在特定时间窗口抓拍的孤立影像[24]。
**分析性判断（Analytic judgment）：** 缺乏信号情报（SIGINT）和人力情报（HUMINT）的深度交叉验证，使得这种基于纯 OSINT 的评估具有固有的脆弱性。如果单一卫星影像受到大气扰动、传感器伪影或敌方定向干扰的影响，可能导致整个战术推断链条的崩塌。

#### 4.5.4 Replicability Question 可复制性存疑
**基于证据的发现（Evidence-based finding）：** 米切尔研究所并未完全开源其用于处理海量卫星影像的自动化脚本、AI 目标识别算法的具体权重，以及筛选中文社交媒体数据的具体代码[25]。
**分析性判断（Analytic judgment）：** 这种方法论上的不透明性降低了该项目在学术意义上的可复制性（Replicability）。第三方独立研究机构难以使用相同的数据集复现其精确的计数结果，这使得部分结论更接近于“专家权威判断”而非“可验证的科学测量”[26]。

### 4.6 Strategic Spillover Effects

分析性判断表明，《中国空军追踪器》的运作已超越了单纯的情报收集范畴，在印太地区产生了显著的战略溢出效应（Strategic Spillover Effects）。

首先，该项目构成了一种**“透明化威慑”（Deterrence through Transparency）**的认知作战工具。通过持续、高调地曝光解放军的基地建设与兵力调动，该平台向北京传递了“美方具备单向战场透明度”的信号。这种做法可能（could）旨在削弱对手的战略突然性，并在认知领域施加心理压力[27]。

其次，该平台的数据输出对印太盟友的防务决策产生了传导效应。基于证据的发现显示，日本、澳大利亚、韩国以及台湾地区的防务研究机构（如 INDSR）频繁引用此类 OSINT 数据来评估自身的防空压力[28]。分析性判断认为，这种外部威胁的具象化，客观上为这些盟友增加国防预算、调整防卫指针以及向美国采购先进不对称武器系统（如防空导弹、无人机）提供了舆论与政策依据。

最后，该项目对中国大陆的军事透明度政策构成了“被动施压”。面对高频次的商业卫星曝光，解放军可能（appears to）被迫在沿海机场扩建与装备部署中投入更高的伪装与隐蔽成本，从而在和平时期消耗其额外的后勤与工程资源[29]。

***

### Key Findings of Chapter 4

> **KF 4.1**
> 《中国空军追踪器》是一个融合多模态商业卫星影像与跨域开源情报（OSINT）的战术/战略评估平台，其核心驱动力源于前美军情报官的专业技艺与米切尔研究所的机构资源。
> 
> **KF 4.2**
> 该项目的数据源矩阵包含六大支柱：商业卫星影像（光学/SAR）、中国官方/半官方信息、行业展会资料、中文社交媒体、美/盟国政府报告以及学术机构产出，形成了一个互为补充的情报生态。
> 
> **KF 4.3**
> 其分析方法论遵循“物理识别 → 工程量计数 → 战术意图反推 → 多源交叉验证”的四步闭环框架，试图将微观的像素变化转化为宏观的政策建议。
> 
> **KF 4.4**
> 追踪器的主要优势在于其多模态数据的稳健性、降低理解门槛的可视化呈现，以及在华盛顿智库圈中填补了宏观趋势与微观商业数据之间的生态位空白。
> 
> **KF 4.5**
> 从情报技艺评估来看，该项目存在潜在的确认偏误（受机构赞助结构影响）、对影像判读的过度自信（难以识别 CC&D 及“软”实力）、单一来源脆弱性以及方法论可复制性不足等结构性风险。
> 
> **KF 4.6**
> 该项目的战略溢出效应显著，不仅作为“透明化威慑”的认知作战工具，还客观上传导并影响了印太盟友（如日、澳、台）的防务采办决策，并对中国大陆的军事部署构成了被动施压。