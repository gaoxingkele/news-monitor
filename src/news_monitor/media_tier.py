"""Media influence tier system for weighting source credibility.

Tier 1: Major international media (highest weight)
Tier 2: Regional major media
Tier 3: Specialized/niche media and think tanks
Tier 4: Unknown/unranked (default)
"""
from __future__ import annotations

from urllib.parse import urlparse

# ── Tier database ────────────────────────────────────────────────────────────

_TIER_1: set[str] = {
    # Global wire services & broadsheets
    "reuters.com",
    "bbc.com", "bbc.co.uk",
    "cnn.com",
    "nytimes.com",
    "washingtonpost.com",
    "theguardian.com",
    "ft.com",
    "economist.com",
    "wsj.com",
    "bloomberg.com",
    "aljazeera.com",
    "scmp.com",
    "nikkei.com",
    "lemonde.fr",
    "dw.com",
}

_TIER_2: set[str] = {
    # Regional majors
    "taipeitimes.com",
    "straitstimes.com",
    "thehindu.com",
    "timesofindia.indiatimes.com", "timesofindia.com",
    "japantimes.co.jp",
    "koreaherald.com",
    "bangkokpost.com",
    "manilatimes.net",
    "france24.com",
    "abc.net.au",
    "cbc.ca",
    "elpais.com",
    "rt.com",
    "firstpost.com",
    "channelnewsasia.com",
    "thestar.com.my",
    "dawn.com",
    "haaretz.com",
    "arabnews.com",
    "thenationalnews.com",
}

_TIER_3: set[str] = {
    # Think tanks & specialized outlets
    "eastasiaforum.org",
    "thediplomat.com",
    "foreignpolicy.com",
    "brookings.edu",
    "carnegieendowment.org",
    "chathamhouse.org",
    "csis.org",
    "rand.org",
    "cfr.org",
    "lowyinstitute.org",
    "aspi.org.au",
    "iiss.org",
    "crisisgroup.org",
    "euobserver.com",
    "asia.nikkei.com",
}

# Pre-build a combined lookup: domain -> tier
_DOMAIN_TIER: dict[str, int] = {}
for _d in _TIER_1:
    _DOMAIN_TIER[_d] = 1
for _d in _TIER_2:
    _DOMAIN_TIER[_d] = 2
for _d in _TIER_3:
    _DOMAIN_TIER[_d] = 3

_TIER_LABELS: dict[int, str] = {
    1: "Tier 1 国际主流",
    2: "Tier 2 区域主流",
    3: "Tier 3 专业/智库",
    4: "Tier 4 其他",
}


def _extract_domain(url: str) -> str:
    """Extract registerable domain from URL."""
    try:
        host = urlparse(url).hostname or ""
        host = host.lower()
        if host.startswith("www."):
            host = host[4:]
        return host
    except Exception:
        return ""


def get_tier(source_url: str) -> int:
    """Return the media tier (1-4) for a given source URL.

    Checks the full hostname first, then progressively strips subdomains.
    Returns 4 (unknown) if no match is found.
    """
    domain = _extract_domain(source_url)
    if not domain:
        return 4

    # Check exact hostname, then parent domains
    parts = domain.split(".")
    for i in range(len(parts) - 1):
        candidate = ".".join(parts[i:])
        if candidate in _DOMAIN_TIER:
            return _DOMAIN_TIER[candidate]
    return 4


def get_tier_label(tier: int) -> str:
    """Return a human-readable label for a tier number."""
    return _TIER_LABELS.get(tier, _TIER_LABELS[4])


def get_tier_badge(source_url: str) -> str:
    """Return a short badge string like '[T1]' for use in reports."""
    tier = get_tier(source_url)
    if tier <= 3:
        return f"[T{tier}]"
    return ""
