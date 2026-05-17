"""学术文献综合检索 — 5 源免费 API 并发。

Sources:
- OpenAlex        (https://api.openalex.org/works)       — 2 亿+ works，含 CJK 元数据
- Semantic Scholar (https://api.semanticscholar.org)      — CS/教育/社科覆盖好
- CrossRef        (https://api.crossref.org/works)        — 全 DOI 期刊
- CNKI 公开搜索页 (search.cnki.com.cn)                   — 中文文献必备
- Google Scholar  (scholar.google.com)                    — 代理抓 HTML

Usage:
    results = await academic_search("柬埔寨 中文教育 华裔", max_per_source=5)
    # returns {"openalex": [...], "semantic_scholar": [...], "crossref": [...], "cnki": [...], "scholar": [...]}
"""
from __future__ import annotations
import asyncio, re, sys, os
from dataclasses import dataclass, asdict
from typing import Sequence
from urllib.parse import quote

import httpx


@dataclass
class Paper:
    source: str
    title: str
    authors: str
    year: str
    venue: str
    url: str
    abstract: str = ""
    cited_by: int = 0


UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"


async def search_openalex(client: httpx.AsyncClient, q: str, limit: int = 10) -> list[Paper]:
    """OpenAlex free API — no key needed. ~8B indexed docs."""
    try:
        r = await client.get(
            "https://api.openalex.org/works",
            params={"search": q, "per-page": limit, "select": "id,title,authorships,publication_year,primary_location,abstract_inverted_index,cited_by_count,doi"},
            timeout=30.0,
            headers={"User-Agent": UA},
        )
        r.raise_for_status()
        out = []
        for w in (r.json().get("results") or [])[:limit]:
            authors = ", ".join(
                (a.get("author") or {}).get("display_name", "")
                for a in (w.get("authorships") or [])[:5]
            )
            venue = ((w.get("primary_location") or {}).get("source") or {}).get("display_name", "") or ""
            # Rehydrate abstract from inverted index
            abs_idx = w.get("abstract_inverted_index") or {}
            abstract = ""
            if abs_idx:
                try:
                    pairs = [(pos, word) for word, poss in abs_idx.items() for pos in poss]
                    pairs.sort()
                    abstract = " ".join(w for _, w in pairs)[:600]
                except Exception: pass
            out.append(Paper(
                source="openalex", title=(w.get("title") or "")[:200],
                authors=authors[:200], year=str(w.get("publication_year") or ""),
                venue=venue[:120], url=w.get("doi") or w.get("id") or "",
                abstract=abstract, cited_by=int(w.get("cited_by_count") or 0),
            ))
        return out
    except Exception as e:
        return [Paper(source="openalex", title=f"ERR {str(e)[:80]}", authors="", year="", venue="", url="")]


async def search_semantic_scholar(client: httpx.AsyncClient, q: str, limit: int = 10) -> list[Paper]:
    """Semantic Scholar free API (rate-limited, ~100/5min)."""
    try:
        r = await client.get(
            "https://api.semanticscholar.org/graph/v1/paper/search",
            params={"query": q, "limit": limit,
                    "fields": "title,authors,year,venue,url,abstract,citationCount"},
            timeout=30.0,
            headers={"User-Agent": UA},
        )
        if r.status_code == 429:
            return [Paper(source="semantic_scholar", title="rate-limited", authors="", year="", venue="", url="")]
        r.raise_for_status()
        out = []
        for p in (r.json().get("data") or [])[:limit]:
            out.append(Paper(
                source="semantic_scholar",
                title=(p.get("title") or "")[:200],
                authors=", ".join(a.get("name","") for a in (p.get("authors") or [])[:5])[:200],
                year=str(p.get("year") or ""),
                venue=(p.get("venue") or "")[:120],
                url=p.get("url") or "",
                abstract=(p.get("abstract") or "")[:600],
                cited_by=int(p.get("citationCount") or 0),
            ))
        return out
    except Exception as e:
        return [Paper(source="semantic_scholar", title=f"ERR {str(e)[:80]}", authors="", year="", venue="", url="")]


