import streamlit as st
from optilab_constants import BACKTEST_RESULTS_FOLDERPATH
from backtest.backtest_analyzer import BacktestAnalyzer
from backtest.metrics import MetricEngine
import plotly.express as px
import os
import plotly.graph_objects as go
import pandas as pd
from optilab_utils.viz_utils import stem_plot, info_box

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
            width: 18px; 
            height: 18px;
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
            <h3 style="margin:0; color:black; text-align:left; padding-left:16px;">
                {title}
                <span class="tooltip">
                    <span class="tooltip-circle">?</span>
                    <span class="tooltiptext">{help_text}</span>
                </span>
            </h3>
            <hr style="margin:-2px 0;">
            <h4 style="margin:10px 0; color:#da1a78; font-size:26px; text-align:left; padding-left:16px;">{value}</h4>
        </div>
    """, unsafe_allow_html=True)






def get_folderhash_to_foldername_map(backtest_results_dir):
    folderhash_to_foldername_map = {}
    for foldername in os.listdir(backtest_results_dir):
        folderpath = os.path.join(backtest_results_dir, foldername)
        if os.path.isdir(folderpath):
            analyzer = BacktestAnalyzer(backtest_results_dir=backtest_results_dir, backtest_folder_name=foldername)
            folderhash_to_foldername_map[analyzer.folder_hash] = foldername
    return folderhash_to_foldername_map


def run():
    cols = st.columns([1]*8)
    for _, col in enumerate(cols):
        with col:
            st.markdown("<br>", unsafe_allow_html=True)
            labeled_box_with_help("Revenue", "$120K", "This is the total revenue for Q1")
    # Initialize session state vars
    st.session_state.setdefault("folderhash_to_foldername_map", {})
    st.session_state.setdefault("folderhash_map_initialized", False)
    st.session_state.setdefault("selected_backtest_folder_name", None)

    BACKTEST_RESULTS_FOLDERPATH = "./backtest_results"
    # Build the folderhash → foldername map only once
    if st.session_state.folderhash_map_initialized is False:
        st.session_state.folderhash_to_foldername_map = get_folderhash_to_foldername_map(BACKTEST_RESULTS_FOLDERPATH)
        st.session_state.folderhash_map_initialized = True

    # UI header
    col = st.container()
    with col:
        st.markdown("---\n# Evaluate Strategy : Detailed Analysis of a Single Backtest")
        st.subheader("[ 1. Enter a valid folder hash directly ] OR ")
        entered_folderhash = st.text_input("FOLDER HASH CODE (Optional)", value="")
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
        st.subheader("[ 2. Select a backtest folder in the sidebar : Folder hash above $\\uparrow$ should be empty > ]")
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
    metrics_engine = MetricEngine(btanalyzer=backtest_analyzer, initial_capital=initial_capital)

    # Display folder info
    col_foldername, col_folder_hash = st.columns([4, 1])
    with col_foldername:
        labeled_box(title="Backtest Folder Name", value=selected_backtest_folder_name)
    with col_folder_hash:
        labeled_box(title="Folder Hash", value=backtest_analyzer.folder_hash)
    st.markdown("<br>", unsafe_allow_html=True)
    
    ############################
    #### CONFIGS and ABOUT #####
    ############################

    strategy_config = backtest_analyzer.get_strategy_config().as_dict()
    backtester_config = backtest_analyzer.get_backtester_config().as_dict()
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

    st.subheader(metrics_engine.btanalyzer.folder_hash)







