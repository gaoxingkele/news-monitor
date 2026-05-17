import io, sys, asyncio
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, "src")
from dotenv import load_dotenv; load_dotenv()
from news_monitor.config_loader import load_config
from news_monitor.sources.newsapi_ai import NewsAPIAI

async def q(na, label, kw_list, langs, hours=72):
    r = await na.fetch_articles(
        keywords=kw_list, countries=[], languages=langs,
        time_range_hours=hours, max_articles=5, topic_name="test",
    )
    print(f"[{label}] count={len(r.articles)} error={repr(r.error)}")
    for a in r.articles:
        print(f"  {a.published_at} {repr(a.language)} | {a.title[:70]}")
    await asyncio.sleep(1.5)

async def main():
    config = load_config("config.yaml")
    na = NewsAPIAI(config["sources"]["newsapi_ai"], "")

    # 1. 单词 Colombia，72h，各语言
    await q(na, "Colombia 72h es+en",        ["Colombia"],              ["es","en"])
    await q(na, "Colombia 72h es+en+zh+pt",  ["Colombia"],              ["es","en","zh","pt"])

    # 2. 两词拆开 vs 合并
    await q(na, "China+Colombia 分两词 or",  ["China","Colombia"],      ["es","en"])
    await q(na, "China Colombia 合并 and",   ["China Colombia"],        ["es","en"])

    # 3. 英文查询
    await q(na, "Colombia China trade en",   ["Colombia China trade"],  ["en"])
    await q(na, "Colombia China relations",  ["Colombia China"],        ["en"])

    # 4. 168h 扩大窗口
    await q(na, "China Colombia 168h",       ["China Colombia"],        ["es","en"], 168)

asyncio.run(main())
