"""Unified pattern detection entry point."""

from __future__ import annotations

from typing import Any

import pandas as pd

from models.trade import Direction, PatternResult
from patterns.multi_candle import detect_multi_patterns
from patterns.single_candle import detect_single_patterns


def _standalone_allowed(pattern: str, cfg: dict[str, Any]) -> bool:
    pattern_cfg = cfg.get("patterns", {}).get(pattern, {})
    if pattern_cfg.get("direction") == "NEUTRAL":
        return bool(pattern_cfg.get("standalone_trade", False))
    return True


def detect_best_pattern(df: pd.DataFrame, cfg: dict[str, Any]) -> PatternResult | None:
    """Try multi-candle patterns first, then single-candle; skip neutral standalones."""
    multi = detect_multi_patterns(df, cfg)
    if multi is not None and multi.direction != Direction.NEUTRAL:
        return multi

    single = detect_single_patterns(df, cfg)
    if single is None:
        return None
    if single.direction == Direction.NEUTRAL and not _standalone_allowed(single.pattern, cfg):
        return None
    return single
