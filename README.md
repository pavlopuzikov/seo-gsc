# seo-gsc

[![sanity](https://github.com/pavlopuzikov/seo-gsc/actions/workflows/sanity.yml/badge.svg)](https://github.com/pavlopuzikov/seo-gsc/actions/workflows/sanity.yml)
[![MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)

Local SEO / GEO / AEO toolkit. Pulls Google Search Console (and optionally GA4)
data and runs five analyses: quick wins, query clustering, content gaps,
title/CTR opportunities, and a week-over-week report.

Built local on `httpx` + `google-auth` (REST), so no third-party broker is ever
granted read access to your Search Console or Analytics data. Works with a live
API pull or a pasted/exported CSV, so you can start before any credentials exist.

It produces the data and the prioritised action list, and stops there. Turning a
priority query into the page that answers it is a writing job, and this tool
deliberately does not try to do it.

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

```bash
python -m venv .venv
source .venv/bin/activate       # Windows PowerShell: .\.venv\Scripts\Activate.ps1
pip install -e .

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
python -m seo_gsc.cli pull       --source api --property portfolio --days 28 --output cache/portfolio.csv
python -m seo_gsc.cli quick-wins --source api --property portfolio --days 28
python -m seo_gsc.cli weekly     --source api --property shop --days 7 --output reports/shop.md
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
runs `scripts/run-weekly-report.ps1` every Monday 08:00. See that script's header
for usage. It looks for `.venv/Scripts/python.exe` in the repo, falling back to
`python` on `PATH`.

## Development

```bash
pip install -e ".[dev]"
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
