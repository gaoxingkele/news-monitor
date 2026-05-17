"""Retry failed downloads using Playwright headless browser.

Reads _index.csv, finds failed entries, fetches via real Chromium browser
to bypass 403/anti-bot protections.

Usage:
    python download_retry_browser.py output/kateer
"""
from __future__ import annotations

import csv
import hashlib
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from playwright.sync_api import sync_playwright


def _extract_text(html: str) -> str:
    text = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '\n', text)
    text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    text = text.replace('&quot;', '"').replace('&#39;', "'").replace('&nbsp;', ' ')
    lines = [line.strip() for line in text.splitlines()]
    lines = [l for l in lines if len(l) > 20]
    return '\n'.join(lines)


def _safe_filename(url: str, title: str) -> str:
    h = hashlib.md5(url.encode()).hexdigest()[:8]
    clean = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', title)[:60].strip().replace(' ', '_')
    if not clean:
        host = urlparse(url).hostname or 'unknown'
        clean = host.replace('.', '_')
    return f"{h}_{clean}"


def main():
    if len(sys.argv) < 2:
        print("Usage: python download_retry_browser.py output/kateer")
        sys.exit(1)

    output_dir = Path(sys.argv[1])
    index_path = output_dir / '_index.csv'

    # Read failed entries
    failed = []
    with open(index_path, 'r', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            if row.get('status', '').startswith('failed'):
                failed.append(row)

    print(f"Found {len(failed)} failed articles to retry with browser")

    if not failed:
        return

    success = 0
    still_failed = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            viewport={'width': 1280, 'height': 800},
            locale='en-US',
        )
        # Block images/fonts/media to speed up
        context.route("**/*.{png,jpg,jpeg,gif,svg,webp,woff,woff2,ttf,mp4,mp3}", lambda route: route.abort())

        page = context.new_page()

        for i, row in enumerate(failed):
            url = row.get('url', '')
            title = row.get('title', '')
            title_zh = row.get('title_zh', '')
            fname = _safe_filename(url, title_zh or title)

            print(f"  [{i+1}/{len(failed)}] {urlparse(url).hostname}: {(title_zh or title)[:50]}...", end=' ', flush=True)

            try:
                page.goto(url, timeout=20000, wait_until='domcontentloaded')
                # Wait a bit for JS rendering
                page.wait_for_timeout(2000)

                html = page.content()
                text = _extract_text(html)

                if len(text) < 100:
                    # Try waiting longer for JS-heavy sites
                    page.wait_for_timeout(3000)
                    html = page.content()
                    text = _extract_text(html)

                # Save HTML
                html_path = output_dir / 'html' / f'{fname}.html'
                with open(html_path, 'w', encoding='utf-8', errors='replace') as f:
                    f.write(html)

                # Update txt file
                txt_path = output_dir / f'{fname}.txt'
                with open(txt_path, 'w', encoding='utf-8') as f:
                    f.write(f"URL: {url}\n")
                    f.write(f"Title: {title}\n")
                    f.write(f"Title (zh): {title_zh}\n")
                    f.write(f"Source: {row.get('source', '')}\n")
                    f.write(f"Category: {row.get('category', '')}\n")
                    f.write(f"Published: {row.get('published_at', '')}\n")
                    f.write(f"Fetched: browser (Playwright)\n")
                    f.write(f"\n{'='*60}\n\n")
                    f.write(text if text else '[No text extracted]')

                if len(text) > 100:
                    success += 1
                    print(f"OK ({len(text)} chars)")
                else:
                    still_failed += 1
                    print(f"EMPTY ({len(text)} chars)")

            except Exception as exc:
                still_failed += 1
                print(f"FAIL ({type(exc).__name__})")

            # Rate limit
            time.sleep(1.0)

        browser.close()

    print(f"\nBrowser retry done: {success} recovered / {still_failed} still failed / {len(failed)} total")

    # Update index
    updated_rows = []
    with open(index_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            if row.get('status', '').startswith('failed'):
                url = row.get('url', '')
                title = row.get('title', '')
                title_zh = row.get('title_zh', '')
                fname = _safe_filename(url, title_zh or title)
                txt_path = output_dir / f'{fname}.txt'
                if txt_path.exists():
                    content = txt_path.read_text(encoding='utf-8', errors='replace')
                    if 'Fetched: browser' in content and len(content) > 500:
                        row['status'] = 'ok (browser)'
            updated_rows.append(row)

    with open(index_path, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        w.writeheader()
        w.writerows(updated_rows)

    print(f"Index updated: {index_path}")


if __name__ == '__main__':
    main()
