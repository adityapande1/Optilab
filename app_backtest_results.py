import pandas as pd
import streamlit as st
import os
from strategy import  Action
from utils.data_utils import read_parquet_data
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from optilab_constants import BACKTEST_DIR

@st.cache_data
def _all_files_in_directory(directory):
    return [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]

@st.cache_data
def _get_backtest_dataframes(backtest_dir):

    # Load all DataFrames from the backtest directory
    hash2position_dfs, df_portfolio_metrics = {}, None
    all_parquet_dfs = [f for f in os.listdir(backtest_dir) if f.endswith(".parquet")]

    for df_filename in all_parquet_dfs:
        if df_filename.startswith("df_position") and df_filename.endswith(".parquet"):
            hash_value = df_filename[len("df_position_"):-len(".parquet")]
            hash2position_dfs[int(hash_value)] = read_parquet_data(os.path.join(backtest_dir, df_filename))
        elif df_filename == "df_portfolio_metrics.parquet":
            df_portfolio_metrics = read_parquet_data(os.path.join(backtest_dir, df_filename))

    return hash2position_dfs, df_portfolio_metrics

def filter_metrics(hash2position_dfs:dict[int, pd.DataFrame], df_portfolio_metrics:pd.DataFrame, initial_backtest_timestamp:pd.Timestamp, final_backtest_timestamp:pd.Timestamp):

    df_portfolio_metrics_filtered = df_portfolio_metrics[initial_backtest_timestamp:final_backtest_timestamp].copy()
    filtered_indices = df_portfolio_metrics_filtered.index
    hash2position_dfs_filtered = {}
    for hash_key, df_position in hash2position_dfs.items():
        df_position_filtered = df_position[initial_backtest_timestamp:final_backtest_timestamp].copy()
        if not df_position_filtered.empty:
             # Reindex to include all filtered indices (NaN where missing)
            df_position_filtered = df_position_filtered.reindex(filtered_indices)
            hash2position_dfs_filtered[hash_key] = df_position_filtered

    return hash2position_dfs_filtered, df_portfolio_metrics_filtered

def plotly_stem(hash2position_dfs, backtest_dir):

    action_json_filepaths = [fl for fl in os.listdir(backtest_dir) if fl.endswith(".json") and fl.startswith("action_")]

    # Ensure consistent index union across all dfs
    all_index = pd.Index(sorted(set().union(*[df.index for df in hash2position_dfs.values()])))
    aligned_dfs = {h: df.reindex(all_index) for h, df in hash2position_dfs.items()}
    
    # Calculate combined pnl (ignoring NaN)
    combined_pnl = pd.DataFrame({h: df['pnl'] for h, df in aligned_dfs.items()}).sum(axis=1, skipna=True)

    # Subplots: combined at top + one per hash
    n_plots = len(hash2position_dfs) + 1
    titles = ["Combined PnL"]
    hash_titles =[]
    for h in aligned_dfs.keys():
        filename = f'action_{int(h)}.json'
        
        if filename in action_json_filepaths:
            action = Action.load(os.path.join(backtest_dir, filename))
        else:
            action = None
        action_key = ''
        if action is not None:
            action_key = action.key

        hash_titles.append(f"Hash: {h}  : Action : {action_key}")
    titles += hash_titles

    fig = make_subplots(rows=n_plots, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.05, subplot_titles=titles)

    # --- Combined PnL (row 1) ---
    for t, v in zip(combined_pnl.index, combined_pnl.values):
        if pd.notna(v):
            color = "green" if v > 0 else "red"
            fig.add_trace(go.Scatter(x=[t, t], y=[0, v], mode="lines", line=dict(color=color)),
                          row=1, col=1)
            fig.add_trace(go.Scatter(x=[t], y=[v], mode="markers", marker=dict(color=color, size=6)),
                          row=1, col=1)

    # --- Individual hashes ---
    for i, (h, df) in enumerate(aligned_dfs.items(), start=2):  # start=2 because row=1 is combined
        for t, v in zip(df.index, df['pnl']):
            if pd.notna(v):
                color = "green" if v > 0 else "red"
                fig.add_trace(go.Scatter(x=[t, t], y=[0, v], mode="lines", line=dict(color=color)),
                              row=i, col=1)
                fig.add_trace(go.Scatter(x=[t], y=[v], mode="markers", marker=dict(color=color, size=6)),
                              row=i, col=1)

    fig.update_layout(height=300*n_plots, showlegend=False, 
                      title_text="PnL Stem Plots", title_x=0.5)

    return fig

