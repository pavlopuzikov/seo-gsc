"""Shared helpers for normalizing raw source rows into the canonical schema."""

from __future__ import annotations

# Maps common header variants (lower-cased, stripped) to canonical columns.
HEADER_ALIASES: dict[str, str] = {
    "top queries": "query",
    "query": "query",
    "queries": "query",
    "search query": "query",
    "top pages": "page",
    "page": "page",
    "pages": "page",
    "landing page": "page",
    "address": "page",
    "url": "page",
    "clicks": "clicks",
    "url clicks": "clicks",
    "impressions": "impressions",
    "ctr": "ctr",
    "click through rate": "ctr",
    "average ctr": "ctr",
    "position": "position",
    "average position": "position",
    "avg. pos": "position",
    "date": "date",
    "country": "country",
    "device": "device",
}


def canonical_header(name: str) -> str | None:
    """Return the canonical column for a raw CSV header, or None if unknown."""
    return HEADER_ALIASES.get(str(name).strip().lower())


def parse_ctr(value) -> float:
    """Parse a CTR cell into a 0..1 fraction.

    Handles GSC UI exports ("5.32%"), fraction strings ("0.0532"), and numbers.
    Any value greater than 1 is assumed to be a percentage and divided by 100.
    """
    if value is None:
        return 0.0
    if isinstance(value, str):
        s = value.strip().replace(",", "")
        if not s:
            return 0.0
        had_percent = s.endswith("%")
        s = s.rstrip("%").strip()
        try:
            num = float(s)
        except ValueError:
            return 0.0
        if had_percent:
            return num / 100.0
        return num / 100.0 if num > 1.0 else num
    try:
        num = float(value)
    except (TypeError, ValueError):
        return 0.0
    return num / 100.0 if num > 1.0 else num


def parse_number(value) -> float:
    """Parse a numeric cell, tolerating thousands separators and blanks."""
    if value is None:
        return 0.0
    if isinstance(value, str):
        s = value.strip().replace(",", "")
        if not s:
            return 0.0
        try:
            return float(s)
        except ValueError:
            return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
