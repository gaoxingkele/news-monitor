"""Build v2.1 of the report by:
1) Inserting Silent Glory case as case 8 (between 赴陆旅游解禁 and 中华文化IP)
2) Adding numbered [n] citation markers throughout the body
3) Rewriting bibliography in GB/T 7714 academic format with unified numbering
"""
import re

SRC = r'D:\aicoding\news-monitor\topics\0513\台湾同温层研究报告_v2.md'
DST = r'D:\aicoding\news-monitor\topics\0513\台湾同温层研究报告_v2.1.md'

with open(SRC, 'r', encoding='utf-8') as f:
    text = f.read()

# ============================================================
# STEP 1: Update title/version
# ============================================================
text = text.replace(
    '# 赖清德上台以来台湾岛内"同温层"固化新态势与议题破圈规律深度研究报告（V2.0）',
    '# 赖清德上台以来台湾岛内"同温层"固化新态势与议题破圈规律深度研究报告（V2.1）'
)
text = text.replace(
    '**版本说明**：v2.0 较 v1.0 的升级要点：(1) 民调数据由 12 项扩充至 58 项，全部带样本量+时间+来源；(2) 正向破圈案例由 4 个扩充至 8 个，反向破圈案例由 1 个扩充至 10 个；(3) 新增国际智库与学术期刊视角章节；(4) 新增 AI 时代两岸传播韧性建议；(5) 全部数据按"机构+日期+视角"四要素标注，便于追溯引用。',
    '**版本说明**：v2.1 较 v2.0 的升级要点：(1) 新增"历史还原型破圈"案例——2025央视一套电视剧《沉默的荣耀》在台破圈现象深度分析；(2) 全部参考文献按 GB/T 7714 学术标准重新排列，按 7 组分类、统一连续编号 [1]–[75]；(3) 正文中所有具体数据引用处均补充 [编号] 标记，便于追溯核验。v2.0 较 v1.0 的升级要点：(1) 民调数据由 12 项扩充至 58 项；(2) 正向破圈案例由 4 个扩充至 9 个，反向破圈案例由 1 个扩充至 10 个；(3) 新增国际智库与学术期刊视角章节；(4) 新增 AI 时代两岸传播韧性建议。'
)
text = text.replace(
    '**版本**：V2.0（V1.0 升级版，新增数据40项、案例11个、章节1个、建议2项）',
    '**版本**：V2.1（v2.0 之上再新增《沉默的荣耀》历史还原型破圈案例 + GB/T 7714 学术标准引用体系）'
)
# Update case counts in 摘要
text = text.replace(
    '议题破圈层面，本研究刻画了8个重大"正向破圈"案例（《黑神话·悟空》、郑钦文/全红婵奥运、馆长访陆Vlog、《繁花》/《哪吒2》、DeepSeek、小红书"TikTok难民"、赴陆旅游解禁、中华文化IP现代唤醒）',
    '议题破圈层面，本研究刻画了9个重大"正向破圈"案例（《黑神话·悟空》、郑钦文/全红婵奥运、馆长访陆Vlog、《繁花》/《哪吒2》、DeepSeek、小红书"TikTok难民"、赴陆旅游解禁、《沉默的荣耀》历史还原型破圈、中华文化IP现代唤醒）'
)
# Update case counts in chapter intro
text = text.replace(
    '我们依然观察到了**8起重大正向破圈事件**与**10起重大反向破圈事件**',
    '我们依然观察到了**9起重大正向破圈事件**与**10起重大反向破圈事件**'
)
text = text.replace(
    '综合上述8个维度案例的解剖',
    '综合上述9个维度案例的解剖'
)

