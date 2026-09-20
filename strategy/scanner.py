"""Universe scanner with audit trail."""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from pathlib import Path
from typing import Callable

import pandas as pd

from config import load_strategy, load_universe
from data.loader import load_ohlcv
from models.trade import Decision, ScanResult, TradeAnalysis
from strategy.qualification import qualify_trade
from strategy.trade_plan import build_trade_plan

PROJECT_ROOT = Path(__file__).parent.parent
AUDIT_DIR = PROJECT_ROOT / "data" / "cache" / "audits"


def lookback_start(scan_date: date, months: int) -> date:
    """Return start date using calendar-month lookback."""
    return (pd.Timestamp(scan_date) - pd.DateOffset(months=months)).date()


def analyze_stock(
    symbol: str,
    scan_date: date,
    cfg: dict | None = None,
    loader: Callable[[str, date, date], pd.DataFrame] | None = None,
) -> TradeAnalysis:
    """Load OHLCV and qualify a single symbol for scan_date."""
    cfg = cfg or load_strategy()
    lookback = cfg.get("timeframe", {}).get("lookback_months", 12)
    start = lookback_start(scan_date, lookback)
    load_fn = loader or load_ohlcv

    try:
        df = load_fn(symbol, start, scan_date)
    except Exception:
        df = pd.DataFrame()

    analysis = qualify_trade(symbol, df, cfg, scan_date)
    if analysis.decision == Decision.TRADE:
        plan = build_trade_plan(analysis, cfg)
        if plan is None:
            analysis.decision = Decision.NO_TRADE
        else:
            analysis.trade_plan = plan
    return analysis


def scan_universe(
    scan_date: date,
    cfg: dict | None = None,
    symbols: list[str] | None = None,
    loader: Callable[[str, date, date], pd.DataFrame] | None = None,
    write_audit: bool = True,
) -> ScanResult:
    """Scan all universe symbols and optionally write audit JSON."""
    cfg = cfg or load_strategy()
    symbols = symbols or load_universe()

    qualified: list = []
    rejected: list = []
    no_pattern: list[str] = []

    for symbol in symbols:
        analysis = analyze_stock(symbol, scan_date, cfg=cfg, loader=loader)
        if analysis.pattern is None:
            no_pattern.append(symbol)
        elif analysis.decision == Decision.TRADE and analysis.trade_plan:
            qualified.append(analysis.trade_plan)
        elif analysis.rejection:
            rejected.append(analysis.rejection)

    result = ScanResult(
        scan_date=scan_date,
        universe=cfg.get("universe", {}).get("type", "nifty50"),
        candidates=len(symbols) - len(no_pattern),
        qualified=qualified,
        rejected=rejected,
        no_pattern=no_pattern,
        strategy_version=cfg.get("version", "1.0.0"),
        data_timestamp=datetime.now(),
    )

    if write_audit:
        _write_audit(result)

    return result


def _write_audit(result: ScanResult) -> Path:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    path = AUDIT_DIR / f"scan_{result.scan_date.isoformat()}.json"
    payload = json.loads(result.model_dump_json())
    path.write_text(json.dumps(payload, indent=2, default=str))
    return path


def _print_report(result: ScanResult, verbose: bool = False) -> None:
    print(f"DAILY TRADE SCAN — {result.universe.upper()} — {result.scan_date:%d %b %Y}")
    print(f"Candidates: {result.candidates} | Qualified: {len(result.qualified)}")
    print()

    if verbose or (not result.qualified and not result.rejected):
        from strategy.diagnostics import format_funnel_report, scan_funnel

        print(format_funnel_report(scan_funnel(result.scan_date)))
        print()

    for plan in result.qualified:
        print(f"{plan.symbol:10s}  {plan.direction.value:5s}  [TRADE]")
        print(f"  Pattern: {plan.pattern} | Prior trend: {plan.prior_trend}")
        print(
            f"  Volume: {plan.volume_ratio:.2f}x | R:R: {plan.rr:.2f} | "
            f"Entry: {plan.entry:.2f} | Stop: {plan.stop:.2f} | Target: {plan.target:.2f} | "
            f"Size: {plan.shares} shares"
        )
        print()

    if result.rejected:
        print("REJECTED:")
        for r in result.rejected:
            print(f"  {r.symbol:10s} → {r.message}")
        print()

    if result.no_pattern and not verbose:
        print(f"NO PATTERN: {len(result.no_pattern)} symbols")
        print("  Tip: run with --verbose to see why (range filter, shape mismatch, gate rejections)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan universe for trade setups")
    parser.add_argument("--date", required=True, help="Scan date (YYYY-MM-DD)")
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show funnel: where each symbol dropped out",
    )
    args = parser.parse_args()

    scan_date = date.fromisoformat(args.date)
    result = scan_universe(scan_date)
    _print_report(result, verbose=args.verbose)


if __name__ == "__main__":
    main()
