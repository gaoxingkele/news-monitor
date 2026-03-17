"""Event-based topic fetcher: Brave + Gemini + Grok, with sentiment classification.

Unlike fetch_topic.py (country monitoring), this script:
  - Searches for a specific event (e.g., Boao Forum 2026)
  - Classifies articles by sentiment (positive/neutral/negative/analysis)
  - Outputs MD + Word reports grouped by attitude
  - Saves checkpoints after each stage; use --resume to skip completed stages

Usage:
    python fetch_event.py boao                        # full run
    python fetch_event.py boao --resume               # resume from last checkpoint
    python fetch_event.py 博鳌                        # Chinese name also works
    python fetch_event.py topics/boao_forum_2026.md   # direct file path
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime, timezone

# Fix Windows UTF-8 output + force unbuffered stdout/stderr
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

import logging

from news_monitor.config_loader import load_config
from news_monitor.models import CycleReport, FetchResult, NewsArticle
from news_monitor.sources.brave_search import BraveSearch
from news_monitor.sources.gemini_search import GeminiSearch
from news_monitor.sources.grok_search import GrokWebSearch, GrokXSearch
from news_monitor.translation.llm_translator import LLMTranslator
from news_monitor.filter.sentiment_classifier import SentimentClassifier
from news_monitor.checkpoint import (
    articles_to_json as _articles_to_json,
    articles_from_json as _articles_from_json,
    save as _save_checkpoint_unified,
    load as _load_checkpoint_unified,
    find_latest as _find_latest_checkpoint_unified,
    CHECKPOINT_DIR as _CHECKPOINT_DIR,
)
from news_monitor.media_tier import get_tier, get_tier_badge
from news_monitor.trend import record_snapshot


# ── Logging: terminal + file, always flushed ──────────────────────────────────

_LOG_DIR = "output/logs"
_log_file = None
_logger = logging.getLogger("fetch_event")


def _init_log():
    """Set up dual logging: console (unbuffered) + file."""
    global _log_file
    Path(_LOG_DIR).mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = str(Path(_LOG_DIR) / f"{ts}_event.log")
    _log_file = open(log_path, "w", encoding="utf-8")

    handler_file = logging.StreamHandler(_log_file)
    handler_console = logging.StreamHandler(sys.stdout)
    fmt = logging.Formatter("%(asctime)s %(message)s", datefmt="%H:%M:%S")
    handler_file.setFormatter(fmt)
    handler_console.setFormatter(fmt)
    _logger.addHandler(handler_file)
    _logger.addHandler(handler_console)
    _logger.setLevel(logging.INFO)

    log(f"Log file: {log_path}")
    return log_path


def log(msg: str) -> None:
    """Print to terminal (flushed) AND write to log file."""
    _logger.info(msg)
    # Force flush both streams
    sys.stdout.flush()
    if _log_file:
        _log_file.flush()


def log_err(msg: str) -> None:
    """Print error in red to terminal AND log file."""
    _logger.error(f"\033[91m{msg}\033[0m")
    sys.stdout.flush()
    if _log_file:
        _log_file.flush()


# ── ANSI colors ──────────────────────────────────────────────────────────────
_RED = "\033[91m"
_YELLOW = "\033[93m"
_GREEN = "\033[92m"
_CYAN = "\033[96m"
_RESET = "\033[0m"


def _err(msg: str) -> str:
    return f"{_RED}{msg}{_RESET}"


# ── Chinese content sites to exclude ─────────────────────────────────────────
_BLOCKED_DOMAINS = {
    "bilibili.com", "b23.tv", "youku.com", "iqiyi.com", "douyin.com",
    "sina.com.cn", "sina.com", "sohu.com", "163.com", "qq.com",
    "ifeng.com", "people.com.cn", "xinhuanet.com", "cctv.com",
    "chinanews.com.cn", "huanqiu.com", "guancha.cn", "thepaper.cn",
    "caixin.com", "jiemian.com", "yicai.com", "cls.cn",
    "weibo.com", "zhihu.com", "douban.com", "tieba.baidu.com",
    "xiaohongshu.com", "xueqiu.com",
    "baidu.com", "sogou.com", "so.com",
    "eastmoney.com", "hexun.com",
    "36kr.com", "csdn.net", "cnblogs.com",
    "taobao.com", "jd.com", "pinduoduo.com",
    "gov.cn",
    "wenxuecity.com", "wforum.com", "creaders.net", "6park.com",
    "pixabay.com",
}


def _is_blocked_domain(url: str) -> bool:
    try:
        host = urlparse(url).hostname or ""
        host = host.lower()
        if host.startswith("www."):
            host = host[4:]
        parts = host.split(".")
        for i in range(len(parts) - 1):
            domain = ".".join(parts[i:])
            if domain in _BLOCKED_DOMAINS:
                return True
    except Exception:
        pass
    return False


def _normalize_url(url: str) -> str:
    try:
        p = urlparse(url)
        host = p.hostname or ""
        if host.startswith("www."):
            host = host[4:]
        path = p.path.rstrip("/")
        return f"{host}{path}".lower()
    except Exception:
        return url.lower().strip("/")


def _engine_label(api_source: str) -> str:
    _MAP = {
        "brave_search": "Brave",
        "gemini_search": "Gemini",
        "grok_web_search": "Grok",
        "grok_x_search": "Grok",
    }
    return _MAP.get(api_source, api_source)


def _filter_blocked(articles: list[NewsArticle]) -> list[NewsArticle]:
    """Early domain filter -- remove blocked domains before dedup/translation."""
    pre = len(articles)
    filtered = [a for a in articles if not (a.source_url and _is_blocked_domain(a.source_url))]
    removed = pre - len(filtered)
    if removed:
        log(f"  Early domain filter: removed {removed} blocked articles")
    return filtered


def _is_grok_x_result(art: NewsArticle) -> bool:
    """Check if article is from Grok X search (typically Twitter/X posts)."""
    url = art.source_url or ""
    return "x.com/" in url or "twitter.com/" in url or art.api_source == "grok_x_search"


def _clean_grok_x_title(title: str) -> str:
    """Clean Grok X search result titles which often contain search query artifacts."""
    import re
    # Strip "Post [post:XX] by Author (@handle, role), Date" format
    m = re.match(r'Post\s+\[post:\d+\]\s+by\s+.+?,\s*\w{3}\s+\w{3}\s+\d+.*?GMT[^:]*:\s*(.*)', title, re.DOTALL)
    if m:
        return m.group(1).strip() or title
    # Strip numbered list items from batch results
    m2 = re.match(r'^\d+\.\s+(.+)', title)
    if m2:
        return m2.group(1).strip()
    return title


def _dedup_merge(articles: list[NewsArticle]) -> list[NewsArticle]:
    """Dedup by normalized URL, merging found_by. Filter blocked domains (safety net)."""
    seen: dict[str, NewsArticle] = {}
    order: list[str] = []
    blocked_count = 0
    for a in articles:
        if a.source_url and _is_blocked_domain(a.source_url):
            blocked_count += 1
            continue
        key = _normalize_url(a.source_url) if a.source_url else (a.fingerprint or "")
        if not key:
            continue
        if key in seen:
            existing = seen[key]
            for engine in a.found_by:
                if engine not in existing.found_by:
                    existing.found_by.append(engine)
            if not existing.published_at and a.published_at:
                existing.published_at = a.published_at
            if not existing.description and a.description:
                existing.description = a.description
        else:
            if not a.found_by and a.api_source:
                a.found_by = [_engine_label(a.api_source)]
            seen[key] = a
            order.append(key)
    if blocked_count:
        log(f"  Blocked {blocked_count} articles from Chinese content sites")
    return [seen[k] for k in order]


# ── Topic file parsing ────────────────────────────────────────────────────────

def _parse_topic_file(path: str) -> dict:
    """Parse an event topic MD file, extracting frontmatter and queries."""
    import yaml

    text = Path(path).read_text(encoding="utf-8")
    meta = {}
    body = text

    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            meta = yaml.safe_load(parts[1]) or {}
            body = parts[2]

    # Parse query groups by section
    sections: list[list[str]] = []
    current: list[str] | None = None
    in_queries = False

    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("## ") and "搜索查询" in stripped:
            in_queries = True
            continue
        if stripped.startswith("## ") and in_queries:
            in_queries = False
            continue
        if not in_queries:
            continue
        if stripped.startswith("### "):
            if current:
                sections.append(current)
            current = []
            continue
        if stripped.startswith("#"):
            continue
        if stripped.startswith("- "):
            query = stripped[2:].strip()
            if query and not query.startswith("site:"):
                if current is None:
                    current = []
                current.append(query)

    if current:
        sections.append(current)

    all_queries = []
    for s in sections:
        all_queries.extend(s)

    # P0-1: For event topics, wrap multi-word event names in quotes for exact matching
    topic_type = meta.get("type", "")
    if topic_type == "event":
        event_names = []
        for key in ("event_name_en", "event_name_zh"):
            name = meta.get(key, "")
            if name and " " in name:
                event_names.append(name)
        if event_names:
            quoted_queries = []
            for q in all_queries:
                new_q = q
                for name in event_names:
                    # Only quote if name appears unquoted in the query
                    if name in new_q and f'"{name}"' not in new_q:
                        new_q = new_q.replace(name, f'"{name}"')
                quoted_queries.append(new_q)
            all_queries = quoted_queries
            # Also update sections
            new_sections = []
            for sec in sections:
                new_sec = []
                for q in sec:
                    new_q = q
                    for name in event_names:
                        if name in new_q and f'"{name}"' not in new_q:
                            new_q = new_q.replace(name, f'"{name}"')
                    new_sec.append(new_q)
                new_sections.append(new_sec)
            sections = new_sections

    meta["query_groups"] = all_queries
    meta["_sections"] = [s for s in sections if s]
    return meta


def _find_topic_file(query: str) -> str | None:
    """Find a topic file matching the query string."""
    topics_dir = Path("topics")
    if not topics_dir.exists():
        return None

    # Direct file path
    if os.path.exists(query) and query.endswith(".md"):
        return query

    # Search by name
    needle = query.lower()
    for f in sorted(topics_dir.glob("*.md")):
        if needle in f.stem.lower():
            return str(f)
        # Also check file content
        try:
            content = f.read_text(encoding="utf-8")[:500].lower()
            if needle in content:
                return str(f)
        except Exception:
            pass
    return None


# ── JSON sidecar ──────────────────────────────────────────────────────────────

def _save_articles_json(articles: list[NewsArticle], md_path: str) -> str:
    json_path = md_path.replace(".md", ".json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(_articles_to_json(articles), f, ensure_ascii=False, indent=1)
    return json_path


# ── Checkpoint wrappers (delegate to unified module) ─────────────────────────

_STAGES = ["fetch_dedup", "translated", "sentiment"]


def _save_checkpoint(
    event_key: str,
    stage: str,
    articles: list[NewsArticle],
    extra: dict | None = None,
) -> str:
    path = _save_checkpoint_unified(event_key, stage, articles, extra)
    log(f"  [checkpoint] {stage}: saved {len(articles)} articles -> {path}")
    return path


def _load_checkpoint(event_key: str, stage: str) -> tuple[list[NewsArticle], dict] | None:
    result = _load_checkpoint_unified(event_key, stage)
    if result is None:
        return None
    articles, extra = result
    saved_at = extra.get("_saved_at", "?")
    log(f"  [checkpoint] {stage}: loaded {len(articles)} articles (saved {saved_at})")
    return articles, extra


def _find_latest_checkpoint(event_key: str) -> str | None:
    return _find_latest_checkpoint_unified(event_key, _STAGES)


# ── Fetcher helpers ───────────────────────────────────────────────────────────

_api_call_counts: dict[str, int] = {}


def _count_api_call(source_label: str, count: int = 1) -> None:
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
    total_timeout: float = 600.0,
) -> list[NewsArticle]:
    """Run a source for all query groups sequentially with rate limiting."""
    total = len(query_groups)
    log(f"\n[{source_label}] fetching {total} query groups...")
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
                        log_err(f"  {progress} ERROR '{kw[:50]}': {result.error.splitlines()[0][:80]}")
                    elif result.articles:
                        log(f"  {progress} '{kw[:50]}': {len(result.articles)}")
                    else:
                        log(f"  {progress} '{kw[:50]}': 0")
                    all_arts.extend(result.articles)
                except asyncio.TimeoutError:
                    _count_api_call(source_label)
                    completed += 1
                    kw = kw_list[0] if kw_list else ""
                    log_err(f"  [{source_label} {completed}/{total}] TIMEOUT '{kw[:50]}': skipped")
                await asyncio.sleep(delay)
    except (asyncio.TimeoutError, TimeoutError):
        log_err(f"  [{source_label}] total timeout ({total_timeout:.0f}s) at {completed}/{total}, stopping.")
    log(f"  [{source_label}] done: {len(all_arts)} articles from {completed}/{total} queries")
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
    log(f"\n[{source_label}] batched: {total} sections ({total_queries} queries merged)...")
    all_arts: list[NewsArticle] = []
    completed = 0
    try:
        async with asyncio.timeout(total_timeout):
            for i, section_queries in enumerate(sections):
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
                        log_err(f"  {progress} ERROR ({len(section_queries)}q) '{section_preview}...': {result.error.splitlines()[0][:80]}")
                    else:
                        log(f"  {progress} ({len(section_queries)}q) '{section_preview}...': {len(result.articles)}")
                    all_arts.extend(result.articles)
                except asyncio.TimeoutError:
                    _count_api_call(source_label)
                    completed += 1
                    log_err(f"  [{source_label} batch {completed}/{total}] TIMEOUT: skipped")
                await asyncio.sleep(delay)
    except (asyncio.TimeoutError, TimeoutError):
        log_err(f"  [{source_label}] total timeout at {completed}/{total}, stopping.")
    log(f"  [{source_label}] done: {len(all_arts)} articles from {completed}/{total} batch calls")
    return all_arts


# ── Executive summary generation (Grok reasoning, 1 API call) ─────────────────

_SUMMARY_PROMPT = """\
你是一位资深国际舆情分析师。下面是关于"{event_name}"的海外媒体报道分类统计和各类代表性标题。

