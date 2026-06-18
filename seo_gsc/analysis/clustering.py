"""Mode 2: query clustering.

Groups queries into topic clusters by shared significant tokens (connected
components over a shared-token graph), so you stop building one thin page per
keyword. Each cluster gets aggregate clicks/impressions, the page that ranks for
it (if any), and a verdict: build a hub page, fold into an existing page, or the
page already exists and just needs optimizing.
"""

from __future__ import annotations

from collections import Counter

from ..config import Thresholds
from ..models import QueryCluster, SearchDataset
from ._common import aggregate, corpus_stopwords, tokenize


class _UnionFind:
    def __init__(self, n: int) -> None:
        self.parent = list(range(n))

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


def _theme(token_lists: list[list[str]], stop: set[str]) -> str:
    counts: Counter[str] = Counter()
    for toks in token_lists:
        for t in toks:
            if t not in stop:
                counts[t] += 1
    top = [t for t, _ in counts.most_common(2)]
    return " ".join(top) if top else "misc"


def cluster_queries(
    dataset: SearchDataset,
    thresholds: Thresholds | None = None,
) -> list[QueryCluster]:
    """Return topic clusters sorted by total impressions (desc)."""
    th = thresholds or Thresholds()
    if not dataset.has_query:
        return []

    by = ["query", "page"] if dataset.has_page else ["query"]
    agg = aggregate(dataset.df, by)
    if agg.empty:
        return []

    # Collapse to one row per query (sum across pages) for clustering, but keep
    # the per-(query,page) detail to pick the ranking page later.
    query_agg = aggregate(dataset.df, ["query"])
    queries = [q for q in query_agg["query"].tolist() if q]
    if not queries:
        return []

    tokens_by_query = {q: tokenize(q) for q in queries}
    stop = corpus_stopwords(list(tokens_by_query.values()))

    # Significant token sets (corpus stopwords removed) drive the edges.
    sig = {q: set(t for t in toks if t not in stop) for q, toks in tokens_by_query.items()}

    # Build inverted index token -> query indices, then union queries sharing
    # at least `cluster_min_shared_tokens` significant tokens.
    idx = {q: i for i, q in enumerate(queries)}
    uf = _UnionFind(len(queries))
    token_to_queries: dict[str, list[str]] = {}
    for q, toks in sig.items():
        for t in toks:
            token_to_queries.setdefault(t, []).append(q)

    min_shared = max(1, th.cluster_min_shared_tokens)
    for t, qs in token_to_queries.items():
        if len(qs) < 2:
            continue
        # Sort for a deterministic anchor regardless of input row order.
        ordered = sorted(qs)
        anchor = ordered[0]
        for other in ordered[1:]:
            shared = len(sig[anchor] & sig[other])
            if shared >= min_shared:
                uf.union(idx[anchor], idx[other])

    # Gather components.
    comps: dict[int, list[str]] = {}
    for q in queries:
        root = uf.find(idx[q])
        comps.setdefault(root, []).append(q)

    qa = query_agg.set_index("query")
    clusters: list[QueryCluster] = []
    for members in comps.values():
        if len(members) < th.cluster_min_queries:
            continue
        sub = qa.loc[members]
        clicks = int(sub["clicks"].sum())
        impressions = int(sub["impressions"].sum())
        ctr = (clicks / impressions) if impressions else 0.0
        position = (
            float((sub["position"] * sub["impressions"]).sum() / impressions) if impressions else 0.0
        )

        ranking_page, page_share = _dominant_page(dataset, members)
        verdict = _verdict(impressions, len(members), ranking_page, page_share, th)

        clusters.append(
            QueryCluster(
                theme=_theme([tokens_by_query[m] for m in members], stop),
                queries=sorted(members, key=lambda m: int(qa.loc[m, "impressions"]), reverse=True),
                clicks=clicks,
                impressions=impressions,
                ctr=ctr,
                avg_position=position,
                ranking_page=ranking_page,
                verdict=verdict,
            )
        )

    clusters.sort(key=lambda c: c.impressions, reverse=True)
    return clusters


def _dominant_page(dataset: SearchDataset, members: list[str]) -> tuple[str, float]:
    """Return (page, impression_share) of the top page serving these queries."""
    if not dataset.has_page:
        return "", 0.0
    df = dataset.df
    sub = df[df["query"].isin(members) & (df["page"].str.len() > 0)]
    if sub.empty:
        return "", 0.0
    by_page = sub.groupby("page")["impressions"].sum().sort_values(ascending=False)
    total = by_page.sum()
    if total <= 0:
        return "", 0.0
    top_page = str(by_page.index[0])
    return top_page, float(by_page.iloc[0] / total)


def _verdict(
    impressions: int,
    n_queries: int,
    ranking_page: str,
    page_share: float,
    th: Thresholds,
) -> str:
    if ranking_page and page_share >= 0.5:
        return "page exists (optimize it)"
    if impressions >= th.quick_win_min_impressions and n_queries >= 3:
        return "build hub page"
    return "fold into existing"
