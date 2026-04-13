"""蒋万安 Tier-0：结构化公开数据（中选会/监察院/立法院/公督盟）。

因国内直接爬台湾政府网站受限，采用搜索引擎获取镜像/报道数据后 LLM 提取。
"""
from __future__ import annotations

from people.data_collection.models import SearchTask

TIER0_TASKS: list[SearchTask] = [
    SearchTask(
        task_id="T0-02", gap_id=2, tier=0,
        title="中选会2022台北市长12行政区得票明细",
        queries_zh=[
            "2022 台北市長選舉 各行政區 得票數 蔣萬安 陳時中 黃珊珊",
            "2022 台北市長 選舉結果 信義區 大安區 中山區 松山區 得票率",
            "111年 直轄市長選舉 台北市 各區得票 中選會",
        ],
        queries_en=["2022 Taipei mayor election results by district Chiang Chen Huang"],
        engines=["brave", "tavily", "gemini"],
        max_results_per_engine=15,
        extraction_schema="""\
提取2022年台北市长选举12个行政区的详细得票数据，输出格式：
每个行政区一条记录，含：区名、蒋万安得票数、蒋万安得票率、陈时中得票数、陈时中得票率、黄珊珊得票数、黄珊珊得票率、投票率。
如果能找到总得票数也一并提取：蒋万安575590票42.29%、陈时中407842票29.95%、黄珊珊342141票25.14%。""",
        v6_module="B模块七 7.1-7.2",
    ),
    SearchTask(
        task_id="T0-03", gap_id=3, tier=0,
        title="监察院财产申报数据",
        queries_zh=[
            "蔣萬安 財產申報 監察院 不動產 存款 2022 2023 2024",
            "蔣萬安 陽光法案 財產 土地 房產",
            "蔣萬安 財產 公職人員 申報 變動",
        ],
        engines=["brave", "tavily"],
        extraction_schema="逐年财产申报数据：年份、不动产（坐落/面积/取得时间）、存款总额、有价证券、汽车、债务，以及年度变动情况。",
        v6_module="B模块十一 11.1",
    ),
    SearchTask(
        task_id="T0-04", gap_id=4, tier=0,
        title="2022政治献金会计报告",
        queries_zh=[
            "蔣萬安 2022 政治獻金 會計報告 企業捐款",
            "蔣萬安 台北市長 選舉 政治獻金 總額 營利事業",
            "蔣萬安 政治獻金 建商 不動產 捐款",
        ],
        engines=["brave", "tavily"],
        extraction_schema="2022年台北市长选举政治献金：总收入、个人捐款总额、营利事业捐款总额、Top5企业捐款来源（公司名+金额）、支出总额。",
        v6_module="B模块十一 11.9",
    ),
    SearchTask(
        task_id="T0-05", gap_id=5, tier=0,
        title="立法院三届提案与出席记录",
        queries_zh=[
            "蔣萬安 立法委員 提案 法案 第8屆 第9屆 第10屆 數量",
            "蔣萬安 立法院 出席率 質詢 委員會 司法法制",
            "蔣萬安 立委 問政 成績 提案數 主提案",
        ],
        engines=["brave", "tavily"],
        extraction_schema="第8/9/10届立委任期：主提案数、共同提案数、院会出席率、委员会出席率、质询次数、重要法案参与记录。",
        v6_module="B模块六 6.1-6.3",
    ),
    SearchTask(
        task_id="T0-06", gap_id=6, tier=0,
        title="公督盟评鉴数据",
        queries_zh=[
            "蔣萬安 公督盟 評鑑 優秀立委 第8屆 第9屆 第10屆",
            "蔣萬安 公民監督國會聯盟 立委 評分 等級",
            "公督盟 蔣萬安 問政品質 表現",
        ],
        engines=["brave", "tavily"],
        extraction_schema="公督盟第8/9/10届逐会期评�的等级（优秀/待观察等）、具体评分项目、排名。",
        v6_module="B模块六 6.7",
    ),
]


def get_all_tier0_tasks() -> list[SearchTask]:
    return TIER0_TASKS
