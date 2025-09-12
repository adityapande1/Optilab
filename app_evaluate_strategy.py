import streamlit as st
from optilab_constants import BACKTEST_RESULTS_FOLDERPATH
from backtest.backtest_analyzer import BacktestAnalyzer
from backtest.metrics import MetricEngine
import plotly.express as px
import os
import plotly.graph_objects as go
import pandas as pd
from optilab_utils.viz_utils import stem_plot, info_box
import quantstats as qs

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


def labeled_box(title: str, value: str):
    st.markdown(f"""
        <div style="padding:0px 0px 0px 0px; border:1px solid #ddd; border-radius:4px; text-align:center;">
            <h3 style="margin:0; color:black; text-align:center;">{title}</h3>
            <hr style="margin:-2px 0;">
            <h4 style="margin:10px 0; color:#da1a78; font-size:26px; text-align:center;">{value}</h4>
        </div>
    """, unsafe_allow_html=True)

def labeled_box_with_help(title: str, value: str, help_text: str = ""):
    st.markdown(f"""
        <style>
        .tooltip {{
            position: relative;
            display: inline-block;
            cursor: help;
            font-family: Arial, sans-serif;
            vertical-align: middle;
        }}

        .tooltip-circle {{
            display: inline-flex;
            justify-content: center;
            align-items: center;
            width: 12px; 
            height: 12px;
            border-radius: 100%;
            background-color: #f0f0f0;
            border: 1px solid #aaa;
            color: #444;
            font-size: 11px;
            font-weight: 600;
            margin-left: 6px;
            vertical-align: middle;
        }}

        .tooltip .tooltiptext {{
            visibility: hidden;
            width: 200px;
            background-color: #f9f9f9;
            color: #333;
            text-align: center;
            border-radius: 6px;
            padding: 6px;
            border: 1px solid #ccc;
            position: absolute;
            z-index: 1;
            bottom: 125%;
            left: 50%;
            margin-left: -100px;
            opacity: 0;
            transition: opacity 0.3s;
            font-size: 12px;
        }}

        .tooltip .tooltiptext::after {{
            content: "";
            position: absolute;
            top: 100%;
            left: 50%;
            margin-left: -5px;
            border-width: 5px;
            border-style: solid;
            border-color: #f9f9f9 transparent transparent transparent;
        }}

        .tooltip:hover .tooltiptext {{
            visibility: visible;
            opacity: 1;
        }}
        </style>

        <div style="padding:0px; border:1px solid #ddd; border-radius:4px; text-align:center;">
            <h5 style="margin:0; color:black; text-align:left; padding-left:16px;">
                {title}
                <span class="tooltip">
                    <span class="tooltip-circle">?</span>
                    <span class="tooltiptext">{help_text}</span>
                </span>
            </h5>
            <hr style="margin:-2px 0;">
            <h6 style="margin:10px 0; color:#da1a78; font-size:26px; text-align:left; padding-left:16px;">{value}</h6>
        </div>
    """, unsafe_allow_html=True)


def histogram(df, colname, nbins=30, title=None, height=600):
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
        height=height,
        title_font_size=24,  # title font size
        font=dict(size=20),  # general font size
        xaxis=dict(tickfont=dict(size=16), showgrid=True, gridcolor='lightgray', gridwidth=1),  # x-axis tick font size
        yaxis=dict(tickfont=dict(size=20), showgrid=True, gridcolor='lightgray', gridwidth=1)  # y-axis tick font size
    )

    # vertical black line a t x=0 , but in the lower level
    fig.add_vline(x=0, line_width=2, line_dash="dash", line_color="black")

    return fig



def get_folderhash_to_foldername_map(backtest_results_dir):
    folderhash_to_foldername_map = {}
    for foldername in os.listdir(backtest_results_dir):
        folderpath = os.path.join(backtest_results_dir, foldername)
        if os.path.isdir(folderpath):
            analyzer = BacktestAnalyzer(backtest_results_dir=backtest_results_dir, backtest_folder_name=foldername)
            folderhash_to_foldername_map[analyzer.folder_hash] = foldername
    return folderhash_to_foldername_map


