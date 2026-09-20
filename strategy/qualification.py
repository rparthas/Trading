"""Trade qualification engine — gated checks per strategy.yaml."""

from __future__ import annotations

from datetime import date

import pandas as pd

from indicators.macd import compute_macd, macd_signal
from indicators.rsi import compute_rsi
from models.trade import (
    Decision,
    Direction,
    GateResult,
    GateType,
    RejectionReason,
    TradeAnalysis,
)
from patterns.detect import detect_best_pattern
from patterns.dow import detect_dow_patterns
from patterns.support_resistance import find_support_resistance_zones, stop_aligned
from patterns.trend import detect_prior_trend
from patterns.volume import volume_confirmed, volume_ratio
from strategy.risk import calc_rr, calc_target_from_sr


def _gate_type(cfg: dict, gate_name: str) -> GateType:
    gate_cfg = cfg.get("gates", {}).get(gate_name, {})
    raw = gate_cfg.get("type", "mandatory")
    return GateType.CONFIRMATORY if raw == "confirmatory" else GateType.MANDATORY


def _first_failed_mandatory(gate_results: list[GateResult]) -> GateResult | None:
    for g in gate_results:
        if g.gate_type == GateType.MANDATORY and not g.passed:
            return g
    return None


def _prior_trend_ok(pattern_name: str, pattern_cfg: dict, trend: str, cfg: dict) -> bool:
    exceptions = set(cfg.get("global", {}).get("prior_trend", {}).get("exceptions", []))
    if pattern_name in exceptions:
        return True
    required = pattern_cfg.get("prior_trend", "any")
    if required == "any":
        return True
    return trend == required


def _rsi_confirms(direction: Direction, rsi: float | None) -> bool:
    if rsi is None:
        return False
    if direction == Direction.LONG:
        return 40 <= rsi <= 70
    if direction == Direction.SHORT:
        return 30 <= rsi <= 60
    return False


def _macd_confirms(direction: Direction, label: str) -> bool:
    if direction == Direction.LONG:
        return label == "bullish"
    if direction == Direction.SHORT:
        return label == "bearish"
    return False


def _zone_for_level(zones: list[tuple[float, float]], level: float | None) -> tuple[float, float] | None:
    if level is None:
        return None
    for zone in zones:
        if zone[0] <= level <= zone[1]:
            return zone
    return (level * 0.995, level * 1.005)


