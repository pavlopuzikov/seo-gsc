"""Expected organic click-through rate by average search position.

The title/CTR mode needs a baseline "what CTR should a page at position N earn",
so it can flag pages that under-perform their rank (a title/meta intent problem)
versus pages that simply rank too low (a ranking problem).

The default table below is a blended desktop+mobile organic CTR curve in the
spirit of public aggregate studies (Advanced Web Ranking, GSC dataset analyses).
It is deliberately conservative and is meant to be CALIBRATED per property: a
brand-heavy site earns far higher position-1 CTR than an informational one. Pass
a per-property override via SeoConfig.ctr_curve.

WHY: Google does not publish an official CTR-by-position curve, so this is an
illustrative default, not ground truth. The analysis reports the curve used.
"""

from __future__ import annotations

# Position -> expected CTR (fraction 0..1). Blended organic, approximate.
DEFAULT_CTR_CURVE: dict[int, float] = {
    1: 0.275,
    2: 0.155,
    3: 0.100,
    4: 0.070,
    5: 0.053,
    6: 0.041,
    7: 0.033,
    8: 0.028,
    9: 0.024,
    10: 0.021,
    11: 0.018,
    12: 0.016,
    13: 0.014,
    14: 0.013,
    15: 0.012,
    16: 0.011,
    17: 0.010,
    18: 0.009,
    19: 0.008,
    20: 0.008,
}

# Expected CTR for any average position beyond the last tabulated rank.
_TAIL_CTR = 0.005


def expected_ctr(position: float, curve: dict[int, float] | None = None) -> float:
    """Return the expected CTR for a (possibly fractional) average position.

    GSC reports average position as a float (for example 7.3), so we linearly
    interpolate between the two bracketing integer ranks. Positions below 1 clamp
    to rank 1; positions past the table use a flat tail value.
    """
    table = curve or DEFAULT_CTR_CURVE
    if not table:
        return 0.0
    ranks = sorted(table)
    lo, hi = ranks[0], ranks[-1]

    if position <= lo:
        return float(table[lo])
    if position >= hi:
        # Interpolate from the last tabulated rank down to the flat tail across
        # the next ten positions, then hold flat, so a position-30 page is not
        # treated the same as a position-21 page.
        if position >= hi + 10:
            return _TAIL_CTR
        last = float(table[hi])
        frac = (position - hi) / 10.0
        return last + (_TAIL_CTR - last) * frac

    # Bracket the position with the nearest DEFINED ranks, so a custom curve with
    # gaps (for example missing rank 11) still interpolates correctly instead of
    # dropping to the tail value.
    lower_rank = max(r for r in ranks if r <= position)
    upper_rank = min(r for r in ranks if r >= position)
    if lower_rank == upper_rank:
        return float(table[lower_rank])
    low_val = float(table[lower_rank])
    high_val = float(table[upper_rank])
    frac = (position - lower_rank) / (upper_rank - lower_rank)
    return low_val + (high_val - low_val) * frac
