# Sample data

`sample-search-console.csv` is **synthetic**. The rows are invented to exercise
every analysis once, not exported from any real Search Console property. It is
the same dataset the test suite builds in `tests/conftest.py`, written out as a
CSV so the CLI can be tried before you have an export of your own:

- one quick win (position 7, 4,000 impressions, low CTR),
- one title/CTR under-performer (position 2, far below the expected CTR),
- one content gap (impressions, no clicks, no ranking page),
- two dated periods, so `weekly --split 2026-06-08` has a before and after.

`tests/test_sample_csv.py` fails if this file drifts from the fixture or stops
producing a result in any of the five analyses.