def qualify_trade(symbol: str, df: pd.DataFrame, cfg: dict, scan_date: date) -> TradeAnalysis:
    """Run all qualification gates and return TradeAnalysis."""
    gate_results: list[GateResult] = []

    if df is None or df.empty:
        gate_results.append(
            GateResult(
                gate="pattern_detected",
                gate_type=GateType.MANDATORY,
                passed=False,
                message="no data",
            )
        )
        return _reject(symbol, scan_date, gate_results, None, "no data for symbol")

    scan_ts = pd.Timestamp(scan_date)
    df = df[df.index <= scan_ts]
    if df.empty:
        gate_results.append(
            GateResult(
                gate="pattern_detected",
                gate_type=GateType.MANDATORY,
                passed=False,
                message="no bars on or before scan date",
            )
        )
        return _reject(symbol, scan_date, gate_results, None, "no bars on scan date")

    pattern = detect_best_pattern(df, cfg)
    gate_results.append(
        GateResult(
            gate="pattern_detected",
            gate_type=_gate_type(cfg, "pattern_detected"),
            passed=pattern is not None,
            value=pattern.pattern if pattern else None,
            message="pattern detected" if pattern else "no recognizable pattern",
        )
    )
    if pattern is None:
        return _reject(symbol, scan_date, gate_results, None, "no recognizable pattern")

    prior_trend = detect_prior_trend(df)
    pattern_cfg = cfg.get("patterns", {}).get(pattern.pattern, {})
    trend_ok = _prior_trend_ok(pattern.pattern, pattern_cfg, prior_trend, cfg)
    gate_results.append(
        GateResult(
            gate="prior_trend",
            gate_type=_gate_type(cfg, "prior_trend"),
            passed=trend_ok,
            value=prior_trend,
            threshold=pattern_cfg.get("prior_trend"),
            message="prior trend valid" if trend_ok else f"prior trend {prior_trend} invalid",
        )
    )

    vol_cfg = cfg.get("volume", {})
    vol_period = vol_cfg.get("average_period", 10)
    vol_min = vol_cfg.get("minimum_ratio", 1.0)
    vol_ratio = volume_ratio(df, vol_period)
    vol_ok = volume_confirmed(df, vol_period, vol_min)
    if vol_cfg.get("confirm_both_pattern_days") and len(df) >= 2:
        prev_avg = df["volume"].iloc[-(vol_period + 1) : -1].mean()
        prev_ratio = float(df["volume"].iloc[-2]) / prev_avg if prev_avg > 0 else 0.0
        vol_ok = vol_ok and prev_ratio >= vol_min
    gate_results.append(
        GateResult(
            gate="volume_confirmed",
            gate_type=_gate_type(cfg, "volume_confirmed"),
            passed=vol_ok,
            value=round(vol_ratio, 3),
            threshold=vol_min,
            message="volume confirmed" if vol_ok else f"volume insufficient ({vol_ratio:.2f}x)",
        )
    )

    sr_bars = cfg.get("timeframe", {}).get("sr_lookback_months", 24) * 21
    sr = find_support_resistance_zones(df, sr_bars)
    support = sr["nearest_support"]
    resistance = sr["nearest_resistance"]
    sr_exists = support is not None or resistance is not None
    gate_results.append(
        GateResult(
            gate="support_resistance_exists",
            gate_type=_gate_type(cfg, "support_resistance_exists"),
            passed=sr_exists,
            value={"support": support, "resistance": resistance},
            message="S/R levels found" if sr_exists else "no S/R levels",
        )
    )

    stop = pattern.stop_reference
    max_sr_dist = cfg.get("support_resistance", {}).get("max_stop_distance_pct", 4.0)
    if pattern.direction == Direction.LONG:
        zone = _zone_for_level(sr["support_zones"], support)
    elif pattern.direction == Direction.SHORT:
        zone = _zone_for_level(sr["resistance_zones"], resistance)
    else:
        zone = None
    aligned = zone is not None and stop_aligned(stop, zone, max_sr_dist)
    sr_distance = None
    if zone is not None:
        low, high = zone
        if stop < low:
            sr_distance = (low - stop) / stop * 100.0 if stop else None
        elif stop > high:
            sr_distance = (stop - high) / stop * 100.0 if stop else None
        else:
            sr_distance = 0.0
    gate_results.append(
        GateResult(
            gate="stop_aligned_with_sr",
            gate_type=_gate_type(cfg, "stop_aligned_with_sr"),
            passed=aligned,
            value=sr_distance,
            threshold=max_sr_dist,
            message="stop aligned with S/R" if aligned else "stop not aligned with S/R",
        )
    )

    dow_evidence = detect_dow_patterns(df)
    dow_ok = len(dow_evidence) > 0
    gate_results.append(
        GateResult(
            gate="dow_pattern",
            gate_type=_gate_type(cfg, "dow_pattern"),
            passed=dow_ok,
            value=dow_evidence,
            message=f"dow evidence: {', '.join(dow_evidence)}" if dow_evidence else "no dow evidence",
        )
    )

    entry = pattern.entry_reference
    min_rr = cfg.get("risk_reward", {}).get("minimum", 1.5)
    target = calc_target_from_sr(entry, stop, pattern.direction, support, resistance, min_rr)
    rr = calc_rr(entry, stop, target, pattern.direction) if target is not None else 0.0
    rr_ok = target is not None and rr >= min_rr
    gate_results.append(
        GateResult(
            gate="risk_reward_minimum",
            gate_type=_gate_type(cfg, "risk_reward_minimum"),
            passed=rr_ok,
            value=round(rr, 3) if target else None,
            threshold=min_rr,
            message=f"R:R {rr:.2f}" if rr_ok else f"R:R {rr:.2f} below {min_rr}",
        )
    )

    ind_cfg = cfg.get("indicators", {})
    rsi_series = compute_rsi(df["close"], ind_cfg.get("rsi", {}).get("period", 14))
    rsi_val = float(rsi_series.iloc[-1]) if not rsi_series.empty and pd.notna(rsi_series.iloc[-1]) else None

    macd_df = compute_macd(
        df["close"],
        fast=ind_cfg.get("macd", {}).get("fast", 12),
        slow=ind_cfg.get("macd", {}).get("slow", 26),
        signal=ind_cfg.get("macd", {}).get("signal", 9),
    )
    macd_label = macd_signal(macd_df)
    rsi_ok = _rsi_confirms(pattern.direction, rsi_val)
    macd_ok = _macd_confirms(pattern.direction, macd_label)

    gate_results.append(
        GateResult(
            gate="macd_confirms",
            gate_type=_gate_type(cfg, "macd_confirms"),
            passed=macd_ok,
            value=macd_label,
            message="MACD confirms" if macd_ok else "MACD does not confirm",
        )
    )
    gate_results.append(
        GateResult(
            gate="rsi_confirms",
            gate_type=_gate_type(cfg, "rsi_confirms"),
            passed=rsi_ok,
            value=rsi_val,
            message="RSI confirms" if rsi_ok else "RSI does not confirm",
        )
    )

    failed = _first_failed_mandatory(gate_results)
    if failed:
        return _reject(symbol, scan_date, gate_results, pattern, failed.message, failed.gate)

    return TradeAnalysis(
        symbol=symbol,
        scan_date=scan_date,
        decision=Decision.TRADE,
        pattern=pattern,
        gate_results=gate_results,
        trade_plan=None,
        rejection=None,
    )


def _reject(
    symbol: str,
    scan_date: date,
    gate_results: list[GateResult],
    pattern,
    message: str,
    failed_gate: str = "pattern_detected",
) -> TradeAnalysis:
    return TradeAnalysis(
        symbol=symbol,
        scan_date=scan_date,
        decision=Decision.NO_TRADE,
        pattern=pattern,
        gate_results=gate_results,
        rejection=RejectionReason(
            symbol=symbol,
            pattern=pattern.pattern if pattern else None,
            failed_gate=failed_gate,
            message=message,
            gate_results=gate_results,
        ),
    )
