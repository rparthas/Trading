"""Normalize raw OHLCV DataFrames to a consistent schema."""

from __future__ import annotations

import pandas as pd

OHLCV_COLUMNS = ["open", "high", "low", "close", "volume"]


def normalize_ohlcv(df: pd.DataFrame, symbol: str | None = None) -> pd.DataFrame:
    """Return a clean OHLCV DataFrame indexed by date (no time component).

    - Lowercase column names
    - Float dtypes for price/volume
    - Sorted ascending by date
    - Duplicate dates removed (keep last)
    - Rows with missing OHLC dropped
    - Volume NaN filled with 0
    """
    if df is None or df.empty:
        return _empty_frame()

    out = df.copy()
    out.columns = [str(c).lower() for c in out.columns]

    # yfinance may use 'adj close' — we keep raw close only
    keep = [c for c in OHLCV_COLUMNS if c in out.columns]
    if len(keep) < 5:
        raise ValueError(f"Missing required OHLCV columns for {symbol or 'unknown'}: {list(out.columns)}")

    out = out[OHLCV_COLUMNS]

    if not isinstance(out.index, pd.DatetimeIndex):
        out.index = pd.to_datetime(out.index)

    # yfinance returns Asia/Kolkata tz-aware; strip to naive dates for consistent comparisons
    if out.index.tz is not None:
        out.index = out.index.tz_localize(None)

    out.index = out.index.normalize()
    out = out[~out.index.duplicated(keep="last")]
    out = out.sort_index()

    for col in ["open", "high", "low", "close"]:
        out[col] = pd.to_numeric(out[col], errors="coerce")

    out["volume"] = pd.to_numeric(out["volume"], errors="coerce").fillna(0.0)

    out = out.dropna(subset=["open", "high", "low", "close"])
    out = out.astype({"open": float, "high": float, "low": float, "close": float, "volume": float})

    # Sanity: high >= low
    invalid = out["high"] < out["low"]
    if invalid.any():
        out = out[~invalid]

    return out


def _naive_ts(ts: pd.Timestamp) -> pd.Timestamp:
    t = pd.Timestamp(ts)
    if t.tz is not None:
        t = t.tz_localize(None)
    return t.normalize()


def slice_date_range(df: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    """Return rows within [start, end] inclusive."""
    if df.empty:
        return df
    start_n = _naive_ts(start)
    end_n = _naive_ts(end)
    mask = (df.index >= start_n) & (df.index <= end_n)
    return df.loc[mask]


def _empty_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=OHLCV_COLUMNS, dtype=float)
