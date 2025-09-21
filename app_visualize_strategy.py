import streamlit as st
import os
from backtest.backtest_analyzer import BacktestAnalyzer
from backtest.metrics import MetricEngine
from optilab_utils.viz_utils import info_box

from connectors.dbconnector import DBConnector
import plotly.graph_objects as go
import pandas as pd
from plotly.subplots import make_subplots

VALID_TIMES = pd.date_range("09:15", "15:29", freq="1min").time


def shift_indices(step: int, df_spot):
    st.session_state.start_idx = min(
        max(0, st.session_state.start_idx + step), len(df_spot) - 1
    )
    st.session_state.end_idx = min(
        max(0, st.session_state.end_idx + step), len(df_spot) - 1
    )
    st.session_state.selected_start_timestamp = df_spot.index[st.session_state.start_idx]
    st.session_state.selected_end_timestamp = df_spot.index[st.session_state.end_idx]




# @st.cache_data
def get_position_infos(backtest_analyzer):
    
    position_infos = []
    for position_hash in backtest_analyzer.get_position_hashes():
        df_position = backtest_analyzer.get_df_position(position_hash=position_hash)
        dictio = {
            'position_hash': position_hash,
            'first_timestamp': df_position.index.min(),
            'last_timestamp': df_position.index.max()
        }
        position_infos.append(dictio)
        
    df_position_info = pd.DataFrame(position_infos)    
    # The coloums first_timestamp and last_timestamp should be in pd.Timestamp format
    df_position_info['first_timestamp'] = pd.to_datetime(df_position_info['first_timestamp'])
    df_position_info['last_timestamp'] = pd.to_datetime(df_position_info['last_timestamp'])

    return df_position_info

def get_folderhash_to_foldername_map(backtest_results_dir):
    folderhash_to_foldername_map = {}
    for foldername in os.listdir(backtest_results_dir):
        folderpath = os.path.join(backtest_results_dir, foldername)
        if os.path.isdir(folderpath):
            analyzer = BacktestAnalyzer(backtest_results_dir=backtest_results_dir, backtest_folder_name=foldername)
            folderhash_to_foldername_map[analyzer.folder_hash] = foldername
    return folderhash_to_foldername_map

def labeled_box(title: str, value: str):
    st.markdown(f"""
        <div style="padding:0px 0px 0px 0px; border:1px solid #ddd; border-radius:4px; text-align:center;">
            <h3 style="margin:0; color:black; text-align:center;">{title}</h3>
            <hr style="margin:-2px 0;">
            <h4 style="margin:10px 0; color:#da1a78; font-size:26px; text-align:center;">{value}</h4>
        </div>
    """, unsafe_allow_html=True)
    
    
def make_candlestick_subplot(df_list, titles=None, height_per_chart=400):

    n = len(df_list)
    if titles is None:
        titles = [f"Stock {i+1}" for i in range(n)]

    fig = make_subplots(
        rows=n,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.01,
        subplot_titles=titles
    )

    for i, df in enumerate(df_list):
        fig.add_trace(go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name=titles[i]), row=i+1, col=1)

        indices_915 = df.index[(df.index.hour == 9) & (df.index.minute == 15)]
        print(indices_915)
        
        for idx_915 in indices_915:
            #. The vline should be below the candlestick
            loc_915 = df.index.get_loc(idx_915)
            fig.add_vline(x=loc_915, line_width=4, line_dash="dash", line_color="#FFEA00", row=i+1, col=1, layer="below")
            
        
    # Layout
    fig.update_layout(height=height_per_chart * n, xaxis_rangeslider_visible=False)

    # Hide rangesliders for all subplots beyond the first
    for i in range(2, n+1):
        fig.update_layout({f"xaxis{i}_rangeslider_visible": False})
    
    fig.update_xaxes(type="category")
    
  
    
    return fig