async def search_crossref(client: httpx.AsyncClient, q: str, limit: int = 10) -> list[Paper]:
    """CrossRef free, no key."""
    try:
        r = await client.get(
            "https://api.crossref.org/works",
            params={"query": q, "rows": limit,
                    "select": "title,author,issued,container-title,URL,DOI,abstract,is-referenced-by-count"},
            timeout=30.0,
            headers={"User-Agent": UA, "Mailto": "research@example.org"},
        )
        r.raise_for_status()
        out = []
        for w in (r.json().get("message", {}).get("items") or [])[:limit]:
            title = (w.get("title") or [""])[0]
            authors = ", ".join(
                f"{a.get('given','')} {a.get('family','')}".strip()
                for a in (w.get("author") or [])[:5]
            )
            year = ""
            issued = w.get("issued", {}).get("date-parts") or []
            if issued and issued[0]: year = str(issued[0][0])
            venue = (w.get("container-title") or [""])[0]
            out.append(Paper(
                source="crossref", title=title[:200], authors=authors[:200],
                year=year, venue=venue[:120],
                url=w.get("URL") or (f"https://doi.org/{w.get('DOI')}" if w.get("DOI") else ""),
                abstract=re.sub(r"<[^>]+>", "", w.get("abstract") or "")[:600],
                cited_by=int(w.get("is-referenced-by-count") or 0),
            ))
        return out
    except Exception as e:
        return [Paper(source="crossref", title=f"ERR {str(e)[:80]}", authors="", year="", venue="", url="")]


async def search_cnki(client: httpx.AsyncClient, q: str, limit: int = 10) -> list[Paper]:
    """CNKI 公开搜索页抓取 (zh)."""
    url = f"https://search.cnki.com.cn/Search.aspx?q={quote(q)}&rank=relevant&cluster=all&val=&p=0"
    try:
        r = await client.get(url, timeout=30.0, headers={"User-Agent": UA,
                             "Referer": "https://search.cnki.com.cn/"})
        html = r.text
        # Parse search result items. CNKI HTML has div.lplist or div.wz_list
        papers = []
        # Try multiple patterns
        # Pattern 1: new layout
        items = re.findall(
            r'<a[^>]*href="(https?://kns\.cnki\.net/[^"]+)"[^>]*>([^<]+)</a>'
            r'(?:.*?<p[^>]*>([^<]+)</p>){0,3}',
            html, re.S
        )[:limit*2]
        for u, title, meta in items:
            title = re.sub(r"<[^>]+>", "", title).strip()
            if not title or len(title) < 5: continue
            papers.append(Paper(
                source="cnki", title=title[:200], authors="", year="", venue="",
                url=u, abstract=meta[:400] if meta else "",
            ))
            if len(papers) >= limit: break
        # Fallback: just report count
        if not papers:
            m = re.search(r'共找到[^\d]*?(\d+)\s*条', html)
            count = m.group(1) if m else "?"
            papers.append(Paper(source="cnki", title=f"[CNKI hit count: {count}]",
                               authors="", year="", venue="", url=url,
                               abstract="HTML 解析未命中条目，仅返回命中数"))
        return papers
    except Exception as e:
        return [Paper(source="cnki", title=f"ERR {str(e)[:80]}", authors="", year="", venue="", url="")]


