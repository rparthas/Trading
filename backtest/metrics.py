"""Backtest performance metrics."""

from __future__ import annotations

import math

import pandas as pd

from backtest.engine import BacktestTrade


def win_rate(trades: list[BacktestTrade]) -> float:
    if not trades:
        return 0.0
    wins = sum(1 for t in trades if t.pnl > 0)
    return wins / len(trades)


def profit_factor(trades: list[BacktestTrade]) -> float:
    gross_profit = sum(t.pnl for t in trades if t.pnl > 0)
    gross_loss = abs(sum(t.pnl for t in trades if t.pnl < 0))
    if gross_loss == 0:
        return float("inf") if gross_profit > 0 else 0.0
    return gross_profit / gross_loss


def max_drawdown(equity_curve: pd.Series) -> float:
    if equity_curve is None or equity_curve.empty:
        return 0.0
    peak = equity_curve.cummax()
    drawdown = (equity_curve - peak) / peak
    return float(abs(drawdown.min()))


def expectancy(trades: list[BacktestTrade]) -> float:
    if not trades:
        return 0.0
    return sum(t.pnl for t in trades) / len(trades)


def sharpe(equity_curve: pd.Series, periods_per_year: int = 252) -> float:
    if equity_curve is None or len(equity_curve) < 2:
        return 0.0
    returns = equity_curve.pct_change().dropna()
    if returns.empty or returns.std() == 0:
        return 0.0
    return float(returns.mean() / returns.std() * math.sqrt(periods_per_year))


def summarize(trades: list[BacktestTrade], equity_curve: pd.Series) -> dict[str, float]:
    return {
        "total_trades": len(trades),
        "win_rate": win_rate(trades),
        "profit_factor": profit_factor(trades),
        "max_drawdown": max_drawdown(equity_curve),
        "expectancy": expectancy(trades),
        "sharpe": sharpe(equity_curve),
        "total_pnl": sum(t.pnl for t in trades),
        "avg_holding_days": sum(t.holding_days for t in trades) / len(trades) if trades else 0.0,
    }
