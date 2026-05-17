"""Generate MD + PDF reports from a pipeline cycle's articles.

Flow:
  1. Always write a Markdown (.md) file.
  2. Try converting MD → PDF via pandoc (xelatex) then weasyprint.
  3. Fall back to fpdf2 with fixed line-height layout.
"""
from __future__ import annotations

import logging
import os
import re
import subprocess
import warnings
from collections import defaultdict
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path

from news_monitor.models import CycleReport, NewsArticle

logger = logging.getLogger("news_monitor.output.pdf_reporter")

_FONT_CANDIDATES = [
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simsun.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
]

# Report categories — only foreign-policy lines, no country-domestic bucket
_BASE_CATEGORIES = [
    ("us",        "美国相关"),
    ("china",     "中国相关"),
    ("sentiment", "对华舆情"),
    ("taiwan",    "台湾相关"),
]

# Default keywords always highlighted
_DEFAULT_HIGHLIGHT = ["中国", "China", "美国", "USA", "US", "台湾", "Taiwan"]


# ── Shared helpers ──────────────────────────────────────────────────────────

def _find_font() -> str | None:
    for path in _FONT_CANDIDATES:
        if os.path.exists(path):
            return path
    return None


def _trunc(text: str, n: int) -> str:
    return text[:n] + "…" if len(text) > n else text


def _build_highlight_pattern(keywords: list[str]) -> re.Pattern | None:
    if not keywords:
        return None
    escaped = sorted((re.escape(k) for k in keywords if k), key=len, reverse=True)
    if not escaped:
        return None
    return re.compile("(" + "|".join(escaped) + ")", re.IGNORECASE)


def _group_by_category(
    articles: list[NewsArticle],
    categories: list[tuple[str, str]],
    default_key: str,
) -> dict[str, list[NewsArticle]]:
    groups: dict[str, list[NewsArticle]] = {cat: [] for cat, _ in categories}
    for art in articles:
        if art.category in groups:
            groups[art.category].append(art)
        # Articles with unrecognized category (country-domestic) are silently dropped
    return groups


# ── Topic clustering ───────────────────────────────────────────────────────

def _is_tweet(art: NewsArticle) -> bool:
    """Check if article is a tweet (from X/Twitter)."""
    url = art.source_url or ""
    return "x.com/i/status/" in url or "twitter.com/i/status/" in url


def _title_similarity(a: str, b: str) -> float:
    """Compute title similarity for clustering."""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _cluster_articles(articles: list[NewsArticle], threshold: float = 0.40) -> list[list[NewsArticle]]:
    """Greedy clustering: group articles with similar titles.

    Returns list of clusters, each cluster is a list of articles.
    First article in each cluster is the representative.
    """
    if not articles:
        return []

    clusters: list[list[NewsArticle]] = []
    cluster_titles: list[str] = []  # representative title for each cluster

    for art in articles:
        title = art.title_zh or art.title or ""
        best_idx = -1
        best_sim = 0.0
        for i, rep_title in enumerate(cluster_titles):
            sim = _title_similarity(title, rep_title)
            if sim > best_sim:
                best_sim = sim
                best_idx = i

        if best_sim >= threshold and best_idx >= 0:
            clusters[best_idx].append(art)
        else:
            clusters.append([art])
            cluster_titles.append(title)

    return clusters


def _cluster_theme_title(cluster: list[NewsArticle]) -> str:
    """Pick the best title for a cluster (longest title_zh)."""
    best = max(cluster, key=lambda a: len(a.title_zh or a.title or ""))
    return best.title_zh or best.title or "未知主题"


def _cluster_summary(cluster: list[NewsArticle]) -> str:
    """Build a condensed summary from cluster articles.

    Collects unique summary sentences, deduplicates by similarity.
    """
    summaries: list[str] = []
    for art in cluster:
        s = art.summary_zh or art.description_zh or art.description or ""
        s = s.strip()
        if not s or len(s) < 10:
            continue
        # Deduplicate similar summaries
        is_dup = False
        for existing in summaries:
            if _title_similarity(s, existing) > 0.50:
                is_dup = True
                break
        if not is_dup:
            summaries.append(s)

    if not summaries:
        return ""
    # Return concatenated unique summaries, truncated
    combined = "；".join(summaries)
    if len(combined) > 500:
        combined = combined[:500] + "…"
    return combined


