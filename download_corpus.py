"""Download article corpus to local directory.

Fetches actual web page content via httpx (no LLM), saves as individual files.
Generates an index CSV for easy browsing.

Usage:
    python download_corpus.py output/reports/XXX.json kateer
    python download_corpus.py output/reports/XXX.json kateer --limit 100
"""
from __future__ import annotations

import asyncio
import csv
import hashlib
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import httpx


# ── Text extraction from HTML ─────────────────────────────────────────────────

def _extract_text(html: str) -> str:
    """Extract readable text from HTML. No external dependencies."""
    # Remove script/style
    text = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html, flags=re.DOTALL | re.IGNORECASE)
    # Remove tags
    text = re.sub(r'<[^>]+>', '\n', text)
    # Decode entities
    text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    text = text.replace('&quot;', '"').replace('&#39;', "'").replace('&nbsp;', ' ')
    # Collapse whitespace
    lines = [line.strip() for line in text.splitlines()]
    lines = [l for l in lines if len(l) > 20]  # skip short noise lines
    return '\n'.join(lines)


def _safe_filename(url: str, title: str) -> str:
    """Generate a safe filename from URL."""
    h = hashlib.md5(url.encode()).hexdigest()[:8]
    # Clean title for filename
    clean = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', title)[:60].strip()
    clean = clean.replace(' ', '_')
    if not clean:
        host = urlparse(url).hostname or 'unknown'
        clean = host.replace('.', '_')
    return f"{h}_{clean}"


# ── Download worker ───────────────────────────────────────────────────────────

_SKIP_DOMAINS = {
    'en.wikipedia.org', 'zh.wikipedia.org',  # Wikipedia has its own API
    'x.com', 'twitter.com',  # Needs auth
}

_SUCCESS = 0
_FAILED = 0
_SKIPPED = 0


async def _download_one(
    client: httpx.AsyncClient,
    article: dict,
    output_dir: Path,
    idx: int,
    total: int,
    semaphore: asyncio.Semaphore,
) -> dict | None:
    """Download one article. Returns metadata dict or None on failure."""
    global _SUCCESS, _FAILED, _SKIPPED

    url = article.get('source_url', '')
    title = article.get('title_zh') or article.get('title', '')
    if not url:
        _SKIPPED += 1
        return None

    host = urlparse(url).hostname or ''
    if host.startswith('www.'):
        host = host[4:]
    if host in _SKIP_DOMAINS:
        _SKIPPED += 1
        # Still save metadata without content
        fname = _safe_filename(url, title)
        meta = {
            'file': f'{fname}.txt',
            'url': url,
            'title': title,
            'title_zh': article.get('title_zh', ''),
            'source': article.get('source_name', ''),
            'category': article.get('category', ''),
            'published_at': article.get('published_at', ''),
            'status': 'skipped',
            'reason': f'domain {host}',
        }
        # Write metadata-only file
        with open(output_dir / f'{fname}.txt', 'w', encoding='utf-8') as f:
            f.write(f"URL: {url}\n")
            f.write(f"Title: {title}\n")
            f.write(f"Source: {article.get('source_name', '')}\n")
            f.write(f"Status: skipped (domain: {host})\n")
            f.write(f"\nDescription: {article.get('description', '')}\n")
        return meta

    async with semaphore:
        try:
            resp = await client.get(url, follow_redirects=True, timeout=15.0)
            resp.raise_for_status()
            html = resp.text
            text = _extract_text(html)

            fname = _safe_filename(url, title)

            # Save raw HTML
            html_path = output_dir / 'html' / f'{fname}.html'
            with open(html_path, 'w', encoding='utf-8', errors='replace') as f:
                f.write(html)

            # Save extracted text
            txt_path = output_dir / f'{fname}.txt'
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(f"URL: {url}\n")
                f.write(f"Title: {title}\n")
                f.write(f"Title (zh): {article.get('title_zh', '')}\n")
                f.write(f"Source: {article.get('source_name', '')}\n")
                f.write(f"Category: {article.get('category', '')}\n")
                f.write(f"Published: {article.get('published_at', '')}\n")
                f.write(f"Description: {article.get('description', '')}\n")
                f.write(f"Summary (zh): {article.get('summary_zh', '')}\n")
                f.write(f"\n{'='*60}\n\n")
                f.write(text if text else '[No text extracted]')

            _SUCCESS += 1
            if _SUCCESS % 20 == 0 or idx == total:
                print(f"  [{_SUCCESS + _FAILED + _SKIPPED}/{total}] ok={_SUCCESS} fail={_FAILED} skip={_SKIPPED}", flush=True)

            return {
                'file': f'{fname}.txt',
                'html_file': f'html/{fname}.html',
                'url': url,
                'title': title,
                'title_zh': article.get('title_zh', ''),
                'source': article.get('source_name', ''),
                'category': article.get('category', ''),
                'published_at': article.get('published_at', ''),
                'status': 'ok',
                'text_length': len(text),
            }

        except Exception as exc:
            _FAILED += 1
            fname = _safe_filename(url, title)
            # Save error record
            with open(output_dir / f'{fname}.txt', 'w', encoding='utf-8') as f:
                f.write(f"URL: {url}\n")
                f.write(f"Title: {title}\n")
                f.write(f"Source: {article.get('source_name', '')}\n")
                f.write(f"Status: FAILED ({type(exc).__name__})\n")
                f.write(f"\nDescription: {article.get('description', '')}\n")
            return {
                'file': f'{fname}.txt',
                'url': url,
                'title': title,
                'title_zh': article.get('title_zh', ''),
                'source': article.get('source_name', ''),
                'category': article.get('category', ''),
                'status': f'failed: {type(exc).__name__}',
            }