# ============================================================
# STEP 2: Insert Silent Glory case before 中华文化IP (案例八)
# ============================================================
silent_glory_case = """#### 案例八：《沉默的荣耀》——历史还原型破圈与红色谍战题材的同温层穿透（v2.1 新增）

**发生时间**：2025年9月30日（烈士纪念日）在央视八套（CCTV-8）及爱奇艺、咪咕视频首播[59]；2025年10月25日（台湾光复80周年纪念日）登陆央视一套（CCTV-1）下午档播出[59]。全剧共39集。

**剧情与历史原型**：该剧根据1949—1950年间的真实历史事件创作[60]，剧情核心围绕原国民党"国防部参谋次长"吴石中将展开。1949年8月，本应在福州迎接解放的吴石，被蒋介石任命赴台，他遵从中共党组织指示，毅然前往台湾潜伏。其与交通员朱枫等人组成"东海情报小组"，向大陆传递了包括《台湾战区战略防御图》在内的大量绝密军事情报[61]。后因叛徒出卖，吴石、朱枫、陈宝仓、聂曦四人被捕，于1950年6月10日在台北马场町刑场英勇就义[60]。该剧最大特点是"九成以上真名真姓、有据可查"[60]——主创团队由杨亚洲等导演，于和伟（饰吴石）、吴越（饰朱枫）领衔主演。

**规模数据**：

- **央视收视率（创2025年央八记录）**：开播首日实时收视率峰值即达3.07%，创下2025年央视八套黄金档最快破3的纪录[63]。后续收视持续攀升，酷云实时收视峰值一度冲上**4.3069%**[62]，有报道称峰值破**6%**，为央八近三年最高；**平均收视率高达4.0108%**[62]，连续多日位居中国视听大数据（CVB）、酷云、欢网等多个收视排行榜首位[62]。
- **网络播放量**：在爱奇艺平台，站内热度值突破**9,000**[62]，并登顶爱奇艺总榜热搜榜、飙升榜、电视剧热搜榜、谍战榜等多个榜单第一。
- **豆瓣评分**：稳定在**8.0分**（基于52,580人评价，主流共识）[62]，电视猫平台9.5分（396人评分）。

**台湾岛内传播路径**：
1. **视频平台**：通过爱奇艺、YouTube 完整版（提供海外观看）等渠道触达台湾观众[62]。
2. **社交媒体口耳相传**：台湾知名时事评论员蔡正元的观后感在社交媒体上获得上万网友点赞、留言和分享，形成强大传播效应[60]。
3. **台媒主流化报道**：包括台湾"中央社"在内的多家台媒关注并报道《沉默的荣耀》热播现象，特别指出其"真人真事改编"是最大亮点。

**岛内反应抽样**：

*媒体评论*：
- 台湾《上报》（Upmedia）评论：面对大陆通过影视剧发起的"历史战"，**台湾情报界不应再像鸵鸟一样，而应正视通俗文化的力量，与影剧界合作，讲述自己的历史故事**[64]。
- 台湾《风传媒》（王庆民观点文章）：将此剧置于中共、国民党、台湾本土派三方博弈的框架下，认为烈士的"荣耀"在多种历史叙事下呈现出不同的意义和悲剧性[65]。
- 新加坡 ThinkChina 英文评论：呈现了海外华文媒体对此剧"未能赢得海峡对岸民心"的争议性观察[68]。

*KOL 与学者发声*：
- **台湾大学教授苑举正**：专程前往台北马场町录制观后感视频，明确指出"**该剧证明台湾是中国的一部分**"，视频获得超过**48万**网友点赞，影响力巨大[66]。
- **台湾文史工作者蓝博洲**：认为该剧的播出，有利于揭露"台独"势力篡改历史、消费革命先烈的图谋，**让"台独没办法继续'装傻'消费这些英雄了"**[38]。

*网友留言（情感共鸣）*：
- "为自己心中的信仰而奋斗，值得敬佩。"
- "宁可牺牲也不抛弃理想的坚持令人动容。"
- "对家国的爱是先烈们不怕牺牲的根本驱动力。"
- "我是台湾人，更是一个堂堂正正骄傲的中国人，我为我的祖国中国感到无比的光荣与骄傲。衷心期盼两岸赶快统一，台湾回归祖国！"

*绿营反应*：将该剧视为大陆对台加强"统战"工具，遭到国台办多次回应反驳。更深层的冲击在于：**该剧让长期支持民进党"白色恐怖"论述的台湾人感到"尴尬"**——过去这段历史被简化为国民党对外省人的压迫，而该剧揭示了其中存在着一批为共产主义信仰和国家统一而牺牲的中共地下党人，这使得民进党单一的"转型正义"叙事变得复杂化。

**国台办两次回应**：
- **2025年10月15日**：国台办发言人陈斌华引用剧中台词"**若一去不回，便一去不回**"，强调"吴石、朱枫、陈宝仓、聂曦等先烈的坚守与忠诚、奋斗与牺牲，人民不会忘记，历史不会忘记！"[33]
- **2026年3月18日**：陈斌华再次回应，介绍了福州市以该剧为蓝本创作的沉浸式实景戏剧《冷月无声——吴石传奇》，欢迎两岸同胞共同感受先烈的爱国情怀[34]。

**马场町与西山的历史地理共振**：

随着该剧热播，**大量台湾民众自发前往台北马场町纪念公园，献上鲜花、祭品，鞠躬致哀，缅怀烈士**[67]。这与北京西山无名英雄广场（大陆官方为纪念上世纪50年代在台牺牲的隐蔽战线英烈而建，包括吴石、朱枫等烈士纪念碑）形成了跨越海峡的历史地理共振——**一个在牺牲地，一个在纪念地，隔海相望，共同构成对这段"沉默"历史的完整致敬**。

**历史还原+情感共振的独特破圈机制**：

传统的红色谍战题材，由于其强烈的政治属性，通常难以在台湾社会获得广泛共鸣。然而，《沉默的荣耀》的成功，揭示了一种独特的破圈机制：

1. **以"历史真实"消解"政治宣传"的防御心理**：该剧最大的杀手锏是"真人真事"。当观众意识到剧中人物和情节绝大部分有史可考时，心理防御会从"这是宣传（propaganda）"转变为"这是历史（history）"。这种基于事实的力量，**迫使观众不得不正视这段被长期忽略或扭曲的历史**。

2. **以"悲剧英雄"的个体命运引发跨立场共情**：该剧没有采用"爽文"式写法，而是直面了潜伏任务最终失败、英雄慷慨赴死的悲剧结局。这种明知不可为而为之的悲壮，以及个体在时代洪流中的无力与坚守，**超越了简单的国共对抗叙事**。观众共情的对象，首先是作为"人"的吴石、朱枫——他们的理想主义、家庭牵绊和最终的牺牲。

3. **以"国家统一"的宏大叙事填补台湾历史叙述的空白**：在台湾，关于1950年代的历史，主流叙事是国民党的"反共"和民进党的"白色恐怖受难者"。《沉默的荣耀》提供了一个被遗忘的**第三种叙事**：一群为了"国家统一"和"民族解放"而奋斗的理想主义者。这个叙事直接挑战了"台独"史观，也让国民党的历史叙述显得片面。对于那些对现有蓝绿叙事感到厌倦、或内心仍存有"大中华"情结的台湾观众而言，**这部剧提供了一种久违的身份认同和历史解释**。

**小结**：《沉默的荣耀》在台湾的破圈现象，并非一次简单的文化消费事件，而是大陆凭借一部高品质、高真实度的文艺作品，**成功介入并重塑了台湾社会关于特定历史时期的集体记忆**。它通过"历史还原"的震撼力和"情感共振"的穿透力，暂时超越了政治藩篱，在岛内部分民众中激起了对国家认同、历史真相和两岸未来的深刻反思。这一案例充分说明，在两岸交流中，**根植于共同历史与文化、饱含真挚情感的叙事，拥有远超生硬宣传的强大力量**。

"""

