"""Risk/reward calculations."""

from __future__ import annotations

from models.trade import Direction


def calc_rr(entry: float, stop: float, target: float, direction: Direction) -> float:
    """Return reward/risk ratio. Returns 0.0 when risk is non-positive."""
    if direction == Direction.LONG:
        risk = entry - stop
        reward = target - entry
    elif direction == Direction.SHORT:
        risk = stop - entry
        reward = entry - target
    else:
        return 0.0

    if risk <= 0:
        return 0.0
    return reward / risk


def calc_target_from_sr(
    entry: float,
    stop: float,
    direction: Direction,
    support: float | None,
    resistance: float | None,
    min_rr: float,
) -> float | None:
    """Derive target from nearest S/R level; fall back to min_rr projection."""
    if direction == Direction.LONG:
        risk = entry - stop
        if risk <= 0:
            return None
        if resistance is not None and resistance > entry:
            target = resistance
        else:
            target = entry + risk * min_rr
        if calc_rr(entry, stop, target, direction) < min_rr:
            target = entry + risk * min_rr
        return target if calc_rr(entry, stop, target, direction) >= min_rr else None

    if direction == Direction.SHORT:
        risk = stop - entry
        if risk <= 0:
            return None
        if support is not None and support < entry:
            target = support
        else:
            target = entry - risk * min_rr
        if calc_rr(entry, stop, target, direction) < min_rr:
            target = entry - risk * min_rr
        return target if calc_rr(entry, stop, target, direction) >= min_rr else None

    return None
