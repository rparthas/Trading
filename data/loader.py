"""Data loader factory with optional caching."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Protocol

import pandas as pd

from config import load_strategy
from data.adapters.yfinance_loader import YFinanceLoader
from data.cache import OHLCVCache
from data.normalizer import normalize_ohlcv, slice_date_range

PROJECT_ROOT = Path(__file__).parent.parent


class DataLoader(Protocol):
    def load_ohlcv(self, symbol: str, start: date, end: date) -> pd.DataFrame: ...


class CachedDataLoader:
    """Wraps a DataLoader with parquet caching."""

    def __init__(self, loader: DataLoader, cache: OHLCVCache, source: str = "yfinance") -> None:
        self.loader = loader
        self.cache = cache
        self.source = source

    def load_ohlcv(self, symbol: str, start: date, end: date) -> pd.DataFrame:
        start_ts = pd.Timestamp(start)
        end_ts = pd.Timestamp(end)

        if self.cache.covers_range(symbol, start_ts, end_ts):
            cached = self.cache.read_range(symbol, start_ts, end_ts)
            if cached is not None and not cached.empty:
                return cached

        fetched = self.loader.load_ohlcv(symbol, start, end)

        if not fetched.empty:
            self.cache.merge_and_write(symbol, fetched, source=self.source)
            full = self.cache.read(symbol)
            if full is not None:
                return slice_date_range(full, start_ts, end_ts)

        return fetched

    def data_timestamp(self, symbol: str) -> str | None:
        meta = self.cache.metadata(symbol)
        return meta.get("data_timestamp") if meta else None


def _resolve_cache_dir(cfg: dict) -> Path:
    raw = cfg.get("data", {}).get("cache_dir", "data/cache")
    path = Path(raw)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def get_loader(use_cache: bool = True) -> DataLoader:
    """Build a DataLoader from strategy.yaml config."""
    cfg = load_strategy()
    data_cfg = cfg.get("data", {})
    provider = data_cfg.get("provider", "yfinance")
    symbol_suffix = data_cfg.get("symbol_suffix", ".NS")

    if provider == "yfinance":
        base: DataLoader = YFinanceLoader(symbol_suffix=symbol_suffix)
    else:
        raise ValueError(f"Unknown data provider: {provider}")

    if use_cache:
        cache = OHLCVCache(_resolve_cache_dir(cfg))
        return CachedDataLoader(base, cache, source=provider)

    return base


def load_ohlcv(symbol: str, start: date, end: date, use_cache: bool = True) -> pd.DataFrame:
    """Convenience function — load normalized OHLCV for a symbol."""
    loader = get_loader(use_cache=use_cache)
    df = loader.load_ohlcv(symbol, start, end)
    return normalize_ohlcv(df, symbol=symbol)
