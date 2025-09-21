import streamlit as st
from connectors.dbconnector import DBConnector
from utils.data_utils import resample_stock_data
import pandas as pd
from optilab_utils.viz_utils import labeled_box, info_box

import plotly.express as px

import numpy as np

import numpy as np

def plot_histogram(df: pd.DataFrame, colname: str, height: int = 600, nbins: int = 200, tick_size: int = 28):
    fig = px.histogram(
        df, 
        x=colname, 
        nbins=nbins,  
        marginal="box",  
        hover_data=df.columns,
        title=f"Histogram of {colname}",
        color_discrete_sequence=["#6495ed"],
        height=height
    )

    # Layout with gridlines
    fig.update_layout(
        xaxis_title=colname,
        yaxis_title="Count",
        template="plotly_white",
        bargap=0.1,
        hovermode="x unified",
        xaxis=dict(
            tickfont=dict(size=tick_size),
            gridcolor="lightgray",
            gridwidth=0.5,
            showgrid=True
        ),
        yaxis=dict(
            tickfont=dict(size=tick_size),
            gridcolor="lightgray",
            gridwidth=0.5,
            showgrid=True
        )
    )
    fig.update_traces(
        marker_line_width=1.5, 
        marker_line_color="black", 
        opacity=1.0, 
        selector=dict(type='histogram')
    )
    
    # Rug trace
    fig.add_trace(px.scatter(df, x=colname, y=[0]*len(df)).data[0])

    # Compute stats
    values = df[colname].dropna()
    mean_val = values.mean()
    sigma = values.std()

    # Vertical lines behind bars
    fig.add_vline(x=mean_val, line_color="#0047ab", line_width=3, layer="below", line_dash="solid")
    fig.add_vline(x=mean_val - sigma, line_color="#367588", line_width=2, layer="below", line_dash="dashdot")
    fig.add_vline(x=mean_val - 2*sigma, line_color="#367588", line_width=2, layer="below", line_dash="dashdot")
    fig.add_vline(x=mean_val + sigma, line_color="#367588", line_width=2, layer="below", line_dash="dashdot")
    fig.add_vline(x=mean_val + 2*sigma, line_color="#367588", line_width=2, layer="below", line_dash="dashdot")

    # Annotations at the top (aligned with lines)
    fig.add_annotation(x=mean_val, y=1.1, yref="paper", text=f"Mean (μ) <br> {mean_val:.4f}", showarrow=False, font=dict(color="black", size=int(tick_size*.8)))
    fig.add_annotation(x=mean_val - sigma, y=1.1, yref="paper", text=f"μ - 1σ <br> {mean_val - sigma:.4f}", showarrow=False, font=dict(color="black", size=int(tick_size*.8)))
    fig.add_annotation(x=mean_val + sigma, y=1.1, yref="paper", text=f"μ + 1σ <br> {mean_val + sigma:.4f}", showarrow=False, font=dict(color="black", size=int(tick_size*.8)))
    fig.add_annotation(x=mean_val + 2*sigma, y=1.1, yref="paper", text=f"μ + 2σ <br> {mean_val + 2*sigma:.4f}", showarrow=False, font=dict(color="black", size=int(tick_size*.8)))
    fig.add_annotation(x=mean_val - 2*sigma, y=1.1, yref="paper", text=f"μ - 2σ <br> {mean_val - 2*sigma:.4f}", showarrow=False, font=dict(color="black", size=int(tick_size*.8)))

    # nu greek mean sign
    print("μ")

    return fig

def opening_gap_pct(df):

    if 'opening_gap_pct' not in df.columns:
        df['opening_gap_pct'] = (df['open'] - df['close'].shift(1)) / df['close'].shift(1) * 100

    about = "`opening_gap_pct` \n### $\\frac{\\text{(today's open - previous day's close)}}{\\text{previous day's close}} \\times 100$"
    about = f"### {about}"
    return about

def daily_range(df, display_about=True):

    if 'daily_range' not in df.columns:
        df['daily_range'] = df['high'] - df['low']

    
    about = "`daily_range` \n### $\\text{today's high} - \\text{today's low}$"
    about = f"### {about}"
    return about

