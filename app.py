import streamlit as st
from analyze import run as run_analyze
from trade import run as run_trade
from home import run as run_home    
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
col1, col2, col3, col4 = st.columns([0.1, 0.1, 0.1, 0.1], gap="small")
with col1:
    if st.button("Home", key="btn_home"):
        st.session_state.page = "Home"
with col2:
    if st.button("Candlesticks", key="btn_candlesticks"):
        st.session_state.page = "Candlesticks"
with col3:
    if st.button("Analyze", key="btn_analyze"):
        st.session_state.page = "Analyze"
with col4:
    if st.button("Trade", key="btn_trade"):
        st.session_state.page = "Trade"


# --- Render selected page ---
if st.session_state.page == "Home":
    run_home()
elif st.session_state.page == "Analyze":
    run_analyze()
elif st.session_state.page == "Trade":
    run_trade()
elif st.session_state.page == "Candlesticks":
    run_candlesticks()