async def search_google_scholar(client: httpx.AsyncClient, q: str, limit: int = 10,
                                  proxy_client: httpx.AsyncClient | None = None) -> list[Paper]:
    """Google Scholar 直抓 HTML (需要翻墙)."""
    c = proxy_client or client
    url = f"https://scholar.google.com/scholar?q={quote(q)}&hl=zh-CN"
    try:
        r = await c.get(url, timeout=30.0,
                         headers={"User-Agent": UA,
                                  "Accept": "text/html,application/xhtml+xml",
                                  "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"})
        html = r.text
        if "unusual traffic" in html.lower() or "captcha" in html.lower():
            return [Paper(source="scholar", title="[Scholar blocked (captcha)]",
                         authors="", year="", venue="", url=url)]
        # Parse .gs_r.gs_or.gs_scl blocks
        blocks = re.findall(
            r'<div class="gs_r gs_or gs_scl".*?<h3 class="gs_rt"[^>]*>(.*?)</h3>'
            r'.*?<div class="gs_a">(.*?)</div>'
            r'(?:.*?<div class="gs_rs">(.*?)</div>)?',
            html, re.S
        )[:limit]
        papers = []
        for title_html, author_line, abstract_html in blocks:
            # Strip tags
            t = re.sub(r"<[^>]+>", "", title_html).strip()
            # Extract URL from title
            m = re.search(r'href="([^"]+)"', title_html)
            u = m.group(1) if m else ""
            if u.startswith("/scholar"):
                u = "https://scholar.google.com" + u
            author_line_clean = re.sub(r"<[^>]+>", "", author_line).strip()
            # Year is in author_line like " - Xxx, 2022 - publisher"
            ym = re.search(r'\b(19|20)\d{2}\b', author_line_clean)
            year = ym.group(0) if ym else ""
            abstract = re.sub(r"<[^>]+>", "", abstract_html or "").strip()[:500]
            papers.append(Paper(
                source="scholar", title=t[:200],
                authors=author_line_clean[:200], year=year,
                venue="", url=u, abstract=abstract,
            ))
        return papers
    except Exception as e:
        return [Paper(source="scholar", title=f"ERR {str(e)[:80]}", authors="", year="", venue="", url="")]


async def academic_search(q: str, max_per_source: int = 5,
                           proxy_url: str = "", include_scholar: bool = True) -> dict[str, list[Paper]]:
    """5-source parallel search. proxy_url used for Scholar only."""
    # Direct clients for OA/SS/CrossRef/CNKI
    direct = httpx.AsyncClient(timeout=30.0, follow_redirects=True, trust_env=False)
    # Scholar goes through overseas proxy
    scholar_kwargs: dict = {"timeout": 30.0, "follow_redirects": True, "trust_env": False}
    if proxy_url: scholar_kwargs["proxy"] = proxy_url
    scholar_c = httpx.AsyncClient(**scholar_kwargs)

    try:
        tasks = [
            search_openalex(direct, q, max_per_source),
            search_semantic_scholar(direct, q, max_per_source),
            search_crossref(direct, q, max_per_source),
            search_cnki(direct, q, max_per_source),
        ]
        if include_scholar:
            tasks.append(search_google_scholar(scholar_c, q, max_per_source))
        results = await asyncio.gather(*tasks, return_exceptions=True)
        keys = ["openalex", "semantic_scholar", "crossref", "cnki"] + (["scholar"] if include_scholar else [])
        out = {}
        for k, r in zip(keys, results):
            out[k] = r if isinstance(r, list) else [
                Paper(source=k, title=f"ERR {str(r)[:80]}", authors="", year="", venue="", url="")
            ]
        return out
    finally:
        await direct.aclose()
        await scholar_c.aclose()


def format_results(bundles: dict[str, list[Paper]]) -> str:
    """Format for LLM consumption."""
    lines = []
    for src, papers in bundles.items():
        lines.append(f"\n### {src.upper()} ({len(papers)} 条)")
        for p in papers[:8]:
            if p.title.startswith("ERR") or p.title.startswith("[") or p.title == "rate-limited":
                lines.append(f"  ⚠ {p.title}")
                continue
            lines.append(f"  - {p.title} ({p.year})")
            if p.authors: lines.append(f"    作者: {p.authors}")
            if p.venue: lines.append(f"    出处: {p.venue}")
            if p.cited_by: lines.append(f"    被引: {p.cited_by}")
            if p.abstract: lines.append(f"    摘要: {p.abstract[:200]}")
            if p.url: lines.append(f"    URL: {p.url}")
    return "\n".join(lines)


# ── self test ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import io, json
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError: pass
    proxy = os.environ.get("LLM_PROXY", "")

    async def _test():
        q = "柬埔寨 华文教育 学生 民族结构"
        print(f"Testing: {q}")
        results = await academic_search(q, max_per_source=3, proxy_url=proxy)
        print(format_results(results))
        print("\n\n=== Stats ===")
        for src, papers in results.items():
            real = [p for p in papers if not p.title.startswith(("ERR", "[", "rate"))]
            print(f"  {src}: {len(real)} real hits")

    asyncio.run(_test())
