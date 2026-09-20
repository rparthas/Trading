"""Tests for backtest layer (M5) — no network required."""

from datetime import date

import pandas as pd

from backtest.engine import run_backtest
from backtest.metrics import expectancy, max_drawdown, profit_factor, sharpe, win_rate
from backtest.reports import print_summary, save_report
from config import load_strategy


def _synthetic_symbol_data(start: date, end: date) -> pd.DataFrame:
    dates = pd.bdate_range(start=start, end=end)
    rows = []
    price = 100.0
    for i, d in enumerate(dates):
        price += 0.1 if i % 5 else -0.5
        rows.append(
            {
                "open": price,
                "high": price + 1.0,
                "low": price - 1.0,
                "close": price + 0.2,
                "volume": 1_000_000 + i * 1000,
            }
        )
    return pd.DataFrame(rows, index=dates)


def test_run_backtest_empty_data():
    cfg = load_strategy()

    def empty_loader(symbol: str, start: date, end: date) -> pd.DataFrame:
        return pd.DataFrame()

    result = run_backtest(["TEST"], date(2026, 1, 1), date(2026, 3, 1), cfg, loader=empty_loader)
    assert result.trades == []
    assert result.initial_capital > 0


def test_run_backtest_with_data(tmp_path):
    cfg = load_strategy()
    data = _synthetic_symbol_data(date(2025, 1, 1), date(2026, 9, 30))

    def mock_loader(symbol: str, start: date, end: date) -> pd.DataFrame:
        return data[(data.index >= pd.Timestamp(start)) & (data.index <= pd.Timestamp(end))]

    result = run_backtest(
        ["TEST"],
        date(2026, 6, 1),
        date(2026, 9, 1),
        cfg,
        loader=mock_loader,
        initial_capital=100_000,
    )
    assert result.equity_curve is not None
    assert len(result.equity_curve) >= 1


def test_metrics_on_empty():
    assert win_rate([]) == 0.0
    assert profit_factor([]) == 0.0
    assert expectancy([]) == 0.0
    assert max_drawdown(pd.Series()) == 0.0
    assert sharpe(pd.Series()) == 0.0


def test_save_report(tmp_path):
    cfg = load_strategy()
    data = _synthetic_symbol_data(date(2025, 1, 1), date(2026, 9, 30))

    def mock_loader(symbol: str, start: date, end: date) -> pd.DataFrame:
        return data[(data.index >= pd.Timestamp(start)) & (data.index <= pd.Timestamp(end))]

    result = run_backtest(
        ["TEST"],
        date(2026, 6, 1),
        date(2026, 8, 1),
        cfg,
        loader=mock_loader,
    )
    print_summary(result)
    equity_path, trades_path = save_report(result, output_dir=tmp_path)
    assert trades_path.exists()
