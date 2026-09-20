"""Multi-candle pattern detection on the latest 2-3 bars."""

from __future__ import annotations

from typing import Any

import pandas as pd

from models.trade import Direction, PatternResult
from patterns.candle_utils import body_ratio, is_bearish, is_bullish
from patterns.single_candle import _detect_neutral_shapes, _global_range_ok
from patterns.trend import detect_prior_trend


def _body_bounds(candle: pd.Series) -> tuple[float, float]:
    return (float(min(candle["open"], candle["close"])), float(max(candle["open"], candle["close"])))


def _engulf_pct(p1: pd.Series, p2: pd.Series) -> float:
    p1_body = abs(p1["close"] - p1["open"])
    if p1_body == 0:
        return 0.0
    if is_bearish(p1) and is_bullish(p2):
        recovery = p2["close"] - p1["close"]
    elif is_bullish(p1) and is_bearish(p2):
        recovery = p1["close"] - p2["close"]
    else:
        return 0.0
    return max(0.0, recovery / p1_body * 100.0)


def _make_multi_result(
    pattern: str,
    direction: Direction,
    strength: float,
    df: pd.DataFrame,
    candle_index: int,
    entry: float,
    stop: float,
    validation: dict[str, float],
) -> PatternResult:
    return PatternResult(
        pattern=pattern,
        direction=direction,
        strength=min(max(strength, 0.0), 1.0),
        candle_index=candle_index,
        entry_reference=entry,
        stop_reference=stop,
        validation=validation,
    )


def _two_candle_patterns(p1: pd.Series, p2: pd.Series, cfg: dict[str, Any], trend: str) -> PatternResult | None:
    patterns = cfg["patterns"]
    p1_lo, p1_hi = _body_bounds(p1)
    p2_lo, p2_hi = _body_bounds(p2)
    engulf = p2_lo <= p1_lo and p2_hi >= p1_hi
    inside = p2_hi <= p1_hi and p2_lo >= p1_lo
    midpoint = (p1["open"] + p1["close"]) / 2.0
    engulf_pct = _engulf_pct(p1, p2)

    checks: list[tuple[str, Direction, str, bool, float, float]] = []

    if trend == "downtrend" and is_bearish(p1) and is_bullish(p2) and engulf:
        checks.append(
            (
                "bullish_engulfing",
                Direction.LONG,
                "min_low_p1_p2",
                True,
                float(p2["close"]),
                float(min(p1["low"], p2["low"])),
            )
        )
    if trend == "uptrend" and is_bullish(p1) and is_bearish(p2) and engulf:
        checks.append(
            (
                "bearish_engulfing",
                Direction.SHORT,
                "max_high_p1_p2",
                True,
                float(p2["close"]),
                float(max(p1["high"], p2["high"])),
            )
        )
    if trend == "downtrend" and is_bearish(p1) and is_bullish(p2) and inside:
        checks.append(
            (
                "bullish_harami",
                Direction.LONG,
                "min_low_p1_p2",
                True,
                float(p2["close"]),
                float(min(p1["low"], p2["low"])),
            )
        )
    if trend == "uptrend" and is_bullish(p1) and is_bearish(p2) and inside:
        checks.append(
            (
                "bearish_harami",
                Direction.SHORT,
                "max_high_p1_p2",
                True,
                float(p2["close"]),
                float(max(p1["high"], p2["high"])),
            )
        )

    piercing_cfg = patterns["piercing_pattern"]
    if (
        trend == "downtrend"
        and is_bearish(p1)
        and is_bullish(p2)
        and p2["open"] < p1["close"]
        and p2["close"] > midpoint
        and piercing_cfg["p2_engulf_pct_min"] <= engulf_pct <= piercing_cfg["p2_engulf_pct_max"]
    ):
        checks.append(
            (
                "piercing_pattern",
                Direction.LONG,
                "pattern_low",
                True,
                float(p2["close"]),
                float(min(p1["low"], p2["low"])),
            )
        )

    dark_cfg = patterns["dark_cloud_cover"]
    if (
        trend == "uptrend"
        and is_bullish(p1)
        and is_bearish(p2)
        and p2["open"] > p1["close"]
        and p2["close"] < midpoint
        and dark_cfg["p2_engulf_pct_min"] <= engulf_pct <= dark_cfg["p2_engulf_pct_max"]
    ):
        checks.append(
            (
                "dark_cloud_cover",
                Direction.SHORT,
                "max_high_p1_p2",
                True,
                float(p2["close"]),
                float(max(p1["high"], p2["high"])),
            )
        )

    results: list[PatternResult] = []
    for pattern, direction, _stop_rule, _, entry, stop in checks:
        strength = 0.75 if "engulfing" in pattern or "harami" in pattern else engulf_pct / 100.0
        validation = {"engulf_pct": engulf_pct, "body_engulfed": float(engulf), "body_inside": float(inside)}
        results.append(_make_multi_result(pattern, direction, strength, pd.DataFrame([p2]), -1, entry, stop, validation))
    return max(results, key=lambda r: r.strength) if results else None