def _parse_tweet_author(title: str) -> tuple[str, str]:
    """Extract author and content from Grok X search title.

    Formats seen:
      'Post [post:12] by Peter Zeihan (@PeterZeihan, geopolitical strategist), Fri Mar 6 2026 21:00:01 GMT'
      'Focus is on the major story: China's Cosco Shipping halting operations...'
      'Here are the most relevant posts from journalists...'
    Returns (author_info, content_snippet).
    """
    author = ""
    content = title

    # Pattern: "Post ... by Author (@handle, role), date"
    m = re.match(r'Post\s+\[post:\d+\]\s+by\s+(.+?)\s*,\s*\w{3}\s+\w{3}\s+\d+', title)
    if m:
        author = m.group(1).strip()
        content = ""  # no content in this format
        return author, content

    # Pattern: "... by Author (@handle)"
    m2 = re.search(r'by\s+([^,]+\(@\w+[^)]*\))', title)
    if m2:
        author = m2.group(1).strip()

    # Strip meta prefixes
    for prefix in ["Focus is on the major story: ", "Here are the most relevant posts "]:
        if content.startswith(prefix):
            content = content[len(prefix):]
            break

    return author, content.strip()


def _tweet_cluster_summary(cluster: list[NewsArticle]) -> str:
    """Build a rich summary for tweet clusters (target ≥150 chars).

    Combines: author info + original English content + translated summaries.
    """
    parts: list[str] = []
    authors: list[str] = []
    seen_content: list[str] = []

    for art in cluster:
        # Extract author and content from original title
        author, orig_content = _parse_tweet_author(art.title or "")
        if author and author not in authors:
            authors.append(author)

        # Original English content (often richer than translated)
        if orig_content and len(orig_content) >= 15:
            is_dup = any(_title_similarity(orig_content, s) > 0.50 for s in seen_content)
            if not is_dup:
                seen_content.append(orig_content)

        # Translated summary
        s = art.summary_zh or art.description_zh or ""
        s = s.strip()
        if s and len(s) >= 10:
            is_dup = any(_title_similarity(s, existing) > 0.50 for existing in parts)
            if not is_dup:
                parts.append(s)

    # Build final summary
    lines: list[str] = []

    # Author line
    if authors:
        lines.append(f"发布者：{'、'.join(authors[:5])}")

    # Chinese summaries
    if parts:
        lines.append("；".join(parts))

    # Supplement with English content if still short
    combined = "。".join(lines)
    if len(combined) < 150 and seen_content:
        eng_parts = [c for c in seen_content if len(c) >= 15]
        if eng_parts:
            lines.append("原文摘要：" + "；".join(eng_parts))

    combined = "。".join(lines)
    if len(combined) > 600:
        combined = combined[:600] + "…"
    return combined


def _split_news_tweets(articles: list[NewsArticle]) -> tuple[list[NewsArticle], list[NewsArticle]]:
    """Split articles into news and tweets."""
    news = [a for a in articles if not _is_tweet(a)]
    tweets = [a for a in articles if _is_tweet(a)]
    return news, tweets


# ── Markdown report ─────────────────────────────────────────────────────────

def _highlight_md(text: str, pattern: re.Pattern | None) -> str:
    """Wrap matched keywords with **bold** in Markdown."""
    if not pattern or not text:
        return text
    return pattern.sub(r"**\1**", text)


