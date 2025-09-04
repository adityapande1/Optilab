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

def run():
    
    # st.session_state.setdefault("chosen_backtests_dict", {})
    # st.session_state.setdefault("counter", 1)
    # st.session_state.setdefault("current_foldercodes", set())

    st.markdown("---\n# Compare Strategies")
    st.markdown("### Please Select strategies from the sidebar to compare\n---")

    # BACKTEST_RESULTS_FOLDERPATH = '../Optiverse/backtest_results'
    # backtest_foldernames = sorted([f for f in os.listdir(BACKTEST_RESULTS_FOLDERPATH) if os.path.isdir(os.path.join(BACKTEST_RESULTS_FOLDERPATH, f))])

    # st.sidebar.subheader("Backtest Selection")
    # selected_backtest_folder_name = st.sidebar.selectbox("Select a backtest code", backtest_foldernames, index=0)
    # initial_capital = st.sidebar.number_input("Initial Capital", value=250000)

    # # Add strategy
    # if st.sidebar.button("Add Selection"):
    #     if selected_backtest_folder_name not in st.session_state.current_foldercodes:
    #         st.session_state.current_foldercodes.add(selected_backtest_folder_name)
    #         key = f"STRATEGY_{st.session_state.counter}"
    #         btanalyzer = BacktestAnalyzer(backtest_results_dir=BACKTEST_RESULTS_FOLDERPATH, backtest_folder_name=selected_backtest_folder_name)
    #         st.session_state.chosen_backtests_dict[key] = {
    #             "foldercode": selected_backtest_folder_name,
    #             "initial_capital": initial_capital,
    #             "backtester_config": btanalyzer.get_backtester_config(),
    #             "strategy_config": btanalyzer.get_strategy_config(),
    #             "metrics": dict()
    #         }
    #         st.session_state.counter += 1

    # # --- Show expanders with delete buttons ---
    # st.write("### Selected Backtest Strategies:")
    # keys_to_delete = []  # to track which keys user wants to delete
    # cols = st.columns([1]*len(st.session_state.chosen_backtests_dict))
    # for (strat_key, strat_info), col in zip(st.session_state.chosen_backtests_dict.items(), cols):
    #     with col:
    #         info_box(val=strat_key, font_size=18)
    #     with col.expander(f"{strat_info['foldercode']}"):
    #         st.write(f"**Folder Code:** {strat_info['foldercode']}")
    #         st.write(f"**Initial Capital:** {strat_info['initial_capital']}")
    #         st.write("**Backtester Config:**", strat_info['backtester_config'])
    #         st.write("**Strategy Config:**", strat_info['strategy_config'])

    #         # Delete button inside expander
    #         if st.button(f"Delete {strat_key}"):
    #             keys_to_delete.append(strat_key)

    # # Delete after loop to avoid runtime modification issues
    # for key in keys_to_delete:
    #     st.session_state.current_foldercodes.discard(st.session_state.chosen_backtests_dict[key]['foldercode'])
    #     st.session_state.chosen_backtests_dict.pop(key, None)

    # ###### Display tthe comparison metrics ######
    # # if st.session_state.chosen_backtests_dict:

    # #     # Calculate metrics for each selected backtest
    # #     for strat_key, strat_info in st.session_state.chosen_backtests_dict.items():


    # # Sample data
    # data = {
    #     "strategy_name": ["strategy1", "strategy2", "strategy3"],
    #     "sharpe_ratio": [1.2, 0.8, 1.5],
    #     "max_dd": [-0.15, -0.25, -0.1],
    #     "sortino_ratio": [1.5, 1.0, 2.0],
    #     "avg_return": [0.08, 0.05, 0.12],
    # }

    # df = pd.DataFrame(data)




    # --- Sample data for 20 strategies ---
    np.random.seed(42)
    strategies = [f"strategy{i}" for i in range(1, 21)]
    df = pd.DataFrame({
        "strategy_name": strategies,
        "initial_capital": np.random.choice([250000], size=20),
        "total_pnl": np.round(np.random.uniform(10000, 50000, 20), 2),
        "total_return_pct": np.round(np.random.uniform(0.05, 0.25, 20), 3),
        "trading_days": np.random.randint(100, 200, size=20),
        "win_days": np.random.randint(40, 120, size=20),
        "loss_days": np.random.randint(20, 80, size=20),
        "win_ratio": np.round(np.random.uniform(0.4, 0.7, 20), 2),
        "sharpe_ratio": np.round(np.random.uniform(0.5, 2.0, 20), 2),
        "max_dd": np.round(np.random.uniform(-0.3, -0.05, 20), 2),
        "sortino_ratio": np.round(np.random.uniform(0.5, 2.5, 20), 2),
        "avg_return": np.round(np.random.uniform(0.03, 0.15, 20), 3),
    })

    # --- Build Ag-Grid options ---
    gb = GridOptionsBuilder.from_dataframe(df)

    # --- DISABLE pagination to show all rows in a single scrollable page ---
    # Comment out or remove: gb.configure_pagination(paginationAutoPageSize=True)

    # Optional: add sidebar, selection, etc.
    gb.configure_side_bar()
    gb.configure_selection("single", use_checkbox=True)

    # Increase font size
    gb.configure_default_column(cellStyle={"font-size": "16px", "text-align": "center"})

    # # Gradient bars for numeric metrics
    # for col in ["sharpe_ratio", "sortino_ratio", "avg_return"]:
    #     gb.configure_column(col, cellRenderer="agBarCellRenderer", cellRendererParams={"color": "lightgreen"})
    # gb.configure_column("max_dd", cellRenderer="agBarCellRenderer", cellRendererParams={"color": "red"})

    grid_options = gb.build()

    # Display
    st.title("Strategy Performance Dashboard")
    AgGrid(df, gridOptions=grid_options, theme="streamlit", height=800)  # increase height if needed
