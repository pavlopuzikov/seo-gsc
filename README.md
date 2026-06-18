# seo-gsc

Local SEO / GEO / AEO toolkit. Pulls Google Search Console (and optionally GA4)
data and runs five analyses: quick wins, query clustering, content gaps,
title/CTR opportunities, and a week-over-week report.

Built local on `httpx` + `google-auth` (REST), so no third-party broker is ever
granted read access to your Search Console or Analytics data. Works with a live
API pull or a pasted/exported CSV, so you can start before any credentials exist.

This tool produces the DATA and the prioritized action list. For turning a
priority query into citation-ready, schema-rich, AI-extractable content, hand off
to the `seo-aeo-geo` skill. See `docs/integration-specs/seo-gsc-skill-suite.md`
and `docs/seo-aeo-playbook-research.md` for the strategy this encodes.

## The five modes

| Command | What it answers |
|---------|-----------------|
| `quick-wins` | Which page-2 / bottom-of-page-1 terms can I lift with one on-page change? |
| `clusters` | Which queries belong together, and do they deserve a hub page or a fold? |
| `gaps` | Where do I earn impressions but no clicks and have no page? (drafts the top one) |
| `titles` | Which page-1 results under-earn the CTR their rank should get? |
| `weekly` | What moved this week, why, and what are next week's 3 priorities? |

## Quick start (CSV, zero credentials)

Export `Queries.csv` / `Pages.csv` (or a combined query+page+date CSV) from the
GSC Performance report, then:

On Windows use Git Bash for the `source` line below, or activate from PowerShell with
`.\shared\venv311\Scripts\Activate.ps1` (cmd.exe: `shared\venv311\Scripts\activate.bat`).

```bash
source shared/venv311/Scripts/activate          # canonical Python 3.11 env
cd tools/seo-gsc
python -m seo_gsc.cli quick-wins --source csv --input Queries.csv
python -m seo_gsc.cli clusters   --source csv --input Queries.csv
python -m seo_gsc.cli titles     --source csv --input Pages.csv
python -m seo_gsc.cli weekly     --source csv --input dated-export.csv --split 2026-06-10
```

Add `--json` for machine-readable output, `--output report.md` to write a file.

## Live API pull

1. Create a Google Cloud service account, enable the Search Console API and (for
   GA4) the Analytics Data API, and download the JSON key.
2. In Search Console > Settings > Users, add the service-account email with at
   least Restricted access to each property. For GA4, add it as a Viewer.
3. `cp .env.example .env.local` and set `SEO_GSC_SERVICE_ACCOUNT_FILE`.
4. `cp config.example.yaml config.yaml` and list your properties.

```bash
python -m seo_gsc.cli pull       --source api --property pavlopuzikov --days 28 --output cache/pp.csv
python -m seo_gsc.cli quick-wins --source api --property pavlopuzikov --days 28
python -m seo_gsc.cli weekly     --source api --property housecall --days 7 --output reports/housecall.md
```

`--days` is the lookback window; the most recent usable day defaults to 3 days
ago (GSC data latency). `--country are` filters to one ISO-3 country.

## Configuration

- `config.yaml` (safe to commit): properties, thresholds, optional CTR-curve override.
- `.env.local` (never commit): the service-account or OAuth key path only.

Thresholds (quick-win position band, impression floors, low-CTR factor, gap
cut-offs, clustering sensitivity) are all in `config.yaml`. The expected-CTR
curve in `seo_gsc/ctr_curve.py` is an illustrative blended default; calibrate it
per property (a brand-heavy site earns much higher position-1 CTR).

## Weekly automation

`scripts/register-weekly-task.ps1` registers a Windows Task Scheduler job that
runs `scripts/run-weekly-report.ps1` every Monday 08:00, mirroring the
`infra/multi-agent` headless pattern. See that script's header for usage.

## Development

```bash
cd tools/seo-gsc
python -m pytest -q
```

Tests run fully offline (no credentials, no network): every analysis mode is
exercised against a fixture dataset in `tests/conftest.py`.

## Design notes

- One normalized `SearchDataset` (pandas-backed) feeds every mode, so sources and
  analyses are decoupled.
- Google client imports are lazy, so the package imports and tests run without
  `google-auth` present.
- Clustering uses connected components over a shared-token graph with corpus
  stopword removal at scale. It is a heuristic: a low-frequency geographic or
  brand hub term can still merge clusters on small datasets; calibrate
  `cluster_min_shared_tokens` if needed.