def run():
    
    BACKTEST_RESULTS_FOLDERPATH = "../Optiverse/backtest_results"
    # Initialize session state vars
    st.session_state.setdefault("selected_backtest_folder_name", None)
    st.session_state.setdefault('folderhash_to_foldername_map', get_folderhash_to_foldername_map(BACKTEST_RESULTS_FOLDERPATH))

    # UI header
    col = st.container()
    with col:
        st.markdown("---\n# Visualize Strategy : Visual Analysis of a Single Backtest")
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
    default_index = 0 if st.session_state.selected_backtest_folder_name is None else backtest_foldernames.index(st.session_state.selected_backtest_folder_name)
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
    dbc = DBConnector()

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
    
    ### SOME HASHES ###
    
    # 4707710022288195093
    # 8166016811902060856
    # 6770455715190846374
    ########
    
    ## Load dataframes
    df_portfolio_metrics = mengine.df_portfolio_metrics
    df_spot = dbc.df_spot.copy()
    df_spot = df_spot[df_spot.index >= df_portfolio_metrics.index.min()]

    # --- Sidebar inputs with keys ---
    min_date = df_portfolio_metrics.index.min().date()
    max_date = df_portfolio_metrics.index.max().date()

    # Sidebar inputs
    selected_start_date = st.sidebar.date_input("Start Date", min_value=min_date, max_value=max_date, value=min_date, key="sidebar_start_date")
    selected_start_time = st.sidebar.selectbox("Start Time", options=VALID_TIMES, index=0, key="sidebar_start_time")
    st.session_state.sidebar_start_ts = pd.Timestamp.combine(selected_start_date, selected_start_time)

    selected_end_date = st.sidebar.date_input("End Date", min_value=min_date, max_value=max_date, value=selected_start_date + pd.Timedelta(days=1), key="sidebar_end_date")
    selected_end_time = st.sidebar.selectbox("End Time", options=VALID_TIMES, index=0, key="sidebar_end_time")
    st.session_state.sidebar_end_ts = pd.Timestamp.combine(selected_end_date, selected_end_time)


    # Write session state vars of sidebar
    st.write(f"### Sidebar Start Date: {st.session_state.sidebar_start_date}")
    st.write(f"### Sidebar Start Time: {st.session_state.sidebar_start_time}")
    st.write(f"### Sidebar Start Timestamp: {st.session_state.sidebar_start_ts}")

    st.write(f"### Sidebar End Date: {st.session_state.sidebar_end_date}")
    st.write(f"### Sidebar End Time: {st.session_state.sidebar_end_time}")
    st.write(f"### Sidebar End Timestamp: {st.session_state.sidebar_end_ts}")
    



























    # df_spot = dbc.df_spot.copy()
    # df_spot = df_spot[df_spot.index >= df_portfolio_metrics.index.min()]
    # st.markdown("#### Summary of All Positions")
    # # st.dataframe(df_position_info, use_container_width=True)
    # # st.dataframe(df_portfolio_metrics, use_container_width=True)




    # if selected_start_timestamp > selected_end_timestamp:
    #     st.sidebar.error("Error: End date must fall after start date.")
        
    # else:


        



    #     # --- Display current state ---
    #     st.write(f"### Selected Time Range: {df_spot.index[st.session_state.start_idx]} to {df_spot.index[st.session_state.end_idx]}")
    #     st.write(f"Start Index: {st.session_state.start_idx}, End Index: {st.session_state.end_idx}")

    #     # --- Navigation buttons ---
    #     col_prev5, col_spacer, col_next5 = st.columns([1.75, 8, 1.75])
    #     with col_prev5:
    #         if st.button("⬅️ Prev5"):
    #             st.session_state.start_idx = max(0, st.session_state.start_idx - 5)
    #             st.session_state.end_idx = max(0, st.session_state.end_idx - 5)
    #     with col_next5:
    #         if st.button("➡️ Next5"):
    #             st.session_state.start_idx = min(len(df_spot) - 1, st.session_state.start_idx + 5)
    #             st.session_state.end_idx = min(len(df_spot) - 1, st.session_state.end_idx + 5)
                
                
    #     df_spot_window = df_spot.iloc[st.session_state.start_idx : st.session_state.end_idx + 1]
    #     fig = make_candlestick_subplot([df_spot_window, df_spot_window, df_spot_window], 
    #                                    titles=["Portfolio metrics", "Portfolio metrics", "Portfolio metrics"],
    #                                    height_per_chart=500)
    #     st.plotly_chart(fig, use_container_width=True)




        
    
    



























    
    
    
    



# # def run():
    
#     dbc = DBConnector()
#     df_stock1 = dbc.df_spot.copy()
#     df_stock2 = dbc.df_spot.copy()
#     df_stock3 = dbc.df_spot.copy()


