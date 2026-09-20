"""Format engine outputs for Streamlit display — no business logic."""

from __future__ import annotations

from models.trade import ScanResult, TradeAnalysis, TradePlan


def scan_result_rows(scan: ScanResult) -> list[dict]:
    rows: list[dict] = []
    for plan in scan.qualified:
        rows.append(
            {
                "Symbol": plan.symbol,
                "Decision": plan.decision.value,
                "Pattern": plan.pattern,
                "Direction": plan.direction.value,
                "Prior trend": plan.prior_trend,
                "Volume": plan.volume_ratio,
                "R:R": plan.rr,
                "Entry": plan.entry,
                "Stop": plan.stop,
                "Target": plan.target,
                "Detail": "",
            }
        )
    for rejection in scan.rejected:
        rows.append(
            {
                "Symbol": rejection.symbol,
                "Decision": "REJECTED",
                "Pattern": rejection.pattern or "",
                "Direction": "",
                "Prior trend": "",
                "Volume": "",
                "R:R": "",
                "Entry": "",
                "Stop": "",
                "Target": "",
                "Detail": f"{rejection.failed_gate}: {rejection.message}",
            }
        )
    for symbol in scan.no_pattern:
        rows.append(
            {
                "Symbol": symbol,
                "Decision": "NO_PATTERN",
                "Pattern": "",
                "Direction": "",
                "Prior trend": "",
                "Volume": "",
                "R:R": "",
                "Entry": "",
                "Stop": "",
                "Target": "",
                "Detail": "No recognizable pattern",
            }
        )
    return rows


def analysis_gate_rows(analysis: TradeAnalysis) -> list[dict]:
    return [
        {
            "Gate": gate.gate,
            "Type": gate.gate_type.value,
            "Passed": gate.passed,
            "Value": gate.value,
            "Threshold": gate.threshold,
            "Message": gate.message,
        }
        for gate in analysis.gate_results
    ]


def trade_plan_dict(plan: TradePlan) -> dict[str, object]:
    return {
        "Symbol": plan.symbol,
        "Direction": plan.direction.value,
        "Pattern": plan.pattern,
        "Prior trend": plan.prior_trend,
        "Entry": plan.entry,
        "Stop": plan.stop,
        "Target": plan.target,
        "R:R": plan.rr,
        "Volume ratio": plan.volume_ratio,
        "Support": plan.support,
        "Resistance": plan.resistance,
        "Shares": plan.shares,
        "Holding period (days)": f"{plan.holding_period_days[0]}–{plan.holding_period_days[1]}",
        "MACD": plan.macd,
        "RSI": plan.rsi,
    }
