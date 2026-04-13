"""蒋万安 v1.0→v1.1 采集任务清单 —— 基于四专家评审汇总的 30 项缺陷。"""
from __future__ import annotations

from people.data_collection.models import SearchTask

# ────────────────────────────────────────────────
#  Tier 1：新闻检索类任务（搜索API+LLM提取）
# ────────────────────────────────────────────────

TIER1_TASKS: list[SearchTask] = [
    # --- A组：历史与谱系 ---
    SearchTask(
        task_id="T1-07", gap_id=7, tier=1,
        title="章孝严非婚生认祖全过程",
        queries_zh=[
            "章孝嚴 蔣孝嚴 DNA 認祖 改姓 2005",
            "章亞若 桂林 1942 死因 蔣經國",
            "蔣經國 非婚生子 章孝慈 章孝嚴 身世",
        ],
        queries_en=["Zhang Xiaoyan Chiang Hsiao-yen DNA paternity"],
        engines=["brave", "tavily"],
        extraction_schema="章孝严认祖改姓的完整时间线（关键日期、DNA鉴定、法律程序、政治影响），章亚若身份与死亡疑云",
        v6_module="B模块一 1.2/1.5",
    ),
    SearchTask(
        task_id="T1-08", gap_id=8, tier=1,
        title="蒋家谱系上五代下二代",
        queries_zh=[
            "蔣萬安 家族 家譜 蔣經國 蔣孝嚴",
            "蔣萬安 配偶 石舫亘 子女",
            "蔣經國 子女 蔣孝文 蔣孝武 蔣孝勇 蔣孝慈 蔣孝嚴",
        ],
        queries_en=["Chiang family tree Chiang Ching-kuo descendants"],
        engines=["brave", "gemini"],
        extraction_schema="完整家族谱系（上五代到下二代），含直系与旁系人物、配偶、职业",
        v6_module="B模块一 1.1",
    ),
    SearchTask(
        task_id="T1-09", gap_id=9, tier=1,
        title="228参与记录（逐年）",
        queries_zh=[
            "蔣萬安 二二八 紀念 參加 致詞 2018",
            "蔣萬安 二二八 紀念 參加 致詞 2019",
            "蔣萬安 二二八 紀念 參加 致詞 2020",
            "蔣萬安 二二八 紀念 2021 2022 2023",
            "蔣萬安 二二八 紀念 2024 2025 2026 道歉",
            "蔣萬安 二二八 蔣經國 白色恐怖 轉型正義",
        ],
        engines=["brave", "tavily"],
        extraction_schema="逐年228参与记录表：年份、活动名称、地点、发言内容摘要、与父辈对照",
        v6_module="B模块一 1.5 / 模块三 3.2",
    ),
    SearchTask(
        task_id="T1-11", gap_id=11, tier=1,
        title="蒋经国戒严角色与白色恐怖数据",
        queries_zh=[
            "蔣經國 戒嚴 白色恐怖 政治犯 促轉會 人數 統計",
            "蔣萬安 回應 轉型正義 威權 蔣經國 歷史",
        ],
        engines=["brave"],
        extraction_schema="蒋经国戒严时期角色、白色恐怖受害者数据（促转会官方）、蒋万安对此的公开表态",
        v6_module="B模块三 3.2",
    ),

    # --- B组：两岸与三角联动 ---
    SearchTask(
        task_id="T1-12", gap_id=12, tier=1,
        title="2019反一国两制'四个必须'原话",
        queries_zh=[
            "蔣萬安 2019 一月 四個必須 反對 一國兩制",
            "蔣萬安 2019年1月3日 一國兩制 表態",
        ],
        engines=["brave", "tavily"],
        extraction_schema="蒋万安2019年1月3日受访原话全文、发言场合、媒体报道",
        v6_module="B模块九 9.4",
    ),
    SearchTask(
        task_id="T1-13a", gap_id=13, tier=1,
        title="三角联动案例：佩洛西访台",
        queries_zh=[
            "蔣萬安 裴洛西 佩洛西 訪台 2022 表態 回應",
            "蔣萬安 2022年8月 台海 危機 國民黨",
        ],
        queries_en=["Chiang Wan-an Pelosi Taiwan visit response"],
        engines=["brave", "tavily"],
        extraction_schema="蒋万安对佩洛西2022年8月访台的具体表态原文、北京反应、华府态度",
        v6_module="B模块十四 14.1",
    ),
    SearchTask(
        task_id="T1-13b", gap_id=13, tier=1,
        title="三角联动案例：美台军售/NDAA",
        queries_zh=[
            "蔣萬安 軍售 美國 台灣 NDAA 國防授權法",
            "蔣萬安 台美 軍事 合作 表態",
        ],
        queries_en=["Chiang Wan-an US arms sales Taiwan NDAA"],
        engines=["brave", "tavily"],
        extraction_schema="蒋万安对美台军售、NDAA涉台条款的具体表态",
        v6_module="B模块十四 14.2",
    ),
    SearchTask(
        task_id="T1-14", gap_id=14, tier=1,
        title="两岸城市交流前后立场对照",
        queries_zh=[
            "蔣萬安 雙城論壇 台北 上海 2023 2024 2025",
            "台北 上海 雙城論壇 重啟 蔣萬安",
            "蔣萬安 兩岸 城市 交流 文化 學術",
            "蔣萬安 訪問 大陸 中國",
        ],
        engines=["brave", "tavily"],
        extraction_schema="双城论坛参与记录、交流前后立场对照（≥3组案例）、访中记录",
        v6_module="B模块九 9.1-9.5",
    ),

    # --- C组：言行与政策 ---
    SearchTask(
        task_id="T1-16a", gap_id=16, tier=1,
        title="对美言行原文",
        queries_zh=[
            "蔣萬安 美國 AIT 訪美 表態",
            "蔣萬安 台美 關係 印太 戰略",
        ],
        queries_en=["Chiang Wan-an US Taiwan relations statement", "Chiang Wan-an AIT"],
        engines=["brave", "tavily", "grok_web"],
        extraction_schema="对美国立场的具体公开表态原文（含日期、场合、媒体来源）",
        v6_module="B模块五 5.3 / 模块十四",
    ),
    SearchTask(
        task_id="T1-16b", gap_id=16, tier=1,
        title="对日言行原文",
        queries_zh=[
            "蔣萬安 日本 東京 城市外交 訪日",
            "蔣萬安 福島 釣魚台 中日",
        ],
        engines=["brave", "tavily"],
        extraction_schema="对日本相关议题（城市外交/福岛/钓鱼岛）的具体言行记录",
        v6_module="B模块五 5.4",
    ),

    # --- D组：派系与人物关系 ---
    SearchTask(
        task_id="T1-17", gap_id=17, tier=1,
        title="与朱立伦侯友宜卢秀燕韩国瑜关系",
        queries_zh=[
            "蔣萬安 朱立倫 關係 2028 提名 黨內",
            "蔣萬安 侯友宜 關係 比較 新北",
            "蔣萬安 盧秀燕 關係 比較 台中",
            "蔣萬安 韓國瑜 關係 立法院長",
        ],
        engines=["brave", "tavily", "grok_x"],
        extraction_schema="四组关系：同台事件、互评引用、竞合态势、2028提名竞争动态",
        v6_module="B模块八 8.7",
    ),
    SearchTask(
        task_id="T1-18", gap_id=18, tier=1,
        title="与民进党关系",
        queries_zh=[
            "蔣萬安 民進黨 跨黨協商 合作 衝突",
            "蔣萬安 台北市 行政院 中央 對抗 合作",
            "蔣萬安 賴清德 陳時中 陳建仁",
        ],
        engines=["brave", "tavily"],
        extraction_schema="与民进党的合作/冲突记录、跨党立法、市府vs中央互动模式",
        v6_module="B模块八 8.8",
    ),
    SearchTask(
        task_id="T1-19", gap_id=19, tier=1,
        title="国民党派系角色与核心班底",
        queries_zh=[
            "蔣萬安 幕僚 團隊 核心 副市長 局處長",
            "國民黨 蔣萬安 派系 馬系 朱系 蔣系",
            "蔣萬安 國民黨 中常委 黨代表 青年",
        ],
        engines=["brave", "tavily"],
        extraction_schema="党内历任职务清单、核心幕僚班底（姓名/职务/背景）、派系归属证据",
        v6_module="B模块八 8.3/8.7",
    ),
    SearchTask(
        task_id="T1-21", gap_id=21, tier=1,
        title="2026九合一选举竞争态势",
        queries_zh=[
            "2026 台北市長 選舉 候選人 蔣萬安 連任",
            "2026 九合一 台北市長 民進黨 民眾黨 候選人",
            "蔣萬安 連任 優勢 劣勢 民調",
        ],
        engines=["brave", "tavily", "grok_x"],
        extraction_schema="2026台北市长选举：蒋万安优劣势、潜在竞争对手（≥5人）及比较",
        v6_module="B模块十五 15.1",
    ),

    # --- E组：补充检索 ---
    SearchTask(
        task_id="T1-25", gap_id=25, tier=1,
        title="与郑丽文关系",
        queries_zh=[
            "蔣萬安 鄭麗文 關係 同台 國民黨",
            "鄭麗文 蔣萬安 合作 衝突",
        ],
        engines=["brave", "tavily"],
        extraction_schema="同台/互评/站台/冲突记录",
        v6_module="B模块八 8.8",
    ),
    SearchTask(
        task_id="T1-26", gap_id=26, tier=1,
        title="与张亚中马英九连战洪秀柱关系",
        queries_zh=[
            "蔣萬安 張亞中 深藍 關係",
            "蔣萬安 馬英九 關係 站台 背書",
            "蔣萬安 連戰 關係",
            "蔣萬安 洪秀柱 關係",
        ],
        engines=["brave", "tavily"],
        extraction_schema="四组关系的互动证据、路线差异、世代交替线索",
        v6_module="B模块八 8.7",
    ),
    SearchTask(
        task_id="T1-27", gap_id=27, tier=1,
        title="军界影响度",
        queries_zh=[
            "蔣萬安 軍方 黃復興 退伍 眷村 軍公教",
            "蔣萬安 國防 退將 軍系 活動",
        ],
        engines=["brave", "grok_x"],
        extraction_schema="与退役将领/黄复兴系统/军公教票仓的互动记录与影响力评估",
        v6_module="B模块八 8.2 / 模块五",
    ),
    SearchTask(
        task_id="T1-28", gap_id=28, tier=1,
        title="著作立言与施政报告",
        queries_zh=[
            "蔣萬安 著作 論文 專欄 書",
            "蔣萬安 施政報告 全文 台北市 2023 2024 2025",
        ],
        queries_en=["\"Chiang Wan-an\" scholar publication"],
        engines=["brave", "gemini"],
        extraction_schema="个人著作/论文/专栏列表，施政报告关键内容摘要",
        v6_module="B模块十 10.5",
    ),
    SearchTask(
        task_id="T1-23", gap_id=23, tier=1,
        title="五大争议事件（含虐童案台智光案）",
        queries_zh=[
            "蔣萬安 爭議 台北 事件 批評",
            "蔣萬安 虐童案 台北 2024",
            "蔣萬安 台智光 爭議 2024",
            "蔣萬安 大巨蛋 爭議",
            "蔣萬安 施政 失誤 批評",
        ],
        engines=["brave", "tavily"],
        extraction_schema="五大争议事件：事件名称、时间、指控内容、蒋万安回应、证据、结论",
        v6_module="B模块十二 12.3",
    ),
    SearchTask(
        task_id="T1-29", gap_id=29, tier=1,
        title="其他党派/社会人士/宗教团体关系",
        queries_zh=[
            "蔣萬安 民眾黨 柯文哲 黃國昌 合作",
            "蔣萬安 宮廟 宗教 佛教 基督教 慈濟",
            "蔣萬安 工商 公會 不動產 建商 協會",
        ],
        engines=["brave", "tavily"],
        extraction_schema="与民众党/宗教团体/工商社团的互动记录",
        v6_module="B模块八 8.9",
    ),
    SearchTask(
        task_id="T1-24", gap_id=24, tier=1,
        title="宾大法学院+Jones Day战略人脉",
        queries_en=[
            "Chiang Wan-an Penn Law alumni",
            "Chiang Wan-an Jones Day New York attorney",
            "Chiang Wan-an CSIS Brookings think tank",
        ],
        queries_zh=["蔣萬安 賓大 法學院 校友 智庫"],
        engines=["brave", "gemini"],
        extraction_schema="海外学术/法律/智库人脉网络，与美国政策圈的具体互动记录",
        v6_module="B模块十 10.1-10.9",
    ),
]


def get_all_tier1_tasks() -> list[SearchTask]:
    return TIER1_TASKS
