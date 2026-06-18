"""Mode 5: weekly report.

Compares the current period against the previous one and produces an
exec-readable markdown summary: site-level week-over-week moves in clicks,
impressions, CTR, and position; the three changes that mattered (biggest movers);
and three priorities for next week, derived from the current quick-wins and
title-CTR opportunities.
"""

from __future__ import annotations

from ..config import Thresholds
from ..models import PeriodDelta, SearchDataset
from ._common import aggregate
from .formatting import md_table, num, pct, pos, signed
from .quick_wins import find_quick_wins
from .title_ctr import find_title_issues


def split_by_date(dataset: SearchDataset, split_date: str) -> tuple[SearchDataset, SearchDataset]:
    """Split a dated dataset into (previous, current) at an ISO split_date.

    current = rows on/after split_date; previous = rows before it.
    """
    if len(dataset) == 0:
        raise ValueError("split_by_date requires a non-empty dataset")
    if not dataset.has_dates:
        raise ValueError("split_by_date requires a dataset with a date dimension")
    df = dataset.df
    previous = SearchDataset(df[df["date"] < split_date], label="previous")
    current = SearchDataset(df[df["date"] >= split_date], label="current")
    return previous, current


def _site_delta(current: SearchDataset, previous: SearchDataset) -> PeriodDelta:
    c, p = current.totals(), previous.totals()
    return PeriodDelta(
        entity="site",
        clicks=int(c["clicks"]),
        clicks_prev=int(p["clicks"]),
        impressions=int(c["impressions"]),
        impressions_prev=int(p["impressions"]),
        ctr=float(c["ctr"]),
        ctr_prev=float(p["ctr"]),
        position=float(c["position"]),
        position_prev=float(p["position"]),
    )


def _entity_deltas(current: SearchDataset, previous: SearchDataset, by: str) -> list[PeriodDelta]:
    """Per-entity (query or page) deltas joined across the two periods."""
    if by == "query" and not current.has_query and not previous.has_query:
        return []
    if by == "page" and not current.has_page and not previous.has_page:
        return []

    cur = aggregate(current.df, [by]).set_index(by)
    prev = aggregate(previous.df, [by]).set_index(by)
    entities = set(cur.index) | set(prev.index)
    deltas: list[PeriodDelta] = []
    for ent in entities:
        if not str(ent):
            continue
        cr = cur.loc[ent] if ent in cur.index else None
        pr = prev.loc[ent] if ent in prev.index else None
        deltas.append(
            PeriodDelta(
                entity=str(ent),
                clicks=int(cr["clicks"]) if cr is not None else 0,
                clicks_prev=int(pr["clicks"]) if pr is not None else 0,
                impressions=int(cr["impressions"]) if cr is not None else 0,
                impressions_prev=int(pr["impressions"]) if pr is not None else 0,
                ctr=float(cr["ctr"]) if cr is not None else 0.0,
                ctr_prev=float(pr["ctr"]) if pr is not None else 0.0,
                position=float(cr["position"]) if cr is not None else 0.0,
                position_prev=float(pr["position"]) if pr is not None else 0.0,
            )
        )
    return deltas


def compare_periods(current: SearchDataset, previous: SearchDataset) -> dict:
    """Return the site delta plus top query/page gainers and losers."""
    site = _site_delta(current, previous)
    by = "page" if (current.has_page or previous.has_page) else "query"
    deltas = _entity_deltas(current, previous, by)
    movers = sorted(deltas, key=lambda d: d.clicks_change, reverse=True)
    gainers = [d for d in movers if d.clicks_change > 0][:5]
    losers = [d for d in reversed(movers) if d.clicks_change < 0][:5]
    return {"site": site, "dimension": by, "gainers": gainers, "losers": losers}


