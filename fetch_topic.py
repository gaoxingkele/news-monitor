"""Multi-source topic fetcher: Brave + Gemini + Grok (web+x) + Tavily, with dedup + translate + filter + report.

Usage:
    python fetch_topic.py 巴拿马                     # single country
    python fetch_topic.py 巴拿马 哥伦比亚 墨西哥      # multiple countries (sequential)
    python fetch_topic.py mexico colombia            # partial match, case-insensitive
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from urllib.parse import urlparse

# Fix Windows UTF-8 output
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from datetime import date, timedelta

from news_monitor.config_loader import load_config
from news_monitor.filter.relevance_filter import RelevanceFilter
from news_monitor.models import CycleReport, FetchResult, NewsArticle
from news_monitor.output.pdf_reporter import generate_report
from news_monitor.sources.brave_search import BraveSearch
from news_monitor.sources.gemini_search import GeminiSearch
from news_monitor.sources.grok_search import GrokWebSearch, GrokXSearch
from news_monitor.sources.tavily_search import TavilySearch
from news_monitor.topics.loader import load_topics_from_dir
from news_monitor.translation.llm_translator import LLMTranslator

# country_code -> (中文名, English name)
_COUNTRY_NAMES: dict[str, tuple[str, str]] = {
    "mx": ("墨西哥", "Mexico"),
    "co": ("哥伦比亚", "Colombia"),
    "ar": ("阿根廷", "Argentina"),
    "br": ("巴西", "Brazil"),
    "cl": ("智利", "Chile"),
    "pe": ("秘鲁", "Peru"),
    "ve": ("委内瑞拉", "Venezuela"),
    "ec": ("厄瓜多尔", "Ecuador"),
    "bo": ("玻利维亚", "Bolivia"),
    "uy": ("乌拉圭", "Uruguay"),
    "py": ("巴拉圭", "Paraguay"),
    "gy": ("圭亚那", "Guyana"),
    "sr": ("苏里南", "Suriname"),
    "gt": ("危地马拉", "Guatemala"),
    "bz": ("伯利兹", "Belize"),
    "sv": ("萨尔瓦多", "El Salvador"),
    "hn": ("洪都拉斯", "Honduras"),
    "ni": ("尼加拉瓜", "Nicaragua"),
    "cr": ("哥斯达黎加", "Costa Rica"),
    "pa": ("巴拿马", "Panama"),
    "sb": ("所罗门群岛", "Solomon Islands"),
    "st": ("圣多美和普林西比", "Sao Tome and Principe"),
    "ki": ("基里巴斯", "Kiribati"),
    "nr": ("瑙鲁", "Nauru"),
    "bf": ("布基纳法索", "Burkina Faso"),
    "do": ("多米尼加", "Dominican Republic"),
    "ht": ("海地", "Haiti"),
    "kn": ("圣基茨和尼维斯", "Saint Kitts and Nevis"),
    "lc": ("圣卢西亚", "Saint Lucia"),
    "vc": ("圣文森特和格林纳丁斯", "Saint Vincent and the Grenadines"),
    "mh": ("马绍尔群岛", "Marshall Islands"),
    "pw": ("帕劳", "Palau"),
    "tv": ("图瓦卢", "Tuvalu"),
    "sz": ("斯威士兰", "Eswatini"),
    "va": ("梵蒂冈", "Vatican"),
}


# -- ANSI colors ---------------------------------------------------------------
_RED = "\033[91m"
_YELLOW = "\033[93m"
_RESET = "\033[0m"


def _err(msg: str) -> str:
    """Wrap message in red ANSI."""
    return f"{_RED}{msg}{_RESET}"


def _warn(msg: str) -> str:
    """Wrap message in yellow ANSI."""
    return f"{_YELLOW}{msg}{_RESET}"


# -- helpers -------------------------------------------------------------------

def _last_week_range(time_range_hours: int = 168) -> tuple[str, str]:
    today = date.today()
    days_since_sunday = (today.weekday() + 1) % 7 or 7
    last_sunday = today - timedelta(days=days_since_sunday)
    from_date = last_sunday - timedelta(days=(time_range_hours // 24) - 1)
    return from_date.strftime("%Y-%m-%d"), last_sunday.strftime("%Y-%m-%d")


# Chinese content sites to exclude — we only want foreign/local-country sources
_BLOCKED_DOMAINS = {
    # 视频平台
    "bilibili.com", "b23.tv", "youku.com", "iqiyi.com", "douyin.com",
    # 门户/新闻
    "sina.com.cn", "sina.com", "sohu.com", "163.com", "qq.com",
    "ifeng.com", "people.com.cn", "xinhuanet.com", "cctv.com",
    "chinanews.com.cn", "huanqiu.com", "guancha.cn", "thepaper.cn",
    "caixin.com", "jiemian.com", "yicai.com", "cls.cn",
    # 社交/论坛
    "weibo.com", "zhihu.com", "douban.com", "tieba.baidu.com",
    "xiaohongshu.com", "xueqiu.com",
    # 搜索/工具
    "baidu.com", "sogou.com", "so.com",
    # 财经
    "eastmoney.com", "hexun.com", "sse.com.cn", "szse.cn",
    # 科技
    "36kr.com", "3dmgame.com", "csdn.net", "cnblogs.com",
    # 电商
    "taobao.com", "jd.com", "pinduoduo.com",
    # 政府（国内政策页面，非外交部具体新闻）
    "gov.cn",
    # 其他中文内容站
    "wenxuecity.com", "wforum.com", "creaders.net", "6park.com",
    "kanzhongguo.com", "secretchina.com", "ntdtv.com",
    "pixabay.com",  # 非新闻，视频素材
}


def _is_blocked_domain(url: str) -> bool:
    """Check if URL belongs to a blocked Chinese content site."""
    try:
        host = urlparse(url).hostname or ""
        host = host.lower()
        if host.startswith("www."):
            host = host[4:]
        # Check exact match and parent domain
        parts = host.split(".")
        for i in range(len(parts) - 1):
            domain = ".".join(parts[i:])
            if domain in _BLOCKED_DOMAINS:
                return True
    except Exception:
        pass
    return False


def _normalize_url(url: str) -> str:
    """Normalize URL for dedup: strip scheme, www, query, trailing slash."""
    try:
        p = urlparse(url)
        host = p.hostname or ""
        if host.startswith("www."):
            host = host[4:]
        path = p.path.rstrip("/")
        return f"{host}{path}".lower()
    except Exception:
        return url.lower().strip("/")


def _dedup_merge(articles: list[NewsArticle]) -> list[NewsArticle]:
    """Dedup by normalized URL, merging found_by across duplicates.
    Also filters out blocked Chinese content domains.
    """
    seen: dict[str, NewsArticle] = {}
    order: list[str] = []
    blocked_count = 0
    for a in articles:
        # Skip blocked Chinese domains
        if a.source_url and _is_blocked_domain(a.source_url):
            blocked_count += 1
            continue
        key = _normalize_url(a.source_url) if a.source_url else (a.fingerprint or "")
        if not key:
            continue
        if key in seen:
            # Merge found_by
            existing = seen[key]
            for engine in a.found_by:
                if engine not in existing.found_by:
                    existing.found_by.append(engine)
            # Keep richer metadata (prefer article with more info)
            if not existing.published_at and a.published_at:
                existing.published_at = a.published_at
            if not existing.description and a.description:
                existing.description = a.description
        else:
            # Ensure found_by is initialized from api_source if empty
            if not a.found_by and a.api_source:
                a.found_by = [_engine_label(a.api_source)]
            seen[key] = a
            order.append(key)
    if blocked_count:
        print(f"  Blocked {blocked_count} articles from Chinese content sites")
    return [seen[k] for k in order]


def _engine_label(api_source: str) -> str:
    """Map api_source name to display label."""
    _MAP = {
        "brave_search": "Brave",
        "gemini_search": "Gemini",
        "grok_web_search": "Grok",
        "grok_x_search": "Grok",
        "tavily_search": "Tavily",
    }
    return _MAP.get(api_source, api_source)


# -- JSON sidecar (save/load filtered articles for merging) --------------------

def _articles_to_json(articles: list[NewsArticle]) -> list[dict]:
    """Serialize articles to JSON-safe dicts."""
    out = []
    for a in articles:
        d = {
            "title": a.title, "source_url": a.source_url,
            "source_name": a.source_name, "description": a.description,
            "language": a.language, "country": a.country,
            "api_source": a.api_source, "found_by": a.found_by,
            "topic_name": a.topic_name, "title_zh": a.title_zh,
            "description_zh": a.description_zh, "summary_zh": a.summary_zh,
            "event_date": a.event_date, "category": a.category,
            "fingerprint": a.fingerprint,
        }
        if a.published_at:
            d["published_at"] = a.published_at.isoformat()
        out.append(d)
    return out


def _articles_from_json(data: list[dict]) -> list[NewsArticle]:
    """Deserialize articles from JSON dicts."""
    from datetime import datetime, timezone
    arts = []
    for d in data:
        a = NewsArticle(
            title=d.get("title", ""),
            source_url=d.get("source_url", ""),
            source_name=d.get("source_name", ""),
            description=d.get("description", ""),
            language=d.get("language", ""),
            country=d.get("country", ""),
            api_source=d.get("api_source", ""),
            found_by=d.get("found_by", []),
            topic_name=d.get("topic_name", ""),
            title_zh=d.get("title_zh", ""),
            description_zh=d.get("description_zh", ""),
            summary_zh=d.get("summary_zh", ""),
            event_date=d.get("event_date", ""),
            category=d.get("category", ""),
            fingerprint=d.get("fingerprint", ""),
        )
        if d.get("published_at"):
            try:
                a.published_at = datetime.fromisoformat(d["published_at"])
            except (ValueError, TypeError):
                pass
        arts.append(a)
    return arts


def _save_articles_json(articles: list[NewsArticle], md_path: str) -> str:
    """Save articles as JSON sidecar next to the MD report."""
    json_path = md_path.replace(".md", ".json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(_articles_to_json(articles), f, ensure_ascii=False, indent=1)
    return json_path


# ── Checkpoint system ─────────────────────────────────────────────────────────

_CHECKPOINT_DIR = "output/checkpoints"
_COUNTRY_STAGES = ["fetch_dedup", "translated", "filtered"]


def _ckpt_path(country_code: str, stage: str) -> str:
    from pathlib import Path
    return str(Path(_CHECKPOINT_DIR) / f"country_{country_code}_{stage}.json")


def _save_ckpt(country_code: str, stage: str, articles: list[NewsArticle], extra: dict | None = None) -> None:
    """Save checkpoint after a pipeline stage."""
    from pathlib import Path
    from datetime import datetime, timezone
    Path(_CHECKPOINT_DIR).mkdir(parents=True, exist_ok=True)
    path = _ckpt_path(country_code, stage)
    payload = {
        "stage": stage,
        "country": country_code,
        "count": len(articles),
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "articles": _articles_to_json(articles),
    }
    if extra:
        payload["extra"] = extra
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    print(f"  [checkpoint] {stage}: saved {len(articles)} articles → {path}")


def _load_ckpt(country_code: str, stage: str) -> tuple[list[NewsArticle], dict] | None:
    """Load checkpoint. Returns (articles, extra) or None."""
    path = _ckpt_path(country_code, stage)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        articles = _articles_from_json(payload.get("articles", []))
        extra = payload.get("extra", {})
        saved_at = payload.get("saved_at", "?")
        print(f"  [checkpoint] {stage}: loaded {len(articles)} articles (saved {saved_at})")
        return articles, extra
    except Exception as exc:
        print(_err(f"  [checkpoint] load failed {path}: {exc}"))
        return None


def _find_latest_ckpt(country_code: str) -> str | None:
    """Find the latest completed checkpoint stage for a country."""
    for stage in reversed(_COUNTRY_STAGES):
        if os.path.exists(_ckpt_path(country_code, stage)):
            return stage
    return None


def _load_articles_json(json_path: str) -> list[NewsArticle]:
    """Load articles from a JSON sidecar file."""
    with open(json_path, "r", encoding="utf-8") as f:
        return _articles_from_json(json.load(f))


# -- section grouping for batch Grok -------------------------------------------

def _group_queries_by_section(topic_file_path: str) -> list[list[str]]:
    """Parse topic MD file, group queries by ### section, skip site: queries.

    Returns list of sections, each section is a list of query strings.
    """
    from pathlib import Path
    text = Path(topic_file_path).read_text(encoding="utf-8")

    # Skip frontmatter
    body = text
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            body = parts[2]

    sections: list[list[str]] = []
    current_section: list[str] | None = None
    in_queries = False

    for line in body.splitlines():
        stripped = line.strip()
        # Detect "## 搜索查询" section
        if stripped.startswith("## ") and "搜索查询" in stripped:
            in_queries = True
            continue
        # Exit queries section on next ## heading
        if stripped.startswith("## ") and in_queries:
            in_queries = False
            continue
        if not in_queries:
            continue
        # New subsection (### ──)
        if stripped.startswith("### "):
            if current_section and current_section:
                sections.append(current_section)
            current_section = []
            continue
        # Skip comments
        if stripped.startswith("#"):
            continue
        # Query bullet
        if stripped.startswith("- "):
            query = stripped[2:].strip()
            if not query:
                continue
            # Skip site: queries (Grok doesn't support them)
            if query.startswith("site:"):
                continue
            if current_section is None:
                current_section = []
            current_section.append(query)

    # Don't forget the last section
    if current_section:
        sections.append(current_section)

    return [s for s in sections if s]


# -- fetchers ------------------------------------------------------------------

# Global API call counter
_api_call_counts: dict[str, int] = {}


def _count_api_call(source_label: str, count: int = 1) -> None:
    """Increment API call counter for a source."""
    _api_call_counts[source_label] = _api_call_counts.get(source_label, 0) + count


async def _fetch_source(
    source,
    query_groups: list[list[str]],
    *,
    source_label: str,
    topic_name: str,
    countries: list[str],
    languages: list[str],
    time_range_hours: int,
    max_articles: int,
    exclude_kw: list[str] | None,
    from_date: str,
    to_date: str,
    delay: float = 1.1,
    per_query_timeout: float = 60.0,
    total_timeout: float = 300.0,
) -> list[NewsArticle]:
    """Run a source for all query groups sequentially with rate limiting."""
    total = len(query_groups)
    print(f"\n[{source_label}] fetching {total} query groups...")
    all_arts: list[NewsArticle] = []
    completed = 0
    try:
        async with asyncio.timeout(total_timeout):
            for i, kw_list in enumerate(query_groups):
                try:
                    result: FetchResult = await asyncio.wait_for(
                        source.fetch_articles(
                            keywords=kw_list,
                            countries=countries,
                            languages=languages,
                            time_range_hours=time_range_hours,
                            max_articles=max_articles,
                            exclude_keywords=exclude_kw,
                            topic_name=topic_name,
                            from_date=from_date,
                            to_date=to_date,
                        ),
                        timeout=per_query_timeout,
                    )
                    _count_api_call(source_label)
                    completed += 1
                    kw = kw_list[0] if kw_list else ""
                    progress = f"[{source_label} {completed}/{total}]"
                    if result.error:
                        print(_err(f"  {progress} ERROR '{kw[:50]}': {result.error.splitlines()[0][:80]}"))
                    elif result.articles:
                        print(f"  {progress} '{kw[:50]}': {len(result.articles)}")
                    else:
                        print(f"  {progress} '{kw[:50]}': 0")
                    all_arts.extend(result.articles)
                except asyncio.TimeoutError:
                    _count_api_call(source_label)
                    completed += 1
                    kw = kw_list[0] if kw_list else ""
                    progress = f"[{source_label} {completed}/{total}]"
                    print(_err(f"  {progress} TIMEOUT '{kw[:50]}': skipped"))
                await asyncio.sleep(delay)
    except (asyncio.TimeoutError, TimeoutError):
        print(_err(f"  [{source_label}] total timeout ({total_timeout:.0f}s) at {completed}/{total}, stopping."))
    print(f"  [{source_label}] done: {len(all_arts)} articles from {completed}/{total} queries")
    return all_arts


async def _fetch_source_batched(
    source,
    sections: list[list[str]],
    *,
    source_label: str,
    topic_name: str,
    countries: list[str],
    languages: list[str],
    time_range_hours: int,
    max_articles: int,
    from_date: str,
    to_date: str,
    delay: float = 2.0,
    per_batch_timeout: float = 180.0,
    total_timeout: float = 1200.0,
) -> list[NewsArticle]:
    """Run a Grok source in batch mode: one API call per section."""
    total = len(sections)
    total_queries = sum(len(s) for s in sections)
    print(f"\n[{source_label}] batched: {total} sections ({total_queries} queries merged)...")
    all_arts: list[NewsArticle] = []
    completed = 0
    try:
        async with asyncio.timeout(total_timeout):
            for i, section_queries in enumerate(sections):
                # Build query_groups for batch: each query as its own list
                batch_groups = [[q] for q in section_queries]
                section_preview = section_queries[0][:40] if section_queries else ""
                try:
                    result: FetchResult = await asyncio.wait_for(
                        source.fetch_articles_batch(
                            query_groups=batch_groups,
                            countries=countries,
                            languages=languages,
                            time_range_hours=time_range_hours,
                            max_articles=max_articles,
                            topic_name=topic_name,
                            from_date=from_date,
                            to_date=to_date,
                        ),
                        timeout=per_batch_timeout,
                    )
                    _count_api_call(source_label)
                    completed += 1
                    progress = f"[{source_label} batch {completed}/{total}]"
                    if result.error:
                        print(_err(f"  {progress} ERROR ({len(section_queries)}q) '{section_preview}...': {result.error.splitlines()[0][:80]}"))
                    else:
                        print(f"  {progress} ({len(section_queries)}q) '{section_preview}...': {len(result.articles)}")
                    all_arts.extend(result.articles)
                except asyncio.TimeoutError:
                    _count_api_call(source_label)
                    completed += 1
                    progress = f"[{source_label} batch {completed}/{total}]"
                    print(_err(f"  {progress} TIMEOUT ({len(section_queries)}q) '{section_preview}...': skipped"))
                await asyncio.sleep(delay)
    except (asyncio.TimeoutError, TimeoutError):
        print(_err(f"  [{source_label}] total timeout ({total_timeout:.0f}s) at {completed}/{total}, stopping."))
    print(f"  [{source_label}] done: {len(all_arts)} articles from {completed}/{total} batch calls (was {total_queries} queries)")
    return all_arts


# -- main ----------------------------------------------------------------------

async def _run_country(
    topic: dict,
    config: dict,
    overseas_proxy: str,
    sources_cfg: dict,
    resume: bool = False,
) -> None:
    """Run the full pipeline for a single country/topic with checkpoint support."""

    query_groups: list[list[str]] = [[q] for q in topic.get("query_groups", [])]
    time_range_hours = topic.get("time_range_hours", 168)
    max_articles     = topic.get("max_articles", 20)
    exclude_kw       = topic.get("exclude_keywords")
    languages        = topic.get("languages", [])
    from_date = os.environ.get("FETCH_FROM") or ""
    to_date = os.environ.get("FETCH_TO") or ""
    if not from_date or not to_date:
        from_date, to_date = _last_week_range(time_range_hours)

    # Reset API call counter
    _api_call_counts.clear()

    # Resolve topic file path for section grouping
    from pathlib import Path
    topic_file_candidates = list(Path("topics").glob("*.md"))
    topic_file_path = ""
    topic_needle = topic.get("name", "").lower()
    for tf in topic_file_candidates:
        if topic_needle in tf.read_text(encoding="utf-8").lower():
            topic_file_path = str(tf)
            break

    # Parse sections for batched Grok calls
    grok_sections: list[list[str]] = []
    if topic_file_path:
        grok_sections = _group_queries_by_section(topic_file_path)
        grok_query_count = sum(len(s) for s in grok_sections)
    else:
        grok_query_count = 0

    local_countries = topic.get("countries", [])
    country_code = local_countries[0] if local_countries else "unknown"
    country_zh, country_en = _COUNTRY_NAMES.get(country_code, (country_code, country_code))
    country_label = f"{country_zh}相关"

    trans_cfg = config.get("translation", {})
    filter_cfg = config.get("filter", {})

    # -- Source selection (FETCH_SOURCES env var) --------------------------------
    _ALL_SOURCES = {"brave", "gemini", "grok_web", "grok_x", "tavily"}
    sources_env = os.environ.get("FETCH_SOURCES", "").strip()
    if sources_env:
        enabled_sources = {s.strip() for s in sources_env.split(",") if s.strip()}
    else:
        enabled_sources = _ALL_SOURCES

    # -- Merge with previous run (MERGE_WITH env var) ---------------------------
    merge_with = os.environ.get("MERGE_WITH", "").strip()
    merge_arts: list[NewsArticle] = []
    if merge_with:
        merge_json = merge_with.replace(".md", ".json").replace(".pdf", ".json")
        if os.path.exists(merge_json):
            merge_arts = _load_articles_json(merge_json)
            print(f"Merging with: {merge_json} ({len(merge_arts)} articles)")
        else:
            print(_err(f"Merge file not found: {merge_json}"))

    # -- Check resume state ----------------------------------------------------
    resume_stage: str | None = None
    if resume:
        resume_stage = _find_latest_ckpt(country_code)
        if resume_stage:
            print(f"\033[92mResuming {country_code} from checkpoint: {resume_stage}\033[0m")
        else:
            print(f"No checkpoint for {country_code}, starting fresh.")

    source_names = sorted(enabled_sources)
    print(f"Topic     : {topic['name']}")
    print(f"Dates     : {from_date} -> {to_date}")
    print(f"Languages : {languages}")
    print(f"Countries : {local_countries}")
    print(f"Sources   : {', '.join(source_names)}")
    if merge_with:
        print(f"Merge     : +{len(merge_arts)} from previous run")
    print(f"Queries   : {len(query_groups)}")
    if grok_sections:
        print(f"Grok batch: {len(grok_sections)} sections ({grok_query_count} queries merged, site: skipped)")
    print(f"Translate : {trans_cfg.get('provider', 'qwen')} -> {trans_cfg.get('fallback_chain', [])}")
    print(f"Filter    : {filter_cfg.get('provider', 'grok')}")
    print("=" * 72)

    raw_total = 0
    unique: list[NewsArticle] = []
    translated = 0
    filtered: list[NewsArticle] = []

    # ══════════════════════════════════════════════════════════════════════
    # STAGE 1: Fetch + Dedup
    # ══════════════════════════════════════════════════════════════════════
    if resume_stage and resume_stage in ("fetch_dedup", "translated", "filtered"):
        loaded = _load_ckpt(country_code, "fetch_dedup")
        if loaded:
            unique, extra = loaded
            raw_total = extra.get("raw_total", len(unique))
            print(f"Skipping fetch+dedup (loaded {len(unique)} articles)")
        else:
            resume_stage = None

    if not unique:
        # -- Shared fetch params
        fetch_kw = dict(
            topic_name=topic.get("name", ""),
            countries=local_countries,
            languages=languages,
            time_range_hours=time_range_hours,
            max_articles=max_articles,
            exclude_kw=exclude_kw,
            from_date=from_date,
            to_date=to_date,
        )

        # -- Init & run enabled sources
        tasks: list[tuple[str, any]] = []

        if "brave" in enabled_sources:
            bv_cfg = sources_cfg.get("brave_search", {})
            if not bv_cfg.get("api_key"):
                bv_cfg["api_key"] = os.environ.get("BRAVEAPI", "")
            brave = BraveSearch(bv_cfg, overseas_proxy)
            tasks.append(("Brave", _fetch_source(
                brave, query_groups, source_label="Brave",
                delay=1.1, per_query_timeout=30.0, total_timeout=600.0,
                **fetch_kw,
            )))

        if "gemini" in enabled_sources:
            gm_cfg = sources_cfg.get("gemini_search", {})
            gemini = GeminiSearch(gm_cfg, overseas_proxy)
            tasks.append(("Gemini", _fetch_source(
                gemini, query_groups, source_label="Gemini",
                delay=2.0, per_query_timeout=60.0, total_timeout=1200.0,
                **fetch_kw,
            )))

        if "tavily" in enabled_sources:
            tv_cfg = sources_cfg.get("tavily_search", {})
            if not tv_cfg.get("api_key"):
                tv_cfg["api_key"] = os.environ.get("TAVILYAPI", "") or os.environ.get("TAVILY_API_KEY", "")
            if "exclude_domains" not in tv_cfg:
                tv_cfg["exclude_domains"] = [
                    "foxsports.com", "espn.com", "mlb.com", "espn.go.com",
                    "mining.com", "retaildive.com", "chainstoreage.com",
                    "simplywall.st", "seekingalpha.com", "fool.com",
                ]
            tavily = TavilySearch(tv_cfg, overseas_proxy)
            tv_queries = [qg for qg in query_groups if not qg[0].startswith("site:")]
            tv_fetch_kw = dict(fetch_kw)
            tv_fetch_kw["max_articles"] = min(fetch_kw.get("max_articles", 20), 5)
            tasks.append(("Tavily", _fetch_source(
                tavily, tv_queries, source_label="Tavily",
                delay=1.0, per_query_timeout=30.0, total_timeout=600.0,
                **tv_fetch_kw,
            )))

        if "grok_web" in enabled_sources:
            gw_cfg = sources_cfg.get("grok_web_search", {})
            grok_web = GrokWebSearch(gw_cfg, overseas_proxy)
            if grok_sections:
                tasks.append(("Grok Web", _fetch_source_batched(
                    grok_web, grok_sections, source_label="Grok Web",
                    topic_name=fetch_kw["topic_name"],
                    countries=fetch_kw["countries"],
                    languages=fetch_kw["languages"],
                    time_range_hours=fetch_kw["time_range_hours"],
                    max_articles=fetch_kw["max_articles"],
                    from_date=fetch_kw["from_date"],
                    to_date=fetch_kw["to_date"],
                    delay=2.0, per_batch_timeout=180.0, total_timeout=1200.0,
                )))
            else:
                tasks.append(("Grok Web", _fetch_source(
                    grok_web, query_groups, source_label="Grok Web",
                    delay=1.5, per_query_timeout=60.0, total_timeout=1200.0,
                    **fetch_kw,
                )))

        if "grok_x" in enabled_sources:
            gx_cfg = sources_cfg.get("grok_x_search", {})
            grok_x = GrokXSearch(gx_cfg, overseas_proxy)
            if grok_sections:
                tasks.append(("Grok X", _fetch_source_batched(
                    grok_x, grok_sections, source_label="Grok X",
                    topic_name=fetch_kw["topic_name"],
                    countries=fetch_kw["countries"],
                    languages=fetch_kw["languages"],
                    time_range_hours=fetch_kw["time_range_hours"],
                    max_articles=fetch_kw["max_articles"],
                    from_date=fetch_kw["from_date"],
                    to_date=fetch_kw["to_date"],
                    delay=2.0, per_batch_timeout=180.0, total_timeout=1200.0,
                )))
            else:
                tasks.append(("Grok X", _fetch_source(
                    grok_x, query_groups, source_label="Grok X",
                    delay=1.5, per_query_timeout=60.0, total_timeout=1200.0,
                    **fetch_kw,
                )))

        results = await asyncio.gather(
            *[t[1] for t in tasks],
            return_exceptions=True,
        )

        all_arts: list[NewsArticle] = []
        source_counts: dict[str, int] = {}
        for (label, _), res in zip(tasks, results):
            if isinstance(res, Exception):
                print(_err(f"\n[{label}] EXCEPTION: {res}"))
                source_counts[label] = 0
            else:
                for a in res:
                    if not a.found_by:
                        a.found_by = [label]
                all_arts.extend(res)
                source_counts[label] = len(res)

        raw_total = len(all_arts)
        print(f"\n{'=' * 72}")
        print(f"Raw totals: {' | '.join(f'{k}: {v}' for k, v in source_counts.items())} | Total: {raw_total}")

        unique = _dedup_merge(all_arts)
        print(f"After dedup: {len(unique)}  (removed {raw_total - len(unique)} duplicates)")

        if merge_arts:
            pre_merge = len(unique)
            combined = list(merge_arts) + list(unique)
            unique = _dedup_merge(combined)
            print(f"After merge: {len(unique)} total  (+{len(unique) - len(merge_arts)} new from this run)")

        from datetime import datetime as _dt, timezone as _tz
        _EPOCH = _dt.min.replace(tzinfo=_tz.utc)
        def _sort_key(a):
            p = a.published_at
            if p is None:
                return _EPOCH
            if p.tzinfo is None:
                p = p.replace(tzinfo=_tz.utc)
            return p
        unique.sort(key=_sort_key, reverse=True)

        multi_source = sum(1 for a in unique if len(a.found_by) > 1)
        print(f"Multi-source articles: {multi_source}")
        print("=" * 72)

        # ★ Checkpoint: fetch_dedup
        _save_ckpt(country_code, "fetch_dedup", unique, {"raw_total": raw_total})

    # ══════════════════════════════════════════════════════════════════════
    # STAGE 2: Translate
    # ══════════════════════════════════════════════════════════════════════
    if resume_stage and resume_stage in ("translated", "filtered"):
        loaded = _load_ckpt(country_code, "translated")
        if loaded:
            unique, extra = loaded
            raw_total = extra.get("raw_total", raw_total)
            translated = extra.get("translated", sum(1 for a in unique if a.title_zh))
            print(f"Skipping translation (loaded {len(unique)} articles, {translated} translated)")
        else:
            resume_stage = "fetch_dedup"

    if not any(a.title_zh for a in unique):
        needs_translate = [a for a in unique if not a.title_zh]
        already_translated = len(unique) - len(needs_translate)
        if needs_translate:
            translator = LLMTranslator(
                provider=trans_cfg.get("provider", "qwen"),
                fallback_chain=trans_cfg.get("fallback_chain", ["deepseek", "grok", "doubao", "glm"]),
                batch_size=trans_cfg.get("batch_size", 0),
                overseas_proxy=overseas_proxy,
                country_zh=country_zh,
                country_en=country_en,
                country_key=country_code,
            )
            print(f"\nTranslating {len(needs_translate)} new articles (skip {already_translated} already done, provider={translator.provider})...", flush=True)
            needs_translate = await translator.translate_articles(needs_translate)
            translated_map = {_normalize_url(a.source_url): a for a in needs_translate}
            for i, a in enumerate(unique):
                key = _normalize_url(a.source_url)
                if key in translated_map:
                    unique[i] = translated_map[key]
        translated = sum(1 for a in unique if a.title_zh)
        print(f"Done. {translated}/{len(unique)} articles translated.", flush=True)

        # ★ Checkpoint: translated
        _save_ckpt(country_code, "translated", unique, {"raw_total": raw_total, "translated": translated})

    # ══════════════════════════════════════════════════════════════════════
    # STAGE 3: Relevance filter
    # ══════════════════════════════════════════════════════════════════════
    if resume_stage == "filtered":
        loaded = _load_ckpt(country_code, "filtered")
        if loaded:
            filtered, extra = loaded
            raw_total = extra.get("raw_total", raw_total)
            translated = extra.get("translated", translated)
            print(f"Skipping filter (loaded {len(filtered)} articles)")
        else:
            resume_stage = "translated"

    if not filtered:
        if merge_arts:
            merged_urls = {_normalize_url(a.source_url) for a in merge_arts}
            new_arts = [a for a in unique if _normalize_url(a.source_url) not in merged_urls]
            old_arts = [a for a in unique if _normalize_url(a.source_url) in merged_urls]
            print(f"\nFiltering {len(new_arts)} new articles (skip {len(old_arts)} from merge)...")
        else:
            new_arts = unique
            old_arts = []

        rf = RelevanceFilter(
            provider=filter_cfg.get("provider", "grok"),
            fallback_chain=filter_cfg.get("fallback_chain", ["qwen", "deepseek", "doubao", "kimi"]),
            batch_size=filter_cfg.get("batch_size", 0),
            overseas_proxy=overseas_proxy,
        )
        if new_arts:
            new_filtered, filter_log = await rf.filter_articles(new_arts, country_zh, country_en)
            removed = len(new_arts) - len(new_filtered)
            print(f"Kept {len(new_filtered)}, removed {removed} irrelevant.")
            if removed:
                for entry in filter_log:
                    if not entry["relevant"]:
                        print(f"  - {entry['title'][:60]}  ({entry['reason']})")
        else:
            new_filtered = []
            filter_log = []

        filtered = old_arts + new_filtered
        print(f"Total after filter: {len(filtered)} ({len(old_arts)} merged + {len(new_filtered)} new)")

        # ★ Checkpoint: filtered
        _save_ckpt(country_code, "filtered", filtered, {"raw_total": raw_total, "translated": translated})

    # -- API Call Summary ------------------------------------------------------
    print(f"\n{'=' * 72}")
    print("== API Call Summary ==")
    total_grok = 0
    total_grok_was = 0
    for label in ["Brave", "Tavily", "Gemini", "Grok Web", "Grok X"]:
        calls = _api_call_counts.get(label, 0)
        if "Grok" in label:
            was = len(query_groups)
            saved = was - calls
            total_grok += calls
            total_grok_was += was
            print(f"  {label:14s}: {calls:3d} calls  (was {was}, saved {saved})")
        else:
            print(f"  {label:14s}: {calls:3d} calls")
    print(f"  {'─' * 40}")
    print(f"  Grok total   : {total_grok:3d} calls  (was {total_grok_was}, saved ~{100*(total_grok_was-total_grok)/max(total_grok_was,1):.0f}%)")
    grok_search_cost = total_grok * 5.0 / 1000
    print(f"  Est. cost    : ~${grok_search_cost:.3f} search calls")
    print(f"  Translate    : {trans_cfg.get('provider', 'qwen')}")
    print(f"  Filter       : {filter_cfg.get('provider', 'grok')}")
    print(f"{'=' * 72}")

    # -- Generate report -------------------------------------------------------
    report = CycleReport(
        total_fetched=raw_total,
        total_after_dedup=len(unique),
        total_translated=translated,
    )
    highlight_keywords = [country_zh, country_en]

    md_path, pdf_path = generate_report(
        articles=filtered,
        report=report,
        output_dir="output/reports",
        topic_name=topic["name"],
        country_key=country_code,
        country_label=country_label,
        highlight_keywords=highlight_keywords,
    )
    # Save JSON sidecar for future merging
    json_path = _save_articles_json(filtered, md_path)
    print(f"\nMD saved  : {md_path}")
    print(f"JSON saved: {json_path}")
    if pdf_path:
        print(f"PDF saved : {pdf_path}")


async def main(topic_filters: list[str]) -> None:
    """Run the pipeline for one or more countries sequentially."""
    config = load_config("config.yaml")
    overseas_proxy = config.get("proxy", {}).get("overseas_proxy", "")
    sources_cfg = config.get("sources", {})

    # Parse --resume flag
    resume = "--resume" in topic_filters
    positional = [a for a in topic_filters if not a.startswith("--")]

    all_topics = load_topics_from_dir("topics")

    # Resolve each filter to a topic
    resolved: list[dict] = []
    for tf in positional:
        needle = tf.lower()
        matches = [t for t in all_topics if needle in t.get("name", "").lower()]
        if not matches:
            print(f"Topic not found: {tf!r}")
            print("Available:", [t.get("name") for t in all_topics])
        else:
            resolved.append(matches[0])

    if not resolved:
        return

    total = len(resolved)
    for idx, topic in enumerate(resolved, 1):
        name = topic.get("name", "unknown")
        if total > 1:
            print(f"\n{'#' * 72}")
            print(f"## Country {idx}/{total}: {name}")
            print(f"{'#' * 72}\n")

        await _run_country(topic, config, overseas_proxy, sources_cfg, resume=resume)

        if idx < total:
            print(f"\n--- Finished {name}, moving to next country ---\n")

    if total > 1:
        print(f"\n{'#' * 72}")
        print(f"## All {total} countries completed.")
        print(f"{'#' * 72}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    asyncio.run(main(sys.argv[1:]))