def run():

    # BACKTEST_DIR = "./backtest_results"
    st.markdown("---\n# Backtest Results Analysis\n---")

    backtest_strategy_ts_codes = sorted([f for f in os.listdir(BACKTEST_DIR)])
    st.sidebar.subheader("Backtest Selection")
    # A dropdown to select a backtest code
    selected_backtest_strategy_ts_code = st.sidebar.selectbox("Select a backtest code", backtest_strategy_ts_codes, index=0)
    selected_backtest_dir = f"{BACKTEST_DIR}/{selected_backtest_strategy_ts_code}"
    all_files_in_selected_backtest_dir = _all_files_in_directory(selected_backtest_dir)
    # assert 'backtest_config.json' in all_files_in_selected_backtest_dir
    # assert 'strategy_config.json' in all_files_in_selected_backtest_dir

    backtest_config_dict, strategy_config_dict = {}, {}
    if 'backtest_config.json' in all_files_in_selected_backtest_dir:
        backtest_config_dict = BacktestConfig.load(os.path.join(selected_backtest_dir, 'backtest_config.json')).__dict__
    if 'strategy_config.json' in all_files_in_selected_backtest_dir:
        strategy_config_dict = StrategyConfig.load(os.path.join(selected_backtest_dir, 'strategy_config.json')).__dict__


    if 'about_strategy.txt' in all_files_in_selected_backtest_dir:
        with open(os.path.join(selected_backtest_dir, 'about_strategy.txt'), 'r') as f:
            about_strategy = f.read()
    else:
        about_strategy = "No information available"

    # Two main columns: left (configs), right (about)
    left_col, right_col = st.columns([1, 2])
    with left_col:
        st.subheader("📊 Backtest Config")
        st.json(backtest_config_dict)
        st.subheader("📊 Strategy Config")
        st.json(strategy_config_dict)
    with right_col:
        st.subheader("📊 About Strategy")
        st.text_area("", value=about_strategy, height=400,label_visibility="collapsed")
    st.markdown("---")

    # In the sidebar selecation for the backtest dates for viz
    hash2position_dfs, df_portfolio_metrics = _get_backtest_dataframes(selected_backtest_dir)
    initial_backtest_pd_timestamp, final_backtest_pd_timestamp = None, None
    if df_portfolio_metrics is not None:
        first_bt_date, last_bt_date = df_portfolio_metrics.index.min().strftime("%Y-%m-%d"), df_portfolio_metrics.index.max().strftime("%Y-%m-%d")
        all_bt_dates = sorted(list(set(df_portfolio_metrics.index.strftime("%Y-%m-%d").tolist())))
        # st.sidebar.write(f"**First Backtest Date:** {first_bt_date}")
        # st.sidebar.write(f"**Last Backtest Date:** {last_bt_date}")

        st.sidebar.markdown("---")
        st.sidebar.subheader("Start Viz Date")
        initial_backtest_date = st.sidebar.selectbox("Select Initial Backtest Date", all_bt_dates, index=0)
        st.sidebar.write(f"**Initial Backtest Date:** {initial_backtest_date}")
        col_hr_initial, col_min_initial = st.sidebar.columns(2)
        with col_hr_initial:
            initial_backtest_hour = st.selectbox("Select Initial Backtest Hour", [9, 10, 11, 12, 13, 14, 15], index=0)
        with col_min_initial:
            if initial_backtest_hour == 9:
                initial_backtest_minute = st.selectbox("Select Initial Backtest Minute", list(range(15, 60)), index=0)
            elif initial_backtest_hour == 15:
                initial_backtest_minute = st.selectbox("Select Initial Backtest Minute", list(range(0, 30)), index=0)
            else:
                initial_backtest_minute = st.selectbox("Select Initial Backtest Minute", list(range(0, 60)), index=0)

        # Write padded time like 9:5 ===> 09:05
        initial_backtest_pd_timestamp = pd.Timestamp(f"{initial_backtest_date} {initial_backtest_hour:02d}:{initial_backtest_minute:02d}")

        # select date in sidebar
        st.sidebar.markdown("---")
        st.sidebar.subheader("End Viz Date")
        final_backtest_dates = [d for d in all_bt_dates if d >= initial_backtest_date]
        final_backtest_date = st.sidebar.selectbox("Select Final Backtest Date", final_backtest_dates, index=0)
        st.sidebar.write(f"**Final Backtest Date:** {final_backtest_date}")

        if pd.to_datetime(final_backtest_date) < pd.to_datetime(initial_backtest_date):
            st.sidebar.error("Final Backtest Date must be after Initial Backtest Date")

        else:
    
            col_hr_final, col_min_final = st.sidebar.columns(2)
            with col_hr_final:
                final_backtest_hour = st.selectbox("Select Final Backtest Hour", [9, 10, 11, 12, 13, 14, 15], index=6)
            with col_min_final:
                if final_backtest_hour == 9:
                    final_backtest_minute = st.selectbox("Select Final Backtest Minute", list(range(15, 60)), index=59)
                elif final_backtest_hour == 15:
                    final_backtest_minute = st.selectbox("Select Final Backtest Minute", list(range(0, 30)), index=29)
                else:
                    final_backtest_minute = st.selectbox("Select Final Backtest Minute", list(range(0, 60)), index=59)

            # Write padded time like 9:5 ===> 09:05
            final_backtest_pd_timestamp = pd.Timestamp(f"{final_backtest_date} {final_backtest_hour:02d}:{final_backtest_minute:02d}")

    st.sidebar.markdown("---")

    # if initial_backtest_pd_timestamp and final_backtest_pd_timestamp are not None the I want a button that can be presse called GO
    viz_state = False
    if initial_backtest_pd_timestamp is not None and final_backtest_pd_timestamp is not None:

        col1, col2 = st.columns(2)
        with col1:
            st.subheader(f"**Initial Backtest TS :** {initial_backtest_pd_timestamp} Day : {initial_backtest_pd_timestamp.day_name()}")
        with col2:
            st.subheader(f"**Final Backtest TS :** {final_backtest_pd_timestamp} Day : {final_backtest_pd_timestamp.day_name()}")

        if st.sidebar.button("🧿 --- **VISUALIZE** --- 🧿"):
            st.session_state.run_backtest = True
            viz_state = True

    st.write("Visualization State:", viz_state)

    if viz_state:
        st.write("The visualization is currently running.")
        hash2position_dfs_filtered, df_portfolio_metrics_filtered = filter_metrics(hash2position_dfs, df_portfolio_metrics, initial_backtest_pd_timestamp, final_backtest_pd_timestamp)

        fig = plotly_stem(hash2position_dfs_filtered, backtest_dir=selected_backtest_dir)
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.write("The visualization is not running.")
