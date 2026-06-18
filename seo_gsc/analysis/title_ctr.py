"""Mode 4: title-tag / meta CTR checker.

Finds pages/queries that earn far fewer clicks than their average position should
(a title/meta intent-match problem, not a ranking problem) and quantifies the
clicks being left on the table. These are clicks you have already earned the rank
for but are not capturing.
"""

from __future__ import annotations

from ..config import Thresholds
from ..ctr_curve import expected_ctr
from ..models import SearchDataset, TitleIssue
from ._common import aggregate

# Past page 1 the lever is ranking, not the title/meta, and the absolute click
# upside is tiny, so we only flag CTR under-performance on page-1 results.
_MAX_POSITION = 10.0


def find_title_issues(
    dataset: SearchDataset,
    thresholds: Thresholds | None = None,
    curve: dict[int, float] | None = None,
    limit: int | None = 50,
) -> list[TitleIssue]:
    """Return CTR under-performers sorted by estimated missed clicks (desc)."""
    th = thresholds or Thresholds()

    # Prefer page-level grouping (a title/meta belongs to a page); fall back to
    # query level if there is no page dimension.
    if dataset.has_page:
        by = ["page", "query"] if dataset.has_query else ["page"]
    elif dataset.has_query:
        by = ["query"]
    else:
        return []

    agg = aggregate(dataset.df, by)
    issues: list[TitleIssue] = []
    for _, r in agg.iterrows():
        impressions = int(r["impressions"])
        position = float(r["position"])
        if impressions < th.low_ctr_min_impressions or position > _MAX_POSITION or position <= 0:
            continue
        exp = expected_ctr(position, curve)
        if exp <= 0:
            continue
        actual = float(r["ctr"])
        if actual < th.low_ctr_factor * exp:
            missed = impressions * (exp - actual)
            issues.append(
                TitleIssue(
                    query=str(r["query"]) if "query" in r else "",
                    page=str(r["page"]) if "page" in r else "",
                    impressions=impressions,
                    clicks=int(r["clicks"]),
                    position=position,
                    actual_ctr=actual,
                    expected_ctr=exp,
                    missed_clicks=round(missed, 1),
                    note=(
                        f"CTR {actual * 100:.1f}% vs about {exp * 100:.1f}% expected at "
                        f"position {position:.1f}. Rewrite the title and meta to match intent."
                    ),
                )
            )

    issues.sort(key=lambda i: i.missed_clicks, reverse=True)
    return issues[:limit] if limit else issues
