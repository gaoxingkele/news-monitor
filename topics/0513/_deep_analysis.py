"""Parallel deep-analysis via Grok-4 (live search) + Gemini 2.5 Pro."""
import os, json, requests, concurrent.futures
from dotenv import load_dotenv
load_dotenv(r'D:\aicoding\news-monitor\.env')

GROK_KEY = os.getenv('GROK_API_KEY')
GEMINI_KEY = os.getenv('GEMINI_API_KEY')
PROXY = os.getenv('LLM_PROXY')
PROXIES = {'http': PROXY, 'https': PROXY} if PROXY else None

CORPUS = open('_research_corpus.txt', 'r', encoding='utf-8').read()
V1 = open('v1_extracted.md', 'r', encoding='utf-8').read()

# Six focused analysis prompts
PROMPTS = {
    "01_polls_data": """你是一位资深台湾问题研究专家。请基于以下背景资料（v1初稿 + 检索语料），系统梳理2024年5月赖清德上台至2026年5月之间，台湾岛内所有重要民调机构（联合报、TVBS、远见、台湾民意基金会、美丽岛电子报、政治大学选研中心、Mainland Affairs Council 陆委会、Pew、Lowy 等）发布的关键数据，覆盖：(1) 赖清德施政满意度、(2) 两岸关系认知、(3) 经济民生不满、(4) 疑美论与避战求和、(5) 统独/身份认同、(6) 各年龄段/职业代际差异。要求每一条数据都带 来源+时间+样本量+具体百分比。最终输出4500字以上的中文资料综述，按时间线和议题双轴交叉编排，方便后续报告引用。""",

    "02_fimi_aigc": """你是认知战与信息操弄领域学者。请基于背景资料 + 你掌握的最新公开报告，深度梳理2024-2026年针对台湾的境外信息操弄（FIMI）与AIGC武器化最新态势：(1) Doublethink Lab 2024选举监测核心发现与方法论；(2) IORG 2024信息环境调查最新数据；(3) Safer Internet Lab 关于AI虚假信息选举防御的报告；(4) GMF、CSIS、Stanford Internet Observatory、V-Dem 的台湾相关分析；(5) 协同性虚假行为（CIB）的TTP演进；(6) Deepfake/虚拟主播/AI克隆语音在2024-2025选举/政治议题中的具体案例；(7) TikTok对台湾Z世代的精准推播与渗透。每一条都要带 机构+报告名+发布日期+核心数据点。中文输出4500字以上。""",

    "03_positive_cases": """你是文化传播与两岸交流研究者。请深度刻画2024-2026年间所有重大"正向破圈"案例：(A)《黑神话·悟空》：销量、Steam全球同时在线、Metacritic评分、岛内媒体评论（中时/联合报/经济日报/赵少康原文）、岛内玩家社群反应、对台湾游戏产业焦虑的发酵；(B) 郑钦文奥运夺金 + 全红婵跳水 + 大陆运动员在台引发反应；(C) 馆长陈之汉 2024-2025 多次访陆Vlog（北京/上海/厦门）的观看数据、留言抽样、对绿营叙事冲击；(D) 大陆爆款影视/动画《繁花》《哪吒2》《长安三万里》在台收视/票房/口碑；(E) DeepSeek-R1/Qwen等大陆AI产品在台冲击与媒体反响；(F) 小红书"TikTok refugee"潮 + 抖音爆款内容跨海传播；(G) 2025赴陆旅游解禁/陆生交流；(H) 中华文化IP（如《黑神话》道教/西游元素）在年轻世代触发的文化基因唤醒数据。要求每个案例必须有：时间、规模数据、传播路径、岛内反应抽样。中文6000字以上。""",

    "04_negative_cases": """你是台湾政治观察者。请深度复盘2024-2026年间所有重大"反向破圈"（民进党/赖清德政治动员失败、引发全民反噬）案例：(A) 726/823 两波大罢免：投票率、24+7选区结果、民调认同度、对赖支持率反噬数据；(B) 国会改革法案/释宪争议/青鸟运动后续；(C) 万里赖皮寮违建争议；(D) 2025总预算冻删/朝野对抗；(E) 卓荣泰内阁满意度滑落历程；(F) 台积电亚利桑那2纳米/4纳米转移引发的"美积电"危机舆情；(G) 鸡蛋荒/缺蛋/进口蛋疑云后续；(H) 汉光演习扰民/全社会防卫动员的民意反弹；(I) 赖清德历次失言（"杂质论"、"中国威胁论"等）民调反噬；(J) 反共网军侧翼翻车事件（如柯志恩诽谤案、王义川大数据案等）。每个案例：时间、操作手法、舆情转折点、民调数据、舆论场反噬规律。中文6000字以上。""",

    "05_international_views": """你是国际关系学者。请深度梳理2024-2026年欧美智库与权威期刊关于台湾舆情、认同、破圈、信息战的最新分析。要求覆盖：Brookings、CSIS、CFR、RAND、Wilson Center、GMF、Lowy Institute、Global Taiwan Institute、Hudson、AEI、Carnegie；以及期刊 Foreign Affairs、Foreign Policy、The Diplomat、Journal of Contemporary China、China Quarterly、Asian Survey 等的代表性文章。每条记录：作者、机构、文章题目、发表时间、核心论点、关键数据/引言。特别关注：(1) Taiwan identity/中华民族认同的国际学者解读；(2) "Silicon Shield"瓦解论；(3) 美国对台政策延续性与川普2.0冲击；(4) "Cognitive warfare"框架下对台分析；(5) 大陆"软实力"破圈的西方观察。中文5000字以上，可附原文金句中英对照。""",

    "06_grok_realtime": """请用grok-4-latest 模型的 Live Search 功能（如果支持），抓取过去90天X平台（推特）、中文社群上关于"台湾 同温层"、"赖清德 民调"、"大罢免"、"黑神话 悟空 台湾"、"馆长 大陆"、"疑美论"、"台积电 美国"等关键词的热度变化趋势，识别TOP 10 推手账号、TOP 10高互动议题/帖子，并对岛内蓝绿白阵营、年轻人/中老年Line群组、TikTok/抖音/YouTube/小红书各平台的舆情温差做一次量化或半量化的对比分析。中文输出3500字以上，附具体账号/帖子URL与互动量。""",
}


