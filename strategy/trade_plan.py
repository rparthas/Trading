"""Build TradePlan from qualified TradeAnalysis."""

from __future__ import annotations

from datetime import datetime

from models.trade import Decision, GateType, TradeAnalysis, TradePlan
from strategy.position_sizing import calc_position_size
from strategy.risk import calc_rr, calc_target_from_sr


def _gate_value(analysis: TradeAnalysis, gate: str):
    for g in analysis.gate_results:
        if g.gate == gate:
            return g
    return None


def build_trade_plan(analysis: TradeAnalysis, cfg: dict) -> TradePlan | None:
    """Convert a qualified TradeAnalysis into a TradePlan with position sizing."""
    if analysis.decision != Decision.TRADE or analysis.pattern is None:
        return None

    pattern = analysis.pattern
    entry = pattern.entry_reference
    stop = pattern.stop_reference

    sr_gate = _gate_value(analysis, "support_resistance_exists")
    support = None
    resistance = None
    if sr_gate and isinstance(sr_gate.value, dict):
        support = sr_gate.value.get("support")
        resistance = sr_gate.value.get("resistance")

    min_rr = cfg.get("risk_reward", {}).get("minimum", 1.5)
    target = calc_target_from_sr(entry, stop, pattern.direction, support, resistance, min_rr)
    if target is None:
        return None

    rr = calc_rr(entry, stop, target, pattern.direction)
    vol_gate = _gate_value(analysis, "volume_confirmed")
    volume_ratio = float(vol_gate.value) if vol_gate and vol_gate.value is not None else 0.0

    trend_gate = _gate_value(analysis, "prior_trend")
    prior_trend = str(trend_gate.value) if trend_gate and trend_gate.value else "unknown"

    macd_gate = _gate_value(analysis, "macd_confirms")
    rsi_gate = _gate_value(analysis, "rsi_confirms")
    macd_label = str(macd_gate.value) if macd_gate and macd_gate.value else None
    rsi_val = float(rsi_gate.value) if rsi_gate and rsi_gate.value is not None else None

    multiplier = 1.0
    risk_cfg = cfg.get("risk", {})
    if macd_gate and rsi_gate and macd_gate.passed and rsi_gate.passed:
        multiplier = risk_cfg.get("indicator_confirmation_size_multiplier", 1.0)

    shares = calc_position_size(
        account=risk_cfg.get("account_size", 1_000_000),
        risk_pct=risk_cfg.get("max_risk_per_trade_pct", 0.5),
        entry=entry,
        stop=stop,
        multiplier=multiplier,
        max_position_pct=risk_cfg.get("max_position_pct"),
    )

    holding = cfg.get("timeframe", {}).get("holding_period_days", [3, 10])
    if isinstance(holding, list) and len(holding) >= 2:
        holding_period = (int(holding[0]), int(holding[1]))
    else:
        holding_period = (3, 10)

    return TradePlan(
        symbol=analysis.symbol,
        direction=pattern.direction,
        pattern=pattern.pattern,
        prior_trend=prior_trend,
        entry=entry,
        stop=stop,
        target=target,
        rr=rr,
        volume_ratio=volume_ratio,
        support=support,
        resistance=resistance,
        shares=shares,
        holding_period_days=holding_period,
        macd=macd_label,
        rsi=rsi_val,
        decision=Decision.TRADE,
        strategy_version=cfg.get("version", "1.0.0"),
        data_timestamp=datetime.now(),
        scan_date=analysis.scan_date,
    )
