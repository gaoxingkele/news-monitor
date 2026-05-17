"""Extract all unique domains from files under output/."""

import os
import re
import json
from pathlib import Path
from urllib.parse import urlparse

OUTPUT_DIR = Path(__file__).parent / "output"
RESULT_FILE = OUTPUT_DIR / "all_domains_deduped.txt"

# Regex for URLs
URL_RE = re.compile(r'https?://[^\s\)\]\}>"\'`,;]+', re.IGNORECASE)

# Regex for @username patterns (Twitter/X handles)
HANDLE_RE = re.compile(r'(?<!\w)@([A-Za-z0-9_]{1,15})(?!\w)')

# Extensions we can read as text
TEXT_EXTS = {'.md', '.txt', '.json', '.csv', '.tsv', '.html', '.htm', '.xml', '.yaml', '.yml', '.log'}


def clean_url(url: str) -> str:
    """Strip trailing punctuation that's likely not part of the URL."""
    # Remove trailing chars that are often markdown/text artifacts
    url = url.rstrip('.,;:!?)]}>\'"')
    # Remove trailing parentheses only if unbalanced
    while url.endswith(')') and url.count('(') < url.count(')'):
        url = url[:-1]
    return url


def extract_domain_or_handle(url: str) -> str | None:
    """Extract domain from URL. For x.com/twitter.com, preserve username path."""
    url = clean_url(url)
    try:
        parsed = urlparse(url)
        host = parsed.hostname
        if not host:
            return None

        # Strip www. prefix
        if host.startswith('www.'):
            host = host[4:]

        # For Twitter/X URLs, keep the username
        if host in ('x.com', 'twitter.com'):
            path_parts = [p for p in parsed.path.split('/') if p]
            if path_parts:
                username = path_parts[0]
                # Skip non-user paths
                if username not in ('search', 'hashtag', 'i', 'intent', 'share', 'home', 'explore', 'notifications', 'messages', 'settings'):
                    return f"{host}/{username}"
            return host

        return host
    except Exception:
        return None


def read_file_text(filepath: Path) -> str:
    """Read file content as text, trying multiple encodings."""
    for enc in ('utf-8', 'utf-8-sig', 'latin-1', 'gbk'):
        try:
            return filepath.read_text(encoding=enc)
        except (UnicodeDecodeError, UnicodeError):
            continue
    return ''


def main():
    domains = set()
    files_scanned = 0
    urls_found = 0

    for root, dirs, files in os.walk(OUTPUT_DIR):
        for fname in files:
            fpath = Path(root) / fname
            ext = fpath.suffix.lower()

            # Skip our own output file and binary files (PDF, images)
            if fpath == RESULT_FILE:
                continue
            if ext in ('.pdf', '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.zip', '.gz'):
                continue

            # Try to read as text
            if ext in TEXT_EXTS or ext == '':
                content = read_file_text(fpath)
            else:
                # Try anyway for unknown extensions
                content = read_file_text(fpath)

            if not content:
                continue

            files_scanned += 1

            # Extract URLs
            for match in URL_RE.finditer(content):
                raw_url = match.group(0)
                urls_found += 1
                domain = extract_domain_or_handle(raw_url)
                if domain:
                    domains.add(domain)

    # Sort alphabetically
    sorted_domains = sorted(domains, key=str.lower)

    # Write output
    RESULT_FILE.write_text('\n'.join(sorted_domains) + '\n', encoding='utf-8')

    print(f"Files scanned: {files_scanned}")
    print(f"URLs found: {urls_found}")
    print(f"Unique domains/handles: {len(sorted_domains)}")
    print(f"Written to: {RESULT_FILE}")


if __name__ == '__main__':
    main()
