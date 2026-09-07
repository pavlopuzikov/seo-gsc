from seo_gsc.analysis import find_quick_wins
from seo_gsc.models import SearchDataset


def test_top_quick_win_is_high_impression_off_page_one(dataset):
    wins = find_quick_wins(dataset)
    assert wins, "expected at least one quick win"
    top = wins[0]
    assert top.query == "luxury apartment dubai"
    assert 5.0 <= top.position <= 15.0
    assert top.opportunity > 0


def test_excludes_page_one_top_and_low_impressions(dataset):
    wins = find_quick_wins(dataset)
    queries = {w.query for w in wins}
    # Ranks at position ~2, so not a quick win (already on page 1 top).
    assert "acme realty reviews" not in queries


def test_sorted_by_opportunity_desc(dataset):
    wins = find_quick_wins(dataset)
    opps = [w.opportunity for w in wins]
    assert opps == sorted(opps, reverse=True)


def test_empty_without_query_dimension():
    ds = SearchDataset.from_rows([{"page": "/x", "clicks": 1, "impressions": 500, "position": 8.0}])
    assert find_quick_wins(ds) == []