def _three_candle_patterns(
    p1: pd.Series, p2: pd.Series, p3: pd.Series, cfg: dict[str, Any], trend: str
) -> PatternResult | None:
    p2_shape = _detect_neutral_shapes(p2, cfg)
    if p2_shape is None or p2_shape.pattern not in cfg["patterns"]["morning_star"]["p2_types"]:
        p2_ok = False
        p2_type = ""
    else:
        p2_ok = True
        p2_type = p2_shape.pattern

    results: list[PatternResult] = []

    if (
        trend == "downtrend"
        and is_bearish(p1)
        and p2_ok
        and p2["high"] < p1["low"]
        and p3["low"] > p2["high"]
        and p3["close"] > p1["open"]
    ):
        stop = float(min(p1["low"], p2["low"], p3["low"]))
        validation = {"p2_type": 1.0 if p2_type == "doji" else 0.5, "gap_down": 1.0, "gap_up": 1.0}
        results.append(
            _make_multi_result(
                "morning_star",
                Direction.LONG,
                0.85,
                pd.DataFrame([p3]),
                -1,
                float(p3["close"]),
                stop,
                validation,
            )
        )

    if (
        trend == "uptrend"
        and is_bullish(p1)
        and p2_ok
        and p2["low"] > p1["high"]
        and p3["high"] < p2["low"]
        and p3["close"] < p1["open"]
    ):
        stop = float(max(p1["high"], p2["high"], p3["high"]))
        validation = {"p2_type": 1.0 if p2_type == "doji" else 0.5, "gap_up": 1.0, "gap_down": 1.0}
        results.append(
            _make_multi_result(
                "evening_star",
                Direction.SHORT,
                0.85,
                pd.DataFrame([p3]),
                -1,
                float(p3["close"]),
                stop,
                validation,
            )
        )

    return max(results, key=lambda r: r.strength) if results else None


def detect_multi_patterns(df: pd.DataFrame, cfg: dict[str, Any]) -> PatternResult | None:
    """Detect the strongest multi-candle pattern ending on the latest bar."""
    if len(df) < 2:
        return None

    if not _global_range_ok(df.iloc[-1], cfg):
        return None

    trend = detect_prior_trend(df)
    candidates: list[PatternResult] = []

    p1, p2 = df.iloc[-2], df.iloc[-1]
    two = _two_candle_patterns(p1, p2, cfg, trend)
    if two is not None:
        candidates.append(two)

    if len(df) >= 3:
        p1, p2, p3 = df.iloc[-3], df.iloc[-2], df.iloc[-1]
        three = _three_candle_patterns(p1, p2, p3, cfg, trend)
        if three is not None:
            candidates.append(three)

    if not candidates:
        return None
    return max(candidates, key=lambda r: r.strength)
