"""Trade qualification and scanning."""

from strategy.position_sizing import calc_position_size
from strategy.qualification import qualify_trade
from strategy.risk import calc_rr, calc_target_from_sr
from strategy.trade_plan import build_trade_plan

__all__ = [
    "calc_rr",
    "calc_target_from_sr",
    "calc_position_size",
    "qualify_trade",
    "build_trade_plan",
    "analyze_stock",
    "scan_universe",
]


def __getattr__(name: str):
    if name in ("analyze_stock", "scan_universe"):
        from strategy.scanner import analyze_stock, scan_universe

        return analyze_stock if name == "analyze_stock" else scan_universe
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
