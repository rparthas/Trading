"""Yahoo Finance data adapter for NSE symbols."""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import yfinance as yf

from data.normalizer import normalize_ohlcv


class YFinanceLoader:
    """Fetch daily OHLCV from Yahoo Finance."""

    def __init__(self, symbol_suffix: str = ".NS") -> None:
        self.symbol_suffix = symbol_suffix

    def _to_yahoo_symbol(self, symbol: str) -> str:
        if symbol.endswith(self.symbol_suffix):
            return symbol
        return f"{symbol}{self.symbol_suffix}"

    def load_ohlcv(self, symbol: str, start: date, end: date) -> pd.DataFrame:
        yahoo_symbol = self._to_yahoo_symbol(symbol)
        # yfinance end date is exclusive — add one day
        end_exclusive = end + timedelta(days=1)

        ticker = yf.Ticker(yahoo_symbol)
        df = ticker.history(start=start.isoformat(), end=end_exclusive.isoformat(), auto_adjust=True)

        if df is None or df.empty:
            return normalize_ohlcv(pd.DataFrame(), symbol=symbol)

        return normalize_ohlcv(df, symbol=symbol)
