"""Support and resistance zone detection."""

from __future__ import annotations

import pandas as pd


def _swing_points(series: pd.Series, kind: str) -> list[tuple[int, float]]:
    points: list[tuple[int, float]] = []
    values = series.tolist()
    for i in range(1, len(values) - 1):
        if kind == "high" and values[i] >= values[i - 1] and values[i] >= values[i + 1]:
            points.append((i, float(values[i])))
        if kind == "low" and values[i] <= values[i - 1] and values[i] <= values[i + 1]:
            points.append((i, float(values[i])))
    return points


def _cluster_levels(levels: list[float], tolerance_pct: float = 1.5) -> list[tuple[float, float]]:
    if not levels:
        return []

    levels = sorted(levels)
    clusters: list[list[float]] = [[levels[0]]]
    for level in levels[1:]:
        anchor = clusters[-1][0]
        if anchor == 0 or abs(level - anchor) / anchor * 100.0 <= tolerance_pct:
            clusters[-1].append(level)
        else:
            clusters.append([level])

    zones: list[tuple[float, float]] = []
    for cluster in clusters:
        low = min(cluster) * 0.995
        high = max(cluster) * 1.005
        zones.append((low, high))
    return zones


def find_support_resistance_zones(df: pd.DataFrame, lookback: int) -> dict:
    """Return S/R zones and nearest levels relative to the latest close."""
    empty = {
        "support_zones": [],
        "resistance_zones": [],
        "nearest_support": None,
        "nearest_resistance": None,
    }
    if df.empty:
        return empty

    n = min(lookback, len(df))
    window = df.iloc[-n:]
    close = float(window["close"].iloc[-1])

    swing_lows = [price for _, price in _swing_points(window["low"], "low")]
    swing_highs = [price for _, price in _swing_points(window["high"], "high")]

    support_zones = _cluster_levels(swing_lows)
    resistance_zones = _cluster_levels(swing_highs)

    supports_below = [zone for zone in support_zones if zone[1] <= close]
    resistances_above = [zone for zone in resistance_zones if zone[0] >= close]

    nearest_support = max(supports_below, key=lambda z: z[1])[1] if supports_below else None
    nearest_resistance = min(resistances_above, key=lambda z: z[0])[0] if resistances_above else None

    return {
        "support_zones": support_zones,
        "resistance_zones": resistance_zones,
        "nearest_support": nearest_support,
        "nearest_resistance": nearest_resistance,
    }


def stop_aligned(stop: float, zone: tuple[float, float], max_pct: float) -> bool:
    """True when stop lies inside the zone or within `max_pct` of it."""
    low, high = zone
    if low <= stop <= high:
        return True
    if stop < low:
        distance_pct = (low - stop) / stop * 100.0 if stop else float("inf")
    else:
        distance_pct = (stop - high) / stop * 100.0 if stop else float("inf")
    return distance_pct <= max_pct
