"""Data sources for seo-gsc.

- csv_source: load a GSC UI export or a pasted CSV (zero-setup bootstrap).
- gsc_api:    live Search Console pull via REST (httpx + google-auth).
- ga4_api:    live GA4 engagement pull via REST (httpx + google-auth).

All three normalize into a SearchDataset (or, for GA4, a plain enrichment frame).
Google imports are lazy so the package imports and tests run without them.
"""

from .csv_source import load_csv, load_csv_text

__all__ = ["load_csv", "load_csv_text"]
