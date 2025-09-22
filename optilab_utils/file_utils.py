import os
import streamlit as st


@st.cache_data
def get_all_folders_in_directory(directory):
    try:
        return [f for f in os.listdir(directory) if os.path.isdir(os.path.join(directory, f))]
    except FileNotFoundError:
        st.error(f'Directory not found: {directory}')
        return []


@st.cache_data
def get_backtest_directory_maps(backtest_results_dir: str) -> tuple[dict, dict]:
    foldername_to_folderhash_map, folderhash_to_foldername_map = {}, {}
    backtest_foldernames = get_all_folders_in_directory(backtest_results_dir)

    for backtest_folder in backtest_foldernames:
        folderhash_txt_path = os.path.join(backtest_results_dir, backtest_folder, 'folder_hash.txt')
        if os.path.exists(folderhash_txt_path):
            with open(folderhash_txt_path, 'r') as f:
                folder_hash = int(f.read().strip())
                foldername_to_folderhash_map[backtest_folder] = folder_hash
                folderhash_to_foldername_map[folder_hash] = backtest_folder

    return foldername_to_folderhash_map, folderhash_to_foldername_map
