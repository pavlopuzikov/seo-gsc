from seo_gsc.models import SearchDataset, COLUMNS


def test_normalizes_missing_columns():
    ds = SearchDataset.from_rows([{"query": "x", "clicks": 5, "impressions": 100}])
    assert list(ds.df.columns) == list(COLUMNS)
    row = ds.df.iloc[0]
    assert row["page"] == ""
    assert row["position"] == 0.0


def test_recomputes_ctr_when_missing():
    ds = SearchDataset.from_rows([{"query": "x", "clicks": 10, "impressions": 200}])
    assert abs(float(ds.df.iloc[0]["ctr"]) - 0.05) < 1e-9


def test_totals_weighted_position():
    ds = SearchDataset.from_rows(
        [
            {"query": "a", "clicks": 0, "impressions": 100, "position": 10.0},
            {"query": "b", "clicks": 0, "impressions": 300, "position": 2.0},
        ]
    )
    totals = ds.totals()
    assert totals["impressions"] == 400
    # Weighted: (10*100 + 2*300)/400 = 4.0
    assert abs(totals["position"] - 4.0) < 1e-9


def test_filter_dates_inclusive(dataset):
    recent = dataset.filter_dates(start="2026-06-08")
    assert recent.has_dates
    assert (recent.df["date"] >= "2026-06-08").all()
