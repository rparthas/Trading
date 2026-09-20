"""Shared candle geometry helpers."""

from __future__ import annotations

from typing import Any

import pandas as pd


def _row(candle: pd.Series | dict[str, Any]) -> dict[str, float]:
    if isinstance(candle, pd.Series):
        return {
            "open": float(candle["open"]),
            "high": float(candle["high"]),
            "low": float(candle["low"]),
            "close": float(candle["close"]),
        }
    return {
        "open": float(candle["open"]),
        "high": float(candle["high"]),
        "low": float(candle["low"]),
        "close": float(candle["close"]),
    }


def candle_range(candle: pd.Series | dict[str, Any]) -> float:
    c = _row(candle)
    return c["high"] - c["low"]


def body_size(candle: pd.Series | dict[str, Any]) -> float:
    c = _row(candle)
    return abs(c["close"] - c["open"])


def body_ratio(candle: pd.Series | dict[str, Any]) -> float:
    r = candle_range(candle)
    return body_size(candle) / r if r > 0 else 0.0


def upper_shadow(candle: pd.Series | dict[str, Any]) -> float:
    c = _row(candle)
    return c["high"] - max(c["open"], c["close"])


def lower_shadow(candle: pd.Series | dict[str, Any]) -> float:
    c = _row(candle)
    return min(c["open"], c["close"]) - c["low"]


def upper_shadow_ratio(candle: pd.Series | dict[str, Any]) -> float:
    r = candle_range(candle)
    return upper_shadow(candle) / r if r > 0 else 0.0


def lower_shadow_ratio(candle: pd.Series | dict[str, Any]) -> float:
    r = candle_range(candle)
    return lower_shadow(candle) / r if r > 0 else 0.0


def range_pct(candle: pd.Series | dict[str, Any]) -> float:
    c = _row(candle)
    if c["close"] == 0:
        return 0.0
    return (c["high"] - c["low"]) / c["close"] * 100.0


def is_bullish(candle: pd.Series | dict[str, Any]) -> bool:
    c = _row(candle)
    return c["close"] > c["open"]


def is_bearish(candle: pd.Series | dict[str, Any]) -> bool:
    c = _row(candle)
    return c["close"] < c["open"]


def shadow_to_body_ratio(candle: pd.Series | dict[str, Any], side: str) -> float:
    body = body_size(candle)
    if body == 0:
        return float("inf")
    shadow = upper_shadow(candle) if side == "upper" else lower_shadow(candle)
    return shadow / body
