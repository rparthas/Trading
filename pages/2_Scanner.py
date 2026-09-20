"""Universe scanner page."""

from datetime import date, timedelta

import streamlit as st

from strategy.scanner import scan_universe
from ui.display import scan_result_rows

st.header("Scanner")
st.caption("Run the full NIFTY 50 qualification scan for a selected date.")

default_date = date.today()
scan_date = st.date_input(
    "Scan date",
    value=default_date,
    max_value=default_date,
    min_value=default_date - timedelta(days=365 * 3),
)

decision_filter = st.segmented_control(
    "Show",
    options=["All", "TRADE", "REJECTED", "NO_PATTERN"],
    default="All",
)


@st.cache_data(show_spinner="Scanning universe…")
def cached_scan(selected_date: date):
    return scan_universe(selected_date)


if st.button("Run scan", type="primary", icon=":material/play_arrow:"):
    cached_scan.clear()

scan = cached_scan(scan_date)
rows = scan_result_rows(scan)

if decision_filter != "All":
    rows = [row for row in rows if row["Decision"] == decision_filter]

metric_cols = st.columns(4)
metric_cols[0].metric("Candidates", scan.candidates)
metric_cols[1].metric("Qualified", len(scan.qualified))
metric_cols[2].metric("Rejected", len(scan.rejected))
metric_cols[3].metric("No pattern", len(scan.no_pattern))

st.dataframe(rows, width="stretch", hide_index=True)

if scan.data_timestamp:
    st.caption(f"Data timestamp: {scan.data_timestamp}")