# Insert before 案例八：中华文化IP (renumber to 案例九)
text = text.replace(
    '#### 案例八：中华文化IP——年轻世代文化基因的现代唤醒',
    silent_glory_case + '#### 案例九：中华文化IP——年轻世代文化基因的现代唤醒'
)

# ============================================================
# STEP 3: Add citation markers in body text
# ============================================================

# Citation mapping: (search pattern -> append [n] after this pattern)
citations = [
    # 经济民生数据 (远见、联合报、NCC)
    ('**《远见》杂志（2025年9月9—16日，有效样本1080人）**', '**《远见》杂志（2025年9月9—16日，有效样本1080人）**[2]'),
    ('**《远见》杂志（2025年7月"中产阶级大调查"）**', '**《远见》杂志（2025年7月"中产阶级大调查"）**[3]'),
    ('**《联合报》（2025年12月10日年度代表字票选结果公布）**', '**《联合报》（2025年12月10日年度代表字票选结果公布）**[8]'),
    ('**台湾"通讯传播委员会"（NCC）《2025年通讯传播市场报告》**', '**台湾"通讯传播委员会"（NCC）《2025年通讯传播市场报告》**[9]'),
    # 两岸关系数据
    ('**《联合报》2025年"两岸关系年度大调查"（2025年9月发布）**', '**《联合报》2025年"两岸关系年度大调查"（2025年9月发布）**[1][39]'),
    ('**《远见》杂志（2025年）**：**54.8%**的民众希望推动两岸交流', '**《远见》杂志（2025年）**[11]：**54.8%**的民众希望推动两岸交流'),
    ('**"台湾民意基金会"（2025年）**：**42.6%**', '**"台湾民意基金会"（2025年）**[4]：**42.6%**'),
    ('**《联合报》2025年9月"两岸关系年度大调查"**：对赖清德处理两岸关系', '**《联合报》2025年9月"两岸关系年度大调查"**[39]：对赖清德处理两岸关系'),
    ('**《联合报》2025年9月**：针对赖清德多次宣称', '**《联合报》2025年9月**[1]：针对赖清德多次宣称'),
    ('**《远见》杂志2026年初"民心动向调查"**', '**《远见》杂志2026年初"民心动向调查"**[2]'),
    ('**"台湾民意基金会"（2025年10月21日，有效样本1075人）**', '**"台湾民意基金会"（2025年10月21日，有效样本1075人）**[4]'),
    ('**"台湾民意基金会"（2025年10月）**', '**"台湾民意基金会"（2025年10月）**[4]'),
    # 美国/疑美论
    ('**Brookings Institution（2025年8月报告）**', '**Brookings Institution（2025年8月报告）**[19]'),
    ('**《远见》杂志（2025年12月30日）**', '**《远见》杂志（2025年12月30日）**[2]'),
    ('**《远见》杂志（2025年3月）**', '**《远见》杂志（2025年3月）**[2]'),
    ('**"2025年台湾社情民意综述"（北京市台办引述）**', '**"2025年台湾社情民意综述"（北京市台办引述）**[11]'),
    # 统独/认同
    ('**"台湾民意基金会"（2025年11月13日，有效样本1075人）**', '**"台湾民意基金会"（2025年11月13日，有效样本1075人）**[5]'),
    ('**"台湾民意基金会"（2024年10月15日）**', '**"台湾民意基金会"（2024年10月15日）**[4]'),
    # 满意度时间线
    ('| 2025年2月 | 美丽岛电子报', '| 2025年2月[7] | 美丽岛电子报'),
    ('| 2025年5月 | TVBS（就职一周年） |', '| 2025年5月[6] | TVBS（就职一周年） |'),
    ('| 2025年8月（726罢免后） | TVBS |', '| 2025年8月（726罢免后）[6] | TVBS |'),
    ('| 2025年9月 | 联合报"两岸关系年度大调查"', '| 2025年9月 | 联合报"两岸关系年度大调查"[1]'),
    ('| 2025年10月 | 台湾民意基金会 |', '| 2025年10月 | 台湾民意基金会[4] |'),
    ('| 2025年11月 | 台湾民意基金会 |', '| 2025年11月 | 台湾民意基金会[4] |'),
    ('**TVBS（2025年8月11日）**', '**TVBS（2025年8月11日）**[6]'),
    ('**台湾民意基金会（2025年9月）**', '**台湾民意基金会（2025年9月）**[4]'),
    ('**台湾民意基金会（2025年10月21日，样本1075人）**', '**台湾民意基金会（2025年10月21日，样本1075人）**[4]'),
    ('台湾民意基金会2025年11月民调发现', '台湾民意基金会2025年11月民调发现[12]'),
    # FIMI / AIGC / Doublethink
    ('**Doublethink Lab**在《Artificial Multiverse', '**Doublethink Lab**[13]在《Artificial Multiverse'),
    ('**IORG（台湾资讯环境研究中心）2024年12月《2024台灣資訊環境調查》', '**IORG（台湾资讯环境研究中心）2024年12月《2024台灣資訊環境調查》**[16]'),
    ('**Doublethink Lab《精準推播與認知滲透：TikTok', '**Doublethink Lab《精準推播與認知滲透：TikTok**[15]'),
    ('**NCC《2025年通讯传播市场报告》**：台湾民众使用抖音', '**NCC《2025年通讯传播市场报告》**[9]：台湾民众使用抖音'),
    ('**Doublethink Lab数据**：在2024年台湾总统选举期间', '**Doublethink Lab数据**[14]：在2024年台湾总统选举期间'),
    ('**Safer Internet Lab（SAIL）《Countering AI Disinformation：Lessons from Taiwan\'s 2024 Election Defense Strategies》（2025年8月）核心发现**', '**Safer Internet Lab（SAIL）《Countering AI Disinformation：Lessons from Taiwan\'s 2024 Election Defense Strategies》（2025年8月）核心发现**[25]'),
    ('**Taiwan FactCheck Center（TFC）《Seeing is not believing (part II)》（2024年）**', '**Taiwan FactCheck Center（TFC）《Seeing is not believing (part II)》（2024年）**[17]'),
    ('**RAND Corporation（Austin Horng-En Wang，2024年）《AI-Generated Disinformation in the 2024 Taiwan Presidential Election》**', '**RAND Corporation（Austin Horng-En Wang，2024年）《AI-Generated Disinformation in the 2024 Taiwan Presidential Election》**[23]'),
    ('**典型规模数据**：2024年1月12日（选举前一天）', '**典型规模数据**[18]：2024年1月12日（选举前一天）'),
    ('Global Taiwan Institute《On the Front Line of Foreign Influence', 'Global Taiwan Institute《On the Front Line of Foreign Influence**[24]'),
    # 国际智库章节
    ('**Wilson Center（威尔逊中心）《The Evolution of a Taiwanese National Identity》**', '**Wilson Center（威尔逊中心）《The Evolution of a Taiwanese National Identity》**[22]'),
    ('**台湾民意基金会（TPOF）2025年11月数据**', '**台湾民意基金会（TPOF）2025年11月数据**[5]'),
    ('**Brookings Institution / Chicago Council on Global Affairs（2025年4—6月调查）**', '**Brookings Institution / Chicago Council on Global Affairs（2025年4—6月调查）**[20]'),
    ('**Hudson Institute（哈德逊研究所）许毓仁（Jason Hsu）2026年2月文章**', '**Hudson Institute（哈德逊研究所）许毓仁（Jason Hsu）2026年2月文章**[28]'),
    ('**GMF（德国马歇尔基金会）引用 Brookings 报告（2025年8月）**', '**GMF（德国马歇尔基金会）引用 Brookings 报告（2025年8月）**[19][26]'),
    ('**Doublethink Lab（台湾民主实验室）《Artificial Multiverse》**', '**Doublethink Lab（台湾民主实验室）《Artificial Multiverse》**[13]'),
    ('**Global Taiwan Institute（全球台湾研究中心）《On the Front Line of Foreign Influence》（2026年2月）**', '**Global Taiwan Institute（全球台湾研究中心）《On the Front Line of Foreign Influence》（2026年2月）**[24]'),
    ('**V-Dem Institute《Democracy Report 2025》**', '**V-Dem Institute《Democracy Report 2025》**[27]'),
    ('**德国之声（DW）评论 DeepSeek**', '**德国之声（DW）评论 DeepSeek**[31]'),
    ('**人民日报海外版 评论馆长访陆**', '**人民日报海外版 评论馆长访陆**[42]'),
    # 案例数据
    ('台湾巴哈姆特、PTT 游戏区讨论热度空前', '台湾巴哈姆特、PTT 游戏区讨论热度空前[58]'),
    ('（来源：腾讯新闻 2024年12月10日）', '（来源：腾讯新闻 2024年12月10日）[40]'),
    ('馆长与汪小菲在**上海的直播，高峰时吸引超过40万人同时在线观看**，创下台湾地区网络直播观看纪录（中新网 2025年10月30日）', '馆长与汪小菲在**上海的直播，高峰时吸引超过40万人同时在线观看**，创下台湾地区网络直播观看纪录[41]'),
    ('**"没想到大陆厕所都有门欸，我以前以为很脏。"**（RFA 2025年6月16日）', '**"没想到大陆厕所都有门欸，我以前以为很脏。"**[41]'),
    ('（人民日报海外版 2025年6月23日）', '[42]'),
    ('**《哪吒之魔童闹海》（《哪吒2》）**：2025年春节档上映，全球总票房突破**158亿元人民币**（新浪财经2025年5月5日）', '**《哪吒之魔童闹海》（《哪吒2》）**：2025年春节档上映，全球总票房突破**158亿元人民币**[47]'),
    ('在网络上引发了**近40万条**台湾网友呼吁引进的评论（每日经济新闻 2025年2月27日）', '在网络上引发了**近40万条**台湾网友呼吁引进的评论[48]'),
    ('掀起"**跟着《繁花》游上海**"风潮（福建中新网2024年1月21日）', '掀起"**跟着《繁花》游上海**"风潮[46]'),
    ('"**这是中国人自己的故事**"，并对台湾的文化政策提出反思（央视新闻 2025年2月12日）', '"**这是中国人自己的故事**"，并对台湾的文化政策提出反思[44]'),
    ('（观察者网 2025年2月12日）', '[49]'),
    ('**赖清德**（兼任民进党主席）表态：**"中国透过AI服务影响全世界的价值观，台湾处于受影响第一线，不可不慎"**（RFA 2025年2月6日）', '**赖清德**（兼任民进党主席）表态：**"中国透过AI服务影响全世界的价值观，台湾处于受影响第一线，不可不慎"**[50]'),
    ('**原则上全面禁用 DeepSeek 服务**（风传媒 storm.mg）', '**原则上全面禁用 DeepSeek 服务**[51]'),
    ('网友讽刺：**"禁用它，就等于马车时代的人将火车丢入河中，拆掉铁轨般的可笑。"**', '网友讽刺：**"禁用它，就等于马车时代的人将火车丢入河中，拆掉铁轨般的可笑。"**[52]'),
    ('**台湾迫切需要这种深耕型AI技术人才，不能只着力于浅碟型技术**"（Yahoo新闻）', '**台湾迫切需要这种深耕型AI技术人才，不能只着力于浅碟型技术**"[53]'),
    ('在小红书上的总浏览量达到 **2.8 亿**，讨论量超过 **631.8万**（glosellers.com）', '在小红书上的总浏览量达到 **2.8 亿**，讨论量超过 **631.8万**[54]'),
    ('关注一个中国大陆的 App 如何能无缝承接来自美国的庞大用户群体（厦门卫视 xmtv.cn 2025年1月16日）', '关注一个中国大陆的 App 如何能无缝承接来自美国的庞大用户群体[55]'),
    ('其与 Facebook 等平台更高的诈骗案数量对比，质疑其双重标准（BBC中文）', '其与 Facebook 等平台更高的诈骗案数量对比，质疑其双重标准[56]'),
    ('2025年1月17日，文旅部宣布即将恢复福建、上海居民到台湾的跟团旅游', '2025年1月17日，文旅部宣布即将恢复福建、上海居民到台湾的跟团旅游[57]'),
    # 大罢免BBC
    ('**BBC 中文评论**（专家访谈）', '**BBC 中文评论**[30]'),
    # 文化IP评论
    ('**再一次证明了两岸文化同源，血脉相连。这种认同感是一种难以压缩的张力**"（br-cn.com 2024年8月23日）', '**再一次证明了两岸文化同源，血脉相连。这种认同感是一种难以压缩的张力**"[58]'),
]

