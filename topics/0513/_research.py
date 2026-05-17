"""Parallel research script for Taiwan echo chamber v2.0 report."""
import os, json, time, sys
import requests
import concurrent.futures
from dotenv import load_dotenv

load_dotenv(r'D:\aicoding\news-monitor\.env')

BRAVE_KEY = os.getenv('BRAVEAPI')
TAVILY_KEY = os.getenv('tavilyapi')
PROXY = os.getenv('LLM_PROXY')
PROXIES = {'http': PROXY, 'https': PROXY} if PROXY else None

# Research queries by topic
QUERIES = {
    "polls_2025": [
        "台湾民意基金会 2025 民调",
        "TVBS 赖清德 满意度 民调 2025",
        "联合报 两岸关系年度大调查 2025",
        "远见杂志 民调 2025 台湾",
        "Taiwan public opinion 2025 cross-strait",
        "台湾 经济 物价 民调 不满 2025",
        "台湾 年度汉字 2025 罢 诈 淹",
        "美丽岛电子报 民调 2025",
    ],
    "demographics": [
        "Z世代 台湾 政治 立场 2025",
        "台湾 年轻人 短视频 TikTok 抖音 2025",
        "台湾 中坚世代 经济 焦虑 房贷",
        "台湾 中老年 Line 群组 假信息",
        "台湾 选民 结构 分裂 2024",
    ],
    "fimi_aigc": [
        "Doublethink Lab Taiwan 2024 election disinformation",
        "IORG 台湾 信息环境 2024 报告",
        "Taiwan deepfake election 2024 AIGC",
        "Coordinated Inauthentic Behavior Taiwan CIB",
        "Safer Internet Lab Taiwan AI disinformation",
        "Stanford Internet Observatory Taiwan",
        "RAND Taiwan information warfare 2024",
        "V-Dem Taiwan democracy 2025",
    ],
    "positive_breakthroughs": [
        "黑神话 悟空 台湾 销量 反响 2024",
        "黑神话 悟空 台湾 媒体 评论",
        "馆长 陈之汉 大陆 旅游 vlog 反响",
        "DeepSeek 台湾 反响 震撼",
        "哪吒2 票房 台湾 反响 2025",
        "繁花 台湾 收视 评价",
        "郑钦文 台湾 反应 奥运",
        "小红书 台湾 用户 TikTok refugee 2025",
        "台湾 旅游 大陆 解禁 2025",
        "全红婵 台湾 关注",
    ],
    "negative_breakthroughs": [
        "大罢免 726 投票结果 全数否决",
        "大罢免 823 第二波 失败",
        "万里 赖皮寮 违建 争议",
        "台积电 亚利桑那 美国 掏空",
        "卓荣泰 内阁 民调 满意度",
        "蛋荒 进口蛋 民进党",
        "立法院 国会改革 释宪 民进党",
        "汉光 演习 扰民 民众",
        "2025 中央政府总预算 冻删",
        "民进党 抗中 失败 选举",
        "赖清德 失言 民调 下滑",
    ],
    "international_thinktanks": [
        "Brookings Taiwan public opinion 2025",
        "CSIS Taiwan information operations 2025",
        "Wilson Center Taiwan identity",
        "Foreign Affairs Taiwan 2025 election",
        "Foreign Policy Taiwan disinformation",
        "Lowy Institute Taiwan poll",
        "Pew Research Taiwan China",
        "Election Study Center Taiwan identity 2024",
        "Mainland Affairs Council Taiwan poll 2025",
        "Global Taiwan Institute report 2025",
    ],
    "academic_journals": [
        "Journal of Contemporary China Taiwan 2024",
        "现代国际关系 台湾 同温层 2024",
        "台湾研究 民进党 抗中保台",
        "群众杂志 黑神话 文化破圈",
        "中评社 台湾民意 2025",
        "Information Manipulation Taiwan academic",
        "Echo chamber Taiwan political polarization journal",
    ],
}


def brave_search(q, count=5):
    try:
        r = requests.get(
            'https://api.search.brave.com/res/v1/web/search',
            headers={'X-Subscription-Token': BRAVE_KEY, 'Accept': 'application/json'},
            params={'q': q, 'count': count},
            timeout=20, proxies=PROXIES,
        )
        if r.status_code == 200:
            data = r.json()
            results = []
            for item in data.get('web', {}).get('results', [])[:count]:
                results.append({
                    'title': item.get('title', ''),
                    'url': item.get('url', ''),
                    'desc': item.get('description', ''),
                })
            return {'engine': 'brave', 'query': q, 'results': results}
        return {'engine': 'brave', 'query': q, 'error': r.status_code, 'msg': r.text[:200]}
    except Exception as e:
        return {'engine': 'brave', 'query': q, 'error': str(e)}


def tavily_search(q, max_results=5):
    try:
        r = requests.post(
            'https://api.tavily.com/search',
            json={'api_key': TAVILY_KEY, 'query': q,
                  'max_results': max_results, 'search_depth': 'advanced',
                  'include_answer': False},
            timeout=30, proxies=PROXIES,
        )
        if r.status_code == 200:
            data = r.json()
            results = []
            for item in data.get('results', [])[:max_results]:
                results.append({
                    'title': item.get('title', ''),
                    'url': item.get('url', ''),
                    'desc': item.get('content', '')[:400],
                })
            return {'engine': 'tavily', 'query': q, 'results': results}
        return {'engine': 'tavily', 'query': q, 'error': r.status_code, 'msg': r.text[:200]}
    except Exception as e:
        return {'engine': 'tavily', 'query': q, 'error': str(e)}


def main():
    all_results = {}
    tasks = []
    for topic, queries in QUERIES.items():
        for q in queries:
            tasks.append((topic, q, 'brave'))
            tasks.append((topic, q, 'tavily'))

    print(f'Total tasks: {len(tasks)}', flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
        futures = {}
        for topic, q, engine in tasks:
            if engine == 'brave':
                f = ex.submit(brave_search, q)
            else:
                f = ex.submit(tavily_search, q)
            futures[f] = (topic, q, engine)

        for i, f in enumerate(concurrent.futures.as_completed(futures)):
            topic, q, engine = futures[f]
            res = f.result()
            all_results.setdefault(topic, []).append(res)
            if (i + 1) % 10 == 0:
                print(f'Progress: {i+1}/{len(tasks)}', flush=True)

    out = r'D:\aicoding\news-monitor\topics\0513\_research_raw.json'
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f'Done. Saved to {out}', flush=True)

    # Summary
    for topic, items in all_results.items():
        ok = sum(1 for it in items if 'results' in it and it['results'])
        print(f'  {topic}: {ok}/{len(items)} non-empty')

if __name__ == '__main__':
    main()