def _render_cluster_md(
    cluster: list[NewsArticle],
    idx: int,
    hl_pattern: re.Pattern | None,
) -> list[str]:
    """Render a single topic cluster in Markdown."""
    lines: list[str] = []
    theme = _cluster_theme_title(cluster)
    hl_theme = _highlight_md(theme, hl_pattern)

    if len(cluster) == 1:
        # Single article — render normally
        art = cluster[0]
        title = art.title_zh or art.title
        summary = art.summary_zh or art.description_zh or art.description or ""
        hl_title = _highlight_md(title, hl_pattern)
        hl_summary = _highlight_md(summary, hl_pattern)

        lines += [f"### {idx}. {hl_title}", ""]
        if hl_summary:
            lines += [hl_summary, ""]

        engine_tag = ""
        if art.found_by:
            engine_tag = f" `[{'+'.join(art.found_by)}]`"
        pub_str = art.published_at.strftime("%Y-%m-%d %H:%M") if art.published_at else "N/A"
        meta = [
            f"**来源：** {art.source_name or 'N/A'}{engine_tag}",
            f"**发布时间：** {pub_str}",
        ]
        if art.event_date:
            meta.append(f"**事件时间：** {art.event_date}")
        if art.source_url:
            meta.append(f"**链接：** {art.source_url}")
        for m in meta:
            lines.append(f"> {m}")
        lines += ["", "---", ""]
    else:
        # Multi-article cluster — theme + summary + link list
        summary = _cluster_summary(cluster)
        hl_summary = _highlight_md(summary, hl_pattern)
        sources_set = set()
        for a in cluster:
            for fb in a.found_by:
                sources_set.add(fb)
        src_tag = f" `[{'+'.join(sorted(sources_set))}]`" if sources_set else ""

        lines += [f"### {idx}. {hl_theme}（{len(cluster)} 篇）{src_tag}", ""]
        if hl_summary:
            lines += [hl_summary, ""]

        # Link list
        for art in cluster:
            art_title = _trunc(art.title_zh or art.title or "", 60)
            art_src = art.source_name or "N/A"
            if art.source_url:
                lines.append(f"- [{art_src}] {art_title} — {art.source_url}")
            else:
                lines.append(f"- [{art_src}] {art_title}")
        lines += ["", "---", ""]

    return lines


def _render_tweets_md(
    tweets: list[NewsArticle],
    start_idx: int,
    hl_pattern: re.Pattern | None,
) -> list[str]:
    """Render tweets section: cluster by theme, rich summaries + link lists."""
    if not tweets:
        return []
    lines: list[str] = []
    clusters = _cluster_articles(tweets, threshold=0.35)

    idx = start_idx
    for cluster in clusters:
        theme = _cluster_theme_title(cluster)
        hl_theme = _highlight_md(theme, hl_pattern)
        summary = _tweet_cluster_summary(cluster)
        hl_summary = _highlight_md(summary, hl_pattern)

        lines += [f"### {idx}. 🐦 {hl_theme}（{len(cluster)} 条推文）", ""]
        if hl_summary:
            lines += [hl_summary, ""]
        for art in cluster:
            # Show author from original title if available
            author, _ = _parse_tweet_author(art.title or "")
            label = f"@{author}" if author else _trunc(art.title_zh or art.title or "", 60)
            if art.source_url:
                lines.append(f"- {label} — {art.source_url}")
            else:
                lines.append(f"- {label}")
        lines += ["", "---", ""]
        idx += 1

    return lines


def _generate_md(
    articles: list[NewsArticle],
    report: CycleReport,
    topic_name: str,
    categories: list[tuple[str, str]],
    default_key: str,
    hl_pattern: re.Pattern | None,
) -> str:
    """Return the full Markdown content as a string."""
    gen_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    groups = _group_by_category(articles, categories, default_key)

    # Count clusters for statistics
    total_clusters = 0
    for cat_key, _ in categories:
        arts = groups[cat_key]
        if arts:
            news, tweets = _split_news_tweets(arts)
            clusters = _cluster_articles(news)
            tweet_clusters = _cluster_articles(tweets, threshold=0.35)
            total_clusters += len(clusters) + len(tweet_clusters)

    lines: list[str] = [
        f"# {topic_name}报告",
        "",
        f"**生成时间：** {gen_time}",
        "",
        "## 周期摘要",
        "",
        "| 指标 | 数量 |",
        "|:---|---:|",
        f"| 抓取文章数 | {report.total_fetched} |",
        f"| 去重后数量 | {report.total_after_dedup} |",
        f"| 已翻译数量 | {report.total_translated} |",
        f"| 聚类主题数 | {total_clusters} |",
        f"| 推送数量 | {report.total_pushed} |",
        "",
        "## 分类统计",
        "",
        "| 类别 | 数量 |",
        "|:---|---:|",
    ]
    for cat_key, cat_label in categories:
        n = len(groups[cat_key])
        if n:
            lines.append(f"| {cat_label} | {n} |")
    lines += ["", "---", ""]

    for cat_key, cat_label in categories:
        arts = groups[cat_key]
        if not arts:
            continue

        news, tweets = _split_news_tweets(arts)
        clusters = _cluster_articles(news)

        cluster_desc = f"{len(clusters)} 个主题" if len(clusters) < len(news) else ""
        tweet_desc = f"，{len(tweets)} 条推文" if tweets else ""
        header_extra = f"（{len(arts)} 篇"
        if cluster_desc:
            header_extra += f"，{cluster_desc}"
        header_extra += f"{tweet_desc}）"
        lines += [
            f"## ■ {cat_label}{header_extra}",
            "",
        ]

        # Render news clusters
        idx = 1
        for cluster in clusters:
            cluster_lines = _render_cluster_md(cluster, idx, hl_pattern)
            lines.extend(cluster_lines)
            idx += 1

        # Render tweets
        if tweets:
            tweet_lines = _render_tweets_md(tweets, idx, hl_pattern)
            lines.extend(tweet_lines)

    return "\n".join(lines)


