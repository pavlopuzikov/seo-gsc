"""Shared fixtures: a small but realistic Search Console dataset.

Two topic clusters (Dubai real estate, astrology), one clear quick win, one clear
title/CTR under-performer, one content gap (impressions, no clicks, no page), and
two dated periods so the weekly report can be exercised offline.
"""

from __future__ import annotations

import pytest

from seo_gsc.models import SearchDataset

# (query, page, clicks, impressions, position, date)
_ROWS = [
    # Quick win: position 7, lots of impressions, low CTR -> big upside.
    ("luxury apartment dubai", "/listings/luxury-apartments", 30, 4000, 7.2, "2026-06-09"),
    ("buy apartment dubai marina", "/listings/marina", 12, 1500, 9.4, "2026-06-09"),
    ("apartment for sale dubai", "/listings/luxury-apartments", 8, 1200, 11.5, "2026-06-10"),
    # Title/CTR problem: ranks position 2 but earns far below expected CTR.
    ("barnes dubai reviews", "/about", 20, 5000, 2.1, "2026-06-10"),
    # Astrology cluster.
    ("birth chart reading", "/blog/birth-chart", 50, 2000, 4.0, "2026-06-09"),
    ("free birth chart", "/blog/birth-chart", 40, 2500, 5.1, "2026-06-10"),
    # Content gap: its own topic (saturn return), impressions, no clicks, no page.
    ("saturn return calculator", "", 0, 900, 18.0, "2026-06-10"),
    ("saturn return meaning", "", 0, 700, 19.2, "2026-06-11"),
    # Previous-period rows (older dates) for week-over-week.
    ("luxury apartment dubai", "/listings/luxury-apartments", 18, 3500, 8.0, "2026-06-02"),
    ("birth chart reading", "/blog/birth-chart", 60, 2100, 3.6, "2026-06-02"),
    ("barnes dubai reviews", "/about", 22, 4800, 2.0, "2026-06-03"),
]


def _rows_as_dicts():
    for q, p, clicks, impr, pos, date in _ROWS:
        yield {
            "query": q,
            "page": p,
            "clicks": clicks,
            "impressions": impr,
            "position": pos,
            "date": date,
        }


@pytest.fixture
def dataset() -> SearchDataset:
    return SearchDataset.from_rows(_rows_as_dicts(), label="fixture")


@pytest.fixture
def current_period(dataset) -> SearchDataset:
    return dataset.filter_dates(start="2026-06-08")


@pytest.fixture
def previous_period(dataset) -> SearchDataset:
    return dataset.filter_dates(end="2026-06-07")
