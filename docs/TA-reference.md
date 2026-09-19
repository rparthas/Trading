# TA Methodology Reference

The strategy rules in `config/strategy.yaml` are derived from:

**Zerodha Varsity — Module 2: Technical Analysis**

Canonical source file: `/Users/rparthas/git/DigitalBrain/0.Inbox/TA.md`

## Key chapters

| Chapter | Topic | Used in |
|---------|-------|---------|
| 5–8 | Candlestick patterns | `patterns/single_candle.py`, `patterns/multi_candle.py` |
| 11 | Support & Resistance | `patterns/support_resistance.py` |
| 16–17 | Dow Theory | `patterns/dow.py` |
| 18 | Risk/Reward + Grand Checklist | `strategy/qualification.py`, `strategy/risk.py` |
| 19 | Scanning methodology | `strategy/scanner.py` |

## Scanning checklist (Ch. 19)

1. Recognizable candlestick pattern (last 3–4 candles)
2. Prior trend validation (bullish → downtrend; bearish → uptrend; Marubozu exempt)
3. Volume ≥ 10-day average
4. S/R exists and aligns with pattern stop (within 4%)
5. Dow patterns (double/triple top/bottom, flags, range breakout)
6. R:R ≥ 1.5
7. MACD + RSI confirmatory (position size adjustment only)
