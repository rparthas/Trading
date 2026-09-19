"""Unit tests for Pydantic models (Milestone 1)."""

from datetime import date

from models.trade import (
    Decision,
    Direction,
    GateResult,
    GateType,
    PatternResult,
    TradePlan,
)


def test_pattern_result_schema():
    p = PatternResult(
        pattern="bullish_hammer",
        direction=Direction.LONG,
        strength=0.82,
        candle_index=-1,
        entry_reference=1455.0,
        stop_reference=1418.0,
        validation={"body_ratio": 0.18},
    )
    assert p.direction == Direction.LONG
    assert p.strength == 0.82


def test_trade_plan_schema():
    plan = TradePlan(
        symbol="RELIANCE",
        direction=Direction.LONG,
        pattern="bullish_hammer",
        prior_trend="downtrend",
        entry=1455.0,
        stop=1418.0,
        target=1520.0,
        rr=1.76,
        volume_ratio=1.42,
        shares=135,
        scan_date=date(2026, 9, 19),
    )
    assert plan.decision == Decision.TRADE
    assert plan.rr >= 1.5


def test_gate_result_mandatory():
    g = GateResult(
        gate="volume_confirmed",
        gate_type=GateType.MANDATORY,
        passed=False,
        value=0.74,
        threshold=1.0,
        message="volume insufficient",
    )
    assert not g.passed
