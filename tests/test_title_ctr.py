from seo_gsc.analysis import find_title_issues


def test_top_title_issue_is_high_rank_low_ctr(dataset):
    issues = find_title_issues(dataset)
    assert issues, "expected at least one title/CTR issue"
    top = issues[0]
    # The position-2 page that earns almost no clicks is the biggest miss.
    assert top.page == "/about" or "barnes" in top.query
    assert top.actual_ctr < top.expected_ctr
    assert top.missed_clicks > 0


def test_sorted_by_missed_clicks_desc(dataset):
    issues = find_title_issues(dataset)
    missed = [i.missed_clicks for i in issues]
    assert missed == sorted(missed, reverse=True)


def test_respects_min_impressions():
    from seo_gsc.models import SearchDataset
    from seo_gsc.config import Thresholds

    ds = SearchDataset.from_rows(
        [{"query": "tiny", "page": "/t", "clicks": 0, "impressions": 10, "position": 2.0}]
    )
    # 10 impressions is below the default 100 floor -> not flagged.
    assert find_title_issues(ds, Thresholds()) == []
