"""Load Search Console UI exports or pasted CSV into a SearchDataset.

This is the zero-credential bootstrap path: a user can export Queries.csv /
Pages.csv from the GSC Performance report (or paste rows into the chat), and
every analysis mode works immediately, before the API service account exists.
"""

from __future__ import annotations

import io
from pathlib import Path

import pandas as pd

from ..models import SearchDataset
from .base import canonical_header, parse_ctr, parse_number


def _frame_to_dataset(raw: pd.DataFrame, label: str) -> SearchDataset:
    if raw.empty:
        return SearchDataset.empty(label)
    if len(raw.columns) < 2:
        raise ValueError(
            f"Parsed only {len(raw.columns)} column(s); the delimiter may be wrong "
            "or the input is not CSV/TSV."
        )
    # Rename known headers to canonical names; drop unmapped columns.
    rename: dict[str, str] = {}
    for col in raw.columns:
        canon = canonical_header(col)
        if canon:
            rename[col] = canon
    df = raw.rename(columns=rename)
    keep = [c for c in df.columns if c in {"query", "page", "clicks", "impressions", "ctr", "position", "date", "country", "device"}]
    if not keep:
        raise ValueError(
            "No recognizable Search Console columns found. Expected some of: "
            "Top queries / Top pages / Clicks / Impressions / CTR / Position."
        )
    df = df[keep].copy()

    if "ctr" in df.columns:
        df["ctr"] = df["ctr"].map(parse_ctr)
    for col in ("clicks", "impressions", "position"):
        if col in df.columns:
            df[col] = df[col].map(parse_number)

    return SearchDataset(df, label=label)


def load_csv(path: str | Path, label: str | None = None) -> SearchDataset:
    """Load a single GSC export CSV/TSV file into a SearchDataset."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"CSV not found: {p}")
    sep = "\t" if p.suffix.lower() in {".tsv", ".tab"} else ","
    # utf-8-sig strips a UTF-8 BOM, which GSC/Excel exports often prepend and
    # which would otherwise corrupt the first header name.
    raw = pd.read_csv(p, sep=sep, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    return _frame_to_dataset(raw, label or p.stem)


def load_csv_text(text: str, label: str = "pasted") -> SearchDataset:
    """Load CSV text (pasted into the chat) into a SearchDataset.

    Auto-detects comma vs tab so a copy out of a spreadsheet also works.
    """
    if not text or not text.strip():
        return SearchDataset.empty(label)
    text = text.lstrip("﻿")  # strip a pasted BOM
    first_line = text.strip().splitlines()[0]
    sep = "\t" if first_line.count("\t") > first_line.count(",") else ","
    raw = pd.read_csv(io.StringIO(text), sep=sep, dtype=str, keep_default_na=False)
    return _frame_to_dataset(raw, label)
