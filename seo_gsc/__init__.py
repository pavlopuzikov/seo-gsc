"""seo-gsc: local SEO/GEO/AEO toolkit over Google Search Console + GA4 data.

Five analysis modes (quick wins, query clustering, content gaps, title/CTR,
weekly report) run on a normalized pandas-backed dataset. Data can come from a
live API pull (sources.gsc_api / sources.ga4_api) or a pasted/exported CSV
(sources.csv_source), so the toolkit works with zero credentials for bootstrap.

WHY: built local on httpx + google-auth REST rather than a third-party MCP, so no
external service is granted read access to Search Console / Analytics data.
"""

from .models import (
    SearchDataset,
    QuickWin,
    QueryCluster,
    ContentGap,
    TitleIssue,
    PeriodDelta,
)

__version__ = "0.1.0"

__all__ = [
    "SearchDataset",
    "QuickWin",
    "QueryCluster",
    "ContentGap",
    "TitleIssue",
    "PeriodDelta",
    "__version__",
]
