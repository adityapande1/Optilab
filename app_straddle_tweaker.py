import streamlit as st
import os
import plotly.graph_objects as go
import numpy as np
import pandas as pd
from utils.data_utils import read_parquet_data
import plotly.express as px


def _parse_foldercode(foldercode: str) -> dict:
    parts = foldercode.split('__')[1:]  # skip the first 'backtest'
    config = {}
    config['folder_code'] = foldercode

    for part in parts:
        key, *vals = part.split('_')
        if key == 'callrisk':
            config['call_risk'] = int(vals[0])
        elif key == 'putrisk':
            config['put_risk'] = int(vals[0])
        elif key == 'entrytime':
            h, m = vals
            config['entry_time'] = f'{int(h):02d}:{int(m):02d}:00'
        elif key == 'exittime':
            h, m = vals
            config['exit_time'] = f'{int(h):02d}:{int(m):02d}:00'
        elif key == 'trail':
            # if it has a risk value -> True, else False
            config['trail_risk'] = bool(int(vals[1])) if len(vals) > 1 else True

    return config


def _generate_foldercode(entry_time: str, exit_time: str, call_risk: int, put_risk: int, trail_risk: bool) -> str:
    entry_h, entry_m = map(int, entry_time.split(':')[:2])
    exit_h, exit_m = map(int, exit_time.split(':')[:2])
    foldercode = f'backtest__callrisk_{call_risk}__putrisk_{put_risk}__entrytime_{entry_h}_{entry_m}__exittime_{exit_h}_{exit_m}'
    if trail_risk:
        foldercode += '__trail_risk_1'
    else:
        foldercode += '__trail_risk_0'
    return foldercode


def _display_config_dict(config: dict):
    """
    Display a configuration dictionary in Streamlit:
    - Shows folder_code at the top in a big highlighted box.
    - Shows the other key-value pairs in 5 small columns with card-like styling.
    """

    # --- Folder Code at top ---
    st.markdown(
        f"""
        <div style="padding:10px; border-radius:10px; background-color:#f0f2f6; 
                    font-size:26px; font-weight:bold; text-align:center;">
            {config.get('folder_code', '')}
        </div>
        """,
        unsafe_allow_html=True,
    )

    # --- Next row in 5 columns ---
    keys = [k for k in config.keys() if k != 'folder_code']
    cols = st.columns(len(keys))

    for col, key in zip(cols, keys):
        col.markdown(
            f"""
            <div style="padding:12px; border-radius:10px; background-color:white; 
                        box-shadow:0 2px 4px rgba(0,0,0,0.1); text-align:center; 
                        font-size:20px;">
                <b>{key.replace('_', ' ').title()}</b><br>
                {config[key]}
            </div>
            """,
            unsafe_allow_html=True,
        )


def stem_plot(df, colname='daily_pnl'):
    fig = go.Figure()

    # Separate positive and negative values
    pos_mask = df[colname] >= 0
    neg_mask = df[colname] < 0

    # Positive stems
    fig.add_trace(go.Scatter(x=df.index[pos_mask], y=df[colname][pos_mask], mode='markers', marker=dict(color='green', size=8), name=f'Positive {colname}'))

    for x, y in zip(df.index[pos_mask], df[colname][pos_mask]):
        fig.add_trace(go.Scatter(x=[x, x], y=[0, y], mode='lines', line=dict(color='green', width=2), showlegend=False))

    # Negative stems
    fig.add_trace(go.Scatter(x=df.index[neg_mask], y=df[colname][neg_mask], mode='markers', marker=dict(color='red', size=8), name=f'Negative {colname}'))

    for x, y in zip(df.index[neg_mask], df[colname][neg_mask]):
        fig.add_trace(go.Scatter(x=[x, x], y=[0, y], mode='lines', line=dict(color='red', width=2), showlegend=False))

    # Layout
    fig.update_layout(title=f'{colname} Stem Plot', xaxis_title='Date', yaxis_title=colname, showlegend=True, template='plotly_white', height=500)

    return fig


@st.cache_data
def _get_backtest_dataframes(backtest_dir):
    # Load all DataFrames from the backtest directory
    hash2position_dfs, df_portfolio_metrics = {}, None
    all_parquet_dfs = [f for f in os.listdir(backtest_dir) if f.endswith('.parquet')]

    for df_filename in all_parquet_dfs:
        if df_filename.startswith('df_position') and df_filename.endswith('.parquet'):
            hash_value = df_filename[len('df_position_') : -len('.parquet')]
            hash2position_dfs[int(hash_value)] = read_parquet_data(os.path.join(backtest_dir, df_filename))
        elif df_filename == 'df_portfolio_metrics.parquet':
            df_portfolio_metrics = read_parquet_data(os.path.join(backtest_dir, df_filename))

    return hash2position_dfs, df_portfolio_metrics