#     if "start_idx" not in st.session_state:
#         st.session_state.start_idx = 0

#     # Window size
#     WINDOW = 125

#     col_prev15, col1_prev5, col_prev1, col_spacer, col_next1, col_next5, col_next15 = st.columns([1.75, 1.75, 1.75, 8, 1.75, 1.75, 1.75])
#     with col_prev15:
#         if st.button("⬅️ Prev15"):
#             st.session_state.start_idx = max(0, st.session_state.start_idx - 15)
#     with col1_prev5:
#         if st.button("⬅️ Prev5"):
#             st.session_state.start_idx = max(0, st.session_state.start_idx - 5)
#     with col_prev1:
#         if st.button("⬅️ Prev1"):
#             st.session_state.start_idx = max(0, st.session_state.start_idx - 1)
#     with col_next1:
#         if st.button("➡️ Next1"):
#             st.session_state.start_idx = min(len(df_stock1) - WINDOW, st.session_state.start_idx + 1)
#     with col_next5:
#         if st.button("➡️ Next5"):
#             st.session_state.start_idx = min(len(df_stock1) - WINDOW, st.session_state.start_idx + 5)
#     with col_next15:
#         if st.button("➡️ Next15"):
#             st.session_state.start_idx = min(len(df_stock1) - WINDOW, st.session_state.start_idx + 15)

#     # Subset of data
#     sub1 = df_stock1.iloc[st.session_state.start_idx : st.session_state.start_idx + WINDOW]
#     sub2 = df_stock2.iloc[st.session_state.start_idx : st.session_state.start_idx + WINDOW]
#     sub3 = df_stock3.iloc[st.session_state.start_idx : st.session_state.start_idx + WINDOW]

#     # Create subplot figure
#     fig = make_candlestick_subplot([sub1, sub2, sub3], titles=["Stock 1", "Stock 2", "Stock 3"], height_per_chart=500)

#     col1, col2 = st.columns([8, 2])
#     with col1:
#         st.plotly_chart(fig, use_container_width=True)
#     with col2:
#         st.markdown("### Current Window Indices:")
#         st.write(f"Start Index: {st.session_state.start_idx}")
#         st.write(f"End Index: {st.session_state.start_idx + WINDOW - 1}")
#         st.markdown("### Instructions:")
#         st.markdown("""
#         - Use the buttons to navigate through the data in increments of 1, 5, or 15.
#         - The candlestick charts will update to show the selected window of data.
#         - Yellow dashed vertical lines indicate 9:15 AM timestamps within the visible range.
#         """)
        
        
        
#     def split_candlestick(df, split_idx, name="Stock"):
#         """
#         Plots candlestick where candles before split_idx are black/white,
#         and after split_idx are colored.
#         """
#         # First segment (B/W candles)
#         trace_bw = go.Candlestick(
#             x=df.index[:split_idx],
#             open=df['open'][:split_idx],
#             high=df['high'][:split_idx],
#             low=df['low'][:split_idx],
#             close=df['close'][:split_idx],
#             name=f"{name} (B/W)",
#             increasing_line_color="black",
#             decreasing_line_color="black",
#             increasing_fillcolor="white",
#             decreasing_fillcolor="lightgrey"
#         )

#         # Second segment (colored candles)
#         trace_colored = go.Candlestick(
#             x=df.index[split_idx:],
#             open=df['open'][split_idx:],
#             high=df['high'][split_idx:],
#             low=df['low'][split_idx:],
#             close=df['close'][split_idx:],
#             name=f"{name} (Colored)",
#             increasing_line_color="darkgreen",   # border for bullish candles
#             decreasing_line_color="crimson",     # border for bearish candles
#             increasing_fillcolor="seagreen",   # fill for bullish candles
#             decreasing_fillcolor="deeppink",         # fill for bearish candles
#             # whiskerwidth=1                     # optional: thickness of wicks
#             )

#         fig = go.Figure(data=[trace_bw, trace_colored])
#         fig.update_layout(xaxis_rangeslider_visible=False, height=900, title=f"{name} Candlestick with Split at Index {split_idx}")
#         fig.update_xaxes(type="category")
        
#         return fig
    
    
#     fig = split_candlestick(sub1, split_idx=60, name="Stock 1")
#     st.plotly_chart(fig, use_container_width=True)