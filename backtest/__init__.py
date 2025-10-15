from dataclasses import dataclass
from collections import defaultdict
from strategy import Action
import pandas as pd
import hashlib
from utils.data_utils import generate_positive_hash
import os
from abc import ABC, abstractmethod
from connectors.dbconnector import DBConnector
from strategy import Strategy
from constants import BACKTEST_RESULTS_FOLDERPATH, SSD_BACKTEST_RESULTS_FOLDERPATH
from typing import Union
from backtest.metrics import update_metric_pnl
from tqdm import tqdm


@dataclass
class Order:
    action: Action
    timestamp: pd.Timestamp
    status: str = 'pending'  # e.g. pending, filled, cancelled, rejected

    def __post_init__(self):
        assert isinstance(self.action, Action), 'action must be an Action instance'
        assert self.action.num_lots == 1, 'Order must be created with exactly 1 lot'
        assert isinstance(self.timestamp, pd.Timestamp), 'timestamp must be a pandas Timestamp'
        assert self.status in ('pending', 'filled', 'cancelled', 'rejected'), 'invalid status'

        # Build unique hash
        order_key = f'{self.action.key}__{self.timestamp}'
        self.hash = self._generate_positive_hash(order_key)

    def _generate_positive_hash(self, s: str) -> int:
        h = hashlib.sha256(s.encode('utf-8')).digest()
        # Take first 8 bytes (64 bits) and make it an integer
        return int.from_bytes(h[:8], 'big', signed=False)

    def update_status(self, new_status: str):
        assert new_status in ('pending', 'filled', 'cancelled', 'rejected'), 'invalid status'
        self.status = new_status