BACKTEST_RESULTS_DIR = os.path.join('..', 'OptiverseDelete', 'backtest_results_old')


def run():
    cols = st.columns([7, 1])
    with cols[0]:
        st.markdown('---\n# Straddle Tweaker \n---')
    with cols[1]:
        st.image('./metadata/straddle_tweaker/cute_cat.gif', width=250)

    backtest_foldercodes = [foldercode for foldercode in os.listdir(BACKTEST_RESULTS_DIR) if os.path.isdir(os.path.join(BACKTEST_RESULTS_DIR, foldercode)) and foldercode.startswith('backtest_')]
    backtest_foldercodes.sort()  # Ensure consistent ordering
    foldercode2config = {foldercode: _parse_foldercode(foldercode) for foldercode in backtest_foldercodes}
    df_codes = pd.DataFrame(foldercode2config.values())

    ###############################
    # Sidebar Selections
    ###############################
    st.sidebar.header('Simulation Parameters')
    selected_entry_time = st.sidebar.selectbox('Select Entry Time', options=sorted(df_codes['entry_time'].unique()))  # 1. Entry Time Dropdown
    selected_exit_time = st.sidebar.selectbox('Select Exit Time', options=sorted(df_codes['exit_time'].unique()))  # 2. Exit Time Dropdown

    st.sidebar.markdown('---')
    st.sidebar.title('Select Risk (CR : CallRisk | PR : PutRisk)')
    selected_CRPR = None
    call_risks = df_codes['call_risk'].unique().tolist()
    put_risks = df_codes['put_risk'].unique().tolist()

    # First row: empty corner + x labels
    cols = st.sidebar.columns(len(call_risks) + 1)
    cols[0].markdown('**PR \\ CR**')  # corner
    for i, call_risk in enumerate(call_risks):
        cols[i + 1].markdown(f'**{call_risk}**')

    # Next rows: y label + buttons
    for put_risk in put_risks:
        cols = st.sidebar.columns(len(call_risks) + 1)
        cols[0].markdown(f'**{put_risk}**')  # y label
        for i, call_risk in enumerate(call_risks):
            if cols[i + 1].button(' ', key=f'{call_risk}_{put_risk}'):  # empty button, unique key
                selected_CRPR = (call_risk, put_risk)

    st.sidebar.markdown('---')
    selected_trail_risk = st.sidebar.toggle('Trail Risk', value=True, help='Toggle on for True, off for False')  # 3. Trail Risk Toggle
    if selected_CRPR:
        # st.sidebar.success(f"Selected point: {selected_point}")
        st.sidebar.success(f'Call Risk = {selected_CRPR[0]}, Put Risk = {selected_CRPR[1]}')

    if selected_CRPR is not None:
        selected_foldercode = _generate_foldercode(entry_time=selected_entry_time, exit_time=selected_exit_time, call_risk=selected_CRPR[0], put_risk=selected_CRPR[1], trail_risk=selected_trail_risk)
        # Display configuration for the selected folder code
        _display_config_dict(foldercode2config.get(selected_foldercode, {'folder_code': 'N/A'}))
        st.markdown('---')
        ###############################
        # Sidebar Selections
        ###############################

        ###############################
        # HeatMap Thingy
        ###############################

        ###############################
        # HeatMap Thingy
        ###############################

        hash2position_dfs, df_portfolio_metrics = _get_backtest_dataframes(os.path.join(BACKTEST_RESULTS_DIR, selected_foldercode))
        # EOD metrics
        assert 'pnl' in df_portfolio_metrics.columns
        df_portfolio_metrics.sort_index(inplace=True)
        df_metrics_eod = df_portfolio_metrics[df_portfolio_metrics.index.time == pd.Timestamp('15:29:00').time()].copy()
        df_metrics_eod['daily_pnl'] = df_metrics_eod['pnl'].diff().values
        df_metrics_eod.iloc[0, df_metrics_eod.columns.get_loc('daily_pnl')] = df_metrics_eod['pnl'].iloc[0]

        ###############################
        # Daily PnL
        ###############################

        if df_portfolio_metrics is not None:
            first_bt_date, last_bt_date = df_portfolio_metrics.index.min().strftime('%Y-%m-%d'), df_portfolio_metrics.index.max().strftime('%Y-%m-%d')
            all_bt_dates = sorted(list(set(df_portfolio_metrics.index.strftime('%Y-%m-%d').tolist())))

            st.sidebar.subheader('Start PnL Date')
            initial_backtest_date = st.sidebar.selectbox('Select Initial Backtest Date', all_bt_dates, index=0)
            # st.sidebar.write(f"**Initial Backtest Date:** {initial_backtest_date}")

            # select date in sidebar
            st.sidebar.subheader('End PnL Date')
            final_backtest_dates = [d for d in all_bt_dates if d >= initial_backtest_date]
            final_backtest_date = st.sidebar.selectbox('Select Final Backtest Date', final_backtest_dates, index=len(final_backtest_dates) - 1)
            # st.sidebar.write(f"**Final Backtest Date:** {final_backtest_date}")

            # Filter the DataFrames based on the selected dates
            df_metrics_filtered = df_metrics_eod[(df_metrics_eod.index >= initial_backtest_date) & (df_metrics_eod.index <= final_backtest_date)]

            with st.sidebar:
                st.header('📅 Select Days')
                mon = st.toggle('Monday', value=True)
                tue = st.toggle('Tuesday', value=True)
                wed = st.toggle('Wednesday', value=True)
                thu = st.toggle('Thursday', value=True)
                fri = st.toggle('Friday', value=True)

            # Example usage
            selected_days = [day for day, enabled in zip(['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'], [mon, tue, wed, thu, fri]) if enabled]

            df_metrics_filtered = df_metrics_filtered[df_metrics_filtered.index.day_name().isin(selected_days)].copy()
            num_unique_days = len(df_metrics_filtered.index.normalize().unique())
            total_daily_pnl = df_metrics_filtered['daily_pnl'].sum()
            top_five_losses = df_metrics_filtered.nsmallest(5, 'daily_pnl')
            top_five_profits = df_metrics_filtered.nlargest(5, 'daily_pnl')
            col1, col2, col3 = st.columns([1, 2.5, 1])
            with col1:
                st.subheader(f'Total PnL: {total_daily_pnl:.2f}')
            with col2:
                st.subheader(f'Selected Days : {", ".join(selected_days)}')
            with col3:
                st.subheader(f'Total Days: {num_unique_days}')

            # Example usage
            fig = stem_plot(df_metrics_filtered, colname='daily_pnl')
            st.plotly_chart(fig, use_container_width=True)

            col1, col2 = st.columns(2)
            with col1:
                st.subheader('Top 5 Daily Losses')
                st.write(top_five_losses[['daily_pnl']])
            with col2:
                st.subheader('Top 5 Daily Profits')
                st.write(top_five_profits[['daily_pnl']])

    ###############################
    # Daily PnL
    ###############################

    # # Sample DataFrame
    # df_pnl = pd.DataFrame({
    #     'call_risk': [1000, 1000, 1000, 1000, 2000,  2000, 2000, 2000, 3000, 3000, 3000, 3000, 4000, 4000, 4000, 4000],
    #     'put_risk':  [1000, 2000, 4000, 3000, 1000,  2000, 4000, 3000, 1000, 2000, 4000, 3000, 1000, 2000, 4000, 3000],
    #     'total_pnl': [1234, 1123, None, None, -3211, -997, None, 1070, None, None, None, -1122, 1080, 1511, 124, 3988]
    # })

    # # Fill missing values with 0 (or any value you prefer)
    # df_pnl['total_pnl'] = df_pnl['total_pnl'].fillna(0)

    # # Create pivot table for heatmap
    # heatmap_data = df_pnl.pivot(index='put_risk', columns='call_risk', values='total_pnl')

    # # Plot heatmap
    # fig = px.imshow(
    #     heatmap_data,
    #     labels=dict(x="Call Risk", y="Put Risk", color="PnL"),
    #     x=heatmap_data.columns,
    #     y=heatmap_data.index,
    #     color_continuous_scale='RdYlGn',  # Green to Red
    #     origin='lower'
    # )

    # fig.update_layout(
    #     title="PnL Heatmap",
    #     xaxis_title="Call Risk",
    #     yaxis_title="Put Risk",
    # )

    # # Display in Streamlit
    # st.plotly_chart(fig)
