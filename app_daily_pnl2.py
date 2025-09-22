import os
from typing import List

import streamlit as st

from backtest.backtest_analyzer import BacktestAnalyzer
from optilab_constants import BACKTEST_RESULTS_FOLDERPATH
from optilab_utils.display_utils import (display_backtest_details,
                                         display_page_title)
from optilab_utils.file_utils import (get_all_folders_in_directory,
                                      get_backtest_directory_maps)
from optilab_utils.input_utils import get_backtest_folder_and_hash_input


def run():

    display_page_title(title="Daily Profit and Loss Analysis",about="Stats and Visualizations for a given backtest run")

    BACKTEST_RESULTS_DIR = '../Optiverse/backtest_results/straddle/'
    foldername_to_folderhash_map, folderhash_to_foldername_map = get_backtest_directory_maps(BACKTEST_RESULTS_DIR)
    backtest_foldernames = [None] + get_all_folders_in_directory(BACKTEST_RESULTS_DIR)
    selected_foldername, selected_folderhash = get_backtest_folder_and_hash_input(backtest_foldernames, folderhash_to_foldername_map, foldername_to_folderhash_map)

    if selected_foldername is not None:
        backtest_analyzer = BacktestAnalyzer(backtest_results_dir=BACKTEST_RESULTS_DIR, backtest_folder_name=selected_foldername)
        display_backtest_details(backtest_analyzer)




