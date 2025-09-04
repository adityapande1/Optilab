import streamlit as st
from optilab_constants import BACKTEST_RESULTS_FOLDERPATH
from backtest.backtest_analyzer import BacktestAnalyzer
from backtest.metrics import MetricEngine
import plotly.express as px
import os
import plotly.graph_objects as go
import pandas as pd
from optilab_utils.viz_utils import stem_plot, info_box


# HTML template with full-width and responsive text
html_template = """
<div style="
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 20px;
    border-radius: 8px;
    background-color: #f9f9f9;
    box-shadow: 4px 4px 12px #c0c0c0, -4px -4px 12px #ffffff;
    width: 100%;
    box-sizing: border-box;
">
    <div style="
        color: black; 
        font-weight: bold; 
        text-align: left;
        margin-right: 20px;
        font-family: 'Courier New', Courier, monospace;
        font-size: 20px;
        flex: 0 0 auto;  /* Key keeps its width */
    ">{key}:</div>
    <div style="
        color: #da1a78; 
        font-weight: bold; 
        font-size: 22px;
        font-family: 'Source Code Pro', monospace;
        flex: 1;          /* Value takes remaining space */
        word-wrap: break-word;
        overflow-wrap: break-word;
    ">{val}</div>
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
def histogram(df, colname, nbins=30, title=None):
    """
    Create a Plotly histogram for a given column in a DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame.
    colname : str
        Column name to plot the histogram.
    nbins : int, optional
        Number of bins in the histogram (default=30).
    title : str, optional
        Title of the plot (default: column name).

    Returns
    -------
    fig : plotly.graph_objs._figure.Figure
        Plotly histogram figure.
    """
    fig = px.histogram(
        df,
        x=colname,
        nbins=nbins,
        title=title if title else f"Histogram of {colname}",
        marginal="box",  # adds a boxplot on top
        opacity=0.75
    )
    fig.update_layout(
        bargap=0.1,
        xaxis_title=colname,
        yaxis_title="Count",
        height=600,
        title_font_size=24,  # title font size
        font=dict(size=20),  # general font size
        xaxis=dict(tickfont=dict(size=16), showgrid=True, gridcolor='lightgray', gridwidth=1),  # x-axis tick font size
        yaxis=dict(tickfont=dict(size=20), showgrid=True, gridcolor='lightgray', gridwidth=1)  # y-axis tick font size
    )

    # vertical black line a t x=0 , but in the lower level
    fig.add_vline(x=0, line_width=2, line_dash="dash", line_color="black")

    return fig


def run():
    cols = st.columns([7, 1])
    with cols[0]:
        st.markdown("---\n# Evaluate Strategy \n---")
    with cols[1]:
        st.image("./metadata/evaluate_strategy/run_dog.gif", width=500)

    BACKTEST_RESULTS_FOLDERPATH = '../Optiverse/backtest_results'

    backtest_foldernames = sorted([f for f in os.listdir(BACKTEST_RESULTS_FOLDERPATH) if os.path.isdir(os.path.join(BACKTEST_RESULTS_FOLDERPATH, f))])
    st.sidebar.subheader("Backtest Selection")
    selected_backtest_folder_name = st.sidebar.selectbox("Select a backtest code", backtest_foldernames, index=0)
    st.markdown(html_template.format(key='backtest_folder_code', val=selected_backtest_folder_name), unsafe_allow_html=True)
    # break <br>
    st.markdown("<br>", unsafe_allow_html=True)
    # At sidebar we input the inital capital default 2_50_000
    initial_capital = st.sidebar.number_input("Initial Capital", value=250000)

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
    ############################
    ############################
    
    
    
    
    metric_engine = MetricEngine(backtest_analyzer, initial_capital=initial_capital)
    df_portfolio_metrics = metric_engine.df_portfolio_metrics
    df_portfolio_metrics_daily = metric_engine.df_portfolio_metrics_daily

    num_traded_days =  len(df_portfolio_metrics_daily.index.unique())
    total_pnl = 15908


    # Example: your DataFrame with portfolio values
    vals = df_portfolio_metrics_daily['portfolio_value'] 
    # st.subheader("📈 Performance Metrics --------------------- ")
    info_box("Performance Metrics: Key statistics of overall portfolio performance")
    st.markdown("<br>", unsafe_allow_html=True)

    # Two columns
    col1, col2 = st.columns([1.5, 3.5])

    # Left column: metrics
    with col1:

        broad_stats = {
            "Initial Portfolio Value (₹) ": initial_capital,
            "Total P&L (₹) ": round(df_portfolio_metrics_daily['portfolio_value'].iloc[-1] - initial_capital, 4),
            "Pct Change (%) ": round((df_portfolio_metrics_daily['portfolio_value'].iloc[-1] - initial_capital) / initial_capital * 100, 2),
            "Final Portfolio Value (₹) ": round(df_portfolio_metrics_daily['portfolio_value'].iloc[-1], 4),
            "Start Date": df_portfolio_metrics_daily.index.min().strftime("%Y-%m-%d"),
            "End Date  ": df_portfolio_metrics_daily.index.max().strftime("%Y-%m-%d"),
            "Total Days": len(df_portfolio_metrics_daily.index.unique()),
        }

        for key, val in broad_stats.items():
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(html_template.format(key=key, val=val), unsafe_allow_html=True)

    # Right column: plot
    with col2:
        # Example plot
        fig = px.line(vals, labels={'index': 'Date', 'value': 'PnL'}, title='Portfolio PnL Over Time')

        # Update layout for font size, height, ticks, and grid
        fig.update_layout(
            height=600,  # figure height
            title_font_size=24,  # title font size
            font=dict(size=20),  # general font size
            xaxis=dict(
                tickfont=dict(size=16),  # x-axis tick font size
                nticks=20,               # approximate number of ticks
                showgrid=True,           # enable grid
                gridcolor='lightgray',   # grid line color
                gridwidth=1              # grid line width
            ),
            yaxis=dict(
                tickfont=dict(size=20),  # y-axis tick font size
                nticks=12,               # approximate number of ticks
                showgrid=True,           # enable grid
                gridcolor='lightgray',   # grid line color
                gridwidth=1              # grid line width
            )
        )

        # Display in Streamlit
        st.plotly_chart(fig, use_container_width=True)


    df_daily = df_portfolio_metrics_daily.copy()
    # Weekly from Thursday to next Wednesday
    df_weekly = df_daily.resample('W-WED').agg({
        'portfolio_value': 'last',                 # portfolio value at end of week
        'daily_return': lambda x: (x + 1).prod() - 1  # compound daily returns
    })

    # Rename column
    # st.subheader("📈 Weekly Metrics --------------------- ")
    info_box("Weekly Metrics: Summary statistics of weekly returns")
    st.markdown("<br>", unsafe_allow_html=True)
    df_weekly = df_weekly.rename(columns={'daily_return': 'weekly_return'})
    df_weekly['weekly_return_pct'] = df_weekly['weekly_return'] * 100
    
    weekly_stats_avg = {
        "Total Weeks": len(df_weekly),
        "Mean Return (%)": round(df_weekly['weekly_return_pct'].mean(), 2),
        "Median Return (%)": round(df_weekly['weekly_return_pct'].median(), 2),
        "Std Dev (%)": round(df_weekly['weekly_return_pct'].std(), 2),
        "Max Return (%)": round(df_weekly['weekly_return_pct'].max(), 2),
        "Min Return (%)": round(df_weekly['weekly_return_pct'].min(), 2),
        "Positive Weeks": (df_weekly['weekly_return_pct'] > 0).sum(),
        "Negative Weeks": (df_weekly['weekly_return_pct'] < 0).sum(),
        "Win Rate (%)": round((df_weekly['weekly_return_pct'] > 0).mean() * 100, 2),
    }

    weekly_stats_topbottom = {
        "Top8": " | ".join(map(str, round(df_weekly['weekly_return_pct'].nlargest(8), 2).to_list())),
        "Bottom8": " | ".join(map(str, round(df_weekly['weekly_return_pct'].nsmallest(8), 2).to_list())),
    }

    cols_avg = st.columns(len(weekly_stats_avg))

    for col, (key, val) in zip(cols_avg, weekly_stats_avg.items()):
        col.metric(label=key, value=val)

    col_top, col_bottom = st.columns(2)
    with col_top:
        st.markdown(html_template.format(key="Top8", val=weekly_stats_topbottom["Top8"]), unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
    with col_bottom:
        st.markdown(html_template.format(key="Bottom8", val=weekly_stats_topbottom["Bottom8"]), unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)


    col1_weekly_plot, col2_weekly_plot = st.columns([1, 1])
    with col1_weekly_plot:
        fig = stem_plot(df_weekly, colname="weekly_return_pct")
        st.plotly_chart(fig, use_container_width=True)
    with col2_weekly_plot:
        fig = histogram(df_weekly, colname="weekly_return_pct")
        st.plotly_chart(fig, use_container_width=True, key='dello')




    # st.subheader("📈 Weekly Metrics --------------------- ")
    info_box("Daily Metrics: Summary statistics of daily returns")
    st.markdown("<br>", unsafe_allow_html=True)


    df_daily['daily_return_pct'] = df_daily['daily_return'] * 100
    daily_stats_avg = {
        "Total Days": len(df_daily),
        "Mean Return (%)": round(df_daily['daily_return_pct'].mean(), 2),
        "Median Return (%)": round(df_daily['daily_return_pct'].median(), 2),
        "Std Dev (%)": round(df_daily['daily_return_pct'].std(), 2),
        "Max Return (%)": round(df_daily['daily_return_pct'].max(), 2),
        "Min Return (%)": round(df_daily['daily_return_pct'].min(), 2),
        "Positive Days": (df_daily['daily_return_pct'] > 0).sum(),
        "Negative Days": (df_daily['daily_return_pct'] < 0).sum(),
        "Win Rate (%)": round((df_daily['daily_return_pct'] > 0).mean() * 100, 2),
    }

    daily_stats_topbottom = {
        "Top8": " | ".join(map(str, round(df_daily['daily_return_pct'].nlargest(8), 2).to_list())),
        "Bottom8": " | ".join(map(str, round(df_daily['daily_return_pct'].nsmallest(8), 2).to_list())),
    }

    cols_avg = st.columns(len(daily_stats_avg))

    for col, (key, val) in zip(cols_avg, daily_stats_avg.items()):
        col.metric(label=key, value=val)

    col_top, col_bottom = st.columns(2)
    with col_top:
        st.markdown(html_template.format(key="Top8", val=daily_stats_topbottom["Top8"]), unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
    with col_bottom:
        st.markdown(html_template.format(key="Bottom8", val=daily_stats_topbottom["Bottom8"]), unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)


    col1_daily_plot, col2_daily_plot = st.columns([1, 1])
    with col1_daily_plot:
        fig = stem_plot(df_daily, colname="daily_return_pct")
        st.plotly_chart(fig, use_container_width=True)
    with col2_daily_plot:
        fig = histogram(df_daily, colname="daily_return_pct", nbins=50)
        st.plotly_chart(fig, use_container_width=True, key='diggy')