import json
import streamlit as st
import os
from utils.data_utils import read_parquet_data
from optilab_constants import BACKTEST_RESULTS_FOLDERPATH
from backtest.backtest_analyzer import BacktestAnalyzer
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

# Define a reusable box style
box_style = """
    <div style="
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 12px;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    ">
        <h3 style="color: #333; margin-bottom: 8px;">{title}</h3>
        <p style="font-size: 28px; font-weight: bold; color: #da1a78; text-align: center;">
            {value}
        </p>
    </div>
"""

box_style_small = """
    <div style="
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 12px;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    ">
        <h5 style="color: #333; margin-bottom: 8px;">{title}</h5>
        <p style="font-size: 18px; font-weight: bold; color: #da1a78; text-align: center;">
            {value}
        </p>
    </div>
"""

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

def run():
    cols = st.columns([7, 1])
    with cols[0]:
        st.markdown("---\n# Daily P&L Analysis \n---")
    with cols[1]:
        st.image("./metadata/daily_pnl/spinning_bear.gif", width=200)

    backtest_foldernames = sorted([f for f in os.listdir(BACKTEST_RESULTS_FOLDERPATH) if os.path.isdir(os.path.join(BACKTEST_RESULTS_FOLDERPATH, f))])

    st.sidebar.subheader("Backtest Selection")
    selected_backtest_folder_name = st.sidebar.selectbox("Select a backtest code", backtest_foldernames, index=0)

    backtest_analyzer = BacktestAnalyzer(
        backtest_results_dir=BACKTEST_RESULTS_FOLDERPATH,
        backtest_folder_name=selected_backtest_folder_name
    )

    ############################
    #### CONFIGS and ABOUT #####
    ############################

    strategy_config = backtest_analyzer.get_strategy_config()
    backtester_config = backtest_analyzer.get_backtester_config()
    about_strategy = backtest_analyzer.get_about()

    # Two main columns: left (configs), right (about)
    left_col, right_col = st.columns([1, 3])
    with left_col:
        st.subheader("📊 Backtest Config")
        st.write(backtester_config)
        st.subheader("📊 Strategy Config")
        st.write(strategy_config)

    with right_col:
        st.subheader("📊 About Strategy")
        rows_left = len(backtester_config) + len(strategy_config) + 5
        st.text_area("", value=about_strategy, height=29*rows_left, label_visibility="collapsed")
    st.markdown("---")

    st.write("#### Backtesteter Config")
    cols = st.columns([1]*len(backtester_config))
    for col, (key, val) in zip(cols, backtester_config.items()):
        col.markdown(box_style_small.format(title=key, value=val), unsafe_allow_html=True)
    st.write("### Strategy Config")
    cols = st.columns([1]*len(strategy_config))
    for col, (key, val) in zip(cols, strategy_config.items()):
        col.markdown(box_style_small.format(title=key, value=val), unsafe_allow_html=True)

    ############################
    ############################

    ############################
    #### Portfolio Metrics #####
    ############################

    # EOD metrics
    df_portfolio_metrics = backtest_analyzer.get_df_portfolio_metrics()
    assert 'pnl' in df_portfolio_metrics.columns
    df_portfolio_metrics.sort_index(inplace=True)
    df_portfolio_metrics_eod = df_portfolio_metrics[df_portfolio_metrics.index.time == pd.Timestamp("15:29:00").time()].copy()
    df_portfolio_metrics_eod['daily_pnl'] = df_portfolio_metrics_eod['pnl'].diff().values
    df_portfolio_metrics_eod.iloc[0, df_portfolio_metrics_eod.columns.get_loc('daily_pnl')] = df_portfolio_metrics_eod['pnl'].iloc[0]


    if df_portfolio_metrics is not None:
        all_bt_dates = sorted(list(set(df_portfolio_metrics.index.strftime("%Y-%m-%d").tolist())))

        st.sidebar.subheader("Start Backtest Date")
        initial_backtest_date = st.sidebar.selectbox("Select Initial Backtest Date", all_bt_dates, index=0)

        # select date in sidebar
        st.sidebar.subheader("End Backtest Date")
        final_backtest_dates = [d for d in all_bt_dates if d >= initial_backtest_date]
        final_backtest_date = st.sidebar.selectbox("Select Final Backtest Date", final_backtest_dates, index=len(final_backtest_dates)-1)

        # Filter the DataFrames based on the selected dates
        df_portfolio_metrics_filtered = df_portfolio_metrics_eod[(df_portfolio_metrics_eod.index >= initial_backtest_date) & (df_portfolio_metrics_eod.index <= final_backtest_date)]

        with st.sidebar:
            st.header("📅 Select Days")
            mon = st.toggle("Monday", value=True)
            tue = st.toggle("Tuesday", value=True)
            wed = st.toggle("Wednesday", value=True)
            thu = st.toggle("Thursday", value=True)
            fri = st.toggle("Friday", value=True)

        # Select days
        selected_days = [day for day, enabled in zip(
            ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
            [mon, tue, wed, thu, fri]
        ) if enabled]

        df_portfolio_metrics_filtered = df_portfolio_metrics_filtered[df_portfolio_metrics_filtered.index.day_name().isin(selected_days)].copy()
        num_unique_days = len(df_portfolio_metrics_filtered.index.normalize().unique())
        total_daily_pnl = df_portfolio_metrics_filtered['daily_pnl'].sum()
        top_eight_losses = df_portfolio_metrics_filtered.nsmallest(8, 'daily_pnl')
        top_eight_profits = df_portfolio_metrics_filtered.nlargest(8, 'daily_pnl')

        # Columns layout
        st.write("### P&L Stats")
        col1, col2, col3 = st.columns([1, 2.5, 1])
        with col1:
            st.markdown(box_style.format(title="Total P&L", value=f"{total_daily_pnl:.2f}"), unsafe_allow_html=True)

        with col2:
            st.markdown(box_style.format(title="Selected Days", value=", ".join(selected_days)), unsafe_allow_html=True)

        with col3:
            st.markdown(box_style.format(title="Total Days", value=num_unique_days), unsafe_allow_html=True)


        # Stem Plot
        fig = stem_plot(df_portfolio_metrics_filtered, colname="daily_pnl")
        st.plotly_chart(fig, use_container_width=True)
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Top 8 Daily Losses")
            st.write(top_eight_losses[['daily_pnl']])
        with col2:
            st.subheader("Top 8 Daily Profits")
            st.write(top_eight_profits[['daily_pnl']])

    ############################
    ############################
