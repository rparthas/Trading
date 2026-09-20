"""Volume confirmation helpers."""

from __future__ import annotations

import pandas as pd


def volume_ratio(df: pd.DataFrame, period: int = 10) -> float:
    """Latest bar volume divided by the prior `period`-bar average."""
    if len(df) < 2:
        return 0.0

    use_period = min(period, len(df) - 1)
    avg = df["volume"].iloc[-(use_period + 1) : -1].mean()
    latest = float(df["volume"].iloc[-1])
    if avg <= 0:
        return 0.0
    return latest / avg


def volume_confirmed(df: pd.DataFrame, period: int, min_ratio: float) -> bool:
    return volume_ratio(df, period) >= min_ratio
