"""Market data schemas."""

from __future__ import annotations

from datetime import date
from typing import Protocol

import pandas as pd
from pydantic import BaseModel, Field


class OHLCVBar(BaseModel):
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: float


class OHLCVSeries(BaseModel):
    symbol: str
    bars: list[OHLCVBar] = Field(default_factory=list)

    def to_dataframe(self) -> pd.DataFrame:
        if not self.bars:
            return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])
        df = pd.DataFrame([b.model_dump() for b in self.bars])
        df["date"] = pd.to_datetime(df["date"])
        return df.set_index("date").sort_index()


class DataLoader(Protocol):
    """Pluggable market data interface — implement for yfinance, NSE, Kite, etc."""

    def load_ohlcv(self, symbol: str, start: date, end: date) -> pd.DataFrame:
        """Return DataFrame with columns: open, high, low, close, volume (date index)."""
        ...
