"""
Analyzes the backtest results 
"""

import os
import pandas as pd
from streamlit import json
from constants import BACKTEST_RESULTS_FOLDERPATH
from utils.data_utils import read_parquet_data
import pickle
from strategy import Action


class BacktestAnalyzer:
    def __init__(self, backtest_folder_name: str, backtest_results_dir: str = None):

        self.backtest_results_dir = backtest_results_dir if backtest_results_dir else BACKTEST_RESULTS_FOLDERPATH
        backtest_foldernames = [f.name for f in os.scandir(self.backtest_results_dir) if f.is_dir()]
        assert backtest_folder_name in backtest_foldernames, f"Backtest folder '{backtest_folder_name}' not found."
        self.folder_name = backtest_folder_name
        self.action_folder_path = os.path.join(self.backtest_results_dir, self.folder_name, "actions")
        self.position_folder_path = os.path.join(self.backtest_results_dir, self.folder_name, "positions")
        self.portfolio_metrics_path = os.path.join(self.backtest_results_dir, self.folder_name, "df_portfolio_metrics.parquet")
        self.strategy_config_path = os.path.join(self.backtest_results_dir, self.folder_name, "strategy_config.pkl")
        self.backtester_config_path = os.path.join(self.backtest_results_dir, self.folder_name, "backtester_config.pkl")
        self.action_hashes = self.get_action_hashes()
        self.position_hashes = self.get_position_hashes()
        self.missing_action_hashes = self.action_hashes - self.position_hashes
        self.missing_position_hashes = self.position_hashes - self.action_hashes

    def get_strategy_config(self):
        strategy_config = {}
        if os.path.exists(self.strategy_config_path):
            with open(self.strategy_config_path, 'rb') as f:
                strategy_config = pickle.load(f)
        return strategy_config

    def get_backtester_config(self) -> dict:
        """
        Retrieve the backtester configuration from `self.backtester_config_path` for the backtest folder.

        Returns:
            dict: The backtester configuration for the backtest folder, or an empty dictionary if not found.
        """
        backtester_config = {}
        if os.path.exists(self.backtester_config_path):
            with open(self.backtester_config_path, 'rb') as f:
                backtester_config = pickle.load(f)
        return backtester_config
    
    def get_about(self) -> str:
        """
        Retrieve the metadata for the backtest folder.

        Returns:
            str: The metadata for the backtest folder, or an empty string if not found.
        """
        about_txt_file_path = os.path.join(self.backtest_results_dir, self.folder_name, "about_strategy.txt")
        about = "No information available"
        if os.path.exists(about_txt_file_path):
            with open(about_txt_file_path, 'r') as f:
                about = f.read()
        return about
    
    def get_action_hashes(self) -> set:
        """
        Retrieve the action hashes for the backtest folder.

        Returns:
            dict: The action hashes for the backtest folder, or an empty dictionary if not found.
        """

        action_json_files = [f for f in os.listdir(self.action_folder_path) if f.endswith('.json') and f.startswith('action_')]
        action_hashes = set()
        for json_filename in action_json_files:
            hashh = int(json_filename.split('_')[1].split('.')[0])
            action_hashes.add(hashh)
        return action_hashes

    def get_hash_to_action(self) -> dict: 
        """
        Retrieve the hash to action mapping for the backtest folder.

        Returns:
            dict: The hash to action mapping for the backtest folder, or an empty dictionary if no action hashes are found.
        """
        hash_to_action = {}
        for action_hash in self.action_hashes:
            hash_to_action[action_hash] = self.get_action(action_hash)
        return hash_to_action
    
    def get_position_hashes(self) -> set:
        """
        Retrieve the position hashes for the backtest folder.

        Returns:
            dict: The position hashes for the backtest folder, or an empty dictionary if not found.
        """

        position_parquet_files = [f for f in os.listdir(self.position_folder_path) if f.endswith('.parquet') and f.startswith('df_position')]
        position_hashes = set()
        for parquet_filename in position_parquet_files:
            hashh = int(parquet_filename[len('df_position_'):-len('.parquet')])
            position_hashes.add(hashh)
        return position_hashes
    
    def get_hash_to_position(self) -> dict:
        """
        Retrieve the hash to position mapping for the backtest folder.

        Returns:
            dict: The hash to position mapping for the backtest folder, or an empty dictionary if no position hashes are found.
        """
        hash_to_position = {}
        for position_hash in self.position_hashes:
            hash_to_position[position_hash] = self.get_df_position(position_hash)
        return hash_to_position

    def get_action(self, action_hash: int) -> dict:
        """
        Retrieve the action for a specific action hash.

        Args:
            action_hash (int): The action hash to retrieve the action for.

        Returns:
            dict: The action for the specified action hash, or None if not found.
        """

        assert action_hash in self.action_hashes, f"Action hash {action_hash} not found in {self.action_folder_path}"
        action_json_file_path = os.path.join(self.action_folder_path, f"action_{action_hash}.json")
        action = Action.load(action_json_file_path)
        return action

    def get_df_position(self, position_hash: int) -> pd.DataFrame:
        """
        Retrieve the DataFrame for a specific position hash.

        Args:
            position_hash (int): The position hash to retrieve the DataFrame for.

        Returns:
            pd.DataFrame: The DataFrame for the specified position hash, or an empty DataFrame if not found.
        """

        assert position_hash in self.position_hashes, f"Position hash {position_hash} not found in {self.position_folder_path}"
        position_parquet_file_path = os.path.join(self.position_folder_path, f"df_position_{position_hash}.parquet")
        df_position = read_parquet_data(position_parquet_file_path)
        return df_position
    
    def get_df_portfolio_metrics(self) -> pd.DataFrame:
        """
        Retrieve the portfolio DataFrame for the backtest folder.

        Returns:
            pd.DataFrame: The portfolio metrics DataFrame for the backtest folder.
        """

        assert os.path.exists(self.portfolio_metrics_path), f"Portfolio metrics file not found in {self.folder_name}"
        return read_parquet_data(self.portfolio_metrics_path)
    


