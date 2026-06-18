"""Normalized data model shared by every source and analysis mode.

The whole toolkit operates on a SearchDataset: a thin, typed wrapper around a
pandas DataFrame with a fixed column contract. GSC API rows, GA4 rows, and CSV
exports are all normalized into this shape, so the five analysis modules never
care where the data came from.

Result types (QuickWin, QueryCluster, ContentGap, TitleIssue, PeriodDelta) are
plain dataclasses so they are trivially serializable to dict/JSON/markdown and
testable without any heavy dependency.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Iterable

import pandas as pd

# Canonical column contract for every SearchDataset. Some sources only populate a
# subset (a GSC "query" pull has no page; a "page" pull has no query); missing
# dimensions are filled with empty strings and missing metrics with 0.
COLUMNS: tuple[str, ...] = (
    "query",
    "page",
    "clicks",
    "impressions",
    "ctr",
    "position",
    "date",
    "country",
    "device",
)

_NUMERIC = ("clicks", "impressions", "ctr", "position")


class SearchDataset:
    """Typed wrapper around a Search Console performance DataFrame."""

    def __init__(self, frame: pd.DataFrame, label: str = "") -> None:
        self.df = self._normalize(frame)
        self.label = label

    # -- construction ---------------------------------------------------------

    @classmethod
    def from_rows(cls, rows: Iterable[dict[str, Any]], label: str = "") -> "SearchDataset":
        return cls(pd.DataFrame(list(rows)), label=label)

    @classmethod
    def empty(cls, label: str = "") -> "SearchDataset":
        return cls(pd.DataFrame(columns=list(COLUMNS)), label=label)

    @staticmethod
    def _normalize(frame: pd.DataFrame) -> pd.DataFrame:
        df = frame.copy()
        for col in COLUMNS:
            if col not in df.columns:
                df[col] = 0 if col in _NUMERIC else ""
        # Coerce types defensively; CSV sources can deliver strings.
        for col in ("clicks", "impressions"):
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype("int64")
        for col in ("ctr", "position"):
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0).astype("float64")
        for col in ("query", "page", "date", "country", "device"):
            df[col] = df[col].fillna("").astype(str)
        # Recompute CTR when it is absent or obviously invalid (0 with clicks),
        # so downstream math never divides by a bad rate. CTR is a fraction 0..1.
        needs = (df["ctr"] <= 0) & (df["impressions"] > 0) & (df["clicks"] > 0)
        df.loc[needs, "ctr"] = df.loc[needs, "clicks"] / df.loc[needs, "impressions"]
        return df[list(COLUMNS)]

    # -- introspection --------------------------------------------------------

    def __len__(self) -> int:
        return len(self.df)

    @property
    def has_query(self) -> bool:
        return bool((self.df["query"].str.len() > 0).any())

    @property
    def has_page(self) -> bool:
        return bool((self.df["page"].str.len() > 0).any())

    @property
    def has_dates(self) -> bool:
        return bool((self.df["date"].str.len() > 0).any())

    def totals(self) -> dict[str, float]:
        """Site-level totals with a correctly weighted CTR and position."""
        clicks = int(self.df["clicks"].sum())
        impressions = int(self.df["impressions"].sum())
        ctr = (clicks / impressions) if impressions else 0.0
        # Impression-weighted average position is the only honest aggregate.
        if impressions:
            position = float((self.df["position"] * self.df["impressions"]).sum() / impressions)
        else:
            position = 0.0
        return {
            "clicks": clicks,
            "impressions": impressions,
            "ctr": ctr,
            "position": position,
            "rows": len(self.df),
        }

    def filter_dates(self, start: str | None = None, end: str | None = None) -> "SearchDataset":
        """Inclusive date-range filter on ISO (YYYY-MM-DD) date strings."""
        df = self.df
        if start:
            df = df[df["date"] >= start]
        if end:
            df = df[df["date"] <= end]
        return SearchDataset(df, label=self.label)


# -- analysis result types ----------------------------------------------------


@dataclass
class QuickWin:
    """A query/page on the cusp of page 1 that one on-page change could lift."""

    query: str
    page: str
    position: float
    impressions: int
    clicks: int
    ctr: float
    opportunity: float  # impressions * (expected position-3 CTR - current CTR)
    recommendation: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class QueryCluster:
    """A topic cluster of related queries and its ranking-page verdict."""

    theme: str
    queries: list[str]
    clicks: int
    impressions: int
    ctr: float
    avg_position: float
    ranking_page: str  # "" means no page yet ranks
    verdict: str  # "build hub page" | "fold into existing" | "page exists"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ContentGap:
    """A cluster earning impressions but ~no clicks and no dedicated page."""

    theme: str
    queries: list[str]
    impressions: int
    clicks: int
    avg_position: float
    suggested_outline: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    internal_link_targets: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TitleIssue:
    """A page/query that under-earns the CTR expected at its position."""

    query: str
    page: str
    impressions: int
    clicks: int
    position: float
    actual_ctr: float
    expected_ctr: float
    missed_clicks: float  # impressions * (expected_ctr - actual_ctr)
    note: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PeriodDelta:
    """Week-over-week (or period-over-period) movement for one entity."""

    entity: str  # "site" or a query / page string
    clicks: int
    clicks_prev: int
    impressions: int
    impressions_prev: int
    ctr: float
    ctr_prev: float
    position: float
    position_prev: float

    @property
    def clicks_change(self) -> int:
        return self.clicks - self.clicks_prev

    @property
    def position_change(self) -> float:
        # Negative is good (moved up the page).
        return self.position - self.position_prev

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["clicks_change"] = self.clicks_change
        d["position_change"] = self.position_change
        return d
