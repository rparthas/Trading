"""Paper trading journal integration."""

from datetime import date

import pandas as pd
import pytest

from models.trade import Direction, TradePlan
from paper.positions import open_paper_from_plan, refresh_paper_entries
from strategy.exit_rules import calc_pnl


def _sample_plan() -> TradePlan:
    return TradePlan(
        symbol="RELIANCE",
        direction=Direction.LONG,
        pattern="bullish_hammer",
        prior_trend="downtrend",
        entry=100.0,
        stop=95.0,
        target=110.0,
        rr=2.0,
        volume_ratio=1.5,
        shares=10,
        scan_date=date(2024, 1, 2),
        holding_period_days=(3, 5),
    )


@pytest.fixture(autouse=True)
def isolated_journal(tmp_path, monkeypatch):
    path = tmp_path / "trades.json"
    monkeypatch.setattr("ui.journal.JOURNAL_PATH", path)


def test_open_paper_blocks_duplicate_symbol():
    plan = _sample_plan()
    entries, err = open_paper_from_plan([], plan)
    assert err is None
    assert len(entries) == 1
    assert entries[0]["status"] == "open"

    entries2, err2 = open_paper_from_plan(entries, plan)
    assert err2 is not None
    assert "already" in err2.lower()
    assert len(entries2) == len(entries)


def test_refresh_closes_on_stop_hit():
    plan = _sample_plan()
    entries, _ = open_paper_from_plan([], plan)

    index = pd.DatetimeIndex(
        [
            pd.Timestamp("2024-01-02"),
            pd.Timestamp("2024-01-03"),
        ]
    )
    df = pd.DataFrame(
        {
            "open": [100.0, 99.0],
            "high": [101.0, 100.0],
            "low": [94.0, 98.0],
            "close": [100.0, 99.0],
        },
        index=index,
    )

    class StubLoader:
        def load_ohlcv(self, symbol: str, start: date, end: date) -> pd.DataFrame:
            return df

    refreshed = refresh_paper_entries(entries, as_of=date(2024, 1, 3), loader=StubLoader())
    closed = refreshed[0]
    assert closed["status"] == "closed"
    assert closed["exit_reason"] == "stop"
    assert closed["exit_price"] == 95.0
    assert closed["pnl"] == calc_pnl("LONG", 100.0, 95.0, 10)
