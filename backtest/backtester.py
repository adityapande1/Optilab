from datetime import timedelta
from pathlib import Path
from connectors.dbconnector import DBConnector
import hashlib
from typing import Union
from strategy import Action, Strategy
import pandas as pd
from dataclasses import asdict, dataclass
from tqdm import tqdm
from collections import defaultdict
from rich import print
import numpy as np
import time
import os
import json

import strategy

@dataclass
class BacktestConfig:
    start_date: pd.Timestamp
    end_date: pd.Timestamp
    cutoff_exit_time: pd.Timestamp
    transaction_cost: float  

    def save(self, savedir: str):
        path = Path(savedir)
        path.mkdir(parents=True, exist_ok=True)

        # Convert dataclass to dict, handling pd.Timestamp
        data = asdict(self)
        for k, v in data.items():
            if isinstance(v, pd.Timestamp):
                data[k] = v.isoformat()

        # Save to JSON
        filename = path / "backtest_config.json"
        with open(filename, "w") as f:
            json.dump(data, f, indent=4)
    
    @classmethod
    def load(cls, backtest_config_json_path):
        with open(backtest_config_json_path, "r") as f:
            data = json.load(f)
        for k, v in data.items():
            if isinstance(v, str):
                try:
                    data[k] = pd.Timestamp(v)
                except ValueError:
                    pass
        return cls(**data)

@dataclass
class Order:
    action: Action
    timestamp: pd.Timestamp
    status: str = "pending"   # e.g. pending, filled, cancelled, rejected
    hash: int | None = None  # Unique hash for the order

    def __post_init__(self):
        assert isinstance(self.action, Action), "action must be an Action instance"
        assert self.action.num_lots == 1, "Order must be created with exactly 1 lot"
        assert isinstance(self.timestamp, pd.Timestamp), "timestamp must be a pandas Timestamp"
        assert self.status in ("pending", "filled", "cancelled", "rejected"), "invalid status"

        # Build unique hash
        order_key = f"{self.action.key}__{self.timestamp}"
        self.hash = self._generate_positive_hash(order_key)

    def to_dict(self):
        d = self.__dict__.copy()
        d["action"] = self.action.to_dict()  # serialize Action inside
        return d

    def _generate_positive_hash(self, s: str) -> int:
        h = hashlib.sha256(s.encode("utf-8")).digest()
        # Take first 8 bytes (64 bits) and make it an integer
        return int.from_bytes(h[:8], "big", signed=False)

    def update_status(self, new_status: str):
        assert new_status in ("pending", "filled", "cancelled", "rejected"), "invalid status"
        self.status = new_status

