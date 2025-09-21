import os
import streamlit as st
from optilab_constants import BACKTEST_RESULTS_FOLDERPATH
import streamlit as st
from typing import List
from backtest.backtest_analyzer import BacktestAnalyzer

from optilab_utils.display_utils import display_page_title, display_backtest_details
from optilab_utils.file_utils import get_all_folders_in_directory, get_backtest_directory_maps
from optilab_utils.input_utils import input_backtest_folder_and_hash

from streamlit_extras.stylable_container import stylable_container


def run():

    display_page_title(title="Daily Profit and Loss Analysis",about="Stats and Visualizations for a given backtest run")

    BACKTEST_RESULTS_DIR = '../Optiverse/backtest_results/weekly_straddle/'
    foldername_to_folderhash_map, folderhash_to_foldername_map = get_backtest_directory_maps(BACKTEST_RESULTS_DIR)
    backtest_foldernames = [None] + get_all_folders_in_directory(BACKTEST_RESULTS_DIR)
    selected_foldername, selected_folderhash = input_backtest_folder_and_hash(backtest_foldernames, folderhash_to_foldername_map, foldername_to_folderhash_map)

    if selected_foldername is not None:
        backtest_analyzer = BacktestAnalyzer(backtest_results_dir=BACKTEST_RESULTS_FOLDERPATH, backtest_folder_name=selected_foldername)
        display_backtest_details(backtest_analyzer)



