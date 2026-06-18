"""Mode 3: content writer from gaps.

Finds clusters that earn impressions but almost no clicks and have no dedicated
page, then drafts a scaffold for the strongest one: an H2/H3 outline derived from
the cluster's queries, the entities to cover, and internal-link targets.

The draft is a starting skeleton. Per the playbook, finished content must be
expert-led and credentialed, not an author-less AI dump, so this hands the
outline to a human (and to the seo-aeo-geo skill for citation/structure depth).
"""

from __future__ import annotations

from ..config import Thresholds
from ..models import ContentGap, QueryCluster, SearchDataset
from ._common import tokenize
from .clustering import cluster_queries


def _outline(theme: str, queries: list[str]) -> list[str]:
    """Build an H2/H3 skeleton from the cluster's distinct query phrasings."""
    outline = [f"H1: {theme.title()}"]
    outline.append("H2: Overview (answer the core question in the first 100 words)")
    seen: set[str] = set()
    for q in queries[:6]:
        key = q.lower().strip()
        if key in seen:
            continue
        seen.add(key)
        outline.append(f"H2: {q.strip().capitalize()}")
    outline.append("H2: Frequently asked questions (FAQ schema)")
    return outline


def find_content_gaps(
    dataset: SearchDataset,
    thresholds: Thresholds | None = None,
    clusters: list[QueryCluster] | None = None,
    limit: int = 10,
    draft_top: int = 1,
) -> list[ContentGap]:
    """Return content gaps; the top `draft_top` get a full outline scaffold."""
    th = thresholds or Thresholds()
    clusters = clusters if clusters is not None else cluster_queries(dataset, th)

    gaps: list[ContentGap] = []
    for c in clusters:
        no_page = (not c.ranking_page) or c.verdict == "build hub page"
        if c.impressions >= th.gap_min_impressions and c.clicks <= th.gap_max_clicks and no_page:
            gaps.append(
                ContentGap(
                    theme=c.theme,
                    queries=c.queries,
                    impressions=c.impressions,
                    clicks=c.clicks,
                    avg_position=c.avg_position,
                )
            )

    gaps.sort(key=lambda g: g.impressions, reverse=True)
    gaps = gaps[:limit]

    # Enrich the strongest gaps with an outline, entities, and link targets.
    ranked_pages = _existing_pages(dataset)
    for g in gaps[:draft_top]:
        g.suggested_outline = _outline(g.theme, g.queries)
        ents: list[str] = []
        for q in g.queries:
            for t in tokenize(q):
                if t not in ents:
                    ents.append(t)
        g.entities = ents[:15]
        g.internal_link_targets = ranked_pages[:5]
    return gaps


def _existing_pages(dataset: SearchDataset, top: int = 20) -> list[str]:
    """Highest-impression existing pages, as candidate internal-link sources."""
    if not dataset.has_page:
        return []
    df = dataset.df
    sub = df[df["page"].str.len() > 0]
    if sub.empty:
        return []
    by_page = sub.groupby("page")["impressions"].sum().sort_values(ascending=False)
    return [str(p) for p in by_page.index[:top]]
