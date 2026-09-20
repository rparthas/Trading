"""Backtest results page."""

from dataclasses import asdict
from datetime import date, timedelta

import pandas as pd
import streamlit as st

from backtest.engine import run_backtest
from backtest.metrics import summarize
from backtest.reports import OUTPUT_DIR, save_report
from config import load_strategy, load_universe

st.header("Backtest")
st.caption("Walk-forward validation over the configured universe and date range.")

cfg = load_strategy()
symbols = load_universe()

default_end = date.today()
default_start = default_end - timedelta(days=365 * 2)

col_start, col_end = st.columns(2)
with col_start:
    start_date = st.date_input("Start date", value=default_start, max_value=default_end)
with col_end:
    end_date = st.date_input("End date", value=default_end, max_value=default_end)

if start_date > end_date:
    st.error("Start date must be on or before end date.")
    st.stop()

if st.button("Run backtest", type="primary", icon=":material/play_arrow:"):
    with st.spinner("Running backtest…"):
        result = run_backtest(symbols, start_date, end_date, cfg)
        save_report(result)

    metrics = summarize(result.trades, result.equity_curve)

    st.subheader("Performance metrics")
    metric_items = list(metrics.items())
    metric_cols = st.columns(min(4, len(metric_items) or 1))
    for index, (name, value) in enumerate(metric_items):
        label = name.replace("_", " ").title()
        if isinstance(value, float):
            if name in {"win_rate", "max_drawdown"}:
                metric_cols[index % len(metric_cols)].metric(label, f"{value:.1%}")
            else:
                metric_cols[index % len(metric_cols)].metric(label, f"{value:.2f}")
        else:
            metric_cols[index % len(metric_cols)].metric(label, str(value))

    if not result.equity_curve.empty:
        st.subheader("Equity curve")
        st.line_chart(result.equity_curve.to_frame("equity"), width="stretch")

    if result.trades:
        st.subheader("Trade log")
        st.dataframe(pd.DataFrame([asdict(trade) for trade in result.trades]), width="stretch", hide_index=True)

    st.caption(f"Reports saved to `{OUTPUT_DIR}`")
