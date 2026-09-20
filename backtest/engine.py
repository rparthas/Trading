"""Walk-forward backtest engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Callable

import pandas as pd

from models.trade import Decision, Direction
from strategy.scanner import analyze_stock, lookback_start


@dataclass
class BacktestTrade:
    symbol: str
    direction: str
    pattern: str
    entry_date: date
    exit_date: date
    entry_price: float
    exit_price: float
    stop: float
    target: float
    shares: int
    pnl: float
    pnl_pct: float
    exit_reason: str
    holding_days: int


@dataclass
class BacktestResult:
    trades: list[BacktestTrade] = field(default_factory=list)
    equity_curve: pd.Series = field(default_factory=pd.Series)
    initial_capital: float = 0.0


def run_backtest(
    symbols: list[str],
    start: date,
    end: date,
    cfg: dict,
    loader: Callable[[str, date, date], pd.DataFrame] | None = None,
    initial_capital: float | None = None,
) -> BacktestResult:
    """Walk-forward daily scan; enter next-day open; exit at stop/target/max holding."""
    capital = initial_capital or cfg.get("risk", {}).get("account_size", 1_000_000)
    load_fn = loader or (lambda s, a, b: pd.DataFrame())

    lookback = cfg.get("timeframe", {}).get("lookback_months", 12)
    holding_cfg = cfg.get("timeframe", {}).get("holding_period_days", [3, 10])
    max_holding = int(holding_cfg[1]) if isinstance(holding_cfg, list) else 10

    # Preload symbol data for simulation
    data_start = lookback_start(start, lookback + 1)
    symbol_data: dict[str, pd.DataFrame] = {}
    for symbol in symbols:
        try:
            df = load_fn(symbol, data_start, end)
            if df is not None and not df.empty:
                symbol_data[symbol] = df.sort_index()
        except Exception:
            continue

    if not symbol_data:
        return BacktestResult(initial_capital=capital)

    all_dates = sorted({d.date() for df in symbol_data.values() for d in df.index})
    trading_days = [d for d in all_dates if start <= d <= end]
    if not trading_days:
        return BacktestResult(initial_capital=capital)

    trades: list[BacktestTrade] = []
    equity = capital
    equity_points: list[tuple[date, float]] = [(trading_days[0], equity)]

    open_positions: list[dict] = []

    for i, scan_date in enumerate(trading_days):
        # Manage open positions using today's bar
        still_open: list[dict] = []
        for pos in open_positions:
            df = symbol_data.get(pos["symbol"])
            bar_ts = pd.Timestamp(scan_date)
            if df is None or bar_ts not in df.index:
                still_open.append(pos)
                continue

            bar = df.loc[bar_ts]
            exit_price, reason = _check_exit(pos, bar, scan_date)
            if exit_price is None:
                still_open.append(pos)
                continue

            pnl = _calc_pnl(pos, exit_price)
            equity += pnl
            trades.append(
                BacktestTrade(
                    symbol=pos["symbol"],
                    direction=pos["direction"],
                    pattern=pos["pattern"],
                    entry_date=pos["entry_date"],
                    exit_date=scan_date,
                    entry_price=pos["entry_price"],
                    exit_price=exit_price,
                    stop=pos["stop"],
                    target=pos["target"],
                    shares=pos["shares"],
                    pnl=pnl,
                    pnl_pct=pnl / (pos["entry_price"] * pos["shares"]) * 100 if pos["shares"] else 0,
                    exit_reason=reason,
                    holding_days=(scan_date - pos["entry_date"]).days,
                )
            )
        open_positions = still_open

        # Scan for new signals (skip last day — no next open)
        if i >= len(trading_days) - 1:
            equity_points.append((scan_date, equity))
            continue

        next_day = trading_days[i + 1]
        max_positions = cfg.get("risk", {}).get("max_open_positions", 5)
        slots = max_positions - len(open_positions)
        if slots <= 0:
            equity_points.append((scan_date, equity))
            continue

        for symbol in symbols:
            if slots <= 0:
                break
            if any(p["symbol"] == symbol for p in open_positions):
                continue

            def _loader(sym: str, s: date, e: date, _sym=symbol) -> pd.DataFrame:
                df = symbol_data.get(_sym, pd.DataFrame())
                if df.empty:
                    return df
                mask = (df.index >= pd.Timestamp(s)) & (df.index <= pd.Timestamp(e))
                return df.loc[mask]

            analysis = analyze_stock(symbol, scan_date, cfg=cfg, loader=_loader)
            if analysis.decision != Decision.TRADE or analysis.trade_plan is None:
                continue

            plan = analysis.trade_plan
            df = symbol_data.get(symbol)
            next_ts = pd.Timestamp(next_day)
            if df is None or next_ts not in df.index:
                continue

            entry_bar = df.loc[next_ts]
            entry_price = float(entry_bar["open"])
            shares = plan.shares if plan.shares > 0 else 1

            open_positions.append(
                {
                    "symbol": symbol,
                    "direction": plan.direction.value,
                    "pattern": plan.pattern,
                    "entry_date": next_day,
                    "entry_price": entry_price,
                    "stop": plan.stop,
                    "target": plan.target,
                    "shares": shares,
                    "max_exit_date": next_ts + pd.Timedelta(days=max_holding),
                }
            )
            slots -= 1

        equity_points.append((scan_date, equity))

    # Close remaining positions at last available close
    if trading_days:
        last_day = trading_days[-1]
        for pos in open_positions:
            df = symbol_data.get(pos["symbol"])
            if df is None or df.empty:
                continue
            available = df[df.index <= pd.Timestamp(last_day)]
            if available.empty:
                continue
            exit_price = float(available.iloc[-1]["close"])
            pnl = _calc_pnl(pos, exit_price)
            equity += pnl
            exit_date = available.index[-1].date()
            trades.append(
                BacktestTrade(
                    symbol=pos["symbol"],
                    direction=pos["direction"],
                    pattern=pos["pattern"],
                    entry_date=pos["entry_date"],
                    exit_date=exit_date,
                    entry_price=pos["entry_price"],
                    exit_price=exit_price,
                    stop=pos["stop"],
                    target=pos["target"],
                    shares=pos["shares"],
                    pnl=pnl,
                    pnl_pct=pnl / (pos["entry_price"] * pos["shares"]) * 100 if pos["shares"] else 0,
                    exit_reason="end_of_backtest",
                    holding_days=(exit_date - pos["entry_date"]).days,
                )
            )

    equity_series = pd.Series(
        [v for _, v in equity_points],
        index=pd.DatetimeIndex([d for d, _ in equity_points]),
        name="equity",
    )

    return BacktestResult(trades=trades, equity_curve=equity_series, initial_capital=capital)


def _calc_pnl(pos: dict, exit_price: float) -> float:
    if pos["direction"] == Direction.LONG.value:
        return (exit_price - pos["entry_price"]) * pos["shares"]
    return (pos["entry_price"] - exit_price) * pos["shares"]


def _check_exit(pos: dict, bar: pd.Series, current_date: date) -> tuple[float | None, str]:
    high = float(bar["high"])
    low = float(bar["low"])
    close = float(bar["close"])

    max_exit = pd.Timestamp(pos["max_exit_date"])
    if pd.Timestamp(current_date) >= max_exit:
        return close, "max_holding"

    if pos["direction"] == Direction.LONG.value:
        if low <= pos["stop"]:
            return pos["stop"], "stop"
        if high >= pos["target"]:
            return pos["target"], "target"
    else:
        if high >= pos["stop"]:
            return pos["stop"], "stop"
        if low <= pos["target"]:
            return pos["target"], "target"

    return None, ""
