import os
from typing import List

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots
import streamlit.components.v1 as components
from backtest.backtest_analyzer import BacktestAnalyzer
from connectors.dbconnector import DBConnector
from optilab_constants import BACKTEST_RESULTS_FOLDERPATH
from optilab_utils.display_utils import display_backtest_details, display_page_title
from optilab_utils.file_utils import get_all_folders_in_directory, get_backtest_directory_maps
from optilab_utils.input_utils import get_backtest_folder_and_hash_input

VALID_TIMES = pd.date_range('09:15', '15:29', freq='1min').time

import streamlit as st
import streamlit.components.v1 as components


def display_text_container(
    text,
    height=450,
    border_color='#524f50',
    border_radius=12,
    box_shadow='2px 2px 8px rgba(0,0,0.25,0.25)',
    padding=4,
    font_size=18,
    font_family='Courier New, monospace',  # Other options: 'Courier New, monospace', 'Georgia, serif', 'Times New Roman, serif'
    font_weight='bold',
    text_color='black',
    text_align='center',
    line_height=1.5,
    background_color='white',
):
    """
    Display a stylish scrollable box with custom text using HTML and CSS in Streamlit.

    """
    html = f"""
    <div style="
        height: {height}px;
        overflow-y: auto;
        border: 8px solid {border_color};
        border-radius: {border_radius}px;
        box-shadow: {box_shadow};
        padding: {padding}px;
        box-sizing: border-box;
        font-size: {font_size}px;
        font-family: {font_family};
        font-weight: {font_weight};
        color: {text_color};
        text-align: {text_align};
        line-height: {line_height};
        background-color: {background_color};
        white-space: pre-wrap;

        display: flex;
        justify-content: center; /* horizontal centering */
        align-items: center;     /* vertical centering */
        text-align: {text_align};
    ">
        {text}
    </div>
    """

    components.html(html, height=height + padding * 2 + 20)


def plot_multi_candlesticks(stock_info_dict):
    n_stocks = len(stock_info_dict)

    fig = make_subplots(rows=n_stocks, cols=1, shared_xaxes=True, vertical_spacing=0.03, subplot_titles=list(stock_info_dict.keys()))

    for i, (stock_name, info) in enumerate(stock_info_dict.items(), start=1):
        df = info['dataframe']
        start_ts = info['redgreen_timestamp_start']
        end_ts = info['redgreen_timestamp_end']
        vlines_map = info.get('vlines_timestamp_to_color_map', {})

        # Masks
        rg_mask = (df.index >= start_ts) & (df.index <= end_ts)
        bw_mask = ~rg_mask

        df_rg = df[rg_mask]
        df_bw = df[bw_mask]

        # --- Red & Green candles first ---
        if not df_rg.empty:
            fig.add_trace(
                go.Candlestick(
                    x=df_rg.index,
                    open=df_rg['open'],
                    high=df_rg['high'],
                    low=df_rg['low'],
                    close=df_rg['close'],
                    increasing_line_color='green',
                    increasing_fillcolor='green',
                    decreasing_line_color='crimson',
                    decreasing_fillcolor='crimson',
                    showlegend=False,
                    name=f'{stock_name} R/G',
                ),
                row=i,
                col=1,
            )

        # --- Black & White candles ---
        if not df_bw.empty:
            fig.add_trace(
                go.Candlestick(
                    x=df_bw.index,
                    open=df_bw['open'],
                    high=df_bw['high'],
                    low=df_bw['low'],
                    close=df_bw['close'],
                    increasing_line_color='black',
                    increasing_fillcolor='white',
                    decreasing_line_color='black',
                    decreasing_fillcolor='black',
                    showlegend=False,
                    name=f'{stock_name} B&W',
                ),
                row=i,
                col=1,
            )

        # Vertical lines
        for ts, color in vlines_map.items():
            # get the row id given ts timestamp, when df is datetime index
            ts_id_array = df.index.get_indexer([ts], method='nearest')
            ts_id = ts_id_array[0] if ts_id_array[0] != -1 else None

            # Add semi-transparent vertical line if ts_id is found
            if ts_id is not None:
                fig.add_vline(x=ts_id, line=dict(color=color, width=6, dash='solid'), opacity=0.5, row=i, col=1, layer='below')

    # Layout
    fig.update_layout(height=500 * n_stocks, template='plotly_white', margin=dict(l=20, r=20, t=40, b=20))

    # Disable range sliders
    for i in range(1, n_stocks + 1):
        fig.update_xaxes(rangeslider_visible=False, row=i, col=1)
    fig.update_xaxes(type='category')

    st.plotly_chart(fig, use_container_width=True)


