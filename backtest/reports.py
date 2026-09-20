"""Backtest report generation."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from backtest.engine import BacktestResult
from backtest.metrics import summarize

OUTPUT_DIR = Path(__file__).parent / "output"


def print_summary(result: BacktestResult) -> None:
    stats = summarize(result.trades, result.equity_curve)
    print("=" * 60)
    print("BACKTEST SUMMARY")
    print("=" * 60)
    print(f"Initial capital:  {result.initial_capital:,.2f}")
    print(f"Final equity:     {float(result.equity_curve.iloc[-1]) if not result.equity_curve.empty else result.initial_capital:,.2f}")
    print(f"Total trades:     {stats['total_trades']}")
    print(f"Win rate:         {stats['win_rate']:.1%}")
    print(f"Profit factor:    {stats['profit_factor']:.2f}")
    print(f"Expectancy:       {stats['expectancy']:,.2f}")
    print(f"Max drawdown:     {stats['max_drawdown']:.1%}")
    print(f"Sharpe ratio:     {stats['sharpe']:.2f}")
    print(f"Avg holding days: {stats['avg_holding_days']:.1f}")
    print("=" * 60)


def save_report(result: BacktestResult, output_dir: Path | None = None) -> tuple[Path, Path]:
    """Save equity curve PNG and trades CSV."""
    out = output_dir or OUTPUT_DIR
    out.mkdir(parents=True, exist_ok=True)

    trades_path = out / "trades.csv"
    rows = [
        {
            "symbol": t.symbol,
            "direction": t.direction,
            "pattern": t.pattern,
            "entry_date": t.entry_date,
            "exit_date": t.exit_date,
            "entry_price": t.entry_price,
            "exit_price": t.exit_price,
            "stop": t.stop,
            "target": t.target,
            "shares": t.shares,
            "pnl": t.pnl,
            "pnl_pct": t.pnl_pct,
            "exit_reason": t.exit_reason,
            "holding_days": t.holding_days,
        }
        for t in result.trades
    ]
    pd.DataFrame(rows).to_csv(trades_path, index=False)

    equity_path = out / "equity_curve.png"
    if not result.equity_curve.empty:
        fig, ax = plt.subplots(figsize=(10, 5))
        result.equity_curve.plot(ax=ax, title="Equity Curve")
        ax.set_ylabel("Equity")
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        fig.savefig(equity_path)
        plt.close(fig)
    else:
        equity_path.write_bytes(b"")

    return equity_path, trades_path