def daily_body(df, display_about=True):

    if 'daily_body' not in df.columns:
        df['daily_body'] = (df['close'] - df['open']).abs()

    about = "`daily_body` \n### $|\\text{today's close} - \\text{today's open}|$"
    about = f"### {about}"
    return about

def daily_movement_pct(df, display_about=True):

    if 'daily_movement_pct' not in df.columns:
        df['daily_movement_pct'] = (df['close'] - df['open']) / df['open'] * 100

    about = "`daily_movement_pct` \n### $\\frac{\\text{(today's close - today's open)}}{\\text{today's open}} \\times 100$"
    about = f"### {about}"

    return about

def opening_extrema_pct(df, display_about=True):

    if 'opening_extrema_pct' not in df.columns:
        df['opening_extrema_pct_high'] = abs(df['high'] - df['close'].shift(1)) / df['close'].shift(1) * 100
        df['opening_extrema_pct_low'] = abs(df['low'] - df['close'].shift(1)) / df['close'].shift(1) * 100
        # find max of the two
        df['opening_extrema_pct'] = df[['opening_extrema_pct_high', 'opening_extrema_pct_low']].max(axis=1)
        df.drop(columns=['opening_extrema_pct_high', 'opening_extrema_pct_low'], inplace=True)

    about = "`opening_extrema_pct` = max(val1, val2)"
    about += "\n### val1 = $\\frac{\\text{|(today's high - previous day's close)|}}{\\text{previous day's close}} \\times 100$ \n### val2 = $\\frac{\\text{|(today's low - previous day's close)|}}{\\text{previous day's close}} \\times 100$ \n"
    about = f"### {about}"
    
    return about


def close_to_close_pct(df):
    
    if 'close_to_close_pct' not in df.columns:
        df['close_to_close_pct'] = (df['close'] - df['close'].shift(1)) / df['close'].shift(1) * 100

    about = "`close_to_close_pct` \n### $\\frac{\\text{(today's close - previous day's close)}}{\\text{previous day's close}} \\times 100$"
    about = f"### {about}"
    return about



def stats_summary(df, colname):
    desc = df[colname].describe().to_dict()
    st.markdown(f"""
    **{colname} Statistics Summary:**
    - Count: {desc['count']:.0f}
    - Mean: {desc['mean']:.4f}
    - Std: {desc['std']:.4f}
    - Min: {desc['min']:.4f}
    - 25%: {desc['25%']:.4f}
    - 50% (Median): {desc['50%']:.4f}
    - 75%: {desc['75%']:.4f}
    - Max: {desc['max']:.4f}
    """)

def filter_df_by_quantiles(df, colname, quantile_lower=0, quantile_upper=100):
    lower_bound = df[colname].quantile(quantile_lower / 100)
    upper_bound = df[colname].quantile(quantile_upper / 100)
    filtered_df = df[(df[colname] >= lower_bound) & (df[colname] <= upper_bound)].copy()
    return filtered_df


