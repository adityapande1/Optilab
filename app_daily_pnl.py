import streamlit as st
import os
from utils.data_utils import read_parquet_data
from optilab_constants import BACKTEST_DIR
import pandas as pd

import streamlit as st
import plotly.graph_objects as go

import streamlit as st
import plotly.graph_objects as go

def stem_plot(df, colname="daily_pnl"):
    fig = go.Figure()

    # Separate positive and negative values
    pos_mask = df[colname] >= 0
    neg_mask = df[colname] < 0

    # Positive stems
    fig.add_trace(go.Scatter(
        x=df.index[pos_mask],
        y=df[colname][pos_mask],
        mode="markers",
        marker=dict(color="green", size=8),
        name=f"Positive {colname}"
    ))

    for x, y in zip(df.index[pos_mask], df[colname][pos_mask]):
        fig.add_trace(go.Scatter(
            x=[x, x],
            y=[0, y],
            mode="lines",
            line=dict(color="green", width=2),
            showlegend=False
        ))

    # Negative stems
    fig.add_trace(go.Scatter(
        x=df.index[neg_mask],
        y=df[colname][neg_mask],
        mode="markers",
        marker=dict(color="red", size=8),
        name=f"Negative {colname}"
    ))

    for x, y in zip(df.index[neg_mask], df[colname][neg_mask]):
        fig.add_trace(go.Scatter(
            x=[x, x],
            y=[0, y],
            mode="lines",
            line=dict(color="red", width=2),
            showlegend=False
        ))

    # Layout
    fig.update_layout(
        title=f"{colname} Stem Plot",
        xaxis_title="Date",
        yaxis_title=colname,
        showlegend=True,
        template="plotly_white",
        height=500
    )

    return fig

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

def run():
    st.markdown("---\n# Daily P&L Analysis\n---")
    backtest_strategy_ts_codes = sorted([f for f in os.listdir(BACKTEST_DIR)])
    st.sidebar.subheader("Backtest Selection")
    # A dropdown to select a backtest code
    selected_backtest_strategy_ts_code = st.sidebar.selectbox("Select a backtest code", backtest_strategy_ts_codes, index=0)
    selected_backtest_dir = f"{BACKTEST_DIR}/{selected_backtest_strategy_ts_code}"
    all_files_in_selected_backtest_dir = _all_files_in_directory(selected_backtest_dir)
    
    # assert 'backtest_config.json' in all_files_in_selected_backtest_dir
    # assert 'strategy_config.json' in all_files_in_selected_backtest_dir
    # strategy_config = StrategyConfig.load(os.path.join(selected_backtest_dir, 'strategy_config.json'))
    # backtest_config = BacktestConfig.load(os.path.join(selected_backtest_dir, 'backtest_config.json'))
    backtest_config_dict, strategy_config_dict = {}, {}     # TODO : Add code to save and load

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

    hash2position_dfs, df_portfolio_metrics = _get_backtest_dataframes(selected_backtest_dir)
    
    # EOD metrics
    assert 'pnl' in df_portfolio_metrics.columns
    df_portfolio_metrics.sort_index(inplace=True)
    df_metrics_eod = df_portfolio_metrics[df_portfolio_metrics.index.time == pd.Timestamp("15:29:00").time()].copy()
    df_metrics_eod['daily_pnl'] = df_metrics_eod['pnl'].diff().values
    df_metrics_eod.iloc[0, df_metrics_eod.columns.get_loc('daily_pnl')] = df_metrics_eod['pnl'].iloc[0]

    if df_portfolio_metrics is not None:
        first_bt_date, last_bt_date = df_portfolio_metrics.index.min().strftime("%Y-%m-%d"), df_portfolio_metrics.index.max().strftime("%Y-%m-%d")
        all_bt_dates = sorted(list(set(df_portfolio_metrics.index.strftime("%Y-%m-%d").tolist())))

        st.sidebar.subheader("Start PnL Date")
        initial_backtest_date = st.sidebar.selectbox("Select Initial Backtest Date", all_bt_dates, index=0)
        # st.sidebar.write(f"**Initial Backtest Date:** {initial_backtest_date}")

        # select date in sidebar
        st.sidebar.subheader("End PnL Date")
        final_backtest_dates = [d for d in all_bt_dates if d >= initial_backtest_date]
        final_backtest_date = st.sidebar.selectbox("Select Final Backtest Date", final_backtest_dates, index=len(final_backtest_dates)-1)
        # st.sidebar.write(f"**Final Backtest Date:** {final_backtest_date}")

        # Filter the DataFrames based on the selected dates
        df_metrics_filtered = df_metrics_eod[(df_metrics_eod.index >= initial_backtest_date) & (df_metrics_eod.index <= final_backtest_date)]

        with st.sidebar:
            st.header("📅 Select Days")
            mon = st.toggle("Monday", value=True)
            tue = st.toggle("Tuesday", value=True)
            wed = st.toggle("Wednesday", value=True)
            thu = st.toggle("Thursday", value=True)
            fri = st.toggle("Friday", value=True)

        # Example usage
        selected_days = [day for day, enabled in zip(
            ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
            [mon, tue, wed, thu, fri]
        ) if enabled]

        df_metrics_filtered = df_metrics_filtered[df_metrics_filtered.index.day_name().isin(selected_days)].copy()
        num_unique_days = len(df_metrics_filtered.index.normalize().unique())
        total_daily_pnl = df_metrics_filtered['daily_pnl'].sum()
        top_five_losses = df_metrics_filtered.nsmallest(5, 'daily_pnl')
        top_five_profits = df_metrics_filtered.nlargest(5, 'daily_pnl')
        col1, col2, col3 = st.columns([1, 2.5, 1])
        with col1:
            st.subheader(f"Total PnL: {total_daily_pnl:.2f}")
        with col2:
            st.subheader(f"Selected Days : {', '.join(selected_days)}")
        with col3:
            st.subheader(f"Total Days: {num_unique_days}")


        # Example usage
        fig = stem_plot(df_metrics_filtered, colname="daily_pnl")
        st.plotly_chart(fig, use_container_width=True)
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Top 5 Daily Losses")
            st.write(top_five_losses[['daily_pnl']])
        with col2:
            st.subheader("Top 5 Daily Profits")
            st.write(top_five_profits[['daily_pnl']])