def generate_md_report(
    articles: list[NewsArticle],
    report: CycleReport,
    output_dir: str,
    topic_name: str,
    country_key: str,
    country_label: str,
    categories: list[tuple[str, str]] | None = None,
    highlight_keywords: list[str] | None = None,
    ts: str | None = None,
) -> str:
    """Write a Markdown report file and return its path."""
    if categories is None:
        categories = list(_BASE_CATEGORIES)
    default_key = categories[-1][0]
    if ts is None:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    kw_set = set(_DEFAULT_HIGHLIGHT)
    if highlight_keywords:
        kw_set.update(highlight_keywords)
    hl_pattern = _build_highlight_pattern(list(kw_set))

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    md_path = str(Path(output_dir) / f"{ts}_{country_key}.md")
    content = _generate_md(articles, report, topic_name, categories, default_key, hl_pattern)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(content)
    logger.info("MD written: %s  (%d articles)", md_path, len(articles))
    return md_path


# ── MD → PDF converters ─────────────────────────────────────────────────────

def _md_to_pdf_pandoc(md_path: str, pdf_path: str) -> bool:
    """Convert via pandoc + xelatex. Returns True on success."""
    try:
        result = subprocess.run(
            [
                "pandoc", md_path, "-o", pdf_path,
                "--pdf-engine=xelatex",
                "-V", "CJKmainfont=Microsoft YaHei",
                "-V", "mainfont=Microsoft YaHei",
                "-V", "geometry:margin=25mm",
                "-V", "fontsize=11pt",
                "--wrap=none",
            ],
            capture_output=True,
            timeout=120,
        )
        if result.returncode == 0:
            logger.info("PDF via pandoc: %s", pdf_path)
            return True
        logger.debug("pandoc failed (rc=%d): %s", result.returncode,
                     result.stderr.decode(errors="replace")[:200])
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass
    return False


