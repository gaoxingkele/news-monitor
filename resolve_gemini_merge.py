"""Resolve Gemini redirect URLs from existing reports, merge with Grok, compare to Brave."""
from __future__ import annotations

import asyncio
import os
import re
import sys
from urllib.parse import urlparse

if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.join(os.path.dirname(__file__) or ".", "src"))
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from news_monitor.proxy import build_httpx_client, get_proxies_for_url

PROXY = "http://127.0.0.1:18182"
REDIRECT_PREFIX = "vertexaisearch.cloud.google.com"


def _norm(url: str) -> str:
    try:
        p = urlparse(url)
        host = p.hostname or ""
        if host.startswith("www."):
            host = host[4:]
        path = p.path.rstrip("/")
        return f"{host}{path}".lower()
    except Exception:
        return url.lower().strip("/")


async def resolve_url(url: str, client) -> str:
    try:
        resp = await client.get(url, follow_redirects=False)
        loc = resp.headers.get("location", "")
        if loc:
            return loc
    except Exception as e:
        print(f"  FAIL: {e}")
    return url


async def resolve_all(urls: list[str]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    # vertexaisearch.cloud.google.com needs proxy (Google domain, not in _OVERSEAS_DOMAINS)
    proxy = PROXY
    async with build_httpx_client(proxy_url=proxy or "", timeout=15.0) as client:
        for i in range(0, len(urls), 5):
            batch = urls[i:i + 5]
            results = await asyncio.gather(*[resolve_url(u, client) for u in batch])
            for old, new in zip(batch, results):
                mapping[old] = new
                tag = "OK" if new != old else "UNCHANGED"
                host = urlparse(new).hostname or ""
                print(f"  [{tag}] {host}")
            await asyncio.sleep(0.3)
    return mapping


def extract_redirect_urls(report_path: str) -> list[str]:
    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()
    pattern = r"https://vertexaisearch\.cloud\.google\.com/grounding-api-redirect/[^\s\)>]+"
    return list(set(re.findall(pattern, content)))


def apply_resolved(content: str, mapping: dict[str, str]) -> str:
    for old, new in mapping.items():
        if old != new:
            content = content.replace(old, new)
    content = content.replace(" [重定向]", "")
    content = re.sub(r"\(vertexaisearch\.cloud\.google\.com\)", "", content)
    return content


def parse_urls_by_source(lines: list[str]) -> dict[str, set[str]]:
    """Parse URLs grouped by source from report lines."""
    result: dict[str, set[str]] = {
        "Brave": set(), "Gemini": set(), "Grok Web": set(), "Grok X": set(),
    }
    current = None
    for line in lines:
        if line.startswith("**Brave**"):
            current = "Brave"
        elif line.startswith("**Gemini**"):
            current = "Gemini"
        elif line.startswith("**Grok Web**"):
            current = "Grok Web"
        elif line.startswith("**Grok X**"):
            current = "Grok X"
        elif line.startswith("###") or line.startswith("## ") or line.startswith("---"):
            current = None
        elif current and line.strip().startswith("http"):
            result[current].add(_norm(line.strip()))
    return result


def build_merged_section(
    all_brave: set[str],
    all_gemini: set[str],
    all_grok_web: set[str],
    all_grok_x: set[str],
    lines: list[str],
) -> str:
    all_new = all_gemini | all_grok_web | all_grok_x
    brave_new = all_brave & all_new
    new_only = all_new - all_brave
    brave_only = all_brave - all_new
    union = brave_only | all_new

    out: list[str] = []
    out.append("")
    out.append("## Gemini+Grok 合并 vs Brave 对比")
    out.append("")
    out.append("| 指标 | 数量 |")
    out.append("|------|------|")
    out.append(f"| Brave 总去重 URL | {len(all_brave)} |")
    out.append(f"| Gemini 去重 URL (真实) | {len(all_gemini)} |")
    out.append(f"| Grok Web 去重 URL | {len(all_grok_web)} |")
    out.append(f"| Grok X 去重 URL | {len(all_grok_x)} |")
    out.append(f"| **新源合并去重** | **{len(all_new)}** |")
    out.append(f"| Brave & 新源 共同 | {len(brave_new)} |")
    out.append(f"| 仅 Brave | {len(brave_only)} |")
    out.append(f"| 仅新源 (Brave 未覆盖) | **{len(new_only)}** |")
    jaccard = len(brave_new) / len(union) if union else 0
    out.append(f"| 合并 Jaccard | {jaccard:.3f} |")
    out.append("")

    out.append("### 分源与 Brave 重叠")
    out.append("")
    out.append("| 对比 | 共同 | 仅Brave | 仅该源 | Jaccard |")
    out.append("|------|------|---------|--------|---------|")
    for name, s in [("Gemini", all_gemini), ("Grok Web", all_grok_web), ("Grok X", all_grok_x)]:
        common = all_brave & s
        only_b = all_brave - s
        only_s = s - all_brave
        u = all_brave | s
        j = len(common) / len(u) if u else 0
        out.append(f"| Brave vs {name} | {len(common)} | {len(only_b)} | {len(only_s)} | {j:.3f} |")
    out.append("")

    # Collect displayable new-only URLs
    out.append(f"### 新源独有发现（Brave 未覆盖）共 {len(new_only)} 条")
    out.append("")

    seen_norms: set[str] = set()
    tweet_count = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("http"):
            continue
        norm = _norm(stripped)
        if norm not in new_only or norm in seen_norms:
            continue
        seen_norms.add(norm)

        if "x.com/i/status" in stripped:
            tweet_count += 1
            continue

        title_line = ""
        if i > 0:
            prev = lines[i - 1].strip()
            if prev.startswith("- "):
                title_line = prev[2:].split(" (")[0]

        host = urlparse(stripped).hostname or ""
        out.append(f"- {title_line[:80]} ({host})")
        out.append(f"  {stripped}")

    if tweet_count:
        out.append(f"- ...及 {tweet_count} 条 X/Twitter 帖子")
    out.append("")

    return "\n".join(out)


async def process_report(country_code: str, country_zh: str) -> None:
    report_path = f"output/reports/search_comparison_{country_code}.md"
    print(f"\n{'=' * 60}")
    print(f"Processing {country_zh} ({report_path})")
    print(f"{'=' * 60}")

    # 1. Extract & resolve redirect URLs
    redirect_urls = extract_redirect_urls(report_path)
    print(f"Found {len(redirect_urls)} Gemini redirect URLs")

    mapping: dict[str, str] = {}
    if redirect_urls:
        print("Resolving...")
        mapping = await resolve_all(redirect_urls)
        resolved_count = sum(1 for o, n in mapping.items() if o != n)
        print(f"Resolved {resolved_count}/{len(redirect_urls)}")

    # 2. Apply resolved URLs to report content
    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()
    updated = apply_resolved(content, mapping)

    # 3. Parse URLs by source
    lines = updated.split("\n")
    urls_by_source = parse_urls_by_source(lines)

    # 4. Build merged comparison section
    merged = build_merged_section(
        urls_by_source["Brave"],
        urls_by_source["Gemini"],
        urls_by_source["Grok Web"],
        urls_by_source["Grok X"],
        lines,
    )

    # 5. Insert merged section before conclusion, remove old overlap sections
    # Remove old "## URL 重叠分析" through to "## 独有发现" end
    # and replace "## 结论" with merged + conclusion
    if "## 结论" in updated:
        updated = updated.replace("## 结论", merged + "\n## 结论")

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(updated)

    b = urls_by_source["Brave"]
    g = urls_by_source["Gemini"]
    gw = urls_by_source["Grok Web"]
    gx = urls_by_source["Grok X"]
    all_new = g | gw | gx
    print(f"\nUpdated: {report_path}")
    print(f"  Brave: {len(b)} | Gemini: {len(g)} | Grok Web: {len(gw)} | Grok X: {len(gx)}")
    print(f"  新源合并: {len(all_new)} | 与Brave重叠: {len(b & all_new)} | 新源独有: {len(all_new - b)}")


async def main():
    await process_report("uy", "乌拉圭")
    await process_report("py", "巴拉圭")


if __name__ == "__main__":
    asyncio.run(main())
