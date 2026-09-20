"""Tests for Milestone 3 pattern and indicator modules."""

import pandas as pd

from config import load_strategy
from indicators.macd import compute_macd, macd_signal
from indicators.moving_average import add_ema, add_sma
from indicators.rsi import compute_rsi
from models.trade import Direction
from patterns.candle_utils import body_ratio, is_bullish, lower_shadow_ratio, range_pct
from patterns.detect import detect_best_pattern
from patterns.dow import detect_dow_patterns
from patterns.multi_candle import detect_multi_patterns
from patterns.single_candle import detect_single_patterns
from patterns.support_resistance import find_support_resistance_zones, stop_aligned
from patterns.trend import detect_prior_trend
from patterns.volume import volume_confirmed, volume_ratio


def _df(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def test_candle_utils_bullish_marubozu_shape():
    candle = {"open": 100.0, "high": 110.0, "low": 100.0, "close": 110.0}
    assert is_bullish(candle)
    assert body_ratio(candle) == 1.0
    assert lower_shadow_ratio(candle) == 0.0
    assert abs(range_pct(candle) - 9.0909) < 0.01


def test_detect_bullish_marubozu():
    cfg = load_strategy()
    df = _df(
        [
            {"open": 105, "high": 106, "low": 100, "close": 101, "volume": 1000},
            {"open": 101, "high": 111, "low": 101, "close": 111, "volume": 1200},
        ]
    )
    result = detect_single_patterns(df, cfg)
    assert result is not None
    assert result.pattern == "bullish_marubozu"
    assert result.direction == Direction.LONG


def test_detect_hammer_in_downtrend():
    cfg = load_strategy()
    base = [{"open": 120 - i, "high": 121 - i, "low": 115 - i, "close": 116 - i, "volume": 1000} for i in range(18)]
    hammer = {"open": 102.0, "high": 103.0, "low": 95.0, "close": 102.5, "volume": 1500}
    df = _df(base + [hammer])
    assert detect_prior_trend(df) == "downtrend"
    result = detect_single_patterns(df, cfg)
    assert result is not None
    assert result.pattern == "hammer"
    assert result.direction == Direction.LONG


def test_detect_bullish_engulfing():
    cfg = load_strategy()
    base = [{"open": 120 - i, "high": 121 - i, "low": 115 - i, "close": 116 - i, "volume": 1000} for i in range(18)]
    p1 = {"open": 102.0, "high": 103.0, "low": 98.0, "close": 99.0, "volume": 1000}
    p2 = {"open": 98.5, "high": 104.0, "low": 98.0, "close": 103.5, "volume": 2000}
    df = _df(base + [p1, p2])
    result = detect_multi_patterns(df, cfg)
    assert result is not None
    assert result.pattern == "bullish_engulfing"
    assert result.direction == Direction.LONG


def test_detect_best_pattern_skips_doji():
    cfg = load_strategy()
    df = _df([{"open": 100.0, "high": 101.0, "low": 99.0, "close": 100.05, "volume": 1000}])
    result = detect_best_pattern(df, cfg)
    assert result is None


def test_volume_ratio_and_confirmation():
    rows = [{"open": 100, "high": 101, "low": 99, "close": 100, "volume": 1000} for _ in range(9)]
    rows.append({"open": 100, "high": 101, "low": 99, "close": 100, "volume": 1500})
    df = _df(rows)
    assert volume_ratio(df, period=10) == 1.5
    assert volume_confirmed(df, period=10, min_ratio=1.0)


def test_support_resistance_and_stop_alignment():
    rows = []
    for i in range(30):
        low = 95 + (i % 5)
        high = low + 5
        rows.append({"open": low + 2, "high": high, "low": low, "close": low + 3, "volume": 1000})
    df = _df(rows)
    zones = find_support_resistance_zones(df, lookback=30)
    assert zones["support_zones"]
    assert zones["resistance_zones"]
    assert stop_aligned(96.0, zones["support_zones"][0], max_pct=4.0)


def test_dow_patterns_returns_evidence():
    rows = []
    price = 100.0
    for i in range(40):
        if i < 10:
            price += 1.0
        elif i < 20:
            price += 0.1
        elif i < 30:
            price += 1.0
        else:
            price += 0.1
        rows.append({"open": price, "high": price + 1, "low": price - 1, "close": price, "volume": 1000})
    df = _df(rows)
    evidence = detect_dow_patterns(df)
    assert isinstance(evidence, list)


def test_indicators_sma_ema_rsi_macd():
    closes = pd.Series([float(100 + i + (i % 3)) for i in range(60)])
    df = _df([{"open": c, "high": c + 1, "low": c - 1, "close": c, "volume": 1000} for c in closes])

    sma_df = add_sma(df, 20)
    ema_df = add_ema(df, 20)
    assert "sma_20" in sma_df.columns
    assert "ema_20" in ema_df.columns
    assert not pd.isna(sma_df["sma_20"].iloc[-1])
    assert not pd.isna(ema_df["ema_20"].iloc[-1])

    rsi = compute_rsi(closes, period=14)
    assert 0 <= rsi.iloc[-1] <= 100

    macd_df = compute_macd(closes)
    assert {"macd", "signal", "histogram"}.issubset(macd_df.columns)
    assert macd_signal(macd_df) in {"bullish", "bearish", "neutral"}