async def download_all(articles: list[dict], output_dir: Path, concurrency: int = 15):
    """Download all articles with concurrency limit."""
    global _SUCCESS, _FAILED, _SKIPPED
    _SUCCESS = _FAILED = _SKIPPED = 0

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / 'html').mkdir(exist_ok=True)

    semaphore = asyncio.Semaphore(concurrency)
    total = len(articles)
    print(f"Downloading {total} articles (concurrency={concurrency})...", flush=True)

    async with httpx.AsyncClient(
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8',
        },
        follow_redirects=True,
        timeout=20.0,
        trust_env=False,
    ) as client:
        tasks = [
            _download_one(client, art, output_dir, i + 1, total, semaphore)
            for i, art in enumerate(articles)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    # Collect metadata
    index = []
    for r in results:
        if isinstance(r, dict):
            index.append(r)
        elif isinstance(r, Exception):
            _FAILED += 1

    print(f"\nDone: {_SUCCESS} ok / {_FAILED} failed / {_SKIPPED} skipped / {total} total", flush=True)

    # Write index CSV
    csv_path = output_dir / '_index.csv'
    if index:
        keys = ['file', 'url', 'title', 'title_zh', 'source', 'category', 'published_at', 'status', 'text_length']
        with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
            w = csv.DictWriter(f, fieldnames=keys, extrasaction='ignore')
            w.writeheader()
            w.writerows(index)
        print(f"Index: {csv_path} ({len(index)} entries)")

    # Write summary JSON
    summary_path = output_dir / '_summary.json'
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump({
            'total': total,
            'success': _SUCCESS,
            'failed': _FAILED,
            'skipped': _SKIPPED,
            'downloaded_at': datetime.now().isoformat(),
        }, f, ensure_ascii=False, indent=2)

    return index


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    json_path = sys.argv[1]
    output_name = sys.argv[2]
    limit = None
    if '--limit' in sys.argv:
        idx = sys.argv.index('--limit')
        limit = int(sys.argv[idx + 1])

    output_dir = Path('output') / output_name

    with open(json_path, 'r', encoding='utf-8') as f:
        articles = json.load(f)

    print(f"Input: {json_path} ({len(articles)} articles)")
    print(f"Output: {output_dir}")

    if limit:
        articles = articles[:limit]
        print(f"Limited to {limit} articles")

    asyncio.run(download_all(articles, output_dir))


if __name__ == '__main__':
    main()
