import os
import streamlit as st
from optilab_constants import BACKTEST_RESULTS_FOLDERPATH
import streamlit as st
from typing import List
from backtest.backtest_analyzer import BacktestAnalyzer

from optilab_utils.display_utils import display_page_title, display_backtest_details
from optilab_utils.file_utils import get_all_folders_in_directory, get_backtest_directory_maps
from optilab_utils.input_utils import input_backtest_folder_and_hash

import pandas as pd
import streamlit as st
from numpy.random import default_rng as rng


def run():

    display_page_title(title="Compare Stratergies",about="Compare multiple backtest runs side by side")

    BACKTEST_RESULTS_DIR = BACKTEST_RESULTS_FOLDERPATH
    foldername_to_folderhash_map, folderhash_to_foldername_map = get_backtest_directory_maps(BACKTEST_RESULTS_DIR)
    backtest_foldernames = [None] + get_all_folders_in_directory(BACKTEST_RESULTS_DIR)

    st.session_state.setdefault("folderhashes_to_compare", [])

    selected_foldername, selected_folderhash = input_backtest_folder_and_hash(backtest_foldernames, folderhash_to_foldername_map, foldername_to_folderhash_map)

    if selected_foldername is not None:
        backtest_analyzer = BacktestAnalyzer(backtest_results_dir=BACKTEST_RESULTS_FOLDERPATH, backtest_folder_name=selected_foldername)
        display_backtest_details(backtest_analyzer)

    if selected_foldername is not None and selected_folderhash not in st.session_state.folderhashes_to_compare:
        if st.button("Add Backtest for comparison", key="button_add_backtest", use_container_width=True):
            st.session_state.folderhashes_to_compare.append(selected_folderhash)
            st.rerun()

    st.write("## Backtests selected for comparison:\n---")
    if len(st.session_state.folderhashes_to_compare) == 0:
        st.info("No backtests selected for comparison. Please select a backtest from the dropdown above and click 'Add Backtest for comparison' button.")
    else:
        for i, folderhash in enumerate(st.session_state.folderhashes_to_compare):
            foldername = folderhash_to_foldername_map[folderhash]
            col_x, col_folderhash, col_foldername = st.columns([1, 3, 8])
            col_folderhash.write(f"##### FOLDERHASH : {folderhash}")
            col_foldername.write(f"##### FOLDERNAME : {foldername}")
            if col_x.button("❌", key=f"removeee_{i}"):
                st.session_state.folderhashes_to_compare.remove(folderhash)
                st.rerun()
            st.markdown("---")

    df = pd.DataFrame(
        {
            "name": ["Roadmap", "Extras", "Issues"],
            "url": [
                "https://roadmap.streamlit.app",
                "https://extras.streamlit.app",
                "https://issues.streamlit.app",
            ],
            "stars": rng(0).integers(0, 1000, size=3),
            "views_history": rng(0).integers(0, 5000, size=(3, 30)).tolist(),
        }
    )

    st.dataframe(
        df,
        column_config={
            "name": "App name",
            "stars": st.column_config.NumberColumn(
                "Github Stars",
                help="Number of stars on GitHub",
                format="%d ⭐",
            ),
            "url": st.column_config.LinkColumn("App URL"),
            "views_history": st.column_config.LineChartColumn(
                "Views (past 30 days)", y_min=0, y_max=5000
            ),
        },
        hide_index=True,
    )
