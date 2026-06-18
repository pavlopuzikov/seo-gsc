"""The five SEO analysis modes, each operating on a SearchDataset."""

from .quick_wins import find_quick_wins
from .clustering import cluster_queries
from .content_gaps import find_content_gaps
from .title_ctr import find_title_issues
from .weekly_report import compare_periods, build_weekly_markdown, split_by_date

__all__ = [
    "find_quick_wins",
    "cluster_queries",
    "find_content_gaps",
    "find_title_issues",
    "compare_periods",
    "build_weekly_markdown",
    "split_by_date",
]
