"""Single-symbol analysis page."""

from datetime import date, timedelta

import streamlit as st

from config import load_universe
from llm.analyst import explain_trade
from models.trade import Decision
from strategy.scanner import analyze_stock
from ui.display import analysis_gate_rows, trade_plan_dict

st.header("Stock analysis")
st.caption("Deep dive on one symbol — gates, trade plan, and optional LLM explanation.")

symbols = load_universe()
default_symbol = st.session_state.get("analysis_symbol", symbols[0] if symbols else "")

col_symbol, col_date = st.columns(2)
with col_symbol:
    symbol = st.selectbox("Symbol", symbols, index=symbols.index(default_symbol) if default_symbol in symbols else 0)
with col_date:
    scan_date = st.date_input(
        "Analysis date",
        value=date.today(),
        max_value=date.today(),
        min_value=date.today() - timedelta(days=365 * 3),
    )

st.session_state["analysis_symbol"] = symbol


@st.cache_data(show_spinner=f"Analyzing {symbol}…")
def cached_analysis(selected_symbol: str, selected_date: date):
    return analyze_stock(selected_symbol, selected_date)


if st.button("Analyze", type="primary", icon=":material/analytics:"):
    cached_analysis.clear()

analysis = cached_analysis(symbol, scan_date)

decision_label = analysis.decision.value
if analysis.decision == Decision.TRADE:
    st.success(f"{symbol} — {decision_label}")
elif analysis.rejection:
    st.warning(f"{symbol} — NO TRADE ({analysis.rejection.failed_gate})")
else:
    st.info(f"{symbol} — {decision_label}")

if analysis.pattern:
    pattern = analysis.pattern
    pattern_cols = st.columns(4)
    pattern_cols[0].metric("Pattern", pattern.pattern)
    pattern_cols[1].metric("Direction", pattern.direction.value)
    pattern_cols[2].metric("Strength", f"{pattern.strength:.2f}")
    pattern_cols[3].metric("Entry ref.", pattern.entry_reference)

st.subheader("Gate checklist")
if analysis.gate_results:
    st.dataframe(analysis_gate_rows(analysis), width="stretch", hide_index=True)
else:
    st.caption("No gate results returned.")

if analysis.trade_plan:
    st.subheader("Trade plan")
    st.table(trade_plan_dict(analysis.trade_plan))

    if st.button("Explain trade", icon=":material/psychology:"):
        with st.spinner("Generating explanation…"):
            explanation = explain_trade(analysis.trade_plan)
        st.markdown(explanation)

if analysis.rejection and analysis.rejection.message:
    st.subheader("Rejection detail")
    st.write(analysis.rejection.message)
