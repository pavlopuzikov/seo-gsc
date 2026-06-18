"""Markdown rendering helpers for analysis output. Dash-free by house rule."""

from __future__ import annotations

from typing import Sequence


def pct(x: float, places: int = 2) -> str:
    return f"{x * 100:.{places}f}%"


def num(x: float) -> str:
    return f"{int(round(x)):,}"


def pos(x: float) -> str:
    return f"{x:.1f}"


def md_table(headers: Sequence[str], rows: Sequence[Sequence[object]]) -> str:
    """Render a GitHub-flavored markdown table. Empty rows yield a placeholder."""
    head = "| " + " | ".join(str(h) for h in headers) + " |"
    sep = "| " + " | ".join("---" for _ in headers) + " |"
    if not rows:
        body = "| " + " | ".join("(none)" for _ in headers) + " |"
        return "\n".join([head, sep, body])
    body_lines = []
    for row in rows:
        body_lines.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join([head, sep, *body_lines])


def signed(x: float, places: int = 0) -> str:
    """Signed number with an explicit plus, for week-over-week deltas."""
    if places == 0:
        return f"{x:+,.0f}"
    return f"{x:+,.{places}f}"