def _md_to_pdf_weasyprint(md_path: str, pdf_path: str) -> bool:
    """Convert via markdown → HTML → weasyprint PDF. Returns True on success."""
    try:
        import markdown as md_lib        # type: ignore
        from weasyprint import HTML      # type: ignore

        md_content = Path(md_path).read_text(encoding="utf-8")
        html_body = md_lib.markdown(
            md_content,
            extensions=["tables", "nl2br"],
        )
        html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
  body {{ font-family: 'Microsoft YaHei', 'SimSun', 'WenQuanYi Zen Hei', sans-serif;
          margin: 20mm; font-size: 11pt; line-height: 1.7; color: #222; }}
  h1 {{ font-size: 18pt; text-align: center; margin-bottom: 10px; }}
  h2 {{ font-size: 13pt; border-bottom: 2px solid #888; margin-top: 20px; padding-bottom: 4px; }}
  h3 {{ font-size: 11pt; margin-top: 14px; margin-bottom: 4px; color: #333; }}
  table {{ border-collapse: collapse; margin: 10px 0; }}
  td, th {{ border: 1px solid #bbb; padding: 4px 10px; }}
  th {{ background: #eee; }}
  blockquote {{ background: #f8f8f8; border-left: 3px solid #bbb;
                padding: 6px 12px; margin: 6px 0; font-size: 10pt; }}
  strong {{ color: #c45a00; }}
  hr {{ border: 0; border-top: 1px solid #ccc; margin: 12px 0; }}
  a {{ color: #1a6ab5; word-break: break-all; }}
</style></head><body>
{html_body}
</body></html>"""
        HTML(string=html).write_pdf(pdf_path)
        logger.info("PDF via weasyprint: %s", pdf_path)
        return True
    except ImportError:
        pass
    except Exception as exc:
        logger.warning("weasyprint failed: %s", exc)
    return False


# ── fpdf2 fallback ──────────────────────────────────────────────────────────

def _mc(pdf, w, h, text, align="L"):
    """multi_cell that always resets x to left margin."""
    pdf.multi_cell(w, h, text, align=align, new_x="LMARGIN", new_y="NEXT")


def _write_highlighted(pdf, size: float, text: str, pattern: re.Pattern | None) -> None:
    """Render text inline with orange keywords via pdf.write().

    After this call, pdf.get_y() is at the TOP of the last written line.
    Caller must call pdf.ln(line_height) to advance past it.
    """
    if not text:
        return
    lh = size * 0.65  # line height in mm (slightly more room for CJK)

    pdf.set_font("CJK", size=size)
    if pattern is None:
        pdf.set_text_color(0, 0, 0)
        pdf.write(lh, text)
        return

    parts = pattern.split(text)
    for part in parts:
        if not part:
            continue
        if pattern.fullmatch(part):
            pdf.set_text_color(210, 90, 0)
        else:
            pdf.set_text_color(0, 0, 0)
        pdf.write(lh, part)
    pdf.set_text_color(0, 0, 0)


def _build_fpdf_pdf(
    articles: list[NewsArticle],
    report: CycleReport,
    pdf_path: str,
    font_path: str,
    FPDF,
    topic_name: str,
    categories: list[tuple[str, str]],
    highlight_keywords: list[str] | None,
) -> str:
    default_key = categories[-1][0]

    kw_set = set(_DEFAULT_HIGHLIGHT)
    if highlight_keywords:
        kw_set.update(highlight_keywords)
    hl_pattern = _build_highlight_pattern(list(kw_set))

    pdf = FPDF()
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(auto=True, margin=15)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        try:
            pdf.add_font("CJK", "", font_path, uni=True)
        except TypeError:
            pdf.add_font("CJK", "", font_path)

    def H(size, text, align="L"):
        pdf.set_font("CJK", size=size)
        _mc(pdf, 0, size * 0.65, text, align=align)
        pdf.ln(2)

    def B(size, text, align="L"):
        pdf.set_font("CJK", size=size)
        _mc(pdf, 0, size * 0.65, text, align=align)

    def rule():
        pdf.set_draw_color(180, 180, 180)
        y = pdf.get_y()
        pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
        pdf.ln(2)

    # ── Cover page ────────────────────────────────────────────────────
    pdf.add_page()
    H(20, f"{topic_name}报告", align="C")
    pdf.ln(3)

    gen_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    B(11, f"生成时间：{gen_time}", align="C")
    pdf.ln(8)

    H(13, "周期摘要")
    for label, value in [
        ("抓取文章数：", str(report.total_fetched)),
        ("去重后数量：", str(report.total_after_dedup)),
        ("已翻译数量：", str(report.total_translated)),
        ("推送数量：",   str(report.total_pushed)),
    ]:
        B(10, f"{label}{value}")

    groups = _group_by_category(articles, categories, default_key)
    pdf.ln(4)
    H(13, "分类统计")
    for cat_key, cat_label in categories:
        n = len(groups[cat_key])
        if n:
            B(10, f"{cat_label}：{n} 篇")

    if report.errors:
        pdf.ln(3)
        H(11, f"错误（{len(report.errors)} 条）：")
        for err in report.errors[:3]:
            B(9, _trunc(err, 90))

    # ── Category sections ─────────────────────────────────────────────
    # Line-height constants (mm).
    lh_title   = 12 * 0.65   # ≈ 7.8 mm
    lh_summary = 10 * 0.65   # ≈ 6.5 mm
    lh_meta    =  9 * 0.65   # ≈ 5.85 mm
    lh_link    =  8 * 0.65   # ≈ 5.2 mm

    def _render_single_article(idx: int, art: NewsArticle) -> None:
        """Render a single article (for single-item clusters)."""
        title = _trunc(art.title_zh or art.title, 80)
        pdf.set_font("CJK", size=12)
        pdf.write(lh_title, f"{idx}. ")
        _write_highlighted(pdf, 12, title, hl_pattern)
        pdf.ln(lh_title + 2)
        pdf.set_x(pdf.l_margin)

        summary = _trunc(
            art.summary_zh or art.description_zh or art.description or "", 240
        )
        if summary:
            _write_highlighted(pdf, 10, summary, hl_pattern)
            pdf.ln(lh_summary + 2)
            pdf.set_x(pdf.l_margin)

        pub_str = (
            art.published_at.strftime("%Y-%m-%d %H:%M")
            if art.published_at else "N/A"
        )
        date_line = f"发布时间：{pub_str}"
        if art.event_date:
            date_line += f"　　事件时间：{art.event_date}"
        engine_tag = f"  [{'+'.join(art.found_by)}]" if art.found_by else ""
        pdf.set_font("CJK", size=9)
        pdf.set_text_color(80, 80, 80)
        _mc(pdf, 0, lh_meta, f"来源：{art.source_name}{engine_tag}　　{date_line}")
        pdf.set_text_color(0, 0, 0)

        if art.source_url:
            pdf.set_font("CJK", size=9)
            pdf.set_text_color(30, 100, 200)
            _mc(pdf, 0, lh_meta, _trunc(art.source_url, 90))
            pdf.set_text_color(0, 0, 0)
        pdf.ln(3)
        rule()

    def _render_cluster_pdf(idx: int, cluster: list[NewsArticle], is_tweet: bool = False) -> None:
        """Render a topic cluster (theme + summary + link list)."""
        if len(cluster) == 1 and not is_tweet:
            _render_single_article(idx, cluster[0])
            return

        theme = _cluster_theme_title(cluster)
        prefix = "T" if is_tweet else ""
        count_label = f"（{len(cluster)} 条推文）" if is_tweet else f"（{len(cluster)} 篇）"
        theme_text = f"{idx}. {prefix}{_trunc(theme, 70)}{count_label}"

        pdf.set_font("CJK", size=12)
        _write_highlighted(pdf, 12, theme_text, hl_pattern)
        pdf.ln(lh_title + 2)
        pdf.set_x(pdf.l_margin)

        if is_tweet:
            summary = _trunc(_tweet_cluster_summary(cluster), 500)
        else:
            summary = _trunc(_cluster_summary(cluster), 400)
        if summary:
            _write_highlighted(pdf, 10, summary, hl_pattern)
            pdf.ln(lh_summary + 2)
            pdf.set_x(pdf.l_margin)

        # Link list
        for art in cluster:
            if is_tweet:
                author, _ = _parse_tweet_author(art.title or "")
                art_title = f"@{author}" if author else _trunc(art.title_zh or art.title or "", 50)
            else:
                art_title = _trunc(art.title_zh or art.title or "", 50)
            src = art.source_name or "N/A"
            link_line = f"  [{src}] {art_title}"
            pdf.set_font("CJK", size=8)
            pdf.set_text_color(80, 80, 80)
            _mc(pdf, 0, lh_link, link_line)
            if art.source_url:
                pdf.set_text_color(30, 100, 200)
                _mc(pdf, 0, lh_link, f"    {_trunc(art.source_url, 85)}")
            pdf.set_text_color(0, 0, 0)

        pdf.ln(3)
        rule()

    for cat_key, cat_label in categories:
        arts = groups[cat_key]
        if not arts:
            continue

        news_arts, tweet_arts = _split_news_tweets(arts)
        clusters = _cluster_articles(news_arts)
        tweet_clusters = _cluster_articles(tweet_arts, threshold=0.35)

        pdf.add_page()
        cluster_desc = f"，{len(clusters)} 个主题" if len(clusters) < len(news_arts) else ""
        tweet_desc = f"，{len(tweet_arts)} 条推文" if tweet_arts else ""
        H(16, f"■ {cat_label}  （{len(arts)} 篇{cluster_desc}{tweet_desc}）")
        rule()
        pdf.ln(2)

        idx = 1
        for cluster in clusters:
            _render_cluster_pdf(idx, cluster)
            idx += 1

        for cluster in tweet_clusters:
            _render_cluster_pdf(idx, cluster, is_tweet=True)
            idx += 1

    pdf.output(pdf_path)
    logger.info("PDF(fpdf2) written: %s  (%d articles)", pdf_path, len(articles))
    return pdf_path


# ── TXT fallback ────────────────────────────────────────────────────────────

def _txt_report(
    articles, report, output_dir,
    topic_name="哥伦比亚地区新闻监测",
    country_key="colombia",
    country_label="哥伦比亚相关",
    categories=None,
) -> str:
    if categories is None:
        categories = list(_BASE_CATEGORIES)
    default_key = categories[-1][0]

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    txt_path = str(Path(output_dir) / f"{ts}_{country_key}.txt")

    lines = [
        f"{topic_name}报告",
        "=" * 60,
        f"生成时间: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"抓取: {report.total_fetched}  去重后: {report.total_after_dedup}"
        f"  翻译: {report.total_translated}  推送: {report.total_pushed}",
        "",
    ]

    groups = _group_by_category(articles, categories, default_key)
    for cat_key, cat_label in categories:
        arts = groups[cat_key]
        if not arts:
            continue
        lines += ["", "=" * 60, f"■ {cat_label}  （{len(arts)} 篇）", ""]
        for idx, art in enumerate(arts, 1):
            title   = art.title_zh or art.title
            summary = art.summary_zh or art.description_zh or art.description
            pub     = art.published_at.strftime("%Y-%m-%d") if art.published_at else "N/A"
            event   = f"  事件时间: {art.event_date}" if art.event_date else ""
            lines += [
                f"{idx}. {_trunc(title, 80)}",
                f"   {_trunc(summary, 200)}" if summary else "",
                f"   来源: {art.source_name}  发布: {pub}{event}",
                f"   {art.source_url}",
                "",
            ]

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    logger.info("TXT written: %s", txt_path)
    return txt_path


# ── Public API ──────────────────────────────────────────────────────────────

def generate_report(
    articles: list[NewsArticle],
    report: CycleReport,
    output_dir: str = "output/reports",
    topic_name: str = "哥伦比亚地区新闻监测",
    country_key: str = "colombia",
    country_label: str = "哥伦比亚相关",
    highlight_keywords: list[str] | None = None,
) -> tuple[str, str]:
    """Generate MD and PDF reports.

    Returns (md_path, pdf_path).  pdf_path may be "" if all PDF methods fail.
    PDF generation order: pandoc → weasyprint → fpdf2 → txt fallback.
    """
    categories = list(_BASE_CATEGORIES)
    # Filter out articles with country-domestic category (not in any foreign-policy line)
    valid_cats = {cat for cat, _ in categories}
    articles = [a for a in articles if a.category in valid_cats]
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # 1. Always generate Markdown
    md_path = generate_md_report(
        articles, report, output_dir, topic_name, country_key, country_label,
        categories, highlight_keywords, ts=ts,
    )

    # 2. Try PDF conversion
    pdf_path = str(Path(output_dir) / f"{ts}_{country_key}.pdf")

    if _md_to_pdf_pandoc(md_path, pdf_path):
        return md_path, pdf_path

    if _md_to_pdf_weasyprint(md_path, pdf_path):
        return md_path, pdf_path

    # 3. fpdf2 fallback
    try:
        from fpdf import FPDF  # type: ignore
        font_path = _find_font()
        if font_path:
            _build_fpdf_pdf(
                articles, report, pdf_path, font_path, FPDF,
                topic_name, categories, highlight_keywords,
            )
            return md_path, pdf_path
        logger.warning("No CJK font found, skipping fpdf2 PDF")
    except ImportError:
        logger.warning("fpdf2 not installed")
    except Exception as exc:
        logger.error("fpdf2 PDF build failed: %s", exc)

    # 4. TXT fallback (no separate MD needed, already done)
    txt_path = _txt_report(
        articles, report, output_dir, topic_name, country_key, country_label, categories
    )
    return md_path, txt_path
