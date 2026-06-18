"""Shared analysis helpers: tokenization and impression-weighted aggregation."""

from __future__ import annotations

import re
from collections import Counter
from typing import Sequence

import pandas as pd

# Generic English stopwords plus filler that adds no topical signal. Domain hub
# terms (for example "dubai", "barnes") are removed dynamically as corpus
# stopwords in cluster_queries, not hardcoded here.
STOPWORDS: frozenset[str] = frozenset(
    {
        "a", "an", "and", "the", "for", "to", "of", "in", "on", "at", "by", "is",
        "are", "be", "with", "from", "or", "as", "how", "what", "where", "when",
        "why", "which", "who", "vs", "your", "you", "my", "me", "i", "it", "this",
        "that", "do", "does", "can", "near", "best", "top", "new",
    }
)

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str, min_len: int = 3) -> list[str]:
    """Lower-case, split on non-alphanumerics, drop stopwords and short tokens.

    Applies a tiny stemming step (strip a trailing plural 's') so "apartment"
    and "apartments" cluster together.
    """
    tokens = []
    for tok in _TOKEN_RE.findall(str(text).lower()):
        if tok in STOPWORDS or len(tok) < min_len:
            continue
        if len(tok) > 4 and tok.endswith("s") and not tok.endswith("ss"):
            tok = tok[:-1]
        tokens.append(tok)
    return tokens


def corpus_stopwords(
    token_lists: Sequence[Sequence[str]],
    doc_fraction: float = 0.6,
    min_docs: int = 8,
) -> set[str]:
    """Tokens appearing in more than `doc_fraction` of queries act like stopwords.

    WHY: a hub term that is in almost every query (for example the brand or city)
    would otherwise merge every cluster into one. Treating it as a corpus
    stopword keeps clusters meaningful. Skipped for small sets (n < min_docs),
    where a term in half the queries is signal, not noise, and stripping it would
    dissolve the cluster it defines.
    """
    n = len(token_lists)
    if n < min_docs:
        return set()
    doc_freq: Counter[str] = Counter()
    for toks in token_lists:
        for tok in set(toks):
            doc_freq[tok] += 1
    cutoff = doc_fraction * n
    return {tok for tok, df in doc_freq.items() if df > cutoff}


def aggregate(df: pd.DataFrame, by: Sequence[str]) -> pd.DataFrame:
    """Group by `by` with summed clicks/impressions and weighted ctr/position."""
    by = list(by)
    if df.empty:
        return pd.DataFrame(columns=by + ["clicks", "impressions", "ctr", "position"])

    work = df.copy()
    work["_pos_weighted"] = work["position"] * work["impressions"]
    grouped = work.groupby(by, dropna=False).agg(
        clicks=("clicks", "sum"),
        impressions=("impressions", "sum"),
        _pos_weighted=("_pos_weighted", "sum"),
    ).reset_index()

    grouped["ctr"] = grouped.apply(
        lambda r: (r["clicks"] / r["impressions"]) if r["impressions"] else 0.0, axis=1
    )
    grouped["position"] = grouped.apply(
        lambda r: (r["_pos_weighted"] / r["impressions"]) if r["impressions"] else 0.0, axis=1
    )
    return grouped.drop(columns=["_pos_weighted"])