请撰写一段 **300-400字的中文综合舆情摘要**，包含：
1. 总体舆情态势（哪种声音占主导）
2. 正面声音的核心论点（2-3句）
3. 负面/批评声音的核心论点（2-3句）
4. 深度分析类文章关注的焦点议题
5. 值得关注的信号或趋势

风格：客观、专业、信息密度高。不要用"综上所述"等套话。直接输出摘要文本，不要加标题。
"""


async def _generate_executive_summary(
    articles: list[NewsArticle],
    event_name: str,
    sentiment_log: list[dict],
    overseas_proxy: str,
) -> str:
    """Generate a 300-400 char executive summary via Grok reasoning. 1 API call."""
    from news_monitor.proxy import get_proxies_for_url, build_httpx_client

    # Build concise input: distribution + top titles per category
    dist = {}
    by_cat: dict[str, list[str]] = {}
    for art in articles:
        cat = art.category or "neutral"
        dist[cat] = dist.get(cat, 0) + 1
        by_cat.setdefault(cat, []).append(art.title_zh or art.title)

    cat_labels = {"positive": "正面", "neutral": "中性", "negative": "负面", "analysis": "分析"}
    input_lines = [f"统计: {', '.join(f'{cat_labels.get(k,k)}={v}' for k,v in dist.items())}，共{len(articles)}篇", ""]
    for cat, label in cat_labels.items():
        titles = by_cat.get(cat, [])
        if titles:
            input_lines.append(f"【{label}】代表性标题:")
            for t in titles[:20]:  # top 20 per category
                input_lines.append(f"  - {t[:80]}")
            input_lines.append("")

    user_msg = "\n".join(input_lines)
    system_prompt = _SUMMARY_PROMPT.format(event_name=event_name)

    api_key = os.environ.get("GROK_API_KEY", "")
    if not api_key:
        return ""

    base_url = os.environ.get("GROK_BASE_URL", "") or "https://api.x.ai/v1"
    url = f"{base_url.rstrip('/')}/chat/completions"
    proxy = get_proxies_for_url(url, overseas_proxy)

    try:
        body = {
            "model": "grok-4-1-fast-reasoning",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_msg},
            ],
            "temperature": 0.3,
        }
        async with build_httpx_client(proxy_url=proxy or "", timeout=120.0) as client:
            resp = await client.post(url, json=body, headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            })
            resp.raise_for_status()
            data = resp.json()
        summary = data["choices"][0]["message"]["content"].strip()
        # Strip markdown fences if any
        if summary.startswith("```"):
            summary = summary.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        log(f"  [summary] generated ({len(summary)} chars)")
        return summary
    except Exception as exc:
        log_err(f"  [summary] failed: {exc}")
        return ""


# ── Topic clustering (title similarity) ──────────────────────────────────────

def _title_sim(a: str, b: str) -> float:
    """Quick similarity via character overlap ratio."""
    if not a or not b:
        return 0.0
    from difflib import SequenceMatcher
    return SequenceMatcher(None, a, b).ratio()


def _cluster_articles(articles: list[NewsArticle], threshold: float = 0.45) -> list[list[NewsArticle]]:
    """Greedy clustering by title similarity. Returns list of clusters."""
    if not articles:
        return []
    clusters: list[list[NewsArticle]] = []
    rep_titles: list[str] = []

    for art in articles:
        title = art.title_zh or art.title or ""
        best_idx, best_sim = -1, 0.0
        for i, rep in enumerate(rep_titles):
            sim = _title_sim(title, rep)
            if sim > best_sim:
                best_sim = sim
                best_idx = i
        if best_sim >= threshold and best_idx >= 0:
            clusters[best_idx].append(art)
        else:
            clusters.append([art])
            rep_titles.append(title)

    return clusters


# ── MD report for sentiment-based grouping ────────────────────────────────────

_SENTIMENT_CATEGORIES = [
    ("positive", "正面/建设性报道"),
    ("neutral",  "中性/客观报道"),
    ("negative", "负面/批评报道"),
    ("analysis", "深度分析"),
]

_SENTIMENT_EMOJI = {
    "positive": "🟢",
    "neutral":  "🔵",
    "negative": "🔴",
    "analysis": "🟣",
}

# How many top articles to show in detail per category
_TOP_N = 15


def _render_cluster_md(
    cluster: list[NewsArticle],
    idx: int,
    importance_map: dict[str, int],
    attitude_map: dict[str, str],
) -> list[str]:
    """Render one cluster (possibly multi-article) in MD."""
    lines: list[str] = []
    rep = cluster[0]  # representative article
    title = rep.title_zh or rep.title
    attitude = attitude_map.get(title, "")
    importance = importance_map.get(title, 3)
    summary = rep.summary_zh or rep.description_zh or rep.description or ""

    if len(cluster) == 1:
        # Single article
        lines.append(f"### {idx}. {title}")
        lines.append("")
        if attitude:
            lines.append(f"> **核心态度：** {attitude}")
            lines.append("")
        if summary and summary != attitude:
            lines.append(summary[:400])
            lines.append("")
        engine_tag = f" `[{'+'.join(rep.found_by)}]`" if rep.found_by else ""
        tier_badge = get_tier_badge(rep.source_url) if rep.source_url else ""
        tier_str = f" `{tier_badge}`" if tier_badge else ""
        pub_str = rep.published_at.strftime("%Y-%m-%d %H:%M") if rep.published_at else "N/A"
        lines.append(f"> **来源：** {rep.source_name or 'N/A'}{tier_str}{engine_tag}  |  **发布：** {pub_str}  |  **重要度：** {'★' * importance}")
        if rep.source_url:
            lines.append(f"> **链接：** {rep.source_url}")
    else:
        # Multi-article cluster
        sources = set()
        for a in cluster:
            for fb in a.found_by:
                sources.add(fb)
        src_tag = f" `[{'+'.join(sorted(sources))}]`" if sources else ""
        lines.append(f"### {idx}. {title}（{len(cluster)} 篇报道）{src_tag}")
        lines.append("")
        if attitude:
            lines.append(f"> **核心态度：** {attitude}")
            lines.append("")
        if summary and summary != attitude:
            lines.append(summary[:400])
            lines.append("")
        # List other articles in cluster (with tier badge)
        for a in cluster[1:]:
            a_title = (a.title_zh or a.title or "")[:60]
            a_src = a.source_name or "N/A"
            a_tier = get_tier_badge(a.source_url) if a.source_url else ""
            tier_prefix = f"{a_tier} " if a_tier else ""
            if a.source_url:
                lines.append(f"- {tier_prefix}[{a_src}] {a_title} — {a.source_url}")
            else:
                lines.append(f"- {tier_prefix}[{a_src}] {a_title}")

    lines += ["", "---", ""]
    return lines


def _generate_sentiment_md(
    articles: list[NewsArticle],
    report: CycleReport,
    event_name: str,
    sentiment_log: list[dict] | None = None,
    executive_summary: str = "",
) -> str:
    """Generate MD content: executive summary + clustered articles by sentiment."""
    gen_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    groups: dict[str, list[NewsArticle]] = {cat: [] for cat, _ in _SENTIMENT_CATEGORIES}
    for art in articles:
        cat = art.category if art.category in groups else "neutral"
        groups[cat].append(art)

    # Build importance/attitude lookup
    importance_map: dict[str, int] = {}
    attitude_map: dict[str, str] = {}
    if sentiment_log:
        for entry in sentiment_log:
            t = entry.get("title", "")
            importance_map[t] = entry.get("importance", 3)
            attitude_map[t] = entry.get("key_attitude", "")

    # Count clusters for stats
    total_clusters = 0
    for cat_key, _ in _SENTIMENT_CATEGORIES:
        arts = groups[cat_key]
        if arts:
            total_clusters += len(_cluster_articles(arts))

    lines = [
        f"# {event_name} — 海外媒体舆情报告",
        "",
        f"**生成时间：** {gen_time}",
        "",
    ]

    # ── Executive summary (improvement #1)
    if executive_summary:
        lines += [
            "## 综合舆情摘要",
            "",
            executive_summary,
            "",
            "---",
            "",
        ]

    # ── Data overview
    lines += [
        "## 数据概览",
        "",
        "| 指标 | 数量 |",
        "|:---|---:|",
        f"| 抓取文章数 | {report.total_fetched} |",
        f"| 去重后数量 | {report.total_after_dedup} |",
        f"| 已翻译数量 | {report.total_translated} |",
        f"| 最终收录 | {len(articles)} |",
        f"| 聚类主题数 | {total_clusters} |",
        "",
        "## 舆情态度分布",
        "",
        "| 类别 | 数量 | 占比 |",
        "|:---|---:|---:|",
    ]
    for cat_key, cat_label in _SENTIMENT_CATEGORIES:
        n = len(groups[cat_key])
        if n:
            pct = n / max(len(articles), 1) * 100
            emoji = _SENTIMENT_EMOJI.get(cat_key, "")
            lines.append(f"| {emoji} {cat_label} | {n} | {pct:.0f}% |")
    lines += ["", "---", ""]

    # ── Sections by sentiment (improvement #2 clustering + #3 top N)
    for cat_key, cat_label in _SENTIMENT_CATEGORIES:
        arts = groups[cat_key]
        if not arts:
            continue

        emoji = _SENTIMENT_EMOJI.get(cat_key, "")
        # P1-4: Sort by tier (lower=better) then importance (higher=better)
        arts.sort(key=lambda a: (get_tier(a.source_url) if a.source_url else 4, -importance_map.get(a.title_zh or a.title, 3)))

        # Cluster
        clusters = _cluster_articles(arts)
        # Sort clusters by max importance in cluster
        clusters.sort(
            key=lambda c: max(importance_map.get(a.title_zh or a.title, 3) for a in c),
            reverse=True,
        )

        shown = min(len(clusters), _TOP_N)
        remaining = len(clusters) - shown
        total_arts = sum(len(c) for c in clusters)

        lines += [f"## {emoji} {cat_label}（{total_arts} 篇，{len(clusters)} 个主题，展示 Top {shown}）", ""]

        # Top N clusters in detail
        for idx, cluster in enumerate(clusters[:_TOP_N], 1):
            cluster_lines = _render_cluster_md(cluster, idx, importance_map, attitude_map)
            lines.extend(cluster_lines)

        # Remaining clusters as compact list
        if remaining > 0:
            lines += [f"#### 其余 {remaining} 个主题", ""]
            for cluster in clusters[_TOP_N:]:
                rep = cluster[0]
                title = (rep.title_zh or rep.title or "")[:70]
                count = f" ({len(cluster)}篇)" if len(cluster) > 1 else ""
                src = rep.source_name or ""
                lines.append(f"- {title}{count} — {src}")
            lines += ["", "---", ""]

        # P1-7: Social media section for Grok X results within this category
        social_arts = [a for a in arts if _is_grok_x_result(a)]
        if social_arts:
            lines += [f"#### 社交媒体舆情（{len(social_arts)} 条）", ""]
            for sa in social_arts[:10]:
                sa_title = (sa.title_zh or sa.title or "")[:80]
                # Extract handle from URL if possible
                handle = ""
                if sa.source_url:
                    import re as _re
                    m = _re.search(r'(?:x\.com|twitter\.com)/([^/]+)', sa.source_url)
                    if m:
                        handle = f"@{m.group(1)}"
                handle_str = f" ({handle})" if handle else ""
                pub = sa.published_at.strftime("%m-%d") if sa.published_at else ""
                pub_str = f" [{pub}]" if pub else ""
                lines.append(f"- {sa_title}{handle_str}{pub_str}")
                if sa.source_url:
                    lines.append(f"  {sa.source_url}")
            if len(social_arts) > 10:
                lines.append(f"- *...及其他 {len(social_arts) - 10} 条*")
            lines += ["", "---", ""]

    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────────────────────

async def _run_event(
    topic: dict, config: dict, overseas_proxy: str, sources_cfg: dict,
    resume: bool = False,
    incremental: bool = False,
) -> None:
    """Run the full event monitoring pipeline with checkpoint support."""

    event_name_zh = topic.get("event_name_zh", topic.get("name", "事件"))
    event_name_en = topic.get("event_name_en", "Event")
    event_key = topic.get("name", "event").replace(" ", "_").lower()[:30]
    query_groups: list[list[str]] = [[q] for q in topic.get("query_groups", [])]
    sections = topic.get("_sections", [])
    time_range_hours = topic.get("time_range_hours", 504)
    max_articles = topic.get("max_articles", 30)
    languages = topic.get("languages", ["en", "zh"])
    exclude_kw = topic.get("exclude_keywords")

    from_date = os.environ.get("FETCH_FROM") or topic.get("fetch_from", "")
    to_date = os.environ.get("FETCH_TO") or topic.get("fetch_to", "")

    trans_cfg = config.get("translation", {})
    filter_cfg = config.get("filter", {})

    # Source selection
    sources_env = os.environ.get("FETCH_SOURCES", "").strip()
    if sources_env:
        enabled_sources = {s.strip() for s in sources_env.split(",") if s.strip()}
    else:
        enabled_sources = {"brave", "gemini", "grok_web", "grok_x"}

    _api_call_counts.clear()

    # -- Check resume state
    resume_stage: str | None = None
    if resume:
        resume_stage = _find_latest_checkpoint(event_key)
        if resume_stage:
            log(f"{_GREEN}Resuming from checkpoint: {resume_stage}{_RESET}")
        else:
            log("No checkpoint found, starting fresh.")

    # P1-6: Incremental mode -- adjust from_date based on last checkpoint time
    if incremental and resume_stage:
        loaded = _load_checkpoint(event_key, resume_stage)
        if loaded:
            _, inc_extra = loaded
            last_saved = inc_extra.get("_saved_at", "")
            if last_saved:
                from_date = last_saved[:10]  # YYYY-MM-DD
                log(f"Incremental mode: fetching from {from_date}")

    log(f"Event     : {event_name_zh} ({event_name_en})")
    log(f"Dates     : {from_date} -> {to_date}")
    log(f"Languages : {languages}")
    log(f"Sources   : {', '.join(sorted(enabled_sources))}")
    log(f"Queries   : {len(query_groups)}")
    if sections:
        log(f"Grok batch: {len(sections)} sections ({sum(len(s) for s in sections)} queries)")
    log(f"Translate : grok (grok-4-1-fast-non-reasoning)")
    log(f"Sentiment : grok (grok-4-1-fast-reasoning)")
    log("=" * 72)

    raw_total = 0
    translated = 0
    unique: list[NewsArticle] = []
    sentiment_log: list[dict] = []

    # ══════════════════════════════════════════════════════════════════════
    # STAGE 1: Fetch + Dedup
    # ══════════════════════════════════════════════════════════════════════
    if resume_stage and resume_stage in ("fetch_dedup", "translated", "sentiment"):
        # Load from checkpoint
        loaded = _load_checkpoint(event_key, "fetch_dedup")
        if loaded:
            unique, extra = loaded
            raw_total = extra.get("raw_total", len(unique))
            log(f"Skipping fetch+dedup (loaded {len(unique)} articles from checkpoint)")
        else:
            resume_stage = None  # checkpoint broken, start fresh

    if not unique:
        # -- Fetch params
        fetch_kw = dict(
            topic_name=topic.get("name", event_name_zh),
            countries=[],
            languages=languages,
            time_range_hours=time_range_hours,
            max_articles=max_articles,
            exclude_kw=exclude_kw,
            from_date=from_date,
            to_date=to_date,
        )

        # -- Init sources
        tasks: list[tuple[str, any]] = []

        if "brave" in enabled_sources:
            bv_cfg = sources_cfg.get("brave_search", {})
            if not bv_cfg.get("api_key"):
                bv_cfg["api_key"] = os.environ.get("BRAVEAPI", "")
            brave = BraveSearch(bv_cfg, overseas_proxy)
            tasks.append(("Brave", _fetch_source(
                brave, query_groups, source_label="Brave",
                delay=1.1, per_query_timeout=30.0, total_timeout=900.0,
                **fetch_kw,
            )))

        if "gemini" in enabled_sources:
            gm_cfg = sources_cfg.get("gemini_search", {})
            gemini = GeminiSearch(gm_cfg, overseas_proxy)
            tasks.append(("Gemini", _fetch_source(
                gemini, query_groups, source_label="Gemini",
                delay=2.0, per_query_timeout=60.0, total_timeout=1500.0,
                **fetch_kw,
            )))

        if "grok_web" in enabled_sources:
            gw_cfg = sources_cfg.get("grok_web_search", {})
            grok_web = GrokWebSearch(gw_cfg, overseas_proxy)
            if sections:
                tasks.append(("Grok Web", _fetch_source_batched(
                    grok_web, sections, source_label="Grok Web",
                    topic_name=fetch_kw["topic_name"], countries=[],
                    languages=languages, time_range_hours=time_range_hours,
                    max_articles=max_articles, from_date=from_date, to_date=to_date,
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
            if sections:
                tasks.append(("Grok X", _fetch_source_batched(
                    grok_x, sections, source_label="Grok X",
                    topic_name=fetch_kw["topic_name"], countries=[],
                    languages=languages, time_range_hours=time_range_hours,
                    max_articles=max_articles, from_date=from_date, to_date=to_date,
                    delay=2.0, per_batch_timeout=180.0, total_timeout=1200.0,
                )))
            else:
                tasks.append(("Grok X", _fetch_source(
                    grok_x, query_groups, source_label="Grok X",
                    delay=1.5, per_query_timeout=60.0, total_timeout=1200.0,
                    **fetch_kw,
                )))

        # -- Run sources in parallel
        results = await asyncio.gather(
            *[t[1] for t in tasks],
            return_exceptions=True,
        )

        all_arts: list[NewsArticle] = []
        source_counts: dict[str, int] = {}
        for (label, _), res in zip(tasks, results):
            if isinstance(res, Exception):
                log_err(f"\n[{label}] EXCEPTION: {res}")
                source_counts[label] = 0
            else:
                for a in res:
                    if not a.found_by:
                        a.found_by = [label]
                all_arts.extend(res)
                source_counts[label] = len(res)

        raw_total = len(all_arts)
        log(f"\n{'=' * 72}")
        log(f"Raw totals: {' | '.join(f'{k}: {v}' for k, v in source_counts.items())} | Total: {raw_total}")

        # P0-2: Early domain filter -- before dedup to avoid wasting translation tokens
        all_arts = _filter_blocked(all_arts)

        # P1-7: Clean Grok X titles
        for a in all_arts:
            if _is_grok_x_result(a):
                a.title = _clean_grok_x_title(a.title)

        # -- Dedup
        unique = _dedup_merge(all_arts)
        log(f"After dedup: {len(unique)}  (removed {raw_total - len(unique)} duplicates)")

        # Sort by date (newest first)
        from datetime import timezone as _tz
        _EPOCH = datetime.min.replace(tzinfo=_tz.utc)
        def _sort_key(a):
            p = a.published_at
            if p is None:
                return _EPOCH
            if p.tzinfo is None:
                p = p.replace(tzinfo=_tz.utc)
            return p
        unique.sort(key=_sort_key, reverse=True)

        multi_source = sum(1 for a in unique if len(a.found_by) > 1)
        log(f"Multi-source articles: {multi_source}")
        log("=" * 72)

        # ★ Save checkpoint: fetch_dedup
        _save_checkpoint(event_key, "fetch_dedup", unique, {"raw_total": raw_total})

    # ══════════════════════════════════════════════════════════════════════
    # STAGE 2: Translate (title only)
    # ══════════════════════════════════════════════════════════════════════
    if resume_stage and resume_stage in ("translated", "sentiment"):
        loaded = _load_checkpoint(event_key, "translated")
        if loaded:
            unique, extra = loaded
            translated = extra.get("translated", sum(1 for a in unique if a.title_zh))
            raw_total = extra.get("raw_total", raw_total)
            log(f"Skipping translation (loaded {len(unique)} articles, {translated} translated)")
        else:
            resume_stage = "fetch_dedup"  # fallback to re-translate

    if not any(a.title_zh for a in unique):
        # Pre-process: save descriptions, then clear so translator only sends titles
        saved_descriptions: list[str] = [a.description for a in unique]
        for a in unique:
            a.description = ""

        # Use grok-4-1-fast-non-reasoning for translation (avoids qwen content filter)
        translator = LLMTranslator(
            provider="grok",
            fallback_chain=["qwen", "deepseek", "doubao", "glm"],
            batch_size=0,
            overseas_proxy=overseas_proxy,
            country_zh=event_name_zh,
            country_en=event_name_en,
        )
        log(f"\nTranslating {len(unique)} titles (provider=grok)...")
        unique = await translator.translate_articles(unique)
        translated = sum(1 for a in unique if a.title_zh)
        log(f"Done. {translated}/{len(unique)} titles translated.")

        # Restore descriptions and build local summaries
        for a, orig_desc in zip(unique, saved_descriptions):
            a.description = orig_desc
            if not a.summary_zh:
                desc = a.description_zh or a.description or ""
                a.summary_zh = desc[:200].strip() if desc else ""

        # ★ Save checkpoint: translated
        _save_checkpoint(event_key, "translated", unique, {"raw_total": raw_total, "translated": translated})

    # ══════════════════════════════════════════════════════════════════════
    # STAGE 3: Sentiment classification
    # ══════════════════════════════════════════════════════════════════════
    if resume_stage == "sentiment":
        loaded = _load_checkpoint(event_key, "sentiment")
        if loaded:
            unique, extra = loaded
            sentiment_log = extra.get("sentiment_log", [])
            raw_total = extra.get("raw_total", raw_total)
            translated = extra.get("translated", translated)
            log(f"Skipping sentiment (loaded {len(unique)} articles)")
        else:
            resume_stage = "translated"

    if not sentiment_log:
        classifier = SentimentClassifier(
            provider="grok",
            fallback_chain=["qwen", "deepseek", "doubao", "kimi"],
            batch_size=0,
            overseas_proxy=overseas_proxy,
        )
        log(f"\nClassifying sentiment for {len(unique)} articles...")
        unique, sentiment_log = await classifier.classify_articles(unique, event_name_zh, event_name_en)

        # Print sentiment distribution
        sentiment_dist: dict[str, int] = {}
        for art in unique:
            sentiment_dist[art.category] = sentiment_dist.get(art.category, 0) + 1
        log(f"Sentiment distribution: {sentiment_dist}")

        # ★ Save checkpoint: sentiment
        _save_checkpoint(event_key, "sentiment", unique, {
            "raw_total": raw_total, "translated": translated,
            "sentiment_log": sentiment_log,
        })

    # -- API Call Summary
    log(f"\n{'=' * 72}")
    log("== API Call Summary ==")
    for label in ["Brave", "Gemini", "Grok Web", "Grok X"]:
        calls = _api_call_counts.get(label, 0)
        if calls:
            log(f"  {label:14s}: {calls:3d} calls")
    log(f"  Translate    : {trans_cfg.get('provider', 'qwen')}")
    log(f"  Sentiment    : grok")
    log(f"{'=' * 72}")

    # ══════════════════════════════════════════════════════════════════════
    # STAGE 4: Executive summary (1 API call, Grok reasoning)
    # ══════════════════════════════════════════════════════════════════════
    log("\nGenerating executive summary...")
    executive_summary = await _generate_executive_summary(
        unique, event_name_zh, sentiment_log, overseas_proxy,
    )

    # ══════════════════════════════════════════════════════════════════════
    # STAGE 5: Generate reports
    # ══════════════════════════════════════════════════════════════════════
    report = CycleReport(
        total_fetched=raw_total,
        total_after_dedup=len(unique),
        total_translated=translated,
    )

    output_dir = "output/reports"
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # 1. MD report
    md_content = _generate_sentiment_md(unique, report, event_name_zh, sentiment_log, executive_summary)
    md_path = str(Path(output_dir) / f"{ts}_boao_forum.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    log(f"\nMD saved  : {md_path}")

    # 2. JSON sidecar
    json_path = _save_articles_json(unique, md_path)
    log(f"JSON saved: {json_path}")

    # 3. Word report
    try:
        from news_monitor.output.docx_reporter import generate_docx_report
        docx_path = generate_docx_report(
            unique, report, output_dir, event_name_zh, sentiment_log, ts=ts,
            executive_summary=executive_summary,
        )
        log(f"DOCX saved: {docx_path}")
    except ImportError:
        log(f"python-docx not installed, skipping Word report. Install with: pip install python-docx")
    except Exception as exc:
        log_err(f"DOCX generation failed: {exc}")

    # 4. PDF report (reuse existing)
    try:
        from news_monitor.output.pdf_reporter import _md_to_pdf_pandoc, _md_to_pdf_weasyprint
        pdf_path = str(Path(output_dir) / f"{ts}_boao_forum.pdf")
        if _md_to_pdf_pandoc(md_path, pdf_path):
            log(f"PDF saved : {pdf_path}")
        elif _md_to_pdf_weasyprint(md_path, pdf_path):
            log(f"PDF saved : {pdf_path}")
        else:
            log(f"PDF conversion not available (pandoc/weasyprint not found)")
    except Exception as exc:
        log_err(f"PDF generation failed: {exc}")

    # P1-5: Record trend snapshot
    sentiment_dist: dict[str, int] = {}
    for art in unique:
        sentiment_dist[art.category] = sentiment_dist.get(art.category, 0) + 1
    try:
        trend_path = record_snapshot(event_key, unique, sentiment_dist)
        log(f"Trend snapshot saved: {trend_path}")
    except Exception as exc:
        log_err(f"Trend snapshot failed: {exc}")


async def main(args: list[str]) -> None:
    _init_log()  # Start dual logging (terminal + file)

    config = load_config("config.yaml")
    overseas_proxy = config.get("proxy", {}).get("overseas_proxy", "")
    sources_cfg = config.get("sources", {})

    # Parse flags
    resume = "--resume" in args
    incremental = "--incremental" in args
    positional = [a for a in args if not a.startswith("--")]
    query = positional[0] if positional else "boao"

    topic_file = _find_topic_file(query)

    if not topic_file:
        log_err(f"No topic file found matching: {query!r}")
        log("Available event topics:")
        for f in sorted(Path("topics").glob("*.md")):
            log(f"  {f.stem}")
        sys.exit(1)

    log(f"Topic file: {topic_file}")
    topic = _parse_topic_file(topic_file)
    await _run_event(topic, config, overseas_proxy, sources_cfg, resume=resume, incremental=incremental)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    asyncio.run(main(sys.argv[1:]))
