"""Trading Analyst Agent — Streamlit entry point."""

import streamlit as st

st.set_page_config(
    page_title="Trading Analyst Agent",
    page_icon=":material/candlestick_chart:",
    layout="wide",
)

dashboard = st.Page(
    "pages/1_Dashboard.py",
    title="Dashboard",
    icon=":material/dashboard:",
    default=True,
)
scanner = st.Page("pages/2_Scanner.py", title="Scanner", icon=":material/search:")
analysis = st.Page(
    "pages/3_Stock_Analysis.py",
    title="Stock analysis",
    icon=":material/analytics:",
)
backtest = st.Page("pages/4_Backtest.py", title="Backtest", icon=":material/timeline:")
journal = st.Page("pages/5_Journal.py", title="Journal", icon=":material/book:")

pg = st.navigation([dashboard, scanner, analysis, backtest, journal])
pg.run()
