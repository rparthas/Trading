"""Position sizing."""

from __future__ import annotations


def calc_position_size(
    account: float,
    risk_pct: float,
    entry: float,
    stop: float,
    multiplier: float = 1.0,
    max_position_pct: float | None = None,
) -> int:
    """Return integer share count based on fixed-fractional risk."""
    risk_per_share = abs(entry - stop)
    if risk_per_share <= 0 or account <= 0 or risk_pct <= 0:
        return 0

    risk_amount = account * (risk_pct / 100.0) * multiplier
    shares = int(risk_amount / risk_per_share)

    if max_position_pct is not None and entry > 0:
        max_shares = int((account * max_position_pct / 100.0) / entry)
        shares = min(shares, max_shares)

    return max(0, shares)
