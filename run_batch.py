"""Batch runner: run fetch_topic.py for multiple countries sequentially.

Supports resume: skips countries that already have a report generated today.

Usage:
    python run_batch.py           # auto-skip completed countries
    python run_batch.py --force   # re-run all countries
"""
from __future__ import annotations

import glob
import os
import subprocess
import sys
import time
from datetime import date, timedelta

# country_name -> country_code (for report file matching)
COUNTRIES = {
    "巴拉圭": "py",
    "智利": "cl",
    "秘鲁": "pe",
    "巴西": "br",
    "阿根廷": "ar",
}


def _has_recent_report(country_code: str, report_dir: str = "output/reports", days: int = 2) -> str | None:
    """Check if a report for this country was generated in the last N days. Returns path if found."""
    for d in range(days):
        prefix = (date.today() - timedelta(days=d)).strftime("%Y%m%d")
        pattern = os.path.join(report_dir, f"{prefix}_*_{country_code}.md")
        matches = sorted(glob.glob(pattern))
        if matches:
            return matches[-1]
    return None


def main():
    force = "--force" in sys.argv
    env = {
        **os.environ,
        "PYTHONUNBUFFERED": "1",
        "PYTHONIOENCODING": "utf-8",
        "FETCH_FROM": os.environ.get("FETCH_FROM", "2026-03-05"),
        "FETCH_TO": os.environ.get("FETCH_TO", "2026-03-12"),
    }
    results = []

    for country, code in COUNTRIES.items():
        # Check for existing report (skip if found, unless --force)
        if not force:
            existing = _has_recent_report(code)
            if existing:
                size_kb = os.path.getsize(existing) / 1024
                print(f"\n{'=' * 80}", flush=True)
                print(f"  >>  {country} ({code}) — SKIP (report exists: {os.path.basename(existing)}, {size_kb:.0f}KB)", flush=True)
                print(f"{'=' * 80}", flush=True)
                results.append((country, "SKIP", f"{size_kb:.0f}KB"))
                continue

        print(f"\n{'=' * 80}", flush=True)
        print(f"  >>  {country} ({code})", flush=True)
        print(f"{'=' * 80}", flush=True)
        t0 = time.time()
        proc = subprocess.run(
            [sys.executable, "-u", "fetch_topic.py", country],
            env=env,
        )
        elapsed = time.time() - t0
        status = "OK" if proc.returncode == 0 else "FAIL"
        results.append((country, status, f"{elapsed:.0f}s"))
        print(f"\n>> {status} {country} - {elapsed:.0f}s", flush=True)

    print(f"\n{'=' * 80}", flush=True)
    print("  BATCH SUMMARY", flush=True)
    print(f"{'=' * 80}", flush=True)
    for country, status, detail in results:
        sym = {"OK": "OK", "SKIP": "->", "FAIL": "!!"}[status]
        print(f"  [{sym}] {country:12s}  {status:5s}  {detail}")


if __name__ == "__main__":
    main()
