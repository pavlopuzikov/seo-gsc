"""Mode 1: GSC quick wins.

Queries/pages sitting just off the top of page 1 (positions 5 to 15 by default)
with enough impressions to matter, ranked by the extra clicks a realistic lift
to roughly position 3 would earn. Each gets one concrete on-page recommendation.

This is the fastest-rankings-this-quarter list from the playbook: small on-page
moves on terms Google already shows you for.
"""

from __future__ import annotations

from typing import Sequence

from ..config import Thresholds
from ..ctr_curve import expected_ctr
from ..models import QuickWin, SearchDataset
from ._common import aggregate

# Target rank we model a quick win as reaching, for the opportunity estimate.
_TARGET_POSITION = 3.0


def _recommendation(query: str, position: float) -> str:
    """One on-page change keyed to how far off page 1 the term sits."""
    if position >= 11:
        return (
            f"On page 2 for '{query}'. Make this the explicit on-page target: put the "
            "exact phrase in the title and H1, answer it in the first 100 words, and add "
            "internal links from your strongest related pages."
        )
    if position >= 8:
        return (
            f"Just below the fold for '{query}'. Tighten the title and meta description to "
            "match the query intent exactly and expand the section that answers it."
        )
    return (
        f"Top of page 1 for '{query}'. Add depth (a focused FAQ and supporting subsections) "
        "and earn one or two contextual links to push into the top 3."
    )


def find_quick_wins(
    dataset: SearchDataset,
    thresholds: Thresholds | None = None,
    curve: dict[int, float] | None = None,
    limit: int | None = 50,
) -> list[QuickWin]:
    """Return quick-win opportunities sorted by estimated clicks gained.

    The opportunity estimate holds impressions constant at the current value and
    applies the CTR expected at the target position. This is deliberately
    conservative: a better rank usually also lifts impressions, so realized gain
    is often higher. Treat it as a prioritization signal, not a forecast.
    """
    th = thresholds or Thresholds()
    if not dataset.has_query:
        return []

    by = ["query", "page"] if dataset.has_page else ["query"]
    agg = aggregate(dataset.df, by)

    band = agg[
        (agg["position"] >= th.quick_win_min_position)
        & (agg["position"] <= th.quick_win_max_position)
        & (agg["impressions"] >= th.quick_win_min_impressions)
    ]

    target_ctr = expected_ctr(_TARGET_POSITION, curve)
    wins: list[QuickWin] = []
    for _, r in band.iterrows():
        impressions = int(r["impressions"])
        clicks = int(r["clicks"])
        actual_ctr = float(r["ctr"])
        position = float(r["position"])
        projected_clicks = impressions * target_ctr
        opportunity = max(0.0, projected_clicks - clicks)
        query = str(r["query"])
        wins.append(
            QuickWin(
                query=query,
                page=str(r["page"]) if "page" in r else "",
                position=position,
                impressions=impressions,
                clicks=clicks,
                ctr=actual_ctr,
                opportunity=round(opportunity, 1),
                recommendation=_recommendation(query, position),
            )
        )

    wins.sort(key=lambda w: w.opportunity, reverse=True)
    return wins[:limit] if limit else wins
