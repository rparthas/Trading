"""Shared stop / target / max-holding exit rules for backtest and paper trading."""

from __future__ import annotations

from datetime import date

import pandas as pd

from models.trade import Direction


def calc_pnl(direction: str, entry_price: float, exit_price: float, shares: int) -> float:
    if direction == Direction.LONG.value:
        return (exit_price - entry_price) * shares
    return (entry_price - exit_price) * shares


def check_bar_exit(
    direction: str,
    stop: float,
    target: float,
    max_exit_date: pd.Timestamp,
    bar: pd.Series,
    current_date: date,
) -> tuple[float | None, str]:
    high = float(bar["high"])
    low = float(bar["low"])
    close = float(bar["close"])

    if pd.Timestamp(current_date) >= max_exit_date:
        return close, "max_holding"

    if direction == Direction.LONG.value:
        if low <= stop:
            return stop, "stop"
        if high >= target:
            return target, "target"
    else:
        if high >= stop:
            return stop, "stop"
        if low <= target:
            return target, "target"

    return None, ""
