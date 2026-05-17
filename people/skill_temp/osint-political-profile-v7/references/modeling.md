# Part C：行为建模层（五框架+交叉验证）

> 所有分析结论须标注其源自Part B事实采集的具体模块号。
> 所有E级推断须标注所用学术框架。

## C.1 Hermann LTA（领导特质分析）

七维度特质评估，1-7分制。

| 维度代码 | 维度名称 | 评估内容 |
|---------|---------|---------|
| BACE | 对约束的信念 | 是否相信自己能影响事件 |
| CC | 概念复杂度 | 认知多元性 vs 非黑即白 |
| NP | 对他者需求的敏感度 | 移情 vs 自我中心 |
| DIS | 不信任感 | 对他人动机的怀疑程度 |
| IGB | 群体内偏好 | 对内团体的忠诚程度 |
| SC | 自我效能 | 对自身能力的自信 |
| TASK | 任务导向 | 任务 vs 关系导向 |

**V7编码透明度标注**（蒋万安实战经验）：
- 每维度须列出≥3条独立行为证据（具体时间+场合+行为描述）
- 每条证据标注来源等级(A/B/C)
- 标注编码一致性（多条证据指向是否一致）
- 格式：`TASK=5 [3条B级证据, 一致性:高]`

**领导风格推断矩阵**：
- 高BACE+高SC+高TASK → 目标驱动型（Goal-Driven）
- 高CC+高NP+低DIS → 开放协作型
- 低CC+高DIS+高IGB → 偏执封闭型
- ...（组合模式参见Hermann 1980原文）

标注：[E-Hermann LTA]

## C.2 George操作码分析

### 哲学信念
- P-1: 政治世界的本质（冲突 vs 和谐）
- P-2: 实现基本目标的前景
- P-3: 政治未来的可预测性
- P-4: 对历史发展的控制力
- P-5: 机会与风险在政治中的角色

### 工具信念
- I-1: 追求目标的最佳策略
- I-2: 追求利益的最佳战术
- I-3: 风险计算
- I-4: 时机选择
- I-5: 合作 vs 冲突的偏好

每条信念须引用≥2个具体行为/言论案例。

标注：[E-George OpCode]

## C.3 Winter动机编码

三维度动机评估：

| 维度 | 高分特征 | 低分特征 |
|------|---------|---------|
| 权力动机(nPow) | 控制他人、追求声望、强硬外交 | 授权下属、低调务实 |
| 成就动机(nAch) | 设定高标准、创新求变、关注绩效 | 维持现状、规避风险 |
| 亲和动机(nAff) | 寻求合作、避免冲突、重视关系 | 独立决策、不惧对抗 |

**组合预测**（Winter 1992）：
- 高nPow+低nAff → 帝国型领导，易卷入冲突
- 高nPow+高nAff → 矛盾型，对内温和对外强硬
- 高nAch+低nPow → 技术官僚型
- 高nAch+高nPow → 战略型企业家
- 高nAff+低nPow → 调和型

**V7横向基线对比**：须与同期2-3位竞争对手做横向比较，标明基线参照系。

标注：[E-Winter Motive]

## C.4 Barber类型学

Active/Passive × Positive/Negative 四分类：

| 类型 | 特征 | 危机行为预测 |
|------|------|-------------|
| Active-Positive | 适应性强，自我实现导向 | 灵活应变，创造性解决 |
| Active-Negative | 权力驱动，自我补偿 | 僵化坚持，升级冲突 |
| Passive-Positive | 寻求认同，顺应环境 | 退缩回避，依赖顾问 |
| Passive-Negative | 义务驱动，消极参与 | 拖延推诿，系统停滞 |

判定须基于：(1)政治活动的投入程度 (2)对政治角色的情感态度。

标注：[E-Barber Type]

## C.5 MBTI认知功能分析

### 三步判定流程

**Step 1: 四字母初判**
基于行为观察初步推断E/I、S/N、T/F、J/P四维度。每维度须有≥2条独立行为证据。

**Step 2: 八功能栈分析**
确定主导函数(dominant)→辅助函数(auxiliary)→第三函数(tertiary)→劣势函数(inferior)。

| 位置 | 功能 | 行为表现 |
|------|------|---------|
| 主导 | 最自然使用的认知模式 | 日常决策的默认路径 |
| 辅助 | 平衡主导的补充功能 | 在需要时自觉调用 |
| 第三 | 发展中的功能 | 偶尔展现，不稳定 |
| 劣势 | 最弱的功能 | 压力下可能"grip"爆发 |

**Step 3: 交叉验证矩阵**

必须与至少一个其他框架交叉验证：

| MBTI特征 | Hermann对应 | George对应 | 一致性 |
|----------|------------|------------|--------|
| Te主导(外向思维) | 高TASK+高SC | I-1倾向理性策略 | ☐一致/☐部分/☐冲突 |
| Ni辅助(内向直觉) | 高CC | P-3高可预测性信念 | ☐一致/☐部分/☐冲突 |
| ... | ... | ... | ... |

**Grip Theory压力预测**：
基于劣势函数预测高压情景下的行为模式变化。例如ENTJ在极端压力下可能出现Fi grip（突然的情绪化/价值观固执）。

标注：[E-MBTI]

**禁止循环论证**：MBTI判定必须基于认知功能的行为观察，不能从权力谋划直接推导人格类型。

## C.6 综合画像合成

将五框架收敛为统一的认知-行为画像，覆盖四个维度：
1. 信息处理模式（CC+MBTI认知栈）
2. 决策风格（George OpCode+Hermann TASK/SC）
3. 人际互动模式（NP+DIS+nAff+E/I）
4. 压力反应预测（Barber类型+Grip Theory+Winter动机组合）

标注：[E-Composite]

## 学术参考文献

- Hermann, M.G. (1980). Explaining Foreign Policy Behavior Using the Personal Characteristics of Political Leaders. *International Studies Quarterly*, 24(1), 7-46.
- George, A.L. (1969). The Operational Code: A Neglected Approach to the Study of Political Leaders and Decision-Making. *International Studies Quarterly*, 13(2), 190-222.
- Winter, D.G. (1992). Personality and Foreign Policy: Historical Overview of Research. In E. Singer & V. Hudson (Eds.), *Political Psychology and Foreign Policy*. Westview Press.
- Barber, J.D. (1972). *The Presidential Character: Predicting Performance in the White House*. Prentice-Hall.
- Glaser, C.L. (2023). Washington's Dangerous New Consensus on China. *Foreign Affairs*.
- Kastner, S.L. (2009). *Political Conflict and Economic Interdependence Across the Taiwan Strait and Beyond*. Stanford University Press.
- Bush, R.C. (2005). *Untying the Knot: Making Peace in the Taiwan Strait*. Brookings Institution Press.
- Christensen, T.J. (2015). *The China Challenge: Shaping the Choices of a Rising Power*. W.W. Norton.
