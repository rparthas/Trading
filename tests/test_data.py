"""Tests for data layer (Milestone 2)."""

from datetime import date

import pandas as pd

from data.cache import OHLCVCache
from data.normalizer import normalize_ohlcv, slice_date_range


def _sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Open": [100.0, 101.0, 102.0],
            "High": [105.0, 106.0, 107.0],
            "Low": [99.0, 100.0, 101.0],
            "Close": [104.0, 105.0, 106.0],
            "Volume": [1000, 1100, 1200],
        },
        index=pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-03"]),
    )


def test_normalize_ohlcv_lowercase_and_sort(tmp_path):
    df = normalize_ohlcv(_sample_df(), symbol="TEST")
    assert list(df.columns) == ["open", "high", "low", "close", "volume"]
    assert df.index.is_monotonic_increasing
    assert df.iloc[-1]["close"] == 106.0


def test_slice_date_range():
    df = normalize_ohlcv(_sample_df())
    sliced = slice_date_range(df, pd.Timestamp("2026-01-02"), pd.Timestamp("2026-01-03"))
    assert len(sliced) == 2


def test_cache_read_write(tmp_path):
    cache = OHLCVCache(tmp_path)
    df = normalize_ohlcv(_sample_df())
    cache.write("RELIANCE", df, source="test")
    loaded = cache.read("RELIANCE")
    assert loaded is not None
    assert len(loaded) == 3
    meta = cache.metadata("RELIANCE")
    assert meta["source"] == "test"


def test_cache_covers_range(tmp_path):
    cache = OHLCVCache(tmp_path)
    cache.write("TCS", normalize_ohlcv(_sample_df()))
    assert cache.covers_range("TCS", pd.Timestamp("2026-01-01"), pd.Timestamp("2026-01-03"))
    assert not cache.covers_range("TCS", pd.Timestamp("2025-01-01"), pd.Timestamp("2026-01-03"))
