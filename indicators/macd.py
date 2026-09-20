"""MACD indicator and signal classification."""

from __future__ import annotations

import pandas as pd


def compute_macd(
    series: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> pd.DataFrame:
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return pd.DataFrame({"macd": macd_line, "signal": signal_line, "histogram": histogram})


def macd_signal(df: pd.DataFrame) -> str:
    """Classify latest MACD vs signal line."""
    if "macd" not in df.columns or "signal" not in df.columns:
        raise ValueError("DataFrame must include macd and signal columns")
    if df.empty or pd.isna(df["macd"].iloc[-1]) or pd.isna(df["signal"].iloc[-1]):
        return "neutral"

    macd_val = float(df["macd"].iloc[-1])
    signal_val = float(df["signal"].iloc[-1])
    if macd_val > signal_val:
        return "bullish"
    if macd_val < signal_val:
        return "bearish"
    return "neutral"
