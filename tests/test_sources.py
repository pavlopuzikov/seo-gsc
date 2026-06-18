from seo_gsc.sources.base import canonical_header, parse_ctr, parse_number
from seo_gsc.sources.csv_source import load_csv_text


def test_canonical_header_maps_gsc_export():
    assert canonical_header("Top queries") == "query"
    assert canonical_header("Top pages") == "page"
    assert canonical_header("CTR") == "ctr"
    assert canonical_header("Average position") == "position"
    assert canonical_header("nonsense") is None


def test_parse_ctr_handles_percent_and_fraction():
    assert abs(parse_ctr("5.32%") - 0.0532) < 1e-9
    assert abs(parse_ctr("0.0532") - 0.0532) < 1e-9
    assert abs(parse_ctr(5.32) - 0.0532) < 1e-9
    assert parse_ctr("") == 0.0


def test_parse_number_strips_separators():
    assert parse_number("1,234") == 1234.0
    assert parse_number("") == 0.0


def test_load_csv_text_gsc_style():
    text = "Top queries,Clicks,Impressions,CTR,Position\n" "luxury villa,12,400,3.00%,6.2\n"
    ds = load_csv_text(text)
    assert len(ds) == 1
    row = ds.df.iloc[0]
    assert row["query"] == "luxury villa"
    assert row["clicks"] == 12
    assert abs(float(row["ctr"]) - 0.03) < 1e-9
    assert abs(float(row["position"]) - 6.2) < 1e-9


def test_load_csv_text_tab_separated():
    text = "query\tclicks\timpressions\tposition\nfoo\t3\t90\t4.0"
    ds = load_csv_text(text)
    assert len(ds) == 1
    assert ds.df.iloc[0]["query"] == "foo"
