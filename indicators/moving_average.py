"""Simple and exponential moving averages."""

from __future__ import annotations

import pandas as pd


def add_sma(df: pd.DataFrame, period: int, column: str = "close", name: str | None = None) -> pd.DataFrame:
    out = df.copy()
    col_name = name or f"sma_{period}"
    out[col_name] = out[column].rolling(period).mean()
    return out


def add_ema(df: pd.DataFrame, period: int, column: str = "close", name: str | None = None) -> pd.DataFrame:
    out = df.copy()
    col_name = name or f"ema_{period}"
    out[col_name] = out[column].ewm(span=period, adjust=False).mean()
    return out
