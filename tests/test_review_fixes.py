"""Regression tests for the adversarial-review fixes."""

import pytest

from seo_gsc.ctr_curve import expected_ctr
from seo_gsc.models import SearchDataset
from seo_gsc.sources.csv_source import load_csv_text
from seo_gsc.analysis import split_by_date


def test_load_csv_text_strips_bom():
    # A leading UTF-8 BOM must not corrupt the first header.
    text = "﻿Top queries,Clicks,Impressions,Position\nvilla dubai,4,300,6.0"
    ds = load_csv_text(text)
    assert len(ds) == 1
    assert ds.df.iloc[0]["query"] == "villa dubai"


def test_load_csv_text_single_column_raises():
    # Wrong delimiter collapses everything into one column; fail loudly.
    with pytest.raises(ValueError):
        load_csv_text("justonecolumn\nfoo\nbar")


def test_load_csv_text_empty_is_empty_dataset():
    assert len(load_csv_text("")) == 0


def test_ctr_curve_interpolates_across_gap():
    # Custom curve missing rank 2 must interpolate between 1 and 3, not drop to tail.
    curve = {1: 0.3, 3: 0.1}
    assert abs(expected_ctr(2.0, curve) - 0.2) < 1e-9


def test_split_by_date_requires_dates():
    ds = SearchDataset.from_rows([{"query": "x", "clicks": 1, "impressions": 10}])
    with pytest.raises(ValueError):
        split_by_date(ds, "2026-01-01")


def test_split_by_date_requires_non_empty():
    with pytest.raises(ValueError):
        split_by_date(SearchDataset.empty(), "2026-01-01")


def test_clustering_is_order_independent(dataset):
    # Shuffling input rows must not change cluster themes (deterministic anchor).
    from seo_gsc.analysis import cluster_queries

    shuffled = SearchDataset(dataset.df.iloc[::-1].reset_index(drop=True))
    a = sorted(c.theme for c in cluster_queries(dataset))
    b = sorted(c.theme for c in cluster_queries(shuffled))
    assert a == b
