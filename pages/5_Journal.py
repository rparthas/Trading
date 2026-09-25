"""Paper trading journal — simulated positions from trade plans."""

from datetime import date

import streamlit as st

from paper.positions import (
    close_paper_entry,
    paper_open_entries,
    refresh_paper_entries,
    split_journal_entries,
)
from ui.journal import add_journal_entry, load_journal, save_journal

st.header("Journal")
st.caption(
    "Paper trades opened from Scanner or Stock analysis. "
    "Positions update on refresh using the same stop, target, and max-holding rules as backtest."
)

if st.button("Refresh positions", type="primary", icon=":material/sync:"):
    with st.spinner("Updating open paper trades…"):
        entries = refresh_paper_entries(load_journal())
    st.session_state["journal_entries"] = entries
    st.rerun()

entries = load_journal()
paper_entries, manual_entries = split_journal_entries(entries)
open_paper = paper_open_entries(entries)
closed_paper = [e for e in paper_entries if e.get("status") == "closed"]

total_realized = sum(float(e.get("pnl", 0)) for e in closed_paper)
unrealized = sum(float(e.get("unrealized_pnl", 0)) for e in open_paper)

metric_cols = st.columns(4)
metric_cols[0].metric("Open paper", len(open_paper))
metric_cols[1].metric("Closed paper", len(closed_paper))
metric_cols[2].metric("Realized P&L", f"₹{total_realized:,.0f}")
metric_cols[3].metric("Unrealized P&L", f"₹{unrealized:,.0f}")

st.subheader("Open paper positions")
if not open_paper:
    st.info("No open paper positions. Open one from **Scanner** or **Stock analysis** when a trade qualifies.")
else:
    st.dataframe(open_paper, width="stretch", hide_index=True)
    with st.expander("Close a position manually"):
        choice = st.selectbox(
            "Position",
            open_paper,
            format_func=lambda e: f"{e['symbol']} @ {e['entry']} ({e['trade_date']})",
        )
        exit_price = st.number_input("Exit price", min_value=0.0, format="%.2f", value=float(choice["entry"]))
        if st.button("Close at price", icon=":material/close:"):
            close_paper_entry(entries, choice["id"], exit_price=exit_price, reason="manual")
            st.success("Position closed.")
            st.rerun()

st.subheader("Closed paper trades")
if not closed_paper:
    st.caption("No closed paper trades yet.")
else:
    st.dataframe(closed_paper, width="stretch", hide_index=True)

with st.expander("Manual log (optional)", expanded=False):
    st.caption("For trades taken outside this app — not simulated.")
    with st.form("journal_entry", border=True):
        symbol = st.text_input("Symbol", placeholder="RELIANCE")
        trade_date = st.date_input("Trade date", value=date.today())
        direction = st.selectbox("Direction", ["LONG", "SHORT"])
        entry = st.number_input("Entry", min_value=0.0, format="%.2f")
        stop = st.number_input("Stop", min_value=0.0, format="%.2f")
        target = st.number_input("Target", min_value=0.0, format="%.2f")
        shares = st.number_input("Shares", min_value=1, step=1)
        outcome = st.selectbox("Outcome", ["Open", "Win", "Loss", "Breakeven"])
        notes = st.text_area("Notes", placeholder="Setup notes, execution details…")
        submitted = st.form_submit_button("Save entry", type="primary", icon=":material/save:")

    if submitted:
        if not symbol.strip():
            st.error("Symbol is required.")
        else:
            payload = {
                "type": "manual",
                "symbol": symbol.strip().upper(),
                "trade_date": trade_date.isoformat(),
                "direction": direction,
                "entry": entry,
                "stop": stop,
                "target": target,
                "shares": int(shares),
                "outcome": outcome,
                "notes": notes.strip(),
            }
            add_journal_entry(entries, payload)
            st.success("Manual entry saved.")
            st.rerun()

    if manual_entries:
        st.dataframe(manual_entries, width="stretch", hide_index=True)

if st.button("Clear entire journal", icon=":material/delete:"):
    save_journal([])
    st.warning("Journal cleared.")
    st.rerun()
