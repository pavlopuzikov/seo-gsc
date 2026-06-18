"""Command-line interface for seo-gsc.

Subcommands map one-to-one to the five analysis modes, plus a `pull` command that
caches a live API pull to CSV. Every command works on either a CSV export
(--source csv --input file.csv) or a live API pull (--source api --property key).

Examples:
  seo-gsc quick-wins --source csv --input Queries.csv
  seo-gsc weekly --source api --property pavlopuzikov --days 7 --output report.md
  seo-gsc pull --property housecall --days 28 --output cache/housecall.csv
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

from .config import load_config, SeoConfig
from .models import SearchDataset
from .analysis import (
    cluster_queries,
    find_content_gaps,
    find_quick_wins,
    find_title_issues,
    build_weekly_markdown,
    split_by_date,
)
from .analysis.formatting import md_table, num, pct, pos
from .sources.csv_source import load_csv

# GSC data lags ~2-3 days; default the most recent usable day to 3 days back.
_DATA_LAG_DAYS = 3


def _date_range(days: int, end: str | None) -> tuple[str, str]:
    if end:
        end_d = dt.date.fromisoformat(end)
    else:
        end_d = dt.date.today() - dt.timedelta(days=_DATA_LAG_DAYS)
    start_d = end_d - dt.timedelta(days=days - 1)
    return start_d.isoformat(), end_d.isoformat()


def _load_api_dataset(config: SeoConfig, property_key: str, start: str, end: str, country: str | None) -> SearchDataset:
    from .sources.gsc_api import GSCClient  # lazy: avoids google-auth import unless used

    prop = config.property(property_key)
    client = GSCClient(
        service_account_file=config.service_account_file,
        oauth_token_file=config.oauth_token_file,
    )
    return client.query(
        prop.site_url,
        start_date=start,
        end_date=end,
        dimensions=("query", "page", "date"),
        country=country or prop.default_country,
        label=prop.name,
    )


def _load_dataset(args, config: SeoConfig) -> SearchDataset:
    if args.source == "csv":
        if not args.input:
            _fail("--input is required when --source csv")
        try:
            return load_csv(args.input)
        except FileNotFoundError:
            _fail(f"CSV not found: {args.input}")
        except ValueError as exc:
            _fail(f"Invalid CSV: {exc}")
    # api
    if not args.property:
        _fail("--property is required when --source api")
    start, end = _date_range(args.days, getattr(args, "end", None))
    if not config.service_account_file and not config.oauth_token_file:
        _fail(
            "No Google credentials configured. Set SEO_GSC_SERVICE_ACCOUNT_FILE in .env.local, "
            "or use --source csv with a GSC export for now."
        )
    return _load_api_dataset(config, args.property, start, end, args.country)


def _fail(msg: str) -> None:
    print(f"error: {msg}", file=sys.stderr)
    raise SystemExit(2)


def _emit(text: str, output: str | None) -> None:
    if output:
        Path(output).write_text(text, encoding="utf-8")
        print(f"wrote {output}")
    else:
        print(text)


# -- renderers ----------------------------------------------------------------


def _render_quick_wins(wins, as_json: bool) -> str:
    if as_json:
        return json.dumps([w.to_dict() for w in wins], indent=2)
    rows = [[w.query, pos(w.position), num(w.impressions), pct(w.ctr), num(w.opportunity)] for w in wins]
    table = md_table(["Query", "Position", "Impressions", "CTR", "Est. clicks gain"], rows)
    recs = "\n".join(f"{i + 1}. {w.recommendation}" for i, w in enumerate(wins))
    return f"# Quick wins\n\n{table}\n\n## Recommended on-page changes\n{recs or '(none)'}"


def _render_clusters(clusters, as_json: bool) -> str:
    if as_json:
        return json.dumps([c.to_dict() for c in clusters], indent=2)
    rows = [
        [c.theme, len(c.queries), num(c.clicks), num(c.impressions), pos(c.avg_position), c.ranking_page or "(no page yet)", c.verdict]
        for c in clusters
    ]
    return "# Query clusters\n\n" + md_table(
        ["Theme", "Queries", "Clicks", "Impressions", "Avg pos", "Ranking page", "Verdict"], rows
    )


def _render_gaps(gaps, as_json: bool) -> str:
    if as_json:
        return json.dumps([g.to_dict() for g in gaps], indent=2)
    rows = [[g.theme, num(g.impressions), num(g.clicks), pos(g.avg_position)] for g in gaps]
    out = ["# Content gaps\n", md_table(["Theme", "Impressions", "Clicks", "Avg pos"], rows)]
    for g in gaps:
        if g.suggested_outline:
            out.append(f"\n## Draft: {g.theme}")
            out.append("\n".join(f"- {line}" for line in g.suggested_outline))
            out.append(f"\n**Entities to cover:** {', '.join(g.entities)}")
            if g.internal_link_targets:
                out.append("**Internal links from:**")
                out.append("\n".join(f"- {p}" for p in g.internal_link_targets))
    return "\n".join(out)


def _render_titles(issues, as_json: bool) -> str:
    if as_json:
        return json.dumps([i.to_dict() for i in issues], indent=2)
    rows = [
        [(i.page or i.query), num(i.impressions), pos(i.position), pct(i.actual_ctr), pct(i.expected_ctr), num(i.missed_clicks)]
        for i in issues
    ]
    return "# Title / meta CTR opportunities\n\n" + md_table(
        ["Page or query", "Impressions", "Position", "Actual CTR", "Expected CTR", "Missed clicks"], rows
    )


# -- command handlers ---------------------------------------------------------


def _cmd_quick_wins(args, config):
    ds = _load_dataset(args, config)
    wins = find_quick_wins(ds, config.thresholds, config.ctr_curve, limit=args.limit)
    _emit(_render_quick_wins(wins, args.json), args.output)


def _cmd_clusters(args, config):
    ds = _load_dataset(args, config)
    clusters = cluster_queries(ds, config.thresholds)
    _emit(_render_clusters(clusters[: args.limit], args.json), args.output)


def _cmd_gaps(args, config):
    ds = _load_dataset(args, config)
    gaps = find_content_gaps(ds, config.thresholds, limit=args.limit)
    _emit(_render_gaps(gaps, args.json), args.output)


def _cmd_titles(args, config):
    ds = _load_dataset(args, config)
    issues = find_title_issues(ds, config.thresholds, config.ctr_curve, limit=args.limit)
    _emit(_render_titles(issues, args.json), args.output)


def _cmd_weekly(args, config):
    name = ""
    if args.source == "csv":
        if not args.input:
            _fail("--input required for csv weekly")
        try:
            ds = load_csv(args.input)
        except (FileNotFoundError, ValueError) as exc:
            _fail(f"Could not load CSV: {exc}")
        if not ds.has_dates:
            _fail("weekly needs a dated dataset; export GSC with the Date dimension or use --source api")
        split = args.split or _default_split(ds)
        previous, current = split_by_date(ds, split)
    else:
        if not args.property:
            _fail("--property is required when --source api")
        prop = config.property(args.property)
        name = prop.name
        end = dt.date.today() - dt.timedelta(days=_DATA_LAG_DAYS)
        cur_start = end - dt.timedelta(days=args.days - 1)
        full_start = end - dt.timedelta(days=2 * args.days - 1)
        if not config.service_account_file and not config.oauth_token_file:
            _fail("No Google credentials; set SEO_GSC_SERVICE_ACCOUNT_FILE or use --source csv")
        ds = _load_api_dataset(config, args.property, full_start.isoformat(), end.isoformat(), args.country)
        previous, current = split_by_date(ds, cur_start.isoformat())

    report = build_weekly_markdown(
        current, previous, property_name=name or args.property, thresholds=config.thresholds, curve=config.ctr_curve
    )
    _emit(report, args.output)


def _cmd_pull(args, config):
    if not args.property:
        _fail("--property is required for pull")
    start, end = _date_range(args.days, getattr(args, "end", None))
    ds = _load_api_dataset(config, args.property, start, end, args.country)
    out_path = Path(args.output or f"{args.property}-{start}-to-{end}.csv")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    ds.df.to_csv(out_path, index=False)
    print(f"pulled {len(ds)} rows to {out_path} ({start} to {end})")


def _default_split(ds: SearchDataset) -> str:
    """Midpoint date of a dated dataset (previous half vs current half)."""
    dates = sorted(d for d in ds.df["date"].unique() if d)
    return dates[len(dates) // 2] if dates else dt.date.today().isoformat()


# -- argument parsing ---------------------------------------------------------


def _add_common(p: argparse.ArgumentParser) -> None:
    p.add_argument("--config", default="config.yaml", help="Path to YAML config (default: config.yaml)")
    p.add_argument("--source", choices=["csv", "api"], default="csv", help="Where data comes from")
    p.add_argument("--input", help="CSV/TSV path (for --source csv)")
    p.add_argument("--property", help="Property key from config (for --source api)")
    p.add_argument("--days", type=int, default=28, help="Lookback window in days (api)")
    p.add_argument("--end", help="End date YYYY-MM-DD (api); default is 3 days ago")
    p.add_argument("--country", help="ISO-3 country filter, e.g. are (api)")
    p.add_argument("--limit", type=int, default=50, help="Max rows in the output")
    p.add_argument("--output", help="Write markdown/JSON to this file instead of stdout")
    p.add_argument("--json", action="store_true", help="Emit JSON instead of markdown")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="seo-gsc", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    for name, handler, help_text in [
        ("quick-wins", _cmd_quick_wins, "Queries at positions 5-15 with the biggest click upside"),
        ("clusters", _cmd_clusters, "Group queries into topic clusters with a hub/fold verdict"),
        ("gaps", _cmd_gaps, "Clusters with impressions but no clicks and no page; drafts the top one"),
        ("titles", _cmd_titles, "Pages under-earning the CTR expected at their position"),
        ("weekly", _cmd_weekly, "Week-over-week report with priorities for next week"),
        ("pull", _cmd_pull, "Pull a live GSC range and cache it to CSV"),
    ]:
        sp = sub.add_parser(name, help=help_text)
        _add_common(sp)
        if name == "weekly":
            sp.add_argument("--split", help="ISO date splitting previous vs current (csv weekly)")
            sp.set_defaults(days=7)
        sp.set_defaults(handler=handler)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = load_config(args.config)
    args.handler(args, config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
