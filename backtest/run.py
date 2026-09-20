"""Backtest CLI entry point."""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

# Allow `python backtest/run.py` without installing the package
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import load_strategy, load_universe
from data.loader import load_ohlcv

from backtest.engine import run_backtest
from backtest.reports import print_summary, save_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run strategy backtest")
    parser.add_argument("--start", required=True, help="Start date YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="End date YYYY-MM-DD")
    parser.add_argument("--symbols", nargs="*", help="Optional symbol list (default: universe)")
    args = parser.parse_args()

    cfg = load_strategy()
    symbols = args.symbols or load_universe()
    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end)

    result = run_backtest(symbols, start, end, cfg, loader=load_ohlcv)
    print_summary(result)
    equity_path, trades_path = save_report(result)
    print(f"Equity curve saved to {equity_path}")
    print(f"Trades log saved to {trades_path}")


if __name__ == "__main__":
    main()