def _priorities(current: SearchDataset, thresholds: Thresholds, curve) -> list[str]:
    """Three concrete priorities from current quick-wins and CTR misses."""
    th = thresholds or Thresholds()
    priorities: list[str] = []

    wins = find_quick_wins(current, th, curve, limit=2)
    for w in wins:
        priorities.append(
            f"Quick win: '{w.query}' at position {w.position:.1f} with {num(w.impressions)} "
            f"impressions (about {num(w.opportunity)} clicks on the table). {w.recommendation}"
        )

    issues = find_title_issues(current, th, curve, limit=2)
    for it in issues:
        target = it.page or it.query
        priorities.append(
            f"CTR fix: {target} earns {pct(it.actual_ctr)} vs about {pct(it.expected_ctr)} "
            f"expected at position {it.position:.1f}; rewrite the title and meta "
            f"(about {num(it.missed_clicks)} clicks recoverable)."
        )

    return priorities[:3] if priorities else ["No high-confidence priority surfaced this week; hold course and re-measure."]


def build_weekly_markdown(
    current: SearchDataset,
    previous: SearchDataset,
    property_name: str = "",
    period_label: str = "this week vs last week",
    thresholds: Thresholds | None = None,
    curve: dict[int, float] | None = None,
) -> str:
    """Assemble the full exec-readable weekly markdown report."""
    th = thresholds or Thresholds()
    cmp = compare_periods(current, previous)
    s: PeriodDelta = cmp["site"]

    header = f"# SEO weekly report: {property_name or 'site'}"
    sub = f"_{period_label}_"

    site_table = md_table(
        ["Metric", "Current", "Previous", "Change"],
        [
            ["Clicks", num(s.clicks), num(s.clicks_prev), signed(s.clicks_change)],
            ["Impressions", num(s.impressions), num(s.impressions_prev), signed(s.impressions - s.impressions_prev)],
            ["CTR", pct(s.ctr), pct(s.ctr_prev), f"{(s.ctr - s.ctr_prev) * 100:+.2f} pts"],
            ["Avg position", pos(s.position), pos(s.position_prev), f"{s.position_change:+.1f}"],
        ],
    )

    dim = cmp["dimension"]
    gain_rows = [[d.entity, signed(d.clicks_change), num(d.clicks), pos(d.position)] for d in cmp["gainers"]]
    lose_rows = [[d.entity, signed(d.clicks_change), num(d.clicks), pos(d.position)] for d in cmp["losers"]]
    gainers = md_table([f"Top gaining {dim}", "Clicks change", "Clicks now", "Position"], gain_rows)
    losers = md_table([f"Top losing {dim}", "Clicks change", "Clicks now", "Position"], lose_rows)

    changes = _what_changed(cmp)
    priorities = _priorities(current, th, curve)

    parts = [
        header,
        sub,
        "",
        "## Site movement",
        site_table,
        "",
        "## What changed (the 3 that mattered)",
        "\n".join(f"{i + 1}. {c}" for i, c in enumerate(changes)),
        "",
        "## Movers",
        gainers,
        "",
        losers,
        "",
        "## Priorities for next week",
        "\n".join(f"{i + 1}. {p}" for i, p in enumerate(priorities)),
        "",
        "_Hand the priority queries to the seo-aeo-geo skill for citation-ready structure and schema._",
    ]
    return "\n".join(parts)


def _what_changed(cmp: dict) -> list[str]:
    dim = cmp["dimension"]
    out: list[str] = []
    if cmp["gainers"]:
        g = cmp["gainers"][0]
        out.append(f"Biggest gain: {dim} '{g.entity}' added {signed(g.clicks_change)} clicks.")
    if cmp["losers"]:
        l = cmp["losers"][0]
        out.append(f"Biggest drop: {dim} '{l.entity}' lost {num(abs(l.clicks_change))} clicks; check for a ranking or SERP-layout change.")
    s = cmp["site"]
    if s.position_change < -0.2:
        out.append(f"Average position improved by {abs(s.position_change):.1f} across the site.")
    elif s.position_change > 0.2:
        out.append(f"Average position slipped by {s.position_change:.1f} across the site; investigate lost rankings.")
    else:
        out.append("Average position held roughly flat week over week.")
    return out[:3]
