from seo_gsc.analysis import find_content_gaps


def test_gap_surfaces_zero_click_no_page_cluster(dataset):
    gaps = find_content_gaps(dataset)
    assert gaps, "expected at least one content gap"
    top = gaps[0]
    assert "saturn" in top.theme or "return" in top.theme
    assert top.clicks <= 1
    assert top.impressions >= 50


def test_top_gap_gets_outline_and_entities(dataset):
    gaps = find_content_gaps(dataset, draft_top=1)
    top = gaps[0]
    assert top.suggested_outline
    assert any(line.startswith("H1:") for line in top.suggested_outline)
    assert top.entities


def test_pages_with_clicks_are_not_gaps(dataset):
    gaps = find_content_gaps(dataset)
    themes = " ".join(g.theme for g in gaps)
    # The birth-chart cluster has clicks and a page, so it is not a gap.
    assert "chart" not in themes