def run():

    # Initialize session state vars
    st.session_state.setdefault("folderhash_to_foldername_map", {})
    st.session_state.setdefault("folderhash_map_initialized", False)
    st.session_state.setdefault("selected_backtest_folder_name", None)

    BACKTEST_RESULTS_FOLDERPATH = "../Optiverse/backtest_results"
    # Build the folderhash → foldername map only once
    if st.session_state.folderhash_map_initialized is False:
        st.session_state.folderhash_to_foldername_map = get_folderhash_to_foldername_map(BACKTEST_RESULTS_FOLDERPATH)
        st.session_state.folderhash_map_initialized = True

    # UI header
    col = st.container()
    with col:
        st.markdown("---\n# Evaluate Strategy : Detailed Analysis of a Single Backtest")
        st.subheader("[ 1. Enter a valid backtest folder hash directly ] OR ")
        entered_folderhash = st.text_input("BACKTEST FOLDER HASH (Optional)", value="")
        if entered_folderhash:
            try:
                entered_folderhash = int(entered_folderhash)
                if entered_folderhash in st.session_state.folderhash_to_foldername_map:
                    st.session_state.selected_backtest_folder_name = (st.session_state.folderhash_to_foldername_map[entered_folderhash])
                    st.success(f"Loaded folder: {st.session_state.selected_backtest_folder_name}")
                else:
                    st.error("Invalid folder hash entered.")
            except ValueError:
                st.error("Folder hash must be an integer.")
        st.subheader("[ 2. Select a backtest folder in the sidebar : Backtest folder hash above $\\uparrow$ should be empty ]")
        st.markdown("---")

    # All available backtest folders
    backtest_foldernames = sorted([
            f
            for f in os.listdir(BACKTEST_RESULTS_FOLDERPATH)
            if os.path.isdir(os.path.join(BACKTEST_RESULTS_FOLDERPATH, f))
        ]
    )

    # Sidebar: dropdown (default to first folder if nothing selected yet)
    default_index = (
        0
        if st.session_state.selected_backtest_folder_name is None
        else backtest_foldernames.index(st.session_state.selected_backtest_folder_name)
    )

    foldername_selected_from_dropdown = st.sidebar.selectbox("Select a backtest foldername", backtest_foldernames, index=default_index)

    # Update state from dropdown (only if no hash override happened this run)
    if not entered_folderhash:
        st.session_state.selected_backtest_folder_name = foldername_selected_from_dropdown

    # Initial capital input
    initial_capital = st.sidebar.number_input("Initial Capital", value=250000)

    # Use the final folder name from session state
    selected_backtest_folder_name = st.session_state.selected_backtest_folder_name
    backtest_analyzer = BacktestAnalyzer(backtest_results_dir=BACKTEST_RESULTS_FOLDERPATH, backtest_folder_name=selected_backtest_folder_name)
    mengine = MetricEngine(btanalyzer=backtest_analyzer, initial_capital=initial_capital)
    backtest_metrics = mengine.metrics
    df_portfolio_metrics_daily = mengine.df_portfolio_metrics_daily
    df_portfolio_metrics_daily['daily_return_pct'] = df_portfolio_metrics_daily['daily_return'] * 100

    # Display folder info
    col_foldername, col_folder_hash = st.columns([4, 1])
    with col_foldername:
        labeled_box(title="Backtest Folder Name", value=selected_backtest_folder_name)
    with col_folder_hash:
        labeled_box(title="Backtest Folder Hash", value=backtest_analyzer.folder_hash)
    st.markdown("<br>", unsafe_allow_html=True)
    
    ############################
    #### CONFIGS and ABOUT #####
    ############################

    strategy_config = backtest_analyzer.get_strategy_config().as_dict()
    backtester_config = backtest_analyzer.get_backtester_config().as_dict()
    about_strategy = backtest_analyzer.get_about()

    # Two main columns: left (configs), right (about)
    info_box("Configs and Strategy Description")
    with st.expander("Expand to see Backtester and Strategy Configs and Detailed Strategy Description", expanded=False):
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

    info_box("Portfolio Performance Metrics")
    # break <br>
    st.markdown("<br>", unsafe_allow_html=True)

    cols_plots = st.columns([1, 1])
    with cols_plots[0]:
        fig = px.line(df_portfolio_metrics_daily['portfolio_value'], labels={'index': 'Date', 'value': 'PnL'}, title='Portfolio PnL Over Time')

        # Update layout for font size, height, ticks, grid, and disable legend
        fig.update_layout(
            height=500,  # figure height
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
            ),
            showlegend=False  # disable legend
        )

        # Display in Streamlit
        st.plotly_chart(fig, use_container_width=True)
    with cols_plots[1]:
        fig = histogram(df_portfolio_metrics_daily, colname="daily_return_pct", nbins=50, height=500)
        st.plotly_chart(fig, use_container_width=True, key='diggy')

    #############################################################################
    ###### BROAD STATS ##########################################################
    #############################################################################

    broad_stats = {
        "Initial Portfolio Value (₹) ": initial_capital,
        "Total P&L (₹) ": round(df_portfolio_metrics_daily['portfolio_value'].iloc[-1] - initial_capital, 4),
        "Final Portfolio Value (₹) ": round(df_portfolio_metrics_daily['portfolio_value'].iloc[-1], 4),
        "Pct Change (%) ": round((df_portfolio_metrics_daily['portfolio_value'].iloc[-1] - initial_capital) / initial_capital * 100, 2),
    }

    cols = st.columns([1]*len(broad_stats))
    for col, (key, val) in zip(cols, broad_stats.items()):
        with col:
            labeled_box(title=key, value=f"{val:.3f}" if isinstance(val, float) else f"{val}")
    # st.markdown("<br>", unsafe_allow_html=True)

    #############################################################################
    #############################################################################


    #############################################################################
    ###### COUNT STATS ##########################################################
    #############################################################################
    
    count_metrics = ['total_days', 'positive_days', 'negative_days', 'win_rate', 'max_win_streak', 'max_loss_streak', 'highest_return', 'lowest_return']
    cols = st.columns([1]*len(count_metrics))
    for col, metric in zip(cols, count_metrics):
        with col:
            labeled_box_with_help(title=metric.replace("_", " ").title(),
                                  value=f"{backtest_metrics[metric]['value']:.4f}" if isinstance(backtest_metrics[metric]['value'], float) else f"{backtest_metrics[metric]['value']}", 
                                  help_text=backtest_metrics[metric]['help'])
    # st.markdown("<br>", unsafe_allow_html=True)
    
    #############################################################################
    #############################################################################


    #############################################################################
    ###### RATIO STATS ##########################################################
    #############################################################################

    ratio_metrics = ['sharpe_ratio', 'sortino_ratio', 'daily_VaR', 'cagr', 'recovery_factor', 'gain_to_pain_ratio', 'avg_win', 'avg_loss']
    cols = st.columns([1]*len(ratio_metrics))
    for col, metric in zip(cols, ratio_metrics):
        with col:
            labeled_box_with_help(title=metric.replace("_", " ").title(),
                                  value=f"{backtest_metrics[metric]['value']:.4f}" if isinstance(backtest_metrics[metric]['value'], float) else f"{backtest_metrics[metric]['value']}", 
                                  help_text=backtest_metrics[metric]['help'])
    st.markdown("<br>", unsafe_allow_html=True)
    
    #############################################################################
    #############################################################################


    #############################################################################
    ###### DRAWDOWN STATS #######################################################
    #############################################################################
    info_box("Drawdown Analysis")

    col_df_drawdown, col_plot_drawdown = st.columns([3, 5])
    with col_df_drawdown:

        st.markdown("### Drawdown Details Dataframe")

        df_drawdown = backtest_metrics['df_drawdown']['value']
        styled_df = (
            df_drawdown.style
            .format({
                "start": lambda t: pd.to_datetime(t).strftime("%Y-%m-%d"),
                "valley": lambda t: pd.to_datetime(t).strftime("%Y-%m-%d"),
                "end": lambda t: pd.to_datetime(t).strftime("%Y-%m-%d"),
                "max drawdown": "{:.2f}%",
                "99% max drawdown": "{:.2f}%"
            })
            .set_properties(**{
                "text-align": "center",
                "font-size": "28px",     # try 28–36px for big but still usable
                "font-weight": "bold",   # makes text bold
            })
            .hide(axis="index")
        )

        st.dataframe(styled_df, use_container_width=True, height=600)

    with col_plot_drawdown:
        matplotlib_fig = qs.plots.drawdowns_periods(returns=df_portfolio_metrics_daily['daily_return'], periods=5, figsize=(10,5), show=False)
        st.pyplot(matplotlib_fig, use_container_width=True)
    
    #############################################################################
    #############################################################################


    #############################################################################
    ###### WEEKLY STATS #######################################################
    #############################################################################
    


    st.markdown("<br>", unsafe_allow_html=True)
    info_box("Weekly Performance Metrics")

    df_weekly = df_portfolio_metrics_daily.resample('W-WED').agg({
        'portfolio_value': 'last',                 # portfolio value at end of week
        'daily_return': lambda x: (x + 1).prod() - 1  # compound daily returns
    })

    # Rename column
    # st.subheader("📈 Weekly Metrics --------------------- ")
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




    col1_weekly_plot, col2_weekly_plot = st.columns([1, 1])
    with col1_weekly_plot:
        fig = stem_plot(df_weekly, colname="weekly_return_pct")
        st.plotly_chart(fig, use_container_width=True)
    with col2_weekly_plot:
        fig = histogram(df_weekly, colname="weekly_return_pct")
        st.plotly_chart(fig, use_container_width=True, key='dello')


    cols = st.columns([1]*len(weekly_stats_avg))
    for col, (key, val) in zip(cols, weekly_stats_avg.items()):
        with col:
            labeled_box(title=key, value=f"{val:.3f}" if isinstance(val, float) else f"{val}")
    st.markdown("<br>", unsafe_allow_html=True)
    col_top, col_bottom = st.columns(2)
    with col_top:
        st.markdown(html_template.format(key="Top8", val=weekly_stats_topbottom["Top8"]), unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
    with col_bottom:
        st.markdown(html_template.format(key="Bottom8", val=weekly_stats_topbottom["Bottom8"]), unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)







