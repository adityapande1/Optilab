import streamlit as st
import os
from backtest.backtest_analyzer import BacktestAnalyzer
from optilab_utils.viz_utils import info_box
import pandas as pd
import numpy as np

from st_aggrid import AgGrid
from st_aggrid.grid_options_builder import GridOptionsBuilder

import streamlit as st
import pandas as pd
import numpy as np
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

def get_folderhash_to_foldername_map(backtest_results_dir):
    folderhash_to_foldername_map = {}
    for foldername in os.listdir(backtest_results_dir):
        folderpath = os.path.join(backtest_results_dir, foldername)
        if os.path.isdir(folderpath):
            analyzer = BacktestAnalyzer(backtest_results_dir=backtest_results_dir, backtest_folder_name=foldername)
            folderhash_to_foldername_map[analyzer.folder_hash] = foldername
    return folderhash_to_foldername_map

def run():
    
    st.markdown("---\n# Compare Strategies")
    st.markdown("### Please Select strategies from the sidebar to compare\n---")
    
    
    # Initialize session state list
    if "hashes" not in st.session_state:
        st.session_state.hashes = []

    st.title("Hash Collector")

    # Input bar for integer
    new_hash = st.number_input("Enter a hash (integer):", step=1)

    # Add button
    if st.button("Add Hash"):
        if new_hash not in st.session_state.hashes:
            st.session_state.hashes.append(int(new_hash))

    st.write("### Hash Collection:")

    # Display hashes with remove button
    for h in st.session_state.hashes:
        col1, col2 = st.columns([4,1])
        with col1:
            col1.metric(label="", value=f"{h}", border=True)
            st.button("x", key=f"remove_{h}")
        with col2:
            if st.button("x", key=f"remove1_{h}"):
                st.session_state.hashes.remove(h)
                st.experimental_rerun()
    
    
    # # Initialize session state vars
    # st.session_state.setdefault("folderhash_to_foldername_map", {})
    # st.session_state.setdefault("folderhash_map_initialized", False)
    # st.session_state.setdefault("selected_backtest_folder_name", None)

    # BACKTEST_RESULTS_FOLDERPATH = "../Optiverse/backtest_results"
    # # Build the folderhash → foldername map only once
    # if st.session_state.folderhash_map_initialized is False:
    #     st.session_state.folderhash_to_foldername_map = get_folderhash_to_foldername_map(BACKTEST_RESULTS_FOLDERPATH)
    #     st.session_state.folderhash_map_initialized = True
    
    
    
    
    
    

    # # --- Sample data for 20 strategies ---
    # np.random.seed(42)
    # strategies = [f"strategy{i}" for i in range(1, 21)]
    # df = pd.DataFrame({
    #     "strategy_name": strategies,
    #     "initial_capital": np.random.choice([250000], size=20),
    #     "total_pnl": np.round(np.random.uniform(10000, 50000, 20), 2),
    #     "total_return_pct": np.round(np.random.uniform(0.05, 0.25, 20), 3),
    #     "trading_days": np.random.randint(100, 200, size=20),
    #     "win_days": np.random.randint(40, 120, size=20),
    #     "loss_days": np.random.randint(20, 80, size=20),
    #     "win_ratio": np.round(np.random.uniform(0.4, 0.7, 20), 2),
    #     "sharpe_ratio": np.round(np.random.uniform(0.5, 2.0, 20), 2),
    #     "max_dd": np.round(np.random.uniform(-0.3, -0.05, 20), 2),
    #     "sortino_ratio": np.round(np.random.uniform(0.5, 2.5, 20), 2),
    #     "avg_return": np.round(np.random.uniform(0.03, 0.15, 20), 3),
    # })

    # # --- Build Ag-Grid options ---
    # gb = GridOptionsBuilder.from_dataframe(df)

    # # --- DISABLE pagination to show all rows in a single scrollable page ---
    # # Comment out or remove: gb.configure_pagination(paginationAutoPageSize=True)

    # # Optional: add sidebar, selection, etc.
    # gb.configure_side_bar()
    # gb.configure_selection("single", use_checkbox=True)

    # # Increase font size
    # gb.configure_default_column(cellStyle={"font-size": "16px", "text-align": "center"})

    # # # Gradient bars for numeric metrics
    # # for col in ["sharpe_ratio", "sortino_ratio", "avg_return"]:
    # #     gb.configure_column(col, cellRenderer="agBarCellRenderer", cellRendererParams={"color": "lightgreen"})
    # # gb.configure_column("max_dd", cellRenderer="agBarCellRenderer", cellRendererParams={"color": "red"})

    # grid_options = gb.build()

    # # Display
    # st.title("Strategy Performance Dashboard")
    # AgGrid(df, gridOptions=grid_options, theme="streamlit", height=800)  # increase height if needed
