from seo_gsc.analysis import cluster_queries
from seo_gsc.analysis._common import tokenize, corpus_stopwords


def test_tokenize_drops_stopwords_and_stems_plural():
    toks = tokenize("the best apartments for sale")
    assert "the" not in toks  # stopword
    assert "best" not in toks  # stopword
    assert "apartment" in toks  # plural stemmed
    assert "sale" in toks


def test_corpus_stopwords_skipped_for_small_sets():
    # Fewer than min_docs queries -> no corpus stopwords even if a term repeats.
    lists = [["dubai", "villa"], ["dubai", "apartment"]]
    assert corpus_stopwords(lists) == set()


def test_clusters_form_by_shared_tokens(dataset):
    clusters = cluster_queries(dataset)
    themes = " ".join(c.theme for c in clusters)
    assert any("dubai" in c.theme or "apartment" in c.theme for c in clusters)
    assert any("saturn" in c.theme or "return" in c.theme for c in clusters)
    # Every cluster has at least the minimum number of queries.
    assert all(len(c.queries) >= 2 for c in clusters)


def test_cluster_has_ranking_page_and_verdict(dataset):
    clusters = cluster_queries(dataset)
    real_estate = next(c for c in clusters if "dubai" in c.theme or "apartment" in c.theme)
    assert real_estate.impressions > 0
    assert real_estate.verdict in {"page exists (optimize it)", "build hub page", "fold into existing"}
