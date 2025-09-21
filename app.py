import streamlit as st
from app_daily_pnl2 import run as run_daily_pnl
from app_evaluate_strategy import run as run_evaluate_strategy
from app_home import run as run_home
from app_nifty_stats import run as run_nifty_stats
from app_visualize_strategy import run as run_visualize_strategy
from app_compare_strategies import run as run_compare_strategies

# --- Wide page setting filling complete window ---
st.set_page_config(page_title="Optiverse Lab", layout="wide", initial_sidebar_state="collapsed")
st.session_state.setdefault(key="current_page", default="Home")

page_button_pairs = [
    ("Home", "button_home"),
    ("Daily PnL", "button_daily_pnl"),
    ("Evaluate Strategy", "button_evaluate_strategy"),
    ("Visualize Strategy", "button_visualize_strategy"),
    ("Compare Strategies", "button_compare_strategies"),
    ("Nifty Stats", "button_nifty_stats"),
]

page_to_funtion_map = {
    "Home": run_home,
    "Daily PnL": run_daily_pnl,
    "Evaluate Strategy": run_evaluate_strategy,
    "Visualize Strategy": run_visualize_strategy,
    "Compare Strategies": run_compare_strategies,
    "Nifty Stats": run_nifty_stats,
}

assert all(page in page_to_funtion_map for page, _ in page_button_pairs), "All pages must have a corresponding function"

columns = st.columns(len(page_button_pairs), gap="small")
for page_column, (page, button) in zip(columns, page_button_pairs):
    with page_column:
        if st.button(page, key=button):
            st.session_state.current_page = page

page_to_funtion_map[st.session_state.current_page]()


