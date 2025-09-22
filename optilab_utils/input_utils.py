import os
from typing import List

import streamlit as st


def get_backtest_folder_and_hash_input(backtest_foldernames: List[str], hash_to_folder_map: dict, folder_to_hash_map: dict) -> (str, str):

    st.markdown("### [ Select Backtest folder ]  OR [ Enter hash directly ] -- Note : Hash takes priority")

    left_col, right_col = st.columns([1, 1])
    with left_col:
        st.markdown("#### Option 1: Enter backtest folder hash")
        folder_hash = st.text_input("Backtest Folder Hash")

    with right_col:
        st.markdown("#### Option 2: Select from available backtests")
        selected_backtest_folder = st.selectbox("Backtest Folder", options=backtest_foldernames)

    # Decide which folder to use
    if folder_hash:
        folder_to_use = hash_to_folder_map.get(int(folder_hash), "Invalid Hash")
        if folder_to_use == "Invalid Hash":
            st.error("Invalid hash entered. Please select a valid backtest folder.")
    else:
        folder_to_use = selected_backtest_folder
        folder_hash = folder_to_hash_map.get(folder_to_use, "Unknown Hash")

    st.success(f"Selected Backtest Folder: {folder_to_use} ")
    st.success(f"Selected Folder Hash: {folder_hash}")
    st.divider()

    return folder_to_use, folder_hash
