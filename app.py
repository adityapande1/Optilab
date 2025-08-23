import streamlit as st
from analyze import run as run_analyze
from trade import run as run_trade
from home import run as run_home    
from yello import run as run_yello
from candlesticks import run as run_candlesticks    

# --- Wide page setting filling complete window ---
st.set_page_config(
    page_title="Optiverse Lab",
    layout="wide",   # 👈 makes it full width
    initial_sidebar_state="collapsed"  # optional: hide sidebar by default
)

# --- Initialize session state ---
if "page" not in st.session_state:
    st.session_state.page = "Home"

# --- Base button styles ---
st.markdown(
    """
    <style>
    div[data-testid="stButton"] > button {
        background-color: #ffffff;
        border: 2px solid #000000;
        border-radius: 12px;
        padding: 12px 28px;
        cursor: pointer;
        font-size: 20px;
        font-weight: 600;
        color: #000000;
        transition: all 0.3s ease;
        box-shadow: 2px 4px 6px rgba(0, 0, 0, 0.15);
    }
    div[data-testid="stButton"] > button:hover {
        background-color: #f8f8f8;
        border-color: #444444;
        transform: translateY(-10px);
        box-shadow: 4px 8px 12px rgba(0, 0, 0, 0.25);
    }
    div[data-testid="stButton"] > button:active {
        transform: translateY(0px);
        box-shadow: 1px 2px 4px rgba(0, 0, 0, 0.2);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Navigation buttons (side by side with small gap) ---
state_names = ["Home", "Candlesticks", "Analyze Backtest Results", "Trade", "Yellow"]
button_names = ["btn_home", "btn_candlesticks", "btn_analyze", "btn_trade", "btn_yellow"]
page_functions = {
    "Home": run_home,
    "Candlesticks": run_candlesticks,
    "Analyze Backtest Results": run_analyze,
    "Trade": run_trade,
    "Yellow": run_yello
}

assert len(state_names) == len(button_names) == len(page_functions), "Inconsistent lengths of state_names, button_names, and page_functions"
assert len(state_names) > 0, "No pages defined"

# --- Create columns for navigation buttons ---
cols=st.columns(len(state_names), gap="small")
for col, state_name, button_name in zip(cols, state_names, button_names):
    with col:
        if st.button(state_name, key=button_name):
            st.session_state.page = state_name

# --- Render selected page dynamically ---
if "page" in st.session_state and st.session_state.page in page_functions:
    page_functions[st.session_state.page]()


