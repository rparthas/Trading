"""Dow Theory pattern evidence (confirmatory only)."""

from __future__ import annotations

import pandas as pd


def _local_extrema(series: pd.Series, kind: str) -> list[tuple[int, float]]:
    points: list[tuple[int, float]] = []
    values = series.tolist()
    for i in range(2, len(values) - 2):
        window = values[i - 2 : i + 3]
        center = values[i]
        if kind == "high" and center == max(window):
            points.append((i, float(center)))
        if kind == "low" and center == min(window):
            points.append((i, float(center)))
    return points


def detect_dow_patterns(df: pd.DataFrame) -> list[str]:
    """Return evidence tags for Dow-style structures in recent price action."""
    if len(df) < 20:
        return []

    window = df.iloc[-60:] if len(df) >= 60 else df
    evidence: list[str] = []
    highs = _local_extrema(window["high"], "high")
    lows = _local_extrema(window["low"], "low")

    if len(highs) >= 2:
        (_, h1), (_, h2) = highs[-2], highs[-1]
        if h1 > 0 and abs(h2 - h1) / h1 <= 0.02:
            evidence.append("double_top")

    if len(lows) >= 2:
        (_, l1), (_, l2) = lows[-2], lows[-1]
        if l1 > 0 and abs(l2 - l1) / l1 <= 0.02:
            evidence.append("double_bottom")

    closes = window["close"]
    first_third = closes.iloc[: len(closes) // 3]
    last_third = closes.iloc[-len(closes) // 3 :]
    if len(first_third) >= 2 and len(last_third) >= 2:
        first_move = (first_third.iloc[-1] - first_third.iloc[0]) / first_third.iloc[0]
        consolidation = last_third.max() - last_third.min()
        if abs(first_move) >= 0.05 and consolidation / closes.iloc[-1] <= 0.03:
            evidence.append("flag")

    range_high = window["high"].iloc[:-5].max()
    range_low = window["low"].iloc[:-5].min()
    latest_close = float(window["close"].iloc[-1])
    if range_high > range_low:
        if latest_close > range_high * 1.01:
            evidence.append("range_breakout")
        elif latest_close < range_low * 0.99:
            evidence.append("range_breakout")

    return evidence
