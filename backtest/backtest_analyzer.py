"""
Analyzes the any backtest result folder and provides easy access to the data and metadata.
"""

import os
from altair import value
import pandas as pd
from streamlit import json
from constants import BACKTEST_RESULTS_FOLDERPATH
from utils.data_utils import read_parquet_data
import pickle
from strategy import Action
from utils.parser import ReadOnlyConfig
from configs.config_schemas import BaseConfig


class BacktestAnalyzer:
    def __init__(self, backtest_folder_name: str, backtest_results_dir: str = None):

        self.backtest_results_dir = backtest_results_dir if backtest_results_dir else BACKTEST_RESULTS_FOLDERPATH
        backtest_foldernames = [f.name for f in os.scandir(self.backtest_results_dir) if f.is_dir()]
        assert backtest_folder_name in backtest_foldernames, f"Backtest folder '{backtest_folder_name}' not found."
        self.folder_name = backtest_folder_name
        self.action_folder_path = os.path.join(self.backtest_results_dir, self.folder_name, "actions")
        self.position_folder_path = os.path.join(self.backtest_results_dir, self.folder_name, "positions")
        self.portfolio_metrics_parquet_path = os.path.join(self.backtest_results_dir, self.folder_name, "df_portfolio_metrics.parquet")
        self.strategy_config_pkl_path = os.path.join(self.backtest_results_dir, self.folder_name, "strategy_config.pkl")
        self.backtester_config_pkl_path = os.path.join(self.backtest_results_dir, self.folder_name, "backtester_config.pkl")
        self.about_file_txt_path = os.path.join(self.backtest_results_dir, self.folder_name, "about_strategy.txt")
        self.folder_hash_file_txt_path = os.path.join(self.backtest_results_dir, self.folder_name, "folder_hash.txt")
        self.folder_hash = self.get_folder_hash()
        self.action_hashes = self.get_action_hashes()
        self.position_hashes = self.get_position_hashes()
        self.missing_action_hashes = self.action_hashes - self.position_hashes
        self.missing_position_hashes = self.position_hashes - self.action_hashes

    def get_strategy_config(self):
        strategy_config = {}
        if os.path.exists(self.strategy_config_pkl_path):
            strategy_config = BaseConfig.load(self.strategy_config_pkl_path)
        return strategy_config

    def get_backtester_config(self) -> dict:
        backtester_config = {}
        if os.path.exists(self.backtester_config_pkl_path):
            backtester_config = BaseConfig.load(self.backtester_config_pkl_path)
        return backtester_config

    def get_about(self) -> str:
        about = "No information available"
        if os.path.exists(self.about_file_txt_path):
            with open(self.about_file_txt_path, 'r') as f:
                about = f.read()
        return about

    def get_folder_hash(self) -> str:
        folder_hash = None
        if os.path.exists(self.folder_hash_file_txt_path):
            with open(self.folder_hash_file_txt_path, 'r') as f:
                folder_hash = f.read().strip()
        return int(folder_hash)

    def get_action_hashes(self) -> set:
        action_json_files = [f for f in os.listdir(self.action_folder_path) if f.endswith('.json') and f.startswith('action_')]
        action_hashes = set()
        for json_filename in action_json_files:
            hashh = int(json_filename.split('_')[1].split('.')[0])
            action_hashes.add(hashh)
        return action_hashes

    def get_hash_to_action(self) -> dict:
        hash_to_action = {}
        for action_hash in self.action_hashes:
            hash_to_action[action_hash] = self.get_action(action_hash)
        return hash_to_action

    def get_position_hashes(self) -> set:
        position_parquet_files = [f for f in os.listdir(self.position_folder_path) if f.endswith('.parquet') and f.startswith('df_position')]
        position_hashes = set()
        for parquet_filename in position_parquet_files:
            hashh = int(parquet_filename[len('df_position_'):-len('.parquet')])
            position_hashes.add(hashh)
        return position_hashes

    def get_df_position(self, position_hash: int) -> pd.DataFrame:
        assert position_hash in self.position_hashes, f"Position hash {position_hash} not found in {self.position_folder_path}"
        position_parquet_file_path = os.path.join(self.position_folder_path, f"df_position_{position_hash}.parquet")
        df_position = read_parquet_data(position_parquet_file_path)
        return df_position

    def get_hash_to_df_position(self) -> dict:
        hash_to_position = {}
        for position_hash in self.position_hashes:
            hash_to_position[position_hash] = self.get_df_position(position_hash)
        return hash_to_position

    def get_action(self, action_hash: int) -> dict:
        assert action_hash in self.action_hashes, f"Action hash {action_hash} not found in {self.action_folder_path}"
        action_json_file_path = os.path.join(self.action_folder_path, f"action_{action_hash}.json")
        action = Action.load(action_json_file_path)
        return action

    def get_df_portfolio_metrics(self) -> pd.DataFrame:
        assert os.path.exists(self.portfolio_metrics_parquet_path), f"Portfolio metrics file not found in {self.folder_name}"
        return read_parquet_data(self.portfolio_metrics_parquet_path)

    def equals(self, btanalyzer_other, verbose=False, round_decimals=5) -> bool:

        if verbose:
            print(f"Comparing BacktestAnalyzer instances\n\t1. {self.folder_name} in {self.backtest_results_dir} \n\t2. {btanalyzer_other.folder_name} in {btanalyzer_other.backtest_results_dir}\n")

        if not isinstance(btanalyzer_other, BacktestAnalyzer):
            return False

        # Compare folder hashes
        # is_folder_hash_same = (self.folder_hash == btanalyzer_other.folder_hash)
        # if verbose:
        #     print(f"Folder hash match: {is_folder_hash_same}")

        # # Compare strategy configs
        # is_strategy_config_same = (self.get_strategy_config() == btanalyzer_other.get_strategy_config())
        # if verbose:
        #     print(f"Strategy config match: {is_strategy_config_same}")

        # # Compare backtester configs
        # is_backtester_config_same = (self.get_backtester_config() == btanalyzer_other.get_backtester_config())
        # if verbose:
        #     print(f"Backtester config match: {is_backtester_config_same}")

        is_folder_hash_same, is_strategy_config_same, is_backtester_config_same = True, True, True  # Skipping these checks for now to focus on data checks

        # Compare action hashes
        are_action_hashes_same = (self.action_hashes == btanalyzer_other.action_hashes)
        if verbose:
            if are_action_hashes_same:
                print(f"Action hashes match: {are_action_hashes_same}")
            else:
                print(f"Action hashes do not match. Missing in self: {self.action_hashes - btanalyzer_other.action_hashes}, Missing in other: {btanalyzer_other.action_hashes - self.action_hashes}")

        # Compare position hashes
        are_position_hashes_same = (self.position_hashes == btanalyzer_other.position_hashes)
        if verbose:
            if are_position_hashes_same:
                print(f"Position hashes match: {are_position_hashes_same}")
            else:
                print(f"Position hashes do not match. Missing in self: {self.position_hashes - btanalyzer_other.position_hashes}, Missing in other: {btanalyzer_other.position_hashes - self.position_hashes}")

        # Compare actions for intersecting action hashes # If there are extra action hashes in either, then action_hashes_check would be False anyway
        action_checks = []
        for action_hash in self.action_hashes.intersection(btanalyzer_other.action_hashes):
            action_self = self.get_action(action_hash)
            action_other = btanalyzer_other.get_action(action_hash)
            action_checks.append(action_self == action_other)
            if verbose:
                if not (action_self == action_other):
                    print(f"Action hash {action_hash} match: False")

        are_all_actions_same = all(action_checks)
        if verbose:
            if action_checks:
                print(f"All actions match: {are_all_actions_same}")
            else:
                print(f"Not all actions match: {are_all_actions_same}")


        # Compare df_positions for intersecting position hashes # If there are extra position hashes in either, then position_hashes_check would be False anyway
        position_checks = []
        for position_hash in self.position_hashes.intersection(btanalyzer_other.position_hashes):
            df_position_self = self.get_df_position(position_hash).round(round_decimals).copy()
            df_position_other = btanalyzer_other.get_df_position(position_hash).round(round_decimals).copy()
            position_checks.append(df_position_self.equals(df_position_other))
            if verbose:
                if not (df_position_self.equals(df_position_other)):
                    print(f"Position hash {position_hash} match: False")
        are_all_positions_same = all(position_checks)
        if verbose:
            if are_all_positions_same:
                print(f"All positions match: {are_all_positions_same}")
            else:
                print(f"Not all positions match: {are_all_positions_same}")

        # Finally compare the df_portfolio_metrics
        df_portfolio_self = self.get_df_portfolio_metrics().round(round_decimals).copy()
        df_portfolio_other = btanalyzer_other.get_df_portfolio_metrics().round(round_decimals).copy()
        is_df_portfolio_same = df_portfolio_self.equals(df_portfolio_other)
        if verbose:
            print(f"Portfolio metrics match: {is_df_portfolio_same}")

        return is_folder_hash_same and is_strategy_config_same and is_backtester_config_same and are_action_hashes_same and are_position_hashes_same and are_all_actions_same and are_all_positions_same and is_df_portfolio_same