class Backtester(ABC):
    """
    Parent class for different types of backtesters.
    """

    def __init__(self, config, strategy: Strategy, dbconnector: DBConnector):
        self.config = config
        self.strategy = strategy
        self.dbconnector = dbconnector

        self.portfolio_metric_tuples = [('net_step_pnl', float, 0), ('pnl', float, 0)]
        self.outstanding_orders = []
        self.orderhash_to_dfposition_map = {}  # Stores dfs of each position (one for each filled order) with key as the hash of that position
        self.orderhash_to_dfstoploss_map = {}  # Maps order hash to its corresponding stoploss dataframe
        self.exit_timestamp_to_squareoffids_map = defaultdict(set)  # Maps exit timestamps to sets of position hashes that need to be squared off at those timestamps

    @abstractmethod
    def run(self):
        """Core backtesting logic to be implemented by subclasses."""
        raise NotImplementedError('Subclasses must implement run()')

    def is_square_off_id_valid(self, square_off_id: int) -> bool:
        """
        Validate if the given `square_off_id` corresponds to an existing (still open and filled) position in `self.strategy.position`.

        Args
        ----------
        square_off_id (int) : The order hash of the position to be squared off.

        Returns
        -------
        bool : True if the `square_off_id` is valid.

        Raises
        -------
        ValueError : If the `square_off_id` does not correspond to any open position in `self.strategy.position`.
        """
        for pos in self.strategy.position:
            if pos['hash'] == square_off_id:
                return True
        raise ValueError(f'{square_off_id} is an invalid hash for a square-off action.')

    def validate_actions(self, actions: list[Action]) -> list[Action]:
        """
        Returns a list of `validated_actions` from the given list of actions.

        An action is considered valid if:
        - It is a fresh new action with square_off_id : `None`
        - It has a valid square_off_id i.e. it is an opposite action to a previously filled and still open position in `self.strategy.position`

        Args
        ----------
        actions (list[Action]) : The list of actions to be validated.

        Returns
        -------
        list[Action] : The list of validated actions.

        """

        validated_actions = []
        for action in actions:
            if action.square_off_id is None or self.is_square_off_id_valid(action.square_off_id):
                validated_actions.append(action)
        return validated_actions

    def get_orders_from_actions(self, actions: list[Action], timestamp: pd.Timestamp) -> list[Order]:
        """
        Converts a list of actions into a list of orders and returns them.

        - Each action is converted into one or more orders based on its `num_lots`.
            - If an action has `num_lots` 1, it is converted into a single order.
            - If an action has `num_lots` greater than 1, it is split into multiple orders, each with `num_lots` 1.
        - Each order is initialized with status "pending" and assigned a unique `positive` hash based on the action's properties and timestamp.


        Args
        ----------
        timestamp (pd.Timestamp) : The timestamp at which the actions are being processed.

        Returns
        -------
        list[Order] : A list of orders. Each order corresponds to a single lot action.

        """
        collected_orders = []
        for action in actions:
            action_list = [action] if action.num_lots == 1 else action.split_to_single_lots()  # Any action in action_list has num_lots = 1
            for single_lot_action in action_list:
                order = Order(action=single_lot_action, timestamp=timestamp, status='pending')
                collected_orders.append(order)
        return collected_orders

    def get_stoploss_actions(self, timestamp: pd.Timestamp) -> Union[list[Action], None]:
        """
        Get a list of stoploss actions for the current `timestamp`.

        - `self.exit_timestamp_to_squareoffids_map` maps an exit timestamp to a set of square_off_ids for which stoploss conditions were met at that exit timestamp.

        >>> Example : self.exit_timestamp_to_squareoffids_map
        ... {
        ...     pd.Timestamp("2023-01-01 10:15:00"): {12366274, 51326278},
        ...     pd.Timestamp("2023-01-02 11:00:00"): {9101111}
        ... }

        Parameters
        ----------
        timestamp : pd.Timestamp
            The timestamp at which to check for stoploss condition.

        Returns
        -------
        stoploss_actions : list[Action] or None
            Actions required to square off the positions for which stoploss conditions were met.
        """
        square_off_ids = self.exit_timestamp_to_squareoffids_map.get(timestamp, set())
        stoploss_actions = self.strategy.square_off_actions(square_off_ids=square_off_ids)
        return stoploss_actions

    def process_outstanding_orders(self, timestamp: pd.Timestamp) -> list[dict]:
        """
        Processes all the orders in `self.outstanding_orders` at the given `timestamp` and returns a list of order statistics dictionaries for `filled` orders.

        - Each order is processed individually, and if it is filled, its statistics are collected and appended to the `filled_orders` list.
        - The order's statistics are generated based on market conditions and action specifications by `self.create_order_stats()` function.
        - If an order is not filled, it remains in the `self.outstanding_orders` list for future processing.

        Args
        ----------
        timestamp (pd.Timestamp) : The timestamp at which the orders are being processed.

        Returns
        -------
        list[dict] : A list of dictionaries containing the order statistics for each `filled` order.

        """

        filled_orders, still_outstanding_orders = [], []

        for order in self.outstanding_orders:
            order_stats = self.create_order_stats(order, timestamp)
            if order.status == 'filled':
                filled_orders.append(order_stats)
            else:
                still_outstanding_orders.append(order)

        self.outstanding_orders = still_outstanding_orders
        return filled_orders

    def get_stoploss_hit_order_hashes(self, filled_orders) -> set:
        """
        Identifies orders from `filled_orders` whose stoploss was hit based on their corresponding stoploss dataframes in `self.orderhash_to_dfstoploss_map`.
            - `self.orderhash_to_dfstoploss_map[order_hash]` gives the stoploss dataframe for that order.
            - If Last rows of that dataframe has `stoploss_hit` as True, it means stoploss was hit for that order at that row's timestamp.

        Args
        ----------
        filled_orders (list[dict]) : A list of dictionaries containing the order statistics for each `filled` order.

        Returns
        -------
        set : A set of order hashes for which stoploss was hit.

        """
        stoploss_hit_order_hashes = set()
        for order_stats in filled_orders:
            df_stoploss = self.orderhash_to_dfstoploss_map.get(order_stats['hash'], pd.DataFrame())
            if not df_stoploss.empty and df_stoploss.iloc[-1]['stoploss_hit']:
                stoploss_hit_order_hashes.add(order_stats['hash'])
        return stoploss_hit_order_hashes

    def register_future_stoploss_hits(self, stoploss_hit_order_hashes: set):
        """
        Adds order hashes to `self.exit_timestamp_to_squareoffids_map` for future stoploss hits.

        Parameters
        ----------
        stoploss_hit_order_hashes : A set of order hashes for which stoploss will hit in future.

        Returns
        -------
        None : Updates `self.exit_timestamp_to_squareoffids_map` in place.
        """
        for order_hash in stoploss_hit_order_hashes:
            df_stoploss = self.orderhash_to_dfstoploss_map.get(order_hash)
            self.exit_timestamp_to_squareoffids_map[df_stoploss.index[-1]].add(order_hash)  # Last timestamp in df_stoploss is when stoploss hits

    def initialize_portfolio_metrics_dataframe(self, timestamps: pd.DatetimeIndex) -> None:
        """
        Initializes `self.df_portfolio_metrics` with a pandas datetime index of given `timestamps`.
            - `df_portfolio_metrics` stores the portfolio's performance metrics over the whole backtesting period.
            - `self.portfolio_metric_tuples` defines the metrics (columns) to be tracked, their initial values and types.

        Args
        ----------
        timestamps (pd.DatetimeIndex) : The timestamps for the backtesting period.

        Returns
        -------
        None : Initializes `self.df_portfolio_metrics` in place.

        """

        self.df_portfolio_metrics = pd.DataFrame(index=timestamps)
        self.df_portfolio_metrics.index.name = 'timestamp'

        for (
            metric_name,
            metric_variable_type,
            metric_default_val,
        ) in self.portfolio_metric_tuples:
            self.df_portfolio_metrics[metric_name] = metric_default_val
            self.df_portfolio_metrics[metric_name] = self.df_portfolio_metrics[metric_name].astype(metric_variable_type)

    def update_step_metrics(self, timestamp: pd.Timestamp, metadata, valid_timestamps: pd.Index):
        for hash, tally_dict in self.strategy.position_tally.items():
            if (tally_dict['closed'] is not None) and (hash not in self.orderhash_to_dfposition_map):  # meaning the open position has been closed and df_position can now be completely made
                order_hash = tally_dict['closed']['action'].square_off_id
                self.orderhash_to_dfposition_map[order_hash] = self.orderhash_to_dfstoploss_map[order_hash][['price']].copy()  # TODO : Check effect of copy()

    def update_final_metrics(self):
        for hash, df_position in tqdm(self.orderhash_to_dfposition_map.items(), desc='Updating Final Metrics'):
            if df_position is not None:
                trade_type = self.strategy.position_tally[hash]['opened']['action'].trade_type
                update_metric_pnl(
                    df=df_position,
                    trade_type=trade_type,
                    lot_size=self.strategy.config.lot_size,
                    per_lot_transaction_cost=self.config.per_lot_transaction_cost,
                )

                assert 'net_step_pnl' in df_position.columns, f'net_step_pnl column not found in df_position for hash {hash}. Ensure update_metric_pnl has been called.'
                net_pnl_aligned = df_position['net_step_pnl'].reindex(self.df_portfolio_metrics.index, fill_value=0)
                self.df_portfolio_metrics['net_step_pnl'] += net_pnl_aligned

        # Compute cumulative PnL
        self.df_portfolio_metrics['pnl'] = self.df_portfolio_metrics['net_step_pnl'].cumsum()

    def create_order_stats(self, order: Order, timestamp: pd.Timestamp) -> dict:
        """
        Return order statistics `dict` for a single order processing it at `timestamp` according to market conditions and action specifications.

        - Processing an order includes:
            - Updating the order status based on market conditions and `action.order_type` to pending, filled, cancelled or rejected
            - Setting stoploss levels if applicable
            - Setting target levels if applicable
            - Setting any other metadata (as key-value pairs) required for position management later

        Args
        ----------
        order (Order) : The `Order` instance to be processed.
        timestamp (pd.Timestamp) : The timestamp at which the order is being processed.

        Returns
        -------
        dict : A dictionary containing the order statistics after processing.

        """
        order_stats = {
            'hash': order.hash,
            'timestamp': timestamp,
            'action': order.action,
            'trade_type': order.action.trade_type,
            'price': None,
            'stoploss_price_level': None,
            'stoploss_hit_timestamp': None,  # The timestamp at which stoploss hits(if it does)
        }

        market_price = self.dbconnector.get_option_price(
            strike=order.action.strike,
            option_type=order.action.option_type,
            expiry_date=order.action.expiry,
            timestamp=timestamp,
            field='close',
        )

        if order.action.order_type == 'market':
            order.update_status('filled')
            order_stats['price'] = market_price
        elif order.action.order_type in ['market_stoploss', 'market_stoploss_trail']:
            order.update_status('filled')
            order_stats['price'] = market_price
            lot_size = self.strategy.config.lot_size
            stoploss_level = (market_price - order.action.stoploss / lot_size) if order.action.trade_type == 'long' else (market_price + order.action.stoploss / lot_size)
            order_stats['stoploss_price_level'] = stoploss_level  # This is the initial stoploss level set at the time of order fill

        elif order.action.order_type == 'limit':
            raise NotImplementedError('Limit orders are not yet supported.')

        order_stats['status'] = order.status
        return order_stats

    def save_results(self, foldername: str = None):
        """Saves the backtest results to the specified directory"""

        folder_path = os.path.join(
            BACKTEST_RESULTS_FOLDERPATH,
            f'{self.strategy.name}__{self.backtest_code}' if foldername is None else foldername,
        )

        # folder_path = os.path.join(
        #     SSD_BACKTEST_RESULTS_FOLDERPATH,
        #     f'{self.strategy.name}__{self.backtest_code}' if foldername is None else foldername,
        # )

        os.makedirs(folder_path, exist_ok=True)

        # Configs
        self.strategy.config.save(filepath=os.path.join(folder_path, 'strategy_config.pkl'))
        self.config.save(filepath=os.path.join(folder_path, 'backtester_config.pkl'))

        # All positions
        # positions_folder_path = os.path.join(folder_path, 'positions')
        # os.makedirs(positions_folder_path, exist_ok=True)
        # for hash, df_position in self.orderhash_to_dfposition_map.items():  # Save df_position
        #     df_position.to_parquet(os.path.join(positions_folder_path, f'df_position_{hash}.parquet'))

        # All actions
        # actions_folder = os.path.join(folder_path, 'actions')
        # os.makedirs(actions_folder, exist_ok=True)
        # # Position tally data
        # for hash, position_dict in self.strategy.position_tally.items():
        #     position_dict['opened']['action'].save(savedir=actions_folder, filename=f'action_{hash}.json')

        # final portfolio metrics
        self.df_portfolio_metrics.to_parquet(os.path.join(folder_path, 'df_portfolio_metrics.parquet'))  # Save portfolio metrics

        # About if present in strategy
        if hasattr(self.strategy, 'about') and callable(getattr(self.strategy, 'about')):  # Save about strategy if about() function implemented
            with open(os.path.join(folder_path, 'about_strategy.txt'), 'w') as f:
                f.write(self.strategy.about())

        # FoldercodeHash : Generate unique str from config (strategy and backtester) for later filtering
        foldercode_str = f'{self.strategy.config.as_str()}___{self.config.as_str()}'
        folder_hash = generate_positive_hash(foldercode_str)
        # Save hash in folder_hash
        with open(os.path.join(folder_path, 'folder_hash.txt'), 'w') as f:
            f.write(str(folder_hash))

        print(f'Backtest results saved to {folder_path}\n')

    def calculate_stoploss_levels(
        self,
        df: pd.DataFrame,
        starting_stoploss_level: float,
        position_type: str = 'long',
        trail_stoploss: bool = False,
    ) -> pd.DataFrame:
        assert isinstance(starting_stoploss_level, (int, float)), 'starting_stoploss_level must be numeric'
        assert position_type in ['long', 'short'], "position_type must be 'long' or 'short'"
        assert isinstance(trail_stoploss, bool), 'trail_stoploss must be a boolean'
        df = df.copy()  # Make a copy of df to avoid modifying the original dataframe
        df['stoploss_hit'] = False

        if trail_stoploss:
            if position_type == 'long':
                df['highest_high_until_now'] = df['high'].cummax().shift(1)
                df['shift_sl_up'] = df['high'] > df['highest_high_until_now']
                df['sl_change'] = (df['high'] - df['highest_high_until_now']).where(df['shift_sl_up'], 0)
                df['stoploss_price_level'] = starting_stoploss_level + df['sl_change'].cumsum()
                df.loc[df.index[1] :, 'stoploss_hit'] = df.loc[df.index[1] :, 'low'].round(6) <= df.loc[df.index[1] :, 'stoploss_price_level'].round(6)
                df = df[
                    [
                        'open',
                        'close',
                        'high',
                        'highest_high_until_now',
                        'shift_sl_up',
                        'sl_change',
                        'stoploss_price_level',
                        'low',
                        'stoploss_hit',
                    ]
                ]

            else:  # short
                df['lowest_low_until_now'] = df['low'].cummin().shift(1)
                df['shift_sl_down'] = df['low'] < df['lowest_low_until_now']
                df['sl_change'] = (df['lowest_low_until_now'] - df['low']).where(df['shift_sl_down'], 0)
                df['stoploss_price_level'] = starting_stoploss_level - df['sl_change'].cumsum()
                df.loc[df.index[1] :, 'stoploss_hit'] = df.loc[df.index[1] :, 'high'].round(6) >= df.loc[df.index[1] :, 'stoploss_price_level'].round(6)
                df = df[
                    [
                        'open',
                        'close',
                        'low',
                        'lowest_low_until_now',
                        'shift_sl_down',
                        'sl_change',
                        'stoploss_price_level',
                        'high',
                        'stoploss_hit',
                    ]
                ]

        else:
            df['stoploss_price_level'] = starting_stoploss_level
            if position_type == 'long':
                df.loc[df.index[1] :, 'stoploss_hit'] = df.loc[df.index[1] :, 'low'].round(6) <= df.loc[df.index[1] :, 'stoploss_price_level'].round(6)
            else:  # short
                df.loc[df.index[1] :, 'stoploss_hit'] = df.loc[df.index[1] :, 'high'].round(6) >= df.loc[df.index[1] :, 'stoploss_price_level'].round(6)
            df = df[['open', 'close', 'high', 'low', 'stoploss_price_level', 'stoploss_hit']]

        # make stoploss sticky
        df['stoploss_hit'] = df['stoploss_hit'].cummax().astype(bool)

        # filter df from the first stoploss hit onward
        first_hit_idx = df.index[df['stoploss_hit']].min()

        if pd.notna(first_hit_idx):
            df = df.loc[:first_hit_idx]

        # Add a price column same as close for compatibility with df_position
        df.loc[:, 'price'] = df['close']
        if df['stoploss_hit'].iloc[-1]:  # For the last row if stoploss_hit is True then set price to stoploss_price_level
            df.at[df.index[-1], 'price'] = df.at[df.index[-1], 'stoploss_price_level']

        return df