# Cache only the folder hash, not the backtest analyzer object
@st.cache_data(hash_funcs={BacktestAnalyzer: lambda _: None})
def get_position_info_dataframe(backtest_analyzer: BacktestAnalyzer, folder_hash: str):
    option_dicts = []
    for order_hash in backtest_analyzer.action_hashes:
        option_dict = {}
        option_dict['action_hash'] = order_hash
        option_dict['action_key'] = backtest_analyzer.get_action(order_hash).key
        df_position = backtest_analyzer.get_df_position(position_hash=order_hash)
        option_dict['pos_entry_ts'] = df_position.index[0] if len(df_position) > 0 else None
        option_dict['pos_exit_ts'] = df_position.index[-1] if len(df_position) > 0 else None
        option_dicts.append(option_dict)

    df_all_positions = pd.DataFrame(option_dicts)
    df_all_positions = df_all_positions.sort_values(by=['pos_entry_ts', 'pos_exit_ts']).reset_index(drop=True)
    return df_all_positions


def filter_position_info(df_position_info: pd.DataFrame, df_spot_filtered: pd.DataFrame) -> pd.DataFrame:
    first_ts, last_ts = df_spot_filtered.index[0], df_spot_filtered.index[-1]


def run():
    # display_page_title(title="Visualize Backtest", about="Candlestick Visualizations for a given backtest run")

    BACKTEST_RESULTS_DIR = '../Optiverse/backtest_results/weekly_straddle_selected/'
    foldername_to_folderhash_map, folderhash_to_foldername_map = get_backtest_directory_maps(BACKTEST_RESULTS_DIR)
    backtest_foldernames = [None] + get_all_folders_in_directory(BACKTEST_RESULTS_DIR)
    selected_foldername, selected_folderhash = get_backtest_folder_and_hash_input(backtest_foldernames, folderhash_to_foldername_map, foldername_to_folderhash_map)

    if selected_foldername is not None:
        st.session_state.setdefault('dbconnector', DBConnector())
        st.session_state.setdefault('available_backtest_timestamps', st.session_state.dbconnector.df_spot.index)
        st.session_state.setdefault('analysis_timestamp_id', 0)

        backtest_analyzer = BacktestAnalyzer(backtest_results_dir=BACKTEST_RESULTS_DIR, backtest_folder_name=selected_foldername)

        ## Load dataframes
        df_portfolio_metrics = backtest_analyzer.get_df_portfolio_metrics()
        available_backtest_dates = np.unique(df_portfolio_metrics.index.date)
        first_backtest_date, last_backtest_date = available_backtest_dates.min(), available_backtest_dates.max()

        # Sidebar inputs
        selected_analysis_date = st.sidebar.date_input('Start Date', min_value=first_backtest_date, max_value=last_backtest_date, value=first_backtest_date, key='sidebar_analysis_date')
        selected_analysis_time = st.sidebar.selectbox('Start Time', options=VALID_TIMES, index=0, key='sidebar_analysis_time')
        selected_num_future_bars = st.sidebar.number_input('Number of Future Bars to Display', min_value=1, max_value=1500, value=100, step=1, key='sidebar_num_future_bars')

        # Compute timestamp from date/time input
        input_timestamp = pd.Timestamp.combine(selected_analysis_date, selected_analysis_time)

        # Only update index if the user manually changes date/time
        if 'last_input_timestamp' not in st.session_state or st.session_state.last_input_timestamp != input_timestamp:
            st.session_state.analysis_timestamp_id = np.searchsorted(st.session_state.available_backtest_timestamps, input_timestamp)
        st.session_state.last_input_timestamp = input_timestamp

        # Next / Previous buttons with step sizes
        col_prev15, col_prev5, col_prev1, col_spacer, col_next1, col_next5, col_next15 = st.columns([1, 1, 1, 6, 1, 1, 1])
        with col_prev15:
            if st.button('Prev15') and st.session_state.analysis_timestamp_id >= 15:
                st.session_state.analysis_timestamp_id -= 15
        with col_prev5:
            if st.button('Prev5') and st.session_state.analysis_timestamp_id >= 5:
                st.session_state.analysis_timestamp_id -= 5
        with col_prev1:
            if st.button('Prev1') and st.session_state.analysis_timestamp_id >= 1:
                st.session_state.analysis_timestamp_id -= 1
        with col_next1:
            if st.button('Next1') and st.session_state.analysis_timestamp_id <= len(st.session_state.available_backtest_timestamps) - 2:
                st.session_state.analysis_timestamp_id += 1
        with col_next5:
            if st.button('Next5') and st.session_state.analysis_timestamp_id <= len(st.session_state.available_backtest_timestamps) - 6:
                st.session_state.analysis_timestamp_id += 5
        with col_next15:
            if st.button('Next15') and st.session_state.analysis_timestamp_id <= len(st.session_state.available_backtest_timestamps) - 16:
                st.session_state.analysis_timestamp_id += 15

        # Update the selected timestamp based on the session state
        selected_analysis_timestamp = st.session_state.available_backtest_timestamps[st.session_state.analysis_timestamp_id]

        # Filter data
        stock_info_dict = {}

        ####### SPOT DICT #########
        df_spot_filtered = st.session_state.dbconnector.df_spot[st.session_state.dbconnector.df_spot.index >= selected_analysis_timestamp].head(selected_num_future_bars).copy()

        # current_timestamp is the middle index of the df_spot_filtered
        current_timestamp = df_spot_filtered.index[len(df_spot_filtered) // 2]

        spot_dict = {
            'dataframe': df_spot_filtered,
            'redgreen_timestamp_start': df_spot_filtered.index[0],
            'redgreen_timestamp_end': df_spot_filtered.index[-1],
        }
        spot_dict['vlines_timestamp_to_color_map'] = {}
        for index, row in df_spot_filtered.iterrows():
            if index.time() == pd.Timestamp('09:15').time():
                spot_dict['vlines_timestamp_to_color_map'][index] = 'goldenrod'

        spot_dict['vlines_timestamp_to_color_map'][current_timestamp] = 'lightgrey'
        stock_info_dict['SPOT'] = spot_dict
        ##########################

        ### get all associated options
        df_position_info = get_position_info_dataframe(backtest_analyzer, backtest_analyzer.folder_hash)

        df_position_info['is_active'] = ((df_position_info['pos_entry_ts'] <= df_spot_filtered.index[-1]) & (df_position_info['pos_exit_ts'] >= df_spot_filtered.index[0])).astype(int)

        df_position_info = df_position_info[df_position_info['is_active'] == 1].reset_index(drop=True)

        # st.dataframe(df_position_info)

        # ####### OPTIONS DICT #########
        for idx, row in df_position_info.iterrows():
            position_info_dict = {}

            action = backtest_analyzer.get_action(row['action_hash'])
            # st.write(action)

            df_option = DBConnector().get_option_df(option_type=action.option_type, strike=action.strike, expiry_date=action.expiry)
            position_info_dict['action_hash'] = row['action_hash']
            position_info_dict['dataframe'] = df_option.loc[df_spot_filtered.index]
            position_info_dict['redgreen_timestamp_start'] = row['pos_entry_ts']
            position_info_dict['redgreen_timestamp_end'] = row['pos_exit_ts'] if row['pos_exit_ts'] is not None else df_option.index[-1]

            position_info_dict['vlines_timestamp_to_color_map'] = {row['pos_entry_ts']: 'lightpink' if action.trade_type == 'short' else 'palegreen', current_timestamp: 'lightgrey'}

            stock_info_dict[f'HASH : {row["action_hash"]}  | {row["action_key"]}'] = position_info_dict

        col_candlestick, col_text = st.columns([4, 1])
        with col_candlestick:
            plot_multi_candlesticks(stock_info_dict=stock_info_dict)
        total_pnl = 0
        with col_text:
            for key, info_dict in stock_info_dict.items():
                if key == 'SPOT':
                    display_text_container(text=f'\n{key}\n{current_timestamp}\nDay of Week : {current_timestamp.day_name()}', border_color='lightgrey')
                else:
                    df_position = backtest_analyzer.get_df_position(position_hash=info_dict['action_hash'])
                    if current_timestamp in df_position.index:
                        current_pnl = df_position.loc[current_timestamp, 'pnl']
                        total_pnl += current_pnl
                        text_to_display = (
                            f'\n{info_dict["action_hash"]}\nPosition ACTIVE'
                            f'\nEntry: {info_dict["redgreen_timestamp_start"]}\nExit: {info_dict["redgreen_timestamp_end"]}'
                            f'\n\nCurrent PnL: {current_pnl:.4f}'
                        )
                        display_text_container(text=text_to_display, border_color='crimson' if current_pnl < 0 else 'green')
                    else:
                        text_to_display = f'\n{info_dict["action_hash"]}\nPosition INACTIVE'
                        display_text_container(text=text_to_display, border_color='lightgrey')

        display_text_container(text=f'TOTAL PnL ACROSS POSITIONS ::::: {total_pnl:.4f}', border_color='crimson' if total_pnl < 0 else 'green', height=120, font_size=28)

        # display_backtest_details(backtest_analyzer)
        st.write(f'Timestamp ID: {st.session_state.analysis_timestamp_id} / {len(st.session_state.available_backtest_timestamps)}')
        st.success(f'Selected Analysis Timestamp: {selected_analysis_timestamp}')

        st.dataframe(df_position_info)