def call_grok(name, prompt, use_live=False):
    body = {
        'model': 'grok-4-latest',
        'messages': [
            {'role': 'system', 'content': '你是高水准的中文政治传播研究者，输出必须准确、可引用、具体到数据点。'},
            {'role': 'user', 'content': prompt},
        ],
        'temperature': 0.2,
    }
    if use_live:
        body['search_parameters'] = {
            'mode': 'auto',
            'max_search_results': 20,
            'return_citations': True,
        }
    try:
        r = requests.post(
            'https://api.x.ai/v1/chat/completions',
            headers={'Authorization': f'Bearer {GROK_KEY}', 'Content-Type': 'application/json'},
            json=body, timeout=600, proxies=PROXIES,
        )
        if r.status_code == 200:
            data = r.json()
            content = data['choices'][0]['message']['content']
            citations = data.get('citations', [])
            return {'name': name, 'engine': 'grok', 'content': content, 'citations': citations}
        return {'name': name, 'engine': 'grok', 'error': r.status_code, 'msg': r.text[:500]}
    except Exception as e:
        return {'name': name, 'engine': 'grok', 'error': str(e)}


def call_gemini(name, prompt, model='gemini-2.5-pro'):
    body = {
        'contents': [{'parts': [{'text': prompt}]}],
        'generationConfig': {'temperature': 0.2, 'maxOutputTokens': 16384},
    }
    try:
        r = requests.post(
            f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_KEY}',
            json=body, timeout=600, proxies=PROXIES,
        )
        if r.status_code == 200:
            data = r.json()
            text = data['candidates'][0]['content']['parts'][0]['text']
            return {'name': name, 'engine': f'gemini-{model}', 'content': text}
        return {'name': name, 'engine': f'gemini-{model}', 'error': r.status_code, 'msg': r.text[:500]}
    except Exception as e:
        return {'name': name, 'engine': f'gemini-{model}', 'error': str(e)}


def build_full_prompt(p, with_corpus=True):
    parts = []
    parts.append('# 任务')
    parts.append(p)
    if with_corpus:
        parts.append('\n\n# v1 报告初稿（供参考但不抄）')
        parts.append(V1[:30000])
        parts.append('\n\n# 检索语料（标题+URL+摘要，约24万字符）')
        # truncate corpus to fit
        parts.append(CORPUS[:170000])
    parts.append('\n\n请基于以上材料给出严谨、可引用、具体到数据点的中文分析，禁止泛泛而谈，禁止编造数据，所有具体数字若来自语料须附 [来源/URL] 标注。')
    return '\n'.join(parts)


def main():
    jobs = []
    # Mix grok and gemini for redundancy
    # Polls / FIMI / international -> gemini 2.5 pro (large context, factual)
    # Cases -> gemini 2.5 pro (long output)
    # Grok realtime -> grok-4 with live search
    plan = [
        ('01_polls_data', 'gemini-2.5-pro', True, False),
        ('02_fimi_aigc', 'gemini-2.5-pro', True, False),
        ('03_positive_cases', 'gemini-2.5-pro', True, False),
        ('04_negative_cases', 'gemini-2.5-pro', True, False),
        ('05_international_views', 'gemini-2.5-pro', True, False),
        ('06_grok_realtime', 'grok-static', True, False),
    ]
    print(f'Total jobs: {len(plan)}', flush=True)

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
        futs = {}
        for name, engine, with_corpus, live in plan:
            prompt_full = build_full_prompt(PROMPTS[name], with_corpus=with_corpus)
            if engine == 'grok-live':
                f = ex.submit(call_grok, name, PROMPTS[name], use_live=True)
            elif engine == 'grok-static':
                f = ex.submit(call_grok, name, prompt_full, use_live=False)
            elif engine.startswith('gemini'):
                f = ex.submit(call_gemini, name, prompt_full, model=engine)
            else:
                f = ex.submit(call_grok, name, prompt_full, use_live=False)
            futs[f] = name

        results = {}
        for f in concurrent.futures.as_completed(futs):
            name = futs[f]
            res = f.result()
            results[name] = res
            ok = 'content' in res
            chars = len(res.get('content', '')) if ok else 0
            print(f'[{name}] engine={res.get("engine")} ok={ok} chars={chars} err={res.get("error","")}', flush=True)

    with open('_deep_analysis.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    # Also save each as MD
    for name, res in results.items():
        with open(f'_deep_{name}.md', 'w', encoding='utf-8') as f:
            f.write(f'# {name}\n\n')
            f.write(f'Engine: {res.get("engine","")}\n\n')
            if 'content' in res:
                f.write(res['content'])
            else:
                f.write(f'ERROR: {res}')
            if res.get('citations'):
                f.write('\n\n## Citations\n')
                for c in res['citations']:
                    f.write(f'- {c}\n')
    print('Saved.')


if __name__ == '__main__':
    main()
