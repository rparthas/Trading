"""Tests for strategy layer (M4) — no network required."""

from datetime import date, timedelta

import pandas as pd

from config import load_strategy
from models.trade import Decision, Direction
from strategy.position_sizing import calc_position_size
from strategy.qualification import qualify_trade
from strategy.risk import calc_rr, calc_target_from_sr
from strategy.scanner import analyze_stock, scan_universe
from strategy.trade_plan import build_trade_plan


def _make_downtrend_df(n: int = 60, base: float = 100.0) -> pd.DataFrame:
    dates = pd.bdate_range(end=date(2026, 9, 19), periods=n)
    closes = [base - i * 0.5 for i in range(n)]
    rows = []
    for i, c in enumerate(closes):
        o = c + 0.2
        h = c + 0.5
        l = c - 0.5
        vol = 1_000_000 if i < n - 1 else 2_500_000
        rows.append({"open": o, "high": h, "low": l, "close": c, "volume": vol})
    df = pd.DataFrame(rows, index=dates)
    # Hammer on last bar
    last = df.iloc[-1]
    df.iloc[-1, df.columns.get_loc("open")] = last["close"] - 0.1
    df.iloc[-1, df.columns.get_loc("close")] = last["close"]
    df.iloc[-1, df.columns.get_loc("low")] = last["close"] - 3.0
    df.iloc[-1, df.columns.get_loc("high")] = last["close"] + 0.2
    df.iloc[-1, df.columns.get_loc("volume")] = 3_000_000
    return df


def test_calc_rr_long():
    rr = calc_rr(100.0, 95.0, 110.0, Direction.LONG)
    assert rr == 2.0


def test_calc_rr_short():
    rr = calc_rr(100.0, 105.0, 90.0, Direction.SHORT)
    assert rr == 2.0


def test_calc_target_from_sr_long():
    target = calc_target_from_sr(100.0, 95.0, Direction.LONG, 90.0, 110.0, 1.5)
    assert target == 110.0
    assert calc_rr(100.0, 95.0, target, Direction.LONG) >= 1.5


def test_calc_position_size():
    shares = calc_position_size(1_000_000, 0.5, 100.0, 95.0)
    assert shares == 1000


def test_qualify_trade_no_data():
    cfg = load_strategy()
    analysis = qualify_trade("TEST", pd.DataFrame(), cfg, date(2026, 9, 19))
    assert analysis.decision == Decision.NO_TRADE


def test_qualify_and_build_plan_with_synthetic_data():
    cfg = load_strategy()
    df = _make_downtrend_df()
    analysis = qualify_trade("TEST", df, cfg, date(2026, 9, 19))
    if analysis.decision == Decision.TRADE:
        plan = build_trade_plan(analysis, cfg)
        assert plan is not None
        assert plan.shares > 0
        assert plan.rr >= cfg["risk_reward"]["minimum"]


def test_scan_universe_mock_loader(tmp_path):
    cfg = load_strategy()
    df = _make_downtrend_df()

    def mock_loader(symbol: str, start: date, end: date) -> pd.DataFrame:
        return df[(df.index >= pd.Timestamp(start)) & (df.index <= pd.Timestamp(end))]

    result = scan_universe(
        date(2026, 9, 19),
        cfg=cfg,
        symbols=["TEST"],
        loader=mock_loader,
        write_audit=False,
    )
    assert result.scan_date == date(2026, 9, 19)
    assert len(result.no_pattern) + len(result.qualified) + len(result.rejected) <= 1


def test_analyze_stock_empty_loader():
    cfg = load_strategy()

    def empty_loader(symbol: str, start: date, end: date) -> pd.DataFrame:
        return pd.DataFrame()

    analysis = analyze_stock("TEST", date(2026, 9, 19), cfg=cfg, loader=empty_loader)
    assert analysis.decision == Decision.NO_TRADE
