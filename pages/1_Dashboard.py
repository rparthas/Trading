"""Dashboard — market status and today's scan summary."""

from datetime import date

import streamlit as st

from config import load_strategy
from strategy.scanner import scan_universe
from ui.display import scan_result_rows

st.header("Dashboard")
st.caption("End-of-day swing scan overview for the NIFTY 50 universe.")

cfg = load_strategy()
today = date.today()

with st.container(border=True):
    st.subheader("Market status")
    st.info(
        "Market status feed is not connected yet. "
        "Use the scanner for a historical or latest available EOD scan date."
    )
    st.metric("Strategy version", cfg.get("version", "unknown"))
    st.metric("Universe", cfg.get("universe", {}).get("type", "nifty50"))

st.subheader("Today's scan summary")


@st.cache_data(show_spinner="Running daily scan…")
def cached_scan(scan_date: date):
    return scan_universe(scan_date)


if st.button("Refresh scan", icon=":material/refresh:"):
    cached_scan.clear()

scan = cached_scan(today)

summary_cols = st.columns(4)
summary_cols[0].metric("Candidates", scan.candidates)
summary_cols[1].metric("Qualified", len(scan.qualified))
summary_cols[2].metric("Rejected", len(scan.rejected))
summary_cols[3].metric("No pattern", len(scan.no_pattern))

if scan.qualified:
    st.success(f"{len(scan.qualified)} qualified trade(s) on {scan.scan_date}.")
    st.dataframe(scan_result_rows(scan), width="stretch", hide_index=True)
elif scan.rejected or scan.no_pattern:
    st.warning(f"No qualified trades on {scan.scan_date}.")
else:
    st.info("Run a scan to populate results.")

if scan.rejected:
    with st.expander("Rejection summary"):
        rejection_counts: dict[str, int] = {}
        for rejection in scan.rejected:
            rejection_counts[rejection.failed_gate] = rejection_counts.get(rejection.failed_gate, 0) + 1
        for gate, count in sorted(rejection_counts.items(), key=lambda item: item[1], reverse=True):
            st.write(f"- **{gate}**: {count}")
