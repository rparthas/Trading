"""Single-candle pattern detection on the latest bar."""

from __future__ import annotations

from typing import Any

import pandas as pd

from models.trade import Direction, PatternResult
from patterns.candle_utils import (
    body_ratio,
    is_bearish,
    is_bullish,
    lower_shadow_ratio,
    range_pct,
    shadow_to_body_ratio,
    upper_shadow_ratio,
)
from patterns.trend import detect_prior_trend


def _global_range_ok(candle: pd.Series, cfg: dict[str, Any]) -> bool:
    rules = cfg.get("global", {}).get("candle_range_pct", {})
    pct = range_pct(candle)
    return rules.get("min", 0.0) <= pct <= rules.get("max", 100.0)


def _prior_trend_ok(pattern_name: str, pattern_cfg: dict[str, Any], trend: str) -> bool:
    required = pattern_cfg.get("prior_trend", "any")
    if required == "any":
        return True
    return trend == required


def _prior_trend_ok_with_cfg(
    pattern_name: str, pattern_cfg: dict[str, Any], trend: str, cfg: dict[str, Any]
) -> bool:
    exceptions = set(cfg.get("global", {}).get("prior_trend", {}).get("exceptions", []))
    if pattern_name in exceptions:
        return True
    return _prior_trend_ok(pattern_name, pattern_cfg, trend)


def _make_result(
    pattern: str,
    direction: Direction,
    strength: float,
    candle: pd.Series,
    entry_key: str,
    stop_key: str,
    validation: dict[str, float],
) -> PatternResult:
    entry = float(candle["close"] if entry_key == "close" else candle[entry_key])
    stop = float(candle["low"] if stop_key == "low" else candle["high"])
    return PatternResult(
        pattern=pattern,
        direction=direction,
        strength=min(max(strength, 0.0), 1.0),
        candle_index=-1,
        entry_reference=entry,
        stop_reference=stop,
        validation=validation,
    )


def _detect_marubozu(candle: pd.Series, cfg: dict[str, Any], trend: str) -> PatternResult | None:
    patterns = cfg["patterns"]
    br = body_ratio(candle)
    usr = upper_shadow_ratio(candle)
    lsr = lower_shadow_ratio(candle)
    validation = {"body_ratio": br, "upper_shadow_ratio": usr, "lower_shadow_ratio": lsr}

    for name, direction in (("bullish_marubozu", Direction.LONG), ("bearish_marubozu", Direction.SHORT)):
        pcfg = patterns[name]
        if not _prior_trend_ok_with_cfg(name, pcfg, trend, cfg):
            continue
        bullish_ok = direction == Direction.LONG and is_bullish(candle)
        bearish_ok = direction == Direction.SHORT and is_bearish(candle)
        if not (bullish_ok or bearish_ok):
            continue
        if (
            br >= pcfg["min_body_ratio"]
            and usr <= pcfg["upper_shadow_max_ratio"]
            and lsr <= pcfg["lower_shadow_max_ratio"]
        ):
            strength = min(br / pcfg["min_body_ratio"], 1.0)
            return _make_result(name, direction, strength, candle, pcfg["entry"], pcfg["stop"], validation)
    return None


def _detect_hammer_family(candle: pd.Series, cfg: dict[str, Any], trend: str) -> PatternResult | None:
    patterns = cfg["patterns"]
    lsb = shadow_to_body_ratio(candle, "lower")
    usb = shadow_to_body_ratio(candle, "upper")
    usr = upper_shadow_ratio(candle)
    lsr = lower_shadow_ratio(candle)
    validation = {
        "lower_shadow_to_body": lsb,
        "upper_shadow_ratio": usr,
        "lower_shadow_ratio": lsr,
    }

    checks = [
        ("hammer", Direction.LONG, "downtrend", is_bullish(candle) or body_ratio(candle) < 0.3),
        ("hanging_man", Direction.SHORT, "uptrend", True),
        ("shooting_star", Direction.SHORT, "uptrend", is_bearish(candle) or body_ratio(candle) < 0.3),
    ]
    for name, direction, required_trend, shape_ok in checks:
        pcfg = patterns[name]
        if trend != required_trend or not shape_ok:
            continue
        if name in ("hammer", "hanging_man"):
            if lsb < pcfg["lower_shadow_to_body_min"] or usr > pcfg["upper_shadow_max_ratio"]:
                continue
            strength = min(lsb / pcfg["lower_shadow_to_body_min"], 1.0)
        else:
            if usb < pcfg["upper_shadow_to_body_min"] or lsr > pcfg["lower_shadow_max_ratio"]:
                continue
            strength = min(usb / pcfg["upper_shadow_to_body_min"], 1.0)
            validation["upper_shadow_to_body"] = usb
        return _make_result(name, direction, strength, candle, pcfg["entry"], pcfg["stop"], validation)
    return None


def _detect_neutral_shapes(candle: pd.Series, cfg: dict[str, Any]) -> PatternResult | None:
    patterns = cfg["patterns"]
    br = body_ratio(candle)
    usr = upper_shadow_ratio(candle)
    lsr = lower_shadow_ratio(candle)
    validation = {"body_ratio": br, "upper_shadow_ratio": usr, "lower_shadow_ratio": lsr}

    doji_cfg = patterns["doji"]
    if br <= doji_cfg["body_max_ratio"]:
        strength = 1.0 - br / doji_cfg["body_max_ratio"]
        return _make_result("doji", Direction.NEUTRAL, strength, candle, "close", "low", validation)

    spin_cfg = patterns["spinning_top"]
    if br <= spin_cfg["body_max_ratio"]:
        balance = abs(usr - lsr)
        if balance <= spin_cfg["shadow_balance_tolerance"]:
            strength = 1.0 - balance / spin_cfg["shadow_balance_tolerance"]
            return _make_result(
                "spinning_top", Direction.NEUTRAL, strength, candle, "close", "low", validation
            )
    return None


def detect_single_patterns(df: pd.DataFrame, cfg: dict[str, Any]) -> PatternResult | None:
    """Detect the strongest single-candle pattern on the latest bar."""
    if df.empty:
        return None

    candle = df.iloc[-1]
    if not _global_range_ok(candle, cfg):
        return None

    trend = detect_prior_trend(df)
    candidates: list[PatternResult] = []
    for detector in (_detect_marubozu, _detect_hammer_family, _detect_neutral_shapes):
        if detector is _detect_neutral_shapes:
            result = detector(candle, cfg)
        else:
            result = detector(candle, cfg, trend)
        if result is not None:
            candidates.append(result)

    if not candidates:
        return None
    return max(candidates, key=lambda r: r.strength)
