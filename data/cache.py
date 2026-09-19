"""Local parquet cache for OHLCV data."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from data.normalizer import normalize_ohlcv, slice_date_range


class OHLCVCache:
    """Per-symbol parquet cache with fetch metadata."""

    def __init__(self, cache_dir: Path | str) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _parquet_path(self, symbol: str) -> Path:
        safe = symbol.replace("/", "_").replace(".", "_")
        return self.cache_dir / f"{safe}.parquet"

    def _meta_path(self, symbol: str) -> Path:
        safe = symbol.replace("/", "_").replace(".", "_")
        return self.cache_dir / f"{safe}.meta.json"

    def read(self, symbol: str) -> pd.DataFrame | None:
        path = self._parquet_path(symbol)
        if not path.exists():
            return None
        df = pd.read_parquet(path)
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)
        return normalize_ohlcv(df, symbol=symbol)

    def read_range(self, symbol: str, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame | None:
        df = self.read(symbol)
        if df is None or df.empty:
            return None
        return slice_date_range(df, start, end)

    def write(self, symbol: str, df: pd.DataFrame, source: str = "unknown") -> None:
        normalized = normalize_ohlcv(df, symbol=symbol)
        normalized.to_parquet(self._parquet_path(symbol))
        meta = {
            "symbol": symbol,
            "source": source,
            "rows": len(normalized),
            "start": normalized.index.min().isoformat() if not normalized.empty else None,
            "end": normalized.index.max().isoformat() if not normalized.empty else None,
            "data_timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._meta_path(symbol).write_text(json.dumps(meta, indent=2))

    def merge_and_write(self, symbol: str, new_df: pd.DataFrame, source: str = "unknown") -> pd.DataFrame:
        """Merge new data with existing cache and persist."""
        existing = self.read(symbol)
        new_normalized = normalize_ohlcv(new_df, symbol=symbol)

        if existing is None or existing.empty:
            merged = new_normalized
        else:
            merged = pd.concat([existing, new_normalized])
            merged = merged[~merged.index.duplicated(keep="last")].sort_index()

        self.write(symbol, merged, source=source)
        return merged

    def metadata(self, symbol: str) -> dict | None:
        path = self._meta_path(symbol)
        if not path.exists():
            return None
        return json.loads(path.read_text())

    def covers_range(self, symbol: str, start: pd.Timestamp, end: pd.Timestamp) -> bool:
        df = self.read(symbol)
        if df is None or df.empty:
            return False
        return df.index.min() <= start.normalize() and df.index.max() >= end.normalize()
