"""Streamlit helpers for opening paper trades from a trade plan."""

import streamlit as st

from models.trade import TradePlan
from paper.positions import open_paper_from_plan
from ui.journal import load_journal


def paper_trade_button(plan: TradePlan, *, key: str, label: str = "Paper trade") -> None:
    if st.button(label, key=key, type="secondary", icon=":material/account_balance:"):
        entries = load_journal()
        updated, error = open_paper_from_plan(entries, plan)
        if error:
            st.error(error)
        else:
            st.session_state["journal_entries"] = updated
            st.success(f"Paper position opened for {plan.symbol}. See Journal.")
            st.rerun()
