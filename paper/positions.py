"""Paper positions persisted in the local trade journal."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from typing import Any

import pandas as pd

from config import load_strategy
from data.loader import get_loader
from models.trade import TradePlan
from strategy.exit_rules import calc_pnl, check_bar_exit
from ui.journal import save_journal

PAPER_TYPE = "paper"
MANUAL_TYPE = "manual"


def split_journal_entries(entries: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    paper = [e for e in entries if e.get("type") == PAPER_TYPE]
    manual = [e for e in entries if e.get("type") != PAPER_TYPE]
    return paper, manual


def paper_open_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    paper, _ = split_journal_entries(entries)
    return [e for e in paper if e.get("status") == "open"]


def _max_holding_days(plan: TradePlan, cfg: dict | None = None) -> int:
    if plan.holding_period_days:
        return int(plan.holding_period_days[1])
    cfg = cfg or load_strategy()
    holding_cfg = cfg.get("timeframe", {}).get("holding_period_days", [3, 10])
    if isinstance(holding_cfg, list) and len(holding_cfg) >= 2:
        return int(holding_cfg[1])
    return 10


def _outcome_from_pnl(pnl: float) -> str:
    if pnl > 0:
        return "Win"
    if pnl < 0:
        return "Loss"
    return "Breakeven"


def open_paper_from_plan(
    entries: list[dict[str, Any]],
    plan: TradePlan,
    *,
    cfg: dict | None = None,
    notes: str = "",
) -> tuple[list[dict[str, Any]], str | None]:
    """Append an open paper position. Returns updated entries and an error message if blocked."""
    cfg = cfg or load_strategy()
    max_positions = int(cfg.get("risk", {}).get("max_open_positions", 5))
    open_now = paper_open_entries(entries)
    if len(open_now) >= max_positions:
        return entries, f"Already at max open paper positions ({max_positions})."
    if any(e["symbol"] == plan.symbol and e.get("status") == "open" for e in entries if e.get("type") == PAPER_TYPE):
        return entries, f"{plan.symbol} already has an open paper position."

    entry_date = plan.scan_date or date.today()
    holding_days = _max_holding_days(plan, cfg)
    payload: dict[str, Any] = {
        "id": str(uuid.uuid4()),
        "type": PAPER_TYPE,
        "status": "open",
        "symbol": plan.symbol,
        "trade_date": entry_date.isoformat(),
        "direction": plan.direction.value,
        "entry": float(plan.entry),
        "stop": float(plan.stop),
        "target": float(plan.target),
        "shares": int(plan.shares) if plan.shares > 0 else 1,
        "pattern": plan.pattern,
        "prior_trend": plan.prior_trend,
        "rr": float(plan.rr),
        "scan_date": entry_date.isoformat(),
        "max_holding_days": holding_days,
        "notes": notes.strip(),
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    updated = [payload, *entries]
    save_journal(updated)
    return updated, None


def _max_exit_ts(entry: dict[str, Any]) -> pd.Timestamp:
    entry_date = date.fromisoformat(entry["trade_date"])
    days = int(entry.get("max_holding_days", 10))
    return pd.Timestamp(entry_date) + pd.Timedelta(days=days)


def _bars_from_entry(symbol: str, entry_date: date, end: date, loader) -> pd.DataFrame:
    start = entry_date - timedelta(days=5)
    df = loader.load_ohlcv(symbol, start, end)
    if df is None or df.empty:
        return pd.DataFrame()
    return df.sort_index()


def _advance_open_entry(entry: dict[str, Any], loader, as_of: date) -> dict[str, Any]:
    entry_date = date.fromisoformat(entry["trade_date"])
    df = _bars_from_entry(entry["symbol"], entry_date, as_of, loader)
    if df.empty:
        return entry

    direction = entry["direction"]
    stop = float(entry["stop"])
    target = float(entry["target"])
    shares = int(entry["shares"])
    entry_price = float(entry["entry"])
    max_exit = _max_exit_ts(entry)

    for ts in df.index:
        bar_date = ts.date() if hasattr(ts, "date") else ts
        if bar_date < entry_date:
            continue
        bar = df.loc[ts]
        exit_price, reason = check_bar_exit(direction, stop, target, max_exit, bar, bar_date)
        if exit_price is None:
            continue
        pnl = calc_pnl(direction, entry_price, exit_price, shares)
        closed = dict(entry)
        closed["status"] = "closed"
        closed["exit_date"] = bar_date.isoformat()
        closed["exit_price"] = float(exit_price)
        closed["exit_reason"] = reason
        closed["pnl"] = round(pnl, 2)
        closed["pnl_pct"] = round(pnl / (entry_price * shares) * 100, 2) if shares else 0.0
        closed["outcome"] = _outcome_from_pnl(pnl)
        closed["closed_at"] = datetime.now().isoformat(timespec="seconds")
        return closed

    mark = float(df.iloc[-1]["close"])
    marked = dict(entry)
    marked["mark_price"] = mark
    marked["unrealized_pnl"] = round(calc_pnl(direction, entry_price, mark, shares), 2)
    marked["marked_at"] = as_of.isoformat()
    return marked


def refresh_paper_entries(
    entries: list[dict[str, Any]],
    *,
    as_of: date | None = None,
    loader=None,
) -> list[dict[str, Any]]:
    """Update open paper trades using EOD bars (stop, target, max holding)."""
    as_of = as_of or date.today()
    loader = loader or get_loader()
    updated: list[dict[str, Any]] = []
    for entry in entries:
        if entry.get("type") != PAPER_TYPE or entry.get("status") != "open":
            updated.append(entry)
            continue
        updated.append(_advance_open_entry(entry, loader, as_of))
    save_journal(updated)
    return updated


def close_paper_entry(
    entries: list[dict[str, Any]],
    entry_id: str,
    *,
    exit_price: float,
    reason: str = "manual",
    exit_date: date | None = None,
) -> list[dict[str, Any]]:
    exit_day = exit_date or date.today()
    updated: list[dict[str, Any]] = []
    for entry in entries:
        if entry.get("id") != entry_id:
            updated.append(entry)
            continue
        if entry.get("type") != PAPER_TYPE or entry.get("status") != "open":
            updated.append(entry)
            continue
        direction = entry["direction"]
        entry_price = float(entry["entry"])
        shares = int(entry["shares"])
        pnl = calc_pnl(direction, entry_price, exit_price, shares)
        closed = dict(entry)
        closed["status"] = "closed"
        closed["exit_date"] = exit_day.isoformat()
        closed["exit_price"] = float(exit_price)
        closed["exit_reason"] = reason
        closed["pnl"] = round(pnl, 2)
        closed["pnl_pct"] = round(pnl / (entry_price * shares) * 100, 2) if shares else 0.0
        closed["outcome"] = _outcome_from_pnl(pnl)
        closed["closed_at"] = datetime.now().isoformat(timespec="seconds")
        updated.append(closed)
    save_journal(updated)
    return updated
