"""Local trade journal page."""

from datetime import date

import streamlit as st

from ui.journal import add_journal_entry, load_journal, save_journal

st.header("Journal")
st.caption("Log trades you took locally. Entries are stored in JSON on disk.")

entries = load_journal()

with st.form("journal_entry", border=True):
    st.subheader("Add trade")
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
        entries = add_journal_entry(
            entries,
            {
                "symbol": symbol.strip().upper(),
                "trade_date": trade_date.isoformat(),
                "direction": direction,
                "entry": entry,
                "stop": stop,
                "target": target,
                "shares": int(shares),
                "outcome": outcome,
                "notes": notes.strip(),
            },
        )
        st.success("Journal entry saved.")
        st.rerun()

st.subheader("Entries")
if not entries:
    st.info("No journal entries yet.")
else:
    st.dataframe(entries, width="stretch", hide_index=True)

    if st.button("Clear journal", icon=":material/delete:"):
        save_journal([])
        st.warning("Journal cleared.")
        st.rerun()
