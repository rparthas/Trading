"""Prior trend detection via swing structure and MA slope."""

from __future__ import annotations

import pandas as pd


def detect_prior_trend(df: pd.DataFrame, lookback: int = 20) -> str:
    """Classify recent price action as uptrend, downtrend, or sideways."""
    if df.empty:
        return "sideways"

    n = min(lookback, len(df))
    window = df.iloc[-n:]
    closes = window["close"]
    highs = window["high"]
    lows = window["low"]

    mid = max(n // 2, 1)
    first_high = highs.iloc[:mid].max()
    second_high = highs.iloc[mid:].max()
    first_low = lows.iloc[:mid].min()
    second_low = lows.iloc[mid:].min()

    ma_period = min(5, n)
    ma = closes.rolling(ma_period).mean().dropna()
    slope = 0.0
    if len(ma) >= 2 and ma.iloc[0] != 0:
        slope = (ma.iloc[-1] - ma.iloc[0]) / ma.iloc[0]

    highs_rising = second_high > first_high
    lows_rising = second_low > first_low
    highs_falling = second_high < first_high
    lows_falling = second_low < first_low

    if highs_rising and lows_rising and slope > 0.01:
        return "uptrend"
    if highs_falling and lows_falling and slope < -0.01:
        return "downtrend"
    return "sideways"