class BackTester:
    '''
    BackTester is responsible to keep track of the metrics.
    '''
    def __init__(self, config: BacktestConfig, strategy: Strategy, dbconnector: DBConnector):
        self.config = config
        self.strategy = strategy
        self.dbconnector = dbconnector
        self.metric_list = [('interval_pnl', float, 0), ('pnl', float, 0)] 
        self.outstanding_orders = []
        self.hash2position_dfs = {}   # Stores dfs of each position (one for each filled order) with key as the hash of that position
        self.initialized_position_hashes = set()

    def fetch_position_dict(self, hash: int) -> dict | None:
        """Fetch the position dict from the strategy's position list using the hash."""
        for pos_dict in self.strategy.position:
            if pos_dict['hash'] == hash:
                return pos_dict
        return None

    def fetch_position_hashes(self) -> list[int]:
        """Fetch the hashes of all currently open positions of the strategy"""
        return [pos_dict['hash'] for pos_dict in self.strategy.position]

    def _initialize_metrics(self, timestamps: pd.DatetimeIndex):
        self.df_portfolio_metrics = pd.DataFrame(index=timestamps)
        self.df_portfolio_metrics.index.name = 'timestamp'

        for metric, metric_type, default_val in self.metric_list:
            self.df_portfolio_metrics[metric] = default_val
            self.df_portfolio_metrics[metric] = self.df_portfolio_metrics[metric].astype(metric_type)

    def validate_action(self, square_off_id: int) -> bool:
        '''
        This function is invoked for checking the validity of a square_off_id.
        - The function proceeds by first searching for the square_off_id in self.strategy.positions.
        - If the square_off_id exists, it will return True
        - If the square_off_id does not exist, it will raise ERROR
        '''
        for position in self.strategy.position:
            if square_off_id == position['hash']:
                return True
        raise ValueError(f"{square_off_id} is an invalid hash for a square-off action.")

    def validate_actions(self, actions: list[Action]) -> list[Action]:
        '''Validate a list of actions. Check square_off_id validity for each square_off action.'''
        validated_actions = []
        for action in actions:
            if action.square_off_id:
                validity = self.validate_action(action.square_off_id)
                if validity:
                    validated_actions.append(action)
            else:
                validated_actions.append(action)
        return validated_actions

    def _collect_orders(self, actions: list[Action], timestamp: pd.Timestamp) -> list[Order]:
        '''Make orders from the actions list, If action.num_lots > 1, first split the action then make orders for each split action'''
        orders = []
        for action in actions:
            if action.num_lots == 1:
                order = Order(action=action, timestamp=timestamp, status="pending", hash=action.square_off_id)
                orders.append(order)
            elif action.num_lots > 1:
                actions_split_list = action.split()
                for split_action in actions_split_list:
                    order = Order(action=split_action, timestamp=timestamp, status="pending", hash=split_action.square_off_id)
                    orders.append(order)

        return orders

    def process_order(self, order: Order, timestamp: pd.Timestamp):
        """Executes a single order and return metadata"""

        order_stats = {
            'timestamp': timestamp,
            'action': order.action,
            'hash': order.hash,
            'trade_type': order.action.trade_type,
            'price': None
        }

        market_price = self.dbconnector.get_option_price(strike=order.action.strike, option_type=order.action.option_type, expiry_date=order.action.expiry, timestamp=timestamp, field='close')
        if order.action.order_type == "market":
            order.update_status("filled")
            order_stats['price'] = market_price
        elif order.action.order_type == "limit":
            raise NotImplementedError("Limit orders are not yet supported.")
        
        order_stats['status'] = order.status

        return order_stats

    def process_orders(self, timestamp: pd.Timestamp):
        """Execute the outstanding orders and return metadata"""
        metadata = []
        still_outstanding = []

        for order in self.outstanding_orders:
            order_stats = self.process_order(order, timestamp)
            if order.status != "filled":
                still_outstanding.append(order)
            else:
                metadata.append(order_stats)
                
        self.outstanding_orders = still_outstanding
        return metadata

    def _create_df_position(self, tally_dict: dict, hash: int, valid_timestamps: pd.Index) -> pd.DataFrame:
        start_timestamp = tally_dict['opened']['timestamp']
        action = tally_dict['opened']['action']
        end_timestamp = tally_dict['closed']['timestamp']
        subset_timestamps = valid_timestamps[(valid_timestamps >= start_timestamp) & (valid_timestamps <= end_timestamp)]
        df_position = self.dbconnector.get_option_df(option_type=action.option_type, strike=action.strike, expiry_date=action.expiry)
        df_position = df_position.loc[subset_timestamps]
        df_position = df_position[['close']]    # choose only the 'close' price
        df_position = df_position.rename(columns={'close': 'price'})    # rename it to price
        self.initialized_position_hashes.add(hash)
        return df_position.copy()

    def update_step_metrics(self, timestamp: pd.Timestamp, metadata, valid_timestamps: pd.Index):

        for hash, tally_dict in self.strategy.position_tally.items():
            if (tally_dict['closed'] is not None) and (hash not in self.initialized_position_hashes):    # meaning the open position has been closed and df_position can now be completely made
                df_position = self._create_df_position(tally_dict, hash, valid_timestamps)
                self.hash2position_dfs[hash] = df_position
    
    def _update_final_metric_interval_pnl(self):
        for hash, df_position in self.hash2position_dfs.items():
            if df_position is not None:
                position = self.strategy.position_tally[hash]['opened']['action'].trade_type
                df_position['interval_pnl'] = df_position['price'].diff() * self.strategy.config.lot_size
                # if trade_type is 'sell' Then do - interval pnl
                if position == 'sell':
                    df_position['interval_pnl'] = -df_position['interval_pnl']
                
    def _update_final_metric_pnl(self):
        for hash, df_position in self.hash2position_dfs.items():
            if df_position is not None:
                df_position['pnl'] = df_position['interval_pnl'].cumsum()
                df_position.at[df_position.index[0], "pnl"] = -self.config.transaction_cost
    
    def _update_final_metric_max_drawdown(self):
        for hash, df_position in self.hash2position_dfs.items():
            running_max = df_position["pnl"].cummax()
            drawdown = running_max - df_position["pnl"]
            df_position["max_drawdown"] = drawdown.cummax()

    def update_final_metrics(self):

        self._update_final_metric_interval_pnl()
        self._update_final_metric_pnl()
        self._update_final_metric_max_drawdown()
        self._update_final_portfolio_metrics()

    def _update_final_portfolio_metrics(self):

        for timestamp in tqdm(self.df_portfolio_metrics.index, desc="Updating Portfolio Metrics", unit="timestamp"):
            total = 0
            for hash, df_position in self.hash2position_dfs.items():
                if timestamp in df_position.index:
                    total += df_position.loc[timestamp, 'interval_pnl']
            self.df_portfolio_metrics.at[timestamp, 'interval_pnl'] = total
        
        self.df_portfolio_metrics['pnl'] = self.df_portfolio_metrics['interval_pnl'].cumsum()

    def run(self) -> dict:

        self.valid_timestamps = self.dbconnector.df_spot.loc[self.config.start_date : self.config.end_date].index
        self.valid_timestamps = self.valid_timestamps.sort_values()
        self._initialize_metrics(timestamps=self.valid_timestamps)
        self.backtest_code = 'backtest__' + pd.Timestamp.now().strftime("%Y-%m-%d_%H:%M:%S")

        for current_timestamp in tqdm(self.valid_timestamps, desc="Running Backtest", unit="timestamp"):

            if current_timestamp.date() == pd.Timestamp("2024-11-01").date():
                continue  # Skip the timestamp for which we don't have data
        
            actions = self.strategy.action(current_timestamp)

            if actions:
                validated_actions = self.validate_actions(actions)
                new_orders = self._collect_orders(validated_actions, current_timestamp)
                self.outstanding_orders.extend(new_orders)

            # 3. Process the orders using process_orders function            
            metadata = self.process_orders(current_timestamp)

            # 4. Inform strategy about the trade by passing the metadata of the trade.            
            self.strategy.on_trade_execution(metadata, self.outstanding_orders)

            # 5. Update all the metrics for the time step by calling the update_metrics function.            
            self.update_step_metrics(current_timestamp, metadata, self.valid_timestamps)

        # 6. When all the timesteps are done, then compute one-time metrics such as Sharpe ratio, Expectancy and more.        
        self.update_final_metrics()
        # import ipdb; ipdb.set_trace()

    def save_backtest_results(self, save_dir: str = None):
        '''Saves the backtest results to the specified directory'''
        save_dir = os.path.join('./backtest_results', f"{self.backtest_code}") if save_dir is None else save_dir
        os.makedirs(save_dir, exist_ok=True)
        self.config.save(save_dir)  # Save the backtest configuration
        self.strategy.config.save(save_dir)  # Save the strategy configuration
        self.df_portfolio_metrics.to_parquet(os.path.join(save_dir, "df_portfolio_metrics.parquet"))    # Save portfolio metrics
        for hash, df_position in self.hash2position_dfs.items():
            df_position.to_parquet(os.path.join(save_dir, f"df_position_{hash}.parquet"))
        if hasattr(self.strategy, "about") and callable(getattr(self.strategy, "about")):
            with open(os.path.join(save_dir, "about_strategy.txt"), "w") as f:
                f.write(self.strategy.about())
        print(f"Backtest results saved to {save_dir}")

