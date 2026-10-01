"""The shipped sample CSV stays in step with the fixture and keeps every mode working."""

from __future__ import annotations

import csv
from pathlib import Path

from seo_gsc.analysis import find_title_issues
from seo_gsc.cli import _render_titles
from seo_gsc.sources.csv_source import load_csv

from .conftest import _ROWS

SAMPLE = Path(__file__).resolve().parent.parent / "examples" / "sample-search-console.csv"


def test_sample_matches_fixture():
    with SAMPLE.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    assert [
        (r["query"], r["page"], int(r["clicks"]), int(r["impressions"]), float(r["position"]), r["date"])
        for r in rows
    ] == list(_ROWS)


def test_sample_loads_with_both_dimensions():
    ds = load_csv(SAMPLE)
    assert ds.has_query and ds.has_page and len(ds.df) == len(_ROWS)


def test_titles_table_names_the_query_when_a_page_repeats():
    issues = find_title_issues(load_csv(SAMPLE))
    pages = [i.page for i in issues]
    assert len(pages) != len(set(pages)), "sample should exercise a page on two rows"
    table = _render_titles(issues, as_json=False)
    assert "| Page | Query |" in table
    assert "free birth chart" in table and "birth chart reading" in table
