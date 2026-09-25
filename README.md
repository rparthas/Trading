# Trading Analyst Agent (TAA)

A deterministic EOD swing-trading analysis engine with an LLM analyst on top.

Python computes every trade decision — entry, stop, target, position size, and qualification gates. The LLM (OpenAI) explains pre-computed evidence only; it never alters trade numbers.

## What it does

Given today's end-of-day market data for the NIFTY 50 universe, TAA answers:

> Are there any technically valid trades today, and if so, what are the exact parameters?

**NO TRADE** is a valid and expected outcome.

## Architecture

```
Market Data → Normalizer → TA Engine → Qualification Gates → Trade Plan → [Backtest | Streamlit | LLM]
```

Signal priority (from Zerodha Varsity TA methodology):

```
Pattern → Prior Trend → Volume → S/R → Dow Structure → R:R ≥ 1.5 → MACD/RSI (confirmatory)
```

## Source of truth

Rules are encoded from [Zerodha Varsity Module 2 — Technical Analysis](https://zerodha.com/varsity/). The canonical reference copy lives at `docs/TA.md` (symlink or copy from DigitalBrain).

## Project structure

```
├── PLAN.md              # Story-level execution plan
├── config/
│   ├── strategy.yaml    # Machine-readable strategy contract
│   └── nifty50.csv      # Universe constituents
├── data/                # Data loaders, normalizer, cache
├── patterns/            # Candlesticks, trend, S/R, Dow
├── indicators/          # RSI, MACD, moving averages
├── strategy/            # Scanner, qualification, risk
├── backtest/            # Historical validation (mandatory gate)
├── llm/                 # OpenAI analyst (explanation only)
├── models/              # Pydantic schemas
└── tests/
```

## Milestones

| # | Milestone | Status |
|---|-----------|--------|
| 0 | Repo bootstrap + plan | Done |
| 1 | Strategy specification (`strategy.yaml`, models) | Done |
| 2 | Market data layer (pluggable loader) | Done |
| 3 | Technical analysis engine | Done |
| 4 | Trade qualification + scanner | Done |
| 5 | Backtesting (validation gate) | Done |
| 6 | Streamlit UI | Done |
| 7 | OpenAI analyst layer | Done |

See [PLAN.md](PLAN.md) for full story-level breakdown.

## Quick start

```bash
# Install uv: https://docs.astral.sh/uv/getting-started/installation/
uv sync --all-groups

# Run tests
uv run pytest

# Daily scan (--verbose shows why stocks were rejected)
uv run python -m strategy.scanner --date 2026-09-18 --verbose

# Backtest
uv run python -m backtest.run --start 2024-01-01 --end 2026-09-01

# Streamlit UI
uv run streamlit run app.py
```

### Family launcher (same Mac, no terminal)

Double-click **`scripts/Launch Trading Analyst.command`**. The first run may take a minute while dependencies install; after that it opens the app in your browser.

- Drag the `.command` file to the Desktop or Dock if you want a shortcut.
- Use **`scripts/Stop Trading Analyst.command`** to quit if the browser tab is closed but the app is still running.
- Put LLM settings in `.env` in the project folder once for AI explanations (optional; template fallback works without them):
  - `OPENAI_API_KEY` — API key for OpenAI or any OpenAI-compatible provider
  - `OPENAI_BASE_URL` — optional base URL (e.g. `http://localhost:11434/v1` for Ollama, or a proxy/gateway); alias: `OPENAI_API_BASE`
  - `OPENAI_MODEL` — optional model name (default `gpt-4o-mini`)

## Design principles

1. **Strategy validity ≠ empirical validity** — valid per methodology ≠ price prediction
2. **Quantified rules only** — no vague pattern detection
3. **Gated qualification** — mandatory gates first, confirmatory indicators last
4. **Backtest before live recommendations** — Milestone 5 blocks UI/LLM
5. **Pluggable data sources** — Yahoo/NSE/Kite behind `DataLoader` interface

## License

Private — personal trading research tool.
