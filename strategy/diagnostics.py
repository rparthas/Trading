"""Scan diagnostics — explain why symbols did or didn't qualify."""

from __future__ import annotations

from collections import Counter
from datetime import date

import pandas as pd

from config import load_strategy, load_universe
from data.loader import load_ohlcv
from models.trade import Decision
from patterns.candle_utils import range_pct
from patterns.detect import detect_best_pattern
from patterns.single_candle import _global_range_ok, detect_single_patterns
from patterns.trend import detect_prior_trend
from strategy.scanner import analyze_stock, lookback_start


def scan_funnel(scan_date: date, symbols: list[str] | None = None) -> dict:
    """Return counts at each stage of the scanning funnel."""
    cfg = load_strategy()
    symbols = symbols or load_universe()
    lookback = cfg.get("timeframe", {}).get("lookback_months", 12)
    start = lookback_start(scan_date, lookback)

    stages: Counter[str] = Counter()
    near_misses: list[dict] = []

    for symbol in symbols:
        try:
            df = load_ohlcv(symbol, start, scan_date)
        except Exception:
            stages["data_error"] += 1
            continue

        if df is None or df.empty:
            stages["no_data"] += 1
            continue

        df = df[df.index <= pd.Timestamp(scan_date)]
        candle = df.iloc[-1]
        rp = range_pct(candle)

        if not _global_range_ok(candle, cfg):
            stages["range_too_small_or_large"] += 1
            continue

        single = detect_single_patterns(df, cfg)
        best = detect_best_pattern(df, cfg)

        if best is None:
            if single and single.direction.value == "NEUTRAL":
                stages["neutral_pattern_skipped"] += 1
                near_misses.append(
                    {
                        "symbol": symbol,
                        "reason": f"{single.pattern} detected but not a standalone trade signal",
                        "range_pct": round(rp, 2),
                    }
                )
            else:
                stages["no_candlestick_shape"] += 1
            continue

        stages["pattern_detected"] += 1
        analysis = analyze_stock(symbol, scan_date, cfg=cfg)

        if analysis.decision == Decision.TRADE:
            stages["qualified_trade"] += 1
        elif analysis.rejection:
            gate = analysis.rejection.failed_gate
            stages[f"rejected_{gate}"] += 1
            near_misses.append(
                {
                    "symbol": symbol,
                    "pattern": best.pattern,
                    "reason": analysis.rejection.message,
                    "failed_gate": gate,
                    "range_pct": round(rp, 2),
                    "prior_trend": detect_prior_trend(df),
                }
            )

    return {
        "scan_date": scan_date.isoformat(),
        "symbols_scanned": len(symbols),
        "stages": dict(stages),
        "near_misses": near_misses[:20],
    }


def format_funnel_report(funnel: dict) -> str:
    lines = [
        f"SCAN FUNNEL — {funnel['scan_date']}",
        f"Symbols scanned: {funnel['symbols_scanned']}",
        "",
        "Where stocks dropped out:",
    ]
    labels = {
        "no_data": "No OHLCV data",
        "data_error": "Data fetch error",
        "range_too_small_or_large": "Last candle range outside 1–10% (TA.md filter)",
        "no_candlestick_shape": "Last 1–3 candles don't match any pattern shape",
        "neutral_pattern_skipped": "Doji/spinning top only (not standalone signals)",
        "pattern_detected": "Pattern found → entered qualification gates",
        "qualified_trade": "Passed all mandatory gates → TRADE",
    }
    for key, count in sorted(funnel["stages"].items(), key=lambda x: -x[1]):
        if key.startswith("rejected_"):
            label = f"Rejected at gate: {key.replace('rejected_', '')}"
        else:
            label = labels.get(key, key)
        lines.append(f"  {count:3d}  {label}")

    misses = funnel.get("near_misses") or []
    if misses:
        lines.append("")
        lines.append("Near misses (pattern found but failed a gate, or neutral skipped):")
        for m in misses[:10]:
            sym = m["symbol"]
            if "failed_gate" in m:
                lines.append(f"  {sym:12s} {m.get('pattern','?')} → {m['failed_gate']}: {m['reason']}")
            else:
                lines.append(f"  {sym:12s} → {m['reason']}")

    return "\n".join(lines)