def run():

    st.markdown("---\n# Nifty Visualization \n---")
    
    ##### Load Data ##### 
    dbconnector = DBConnector()
    df_nifty_1min = dbconnector.df_spot.copy()
    # df_nifty_1min = df_nifty_1min[df_nifty_1min.index >= '2023-10-01']
    df_nifty_daily = resample_stock_data(df=df_nifty_1min, interval=375)
    df_nifty_daily.index = df_nifty_daily.index.normalize()

    ##### Date Selection Sidebar #####
    unique_dates = df_nifty_daily.index.normalize().unique().sort_values()
    st.sidebar.markdown("# Select Date Range")
    selected_start_date = st.sidebar.date_input(
        "Start Date",
        value=unique_dates[0].date(),
        min_value=unique_dates[0].date(),
        max_value=unique_dates[-1].date()
    )
    min_end_date = unique_dates[unique_dates >= pd.to_datetime(selected_start_date)][0]
    selected_end_date = st.sidebar.date_input(
        "End Date",
        value=unique_dates[-1].date(),
        min_value=min_end_date.date(),
        max_value=unique_dates[-1].date()
    )
    df_nifty_daily = df_nifty_daily[
        (df_nifty_daily.index >= pd.to_datetime(selected_start_date)) &
        (df_nifty_daily.index <= pd.to_datetime(selected_end_date))
    ]

    st.sidebar.write(f"Selected Date Range: {selected_start_date} to {selected_end_date}")
    col1, col2, col3 = st.columns([12, 12, 4])
    with col1:
        labeled_box(title='Start Date', value=str(selected_start_date))
    with col2:
        labeled_box(title='End Date', value=str(selected_end_date))
    with col3:
        labeled_box(title='Total Days Analysed', value=len(df_nifty_daily))

    #####################################################################################################################################
    ########## Histogram & stats Vizualization of Daily  ################################################################################
    #####################################################################################################################################

    hist_fields = [None, 'opening_gap_pct', 'daily_range', 'daily_body', 'daily_movement_pct', 'opening_extrema_pct', 'close_to_close_pct']
    hist_field_to_field_function = {
        'opening_gap_pct': opening_gap_pct,
        'daily_range': daily_range,
        'daily_body': daily_body,
        'daily_movement_pct': daily_movement_pct,
        'opening_extrema_pct': opening_extrema_pct,
        'close_to_close_pct': close_to_close_pct,
    }
    # Give radio button options to select histogram field
    hist_field = st.sidebar.radio("Select Histogram Field", hist_fields, index=0)

    st.sidebar.markdown('---')
    st.sidebar.markdown(f"# `{hist_field}`")
    
    if hist_field is None:
        st.info("Select a histogram field from the sidebar to visualize its distribution.")
    else:
        field_calculator_function = hist_field_to_field_function[hist_field]
        about = field_calculator_function(df_nifty_daily)

        col_quantile, col_histogram = st.columns([2.5, 7.5])
        with col_quantile:
            st.markdown("---")
            st.markdown(f"## Calculation")
            st.markdown(about)
            st.markdown("---")

            st.markdown(f"## Select Quantiles")
            # Two select boxes for quantile selection
            q_lower_col, q_upper_col = st.columns(2)
            with q_lower_col:
                quantile_lower = st.selectbox("Select Lower Quantile Percentage", options=[i / 2 for i in range(201)], index=2)
            with q_upper_col:
                quantile_upper = st.selectbox("Select Upper Quantile Percentage", options=[i / 2 for i in range(201)], index=198)
            if quantile_lower > quantile_upper:
                st.error("Error: Upper Quantile must be greater than or equal to Lower Quantile.")

            st.markdown("---")
            st.markdown(f"## Select Bins")
            num_bins = st.slider("Number of Bins", min_value=10, max_value=500, value=100, step=1)

        with col_histogram:
            df_nifty_daily_filtered = filter_df_by_quantiles(df_nifty_daily,hist_field, quantile_lower=quantile_lower, quantile_upper=quantile_upper)
            fig = plot_histogram(df_nifty_daily_filtered, colname=hist_field, height=800, nbins=num_bins)
            stats_dict = df_nifty_daily_filtered[hist_field].describe().to_dict()
            st.plotly_chart(fig, use_container_width=True)
    
        cols = st.columns(len(stats_dict))
        for col, (key, value) in zip(cols, stats_dict.items()):
            with col:
                labeled_box(title=key.capitalize(), value=f"{value:.3f}")

        top10 = df_nifty_daily_filtered.nlargest(10, hist_field)[hist_field]
        top10_infobox_str = f"Top10 : " + ' | '.join([f"{val:.3f}" for val in top10.values])
        info_box(val=top10_infobox_str)

        bottom10 = df_nifty_daily_filtered.nsmallest(10, hist_field)[hist_field]
        bottom10_infobox_str = f"Bottom10 : " + ' | '.join([f"{val:.3f}" for val in bottom10.values])
        info_box(val=bottom10_infobox_str)