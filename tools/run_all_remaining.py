"""依次跑剩余 54 国（12 批次），串行后台执行。"""
from __future__ import annotations
import asyncio, io, sys, os, time, logging
from pathlib import Path
from datetime import datetime

ROOT = Path(r"D:\aicoding\news-monitor")
sys.path.insert(0, str(ROOT / "tools"))

os.environ['PYTHONIOENCODING'] = 'utf-8'

from run_batch_pipeline import run_pipeline

_LOG_FILE = ROOT / 'output' / f'run_all_remaining_{datetime.now():%Y%m%d}.log'
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s",
                    datefmt="%H:%M:%S",
                    handlers=[logging.FileHandler(_LOG_FILE, encoding='utf-8')])
log = logging.getLogger("all")

# ── 12 批次配置 ─────────────────────────────────────────────────────────────
BATCHES = [
    (3,  "南亚I",     ["文莱","东帝汶","不丹","孟加拉国","尼泊尔"]),
    (4,  "南亚II",    ["斯里兰卡","印度","巴基斯坦","阿富汗","马尔代夫"]),
    (5,  "中亚",      ["土库曼斯坦","乌兹别克斯坦","哈萨克斯坦","塔吉克斯坦","吉尔吉斯斯坦"]),
    (6,  "西亚海湾",  ["阿曼","伊朗","阿联酋","卡塔尔","巴林"]),
    (7,  "西亚阿拉伯",["沙特阿拉伯","科威特","也门","土耳其","伊拉克"]),
    (8,  "地中海东岸",["叙利亚","约旦","黎巴嫩","以色列","格鲁吉亚"]),
    (9,  "高加索北非",["亚美尼亚","阿塞拜疆","埃及","爱沙尼亚","拉脱维亚"]),
    (10, "欧洲中部I", ["立陶宛","德国","波兰","捷克","斯洛文尼亚"]),
    (11, "巴尔干I",   ["克罗地亚","塞尔维亚","波黑","黑山","阿尔巴尼亚"]),
    (12, "欧洲中部II",["匈牙利","斯洛伐克","北马其顿","罗马尼亚","保加利亚"]),
    (13, "东欧",      ["摩尔多瓦","乌克兰","白俄罗斯","俄罗斯","_无"]),  # 只有4国凑不成5，占位
]

async def main():
    t_start = time.time()
    log.info("===== 启动：剩余 54 国 / %d 批次 =====", len(BATCHES))
    results = []
    for batch_id, region, countries in BATCHES:
        # 滤掉占位国
        countries = [c for c in countries if not c.startswith("_")]
        if not countries: continue
        log.info("\n########## 批次 %d [%s] %s ##########",
                 batch_id, region, "/".join(countries))
        t0 = time.time()
        try:
            path = await run_pipeline(batch_id, countries, region_tag=region)
            results.append((batch_id, region, countries, path, True))
            log.info("批次 %d 完成 %.1fs，输出: %s", batch_id, time.time()-t0, path.name)
        except Exception as e:
            log.error("批次 %d 失败: %s", batch_id, str(e)[:200])
            results.append((batch_id, region, countries, None, False))

    log.info("\n===== 全部完成 in %.1fs =====", time.time()-t_start)
    for bid, reg, cs, p, ok in results:
        status = "✓" if ok else "✗"
        log.info("  %s 批次 %d [%s] %s -> %s", status, bid, reg, "/".join(cs),
                 p.name if p else "FAILED")

if __name__ == "__main__":
    asyncio.run(main())