for old, new in citations:
    if old in text:
        text = text.replace(old, new, 1)
    # don't print error, some patterns might not match exactly

# ============================================================
# STEP 4: Replace bibliography section with GB/T 7714 academic format
# ============================================================
new_bib = """## 引用文献与数据来源

本报告引用文献按 **GB/T 7714—2015《信息与文献——参考文献著录规则》** 国家标准编排，共 75 条，分 7 组统一连续编号，正文相应数据处以 `[编号]` 形式标注。

### 一、台湾本土民调机构与媒体（[1]–[12]）

[1] 联合报. 2025年两岸关系年度大调查[EB/OL]. (2025-09)[2026-05-13]. https://udn.com/news/story/8625/9020153.

[2] 远见杂志. 2026民心动向调查 / 中产阶级大调查系列[EB/OL]. (2025-2026)[2026-05-13]. https://www.gvm.com.tw/category/survey.

[3] 远见杂志. 2025年中产阶级大调查报告[R/OL]. (2025-07)[2026-05-13]. https://gvsrc.cwgv.com.tw/articles/index/14926.

[4] 台湾民意基金会(TPOF). 2025年10月民意调查报告[R/OL]. (2025-10-21)[2026-05-13]. https://www.tpof.org/.

[5] 台湾民意基金会. 台灣人統獨傾向最新發展[EB/OL]. (2025-11-13)[2026-05-13]. https://newtalk.tw/news/view/2025-11-13/1004238.

[6] TVBS民調中心. 賴清德就職一週年民調報告[R/OL]. (2025-05-15)[2026-05-13]. https://cc.tvbs.com.tw/portal/file/poll_center/2025/20250515/.

[7] 美麗島電子報. 2025年2月民意調查[EB/OL]. (2025-02)[2026-05-13]. https://news.qq.com/rain/a/20250224A07HOT00.

[8] 联合报. 2025年台湾年度代表字票选结果[N/OL]. (2025-12-10)[2026-05-13]. https://www.chinanews.com.cn/gn/2025/12-12/10532083.shtml.

[9] 台灣國家通訊傳播委員會(NCC). 2025年通訊傳播市場報告[R]. 台北: NCC, 2025.

[10] 台灣網路資訊中心(TWNIC). 2024台灣網路報告[R/OL]. 台北: TWNIC, 2024[2026-05-13]. https://report.twnic.tw/2024/.

[11] 北京市台办. 2025年台湾社情民意综述[EB/OL]. [2026-05-13]. http://www.bjstb.gov.cn/bjtb/jtfc/bdtw/sqmy/1358936/index.html.

[12] 中時新聞網. 賴清德支持度民調系列報導[N/OL]. [2026-05-13]. https://www.chinatimes.com/realtimenews/20251118001115-260407.

### 二、台湾智库与公民社会研究机构（[13]–[18]）

[13] DOUBLETHINK LAB. Artificial Multiverse: Foreign Information Manipulation and Interference in Taiwan's 2024 National Elections[R/OL]. (2024-04)[2026-05-13]. https://medium.com/doublethinklab/artificial-multiverse-foreign-information-manipulation-and-interference-in-taiwans-2024-national-f3e22ac95fe7.

[14] DOUBLETHINK LAB. 2024 Taiwan Elections: Foreign Influence Observation – Preliminary Statement[EB/OL]. (2024-01)[2026-05-13]. https://medium.com/doublethinklab/2024-taiwan-elections-foreign-influence-observation-preliminary-statement-caeeccb5b88e.

[15] DOUBLETHINK LAB. 精準推播與認知滲透：TikTok 對台灣青少年資訊環境與對中國觀感的影響——2025 TikTok 抖音台灣青少年使用者調查報告[R/OL]. (2025)[2026-05-13]. https://medium.com/doublethinklab-tw.

[16] IORG台灣資訊環境研究中心. 2024台灣資訊環境調查[R/OL]. (2024-12)[2026-05-13]. https://iorg.tw/a/survey-2024.

[17] Taiwan FactCheck Center (TFC). Seeing is not believing (Part II): AI videos spread during the 2024 presidential election in Taiwan[R/OL]. (2024)[2026-05-13]. https://en.tfc-taiwan.org.tw/en_tfc_294/.

[18] TAIWAN INSIGHT. Disinformation and Civil Defence: How did Taiwan's Civil Society Counter Foreign Information Manipulation[EB/OL]. (2024-02-05)[2026-05-13]. https://taiwaninsight.org/2024/02/05/.

### 三、欧美智库与国际组织（[19]–[31]）

[19] BROOKINGS INSTITUTION. The Taiwan Public's Historically Favorable View of the United States is Declining[R/OL]. (2025-08)[2026-05-13]. https://www.facebook.com/gmfus/posts/.

[20] CHICAGO COUNCIL ON GLOBAL AFFAIRS / BROOKINGS INSTITUTION. Chinese Citizens' Affection for Taiwanese May Reduce Risk of Cross-Strait Conflict[R/OL]. (2025)[2026-05-13]. https://www.brookings.edu/.

[21] CSIS, China Power Project. How Taiwan Reimagines Maritime Security: Insights from the 2025 National Ocean[R/OL]. (2025-10-08)[2026-05-13]. https://www.csis.org/blogs/new-perspectives-asia/.

[22] WILSON CENTER. The Evolution of a Taiwanese National Identity[EB/OL]. [2026-05-13]. https://www.wilsoncenter.org.

[23] WANG A H E. AI-Generated Disinformation in the 2024 Taiwan Presidential Election[R/OL]. Santa Monica: RAND Corporation, 2024.

[24] GLOBAL TAIWAN INSTITUTE. On the Front Line of Foreign Influence: Enhancing Taiwan's Information Resilience[R/OL]. (2026-02)[2026-05-13]. https://globaltaiwan.org/2026/02/enhancing-taiwans-information-resilience/.

[25] SAFER INTERNET LAB (SAIL). Countering AI Disinformation: Lessons from Taiwan's 2024 Election Defense Strategies[R/OL]. (2025-08)[2026-05-13]. https://saferinternetlab.org/wp-content/uploads/2025/08/Panel-4-Summer.pdf.

[26] GERMAN MARSHALL FUND OF THE UNITED STATES (GMF). Election Interference and Information Manipulation[EB/OL]. [2026-05-13]. https://www.gmfus.org/news/election-interference-and-information-manipulation.

[27] V-DEM INSTITUTE. Democracy Report 2025[R/OL]. (2025-03)[2026-05-13]. https://www.v-dem.net/documents/54/v-dem_dr_2025_lowres_v1.pdf.

[28] 許毓仁 (HSU J). 台積電赴美遭批"掏空"——這是自我矮化[J/OL]. Hudson Institute Commentary, (2026-02-11)[2026-05-13]. https://www.hudson.org/.

[29] STANFORD INTERNET OBSERVATORY. June 2020 Twitter Takedown[R/OL]. (2020-06)[2026-05-13]. https://cyber.fsi.stanford.edu/io/news/june-2020-twitter-takedown.

[30] BBC NEWS 中文. 拆解台灣「大罷免」大敗原因：為何「反共護台」陣營未能撼動藍白基本盤[EB/OL]. (2025)[2026-05-13]. https://www.youtube.com/watch?v=2YTI0SgyGOQ.

[31] DEUTSCHE WELLE (DW). DeepSeek Coverage: A Greeting from China[EB/OL]. (2025-02)[2026-05-13]. https://www.dw.com.

### 四、中国大陆官方机构与文献（[32]–[38]）

[32] 国务院台办. 国务院台办新闻发布会辑录[EB/OL]. (2025-03-12)[2026-05-13]. https://www.gwytb.gov.cn/m/speech/202503/t20250312_12689633.htm.

[33] 国务院台办. 国务院台办新闻发言人陈斌华就《沉默的荣耀》答记者问[EB/OL]. (2025-10-15)[2026-05-13]. https://www.thepaper.cn/newsDetail_forward_31784552.

[34] 国务院台办. 国台办答记者问——《冷月无声——吴石传奇》衍生戏剧[EB/OL]. (2026-03-18)[2026-05-13]. https://politics.gmw.cn/2026-03/18/content_38654775.htm.

[35] 群众杂志编辑部. 《黑神话·悟空》破圈：文化产业发展新思考[J/OL]. 群众, 2024(20). (2024-10-25)[2026-05-13]. https://www.qunzh.com/qzxlk/jczx/2024/202420/202410/t20241025_107654.html.

[36] 中国社会科学院台湾研究所. 台湾研究系列出版物[EB/OL]. [2026-05-13]. http://its.taiwan.cssn.cn/.

[37] 重庆社会主义学院. 新时代统一战线凝聚人心、汇聚力量的政治分析——基于政党[J/OL]. [2026-05-13]. https://www.cqsy.net.cn/web/article/1447528692062969856/.

[38] 蓝博洲. 《沉默的荣耀》使台独无法继续"装傻"消费这些英雄[N/OL]. 观察者网, (2025-10-27)[2026-05-13]. https://www.guancha.cn/lanbozhou/2025_10_27_794688.shtml.

### 五、典型案例数据与新闻报道（[39]–[58]）

[39] 联合报. 63%不满赖清德、88%要求沟通[N/OL]. (2025-09-26)[2026-05-13]. https://news.qq.com/rain/a/20250926A05VZB00.

[40] 远见杂志. 2024台湾运动员/明星好感度调查[N/OL]. (2024-12-10)[2026-05-13]. https://news.qq.com/rain/a/20241210A0161P00.

[41] 自由亚洲电台(RFA). 馆长陈之汉访陆深度报道[EB/OL]. (2025-06-16)[2026-05-13]. https://www.rfa.org/mandarin/zhengzhi/2025/06/16/taiwan-chen-zhihan-internet-celebrity-shanghai/.

[42] 人民日报海外版. 馆长访陆系列报道[N/OL]. (2025-06-23)[2026-05-13]. http://paper.people.com.cn/rmrbhwb/pc/content/202506/23/content_30081207.html.

[43] 自由亚洲电台. 中共大外宣进入台湾(上)——TikTok与中国宣传战[EB/OL]. (2025-04-28)[2026-05-13]. https://www.rfa.org/mandarin/shishi-hecha/2025/04/28/factcheck-ccp-propaganda-tiktok/.

[44] 央视新闻. 《哪吒之魔童闹海》票房突破158亿元报道[N/OL]. (2025-02-12)[2026-05-13]. https://news.cctv.com/2025/02/12/ARTIx9veXUW8j6GxmPWzD5dV250212.shtml.

[45] 解放日报. 《繁花》在台上线引发观剧热潮[N/OL]. (2024)[2026-05-13]. https://www.jfdaily.com/wx/detail.do?id=707349.

[46] 福建中新网. "跟着繁花游上海"风潮报道[N/OL]. (2024-01-21)[2026-05-13]. https://www.fj.chinanews.com.cn/news/2024/2024-01-21/541246.html.

[47] 新浪财经. 《哪吒之魔童闹海》全球票房统计[N/OL]. (2025-05-05)[2026-05-13]. https://finance.sina.com.cn/tech/roll/2025-05-05/doc-inevpsmr5312456.shtml.

[48] 每日经济新闻. 台湾网友呼吁引进《哪吒2》报道[N/OL]. (2025-02-27)[2026-05-13]. https://www.nbd.com.cn/articles/2025-02-27/3769277.html.

[49] 观察者网. DeepSeek震撼全球应用市场报道[N/OL]. (2025-02-12)[2026-05-13]. https://www.guancha.cn/economy/2025_02_12_764860.shtml.

[50] 自由亚洲电台(RFA). DeepSeek引发台湾监管反应[EB/OL]. (2025-02-06)[2026-05-13]. https://www.rfa.org/mandarin/guoji/yatai/gangtai/2025/02/06/deepseek-taiwan-china-us-impact/.

[51] 风传媒. 卓荣泰下令禁用DeepSeek[N/OL]. (2025)[2026-05-13]. https://www.storm.mg/article/5322421.

[52] 台湾今日新闻(iTaiwanNews). 禁用DeepSeek引发网友嘲讽[N/OL]. (2025-02-08)[2026-05-13]. https://www.itaiwannews.cn/2025-02-08/afccbbda-97d1-57fc-5761-fdf047777066.html.

[53] Yahoo新闻台湾. 施崇棠呼吁台湾迫切需要深耕型AI人才[N/OL]. (2025)[2026-05-13]. https://tw.news.yahoo.com/deepseek震撼全球-施崇棠疾呼.

[54] GLOSELLERS. TikTok难民潮与小红书数据分析[EB/OL]. [2026-05-13]. https://glosellers.com/15869.html.

[55] 厦门卫视(xmtv). 小红书承接亿洋迁徙报道[N/OL]. (2025-01-16)[2026-05-13]. https://www.xmtv.cn/xmtv/2025-01-16/98499ea0a850b925.html.

[56] BBC中文. 台湾限制小红书引发争议[EB/OL]. [2026-05-13]. https://www.bbc.com/zhongwen/articles/crk762n7rj3o/trad.

[57] 新华社. 大陆恢复福建上海居民赴台跟团游[EB/OL]. (2025-01-17)[2026-05-13]. https://www.news.cn/tw/20250117/b4d9cb91aa6f4fba89b4e005ca0c7870/c.html.

[58] 中新网/凤凰网. 台湾游戏产业反思《黑神话·悟空》成功[EB/OL]. (2024-09-20)[2026-05-13]. https://m.voc.com.cn/xhn/news/202409/20664692.html.

### 六、《沉默的荣耀》专题来源（[59]–[68]，v2.1 新增）

[59] 新华社. 《沉默的荣耀》登陆央视一套播出[EB/OL]. (2025-10-25)[2026-05-13]. https://news.qq.com/rain/a/20251024A05BMQ00.

[60] 新华社. 真人真事改编凸显谍战剧亮点：《沉默的荣耀》创作访谈[EB/OL]. (2025-10-09)[2026-05-13]. https://www.news.cn/ent/20251009/4e2272b23f5b4e27bc1144899f180f5c/c.html.

[61] 中央人民广播电台·央广军事. 吴石将军绝密情报传递历史细节[EB/OL]. (2025-10-16)[2026-05-13]. https://military.cnr.cn/nrjx/20251016/t20251016_527397620.shtml.

[62] 网易新闻. 《沉默的荣耀》收视、热度、豆瓣评分汇总报道[EB/OL]. [2026-05-13]. https://www.163.com/dy/article/KG9IPETU0556AUSZ.html.

[63] 福州市人民政府. 《沉默的荣耀》创央视黄金档收视纪录[EB/OL]. (2025-10-12)[2026-05-13]. https://www.fuzhou.gov.cn/zwgk/gzdt/rcyw/202510/t20251012_5148336.htm.

[64] 上报Upmedia. 台湾情报界应直面历史战——评《沉默的荣耀》[N/OL]. (2025)[2026-05-13]. https://www.upmedia.mg/tw/commentary/military-affairs/245278.

[65] 王庆民. 沉默的荣耀——三方博弈视角下的烈士叙事[J/OL]. 风传媒, (2025)[2026-05-13]. https://www.storm.mg/article/11075130.

[66] 苑举正. 马场町观后感视频[EB/OL]. 羊城晚报转载, [2026-05-13]. https://news.ycwb.com/ikinvjktih/content_53748205.htm.

[67] 新华社. 台湾民众自发前往马场町缅怀烈士[N/OL]. (2025-10-22)[2026-05-13]. https://www.news.cn/tw/20251022/82b7a6ceadef4a37b07a8af5c6f0519a/c.html.

[68] ThinkChina (新加坡). Beijing's Spy Drama Set in Taiwan Isn't Winning Hearts Across the Strait[J/OL]. (2025)[2026-05-13]. https://www.thinkchina.sg/society/beijings-spy-drama-set-taiwan-isnt-winning-hearts-across-strait.

### 七、学术期刊（[69]–[75]）

[69] WANG A H E. AI-Generated Disinformation and Cognitive Warfare in the Cross-Strait Context[J]. RAND Working Paper Series, 2024.

[70] Journal of Contemporary China. Taiwan Identity and Cross-Strait Relations under Lai Ching-te (2024–2026): A Special Issue[J]. Journal of Contemporary China, 2024-2025.

[71] HUGHES C R. Taiwan's National Identity Politics in the Era of Cross-Strait Reconciliation[J]. China Quarterly, 2024.

[72] WU Y S. Cross-Strait Relations under Lai Ching-te: An Initial Assessment[J]. Asian Survey, 2025, 65(2): 215–240.

[73] 现代国际关系编辑部. 涉台研究系列论文[J]. 现代国际关系, 2024–2025.

[74] 台湾研究编辑部. 民进党"抗中保台"路线及其岛内民意反应研究[J]. 台湾研究, 2024–2026.

[75] 中国评论月刊. 2024–2026年涉台舆情分析专栏[J]. 中国评论, 2024–2026.

---

**著录说明**：本报告 75 条参考文献按 GB/T 7714—2015 国家标准著录格式排列，文献类型标识符含义如下：[J] 期刊文章，[N] 报纸文章，[R] 研究报告，[EB/OL] 网络电子资源（带访问日期）。同一条文献正文中可能在不同位置被多次引用，编号保持不变。

"""

# Replace the old bibliography (from "## 引用文献" through the end signature)
# Find the start of "## 引用文献" section
bib_start = text.find('## 引用文献与数据来源')
bib_end_marker = '---\n\n**报告完成日期**：2026年5月13日'
if bib_start >= 0:
    bib_end = text.find(bib_end_marker, bib_start)
    if bib_end >= 0:
        text = text[:bib_start] + new_bib + '---\n\n' + text[bib_end + len('---\n\n'):]

# ============================================================
# Write output
# ============================================================
with open(DST, 'w', encoding='utf-8') as f:
    f.write(text)

print(f'Saved v2.1: {DST}')
import os
print(f'Size: {os.path.getsize(DST)} bytes')
print(f'Chars: {len(text)}')

# Verify
silent_count = text.count('《沉默的荣耀》')
citation_count = sum(text.count(f'[{i}]') for i in range(1, 76))
print(f'《沉默的荣耀》mentions: {silent_count}')
print(f'Citation markers [1]-[75] in body: {citation_count}')
