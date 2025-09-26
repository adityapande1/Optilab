import hashlib
import os
import pickle
from collections import defaultdict
from dataclasses import dataclass
from typing import Union

import pandas as pd
from rich import print
from tqdm import tqdm

from backtest.metrics import update_metric_pnl
from backtest import Order, Backtester
from connectors.dbconnector import DBConnector
from constants import BACKTEST_RESULTS_FOLDERPATH
from strategy import Action, Strategy
from utils.data_utils import generate_positive_hash
from utils.data_utils import generate_combined_ohlc_dataframe


class PositionalBackTester(Backtester):
    """
    PositionalBackTester is responsible to keep track of the metrics.
    """

    def __init__(self, config, strategy: Strategy, dbconnector: DBConnector):
        super().__init__(config, strategy, dbconnector)
        self.portfolio_metric_tuples = [('net_step_pnl', float, 0), ('pnl', float, 0)]
        self.outstanding_orders = []
        self.orderhash_to_dfposition_map = {}  # Stores dfs of each position (one for each filled order) with key as the hash of that position
        self.orderhash_to_dfstoploss_map = {}  # Maps order hash to its corresponding stoploss dataframe
        self.exit_timestamp_to_squareoffids_map = defaultdict(set)  # Maps exit timestamps to sets of position hashes that need to be squared off at those timestamps

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

    def process_outstanding_orders(self, timestamp: pd.Timestamp) -> list[dict]:
        """
        Processes all the orders in `self.outstanding_orders` at the given `timestamp` and returns a list of order statistics dictionaries for `filled` orders.

        - Each order is processed individually, and if it is filled, its statistics are collected and appended to the `metadata` list.
        - The order's statistics are generated based on market conditions and action specifications by `self.process_order()` function.
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

    def get_stoploss_actions(self, timestamp: pd.Timestamp) -> Union[list[Action], None]:
        """
        Get stoploss actions for the current `timestamp`.

        - `self.timestamp_to_squareoffids` is a dictionary mapping different timestamps to sets of position hashes that need to be squared off at those timestamps.

        >>> Example : self.timestamp_to_squareoffids
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

    def create_df_stoploss(self, order_stats: dict, df_stoploss_combined: pd.DataFrame) -> pd.DataFrame:
        """
        Create a DataFrame `df_stoploss` to track stoploss levels over time for given order_stats.
            - The DataFrame's index is a datetime index ranging from the order's filled timestamp to the strategy's exit timestamp on the same day.
            - The stoploss levels are calculated based on the initial stoploss level and whether the position is long or short by the `calculate_stoploss_levels()` function.

        Parameters
        ----------
        order_stats : A dictionary containing order statistics for a filled order.

        Returns
        -------
        pd.DataFrame : A DataFrame containing OHLC prices and calculated stoploss levels over time.
        """

        df_stoploss_option = self.dbconnector.get_option_df(
            option_type=order_stats['action'].option_type,
            strike=order_stats['action'].strike,
            expiry_date=order_stats['action'].expiry,
        )[['open', 'high', 'low', 'close']]
        start_timestamp = order_stats['timestamp']  # start_timestamp is the entry time when order was filled

        if self.strategy.name == 'Straddle':
            end_timestamp = pd.Timestamp.combine(start_timestamp.date(), self.strategy.config.exit_time)  # end_timestamp is the exit time on the same day as order_stats['timestamp']
        elif self.strategy.name == 'WeeklyStraddle':
            end_timestamp = self.strategy.entry_ts_to_exit_ts_map.get(self.strategy.latest_entry_timestamp, None)

        if not df_stoploss_combined.empty and df_stoploss_combined.iloc[-1]['stoploss_hit']:
            end_timestamp = min(end_timestamp, df_stoploss_combined.index[-1])

        df_stoploss_option = df_stoploss_option.loc[(df_stoploss_option.index >= start_timestamp) & (df_stoploss_option.index <= end_timestamp)].copy()

        assert not df_stoploss_option.empty, f'df_stoploss is empty for order_stats : {order_stats}'
        df_stoploss_option = self.calculate_stoploss_levels(
            df=df_stoploss_option,
            starting_stoploss_level=order_stats['stoploss_price_level'],
            position_type=order_stats['trade_type'],
            trail_stoploss=(order_stats['action'].order_type == 'market_stoploss_trail'),
        )

        return df_stoploss_option

    def initialize_stoploss_dataframes(self, filled_orders: list[dict], df_stoploss_combined: pd.DataFrame) -> set:
        """
        Initialize a stoploss DataFrame for each `stoploss` type order in `filled_orders`.
            - NOTE: `filled_orders` is a list of dictionaries containing order statistics `dict` for `filled` orders only.
            - Create a DataFrame `df_stoploss` for each order in `filled_orders` if order_type in ( "market_stoploss" or "market_stoploss_trail")
            - Store the DataFrame as `self.orderhash_to_dfstoploss_map[order_hash] = df_stoploss`

        Parameters
        ----------
        filled_orders : A list of dictionaries containing order statistics for `filled` orders.

        Returns
        -------
        A set of order hashes for which stoploss will hit in future.

        Example `filled_orders` list
        -------
        >>> filled_orders=[
        ...                {
        ...                    'hash': 14708032500100578527,
        ...                    'timestamp': Timestamp('2024-01-01 09:15:00'),
        ...                    'action': Action(option_type='CE', strike=21700, trade_type='short', expiry='2024-01-04',
        ...                                     order_type='market_stoploss_trail', num_lots=1, limit_price=None, lot_type='full',
        ...                                     lot_idx=1, square_off_id=None, stoploss=3500.0, target=None),
        ...                    'trade_type': 'short',
        ...                    'price': 137.45,
        ...                    'stoploss_price_level': 184.1166,
        ...                    'stoploss_hit_timestamp': None,
        ...                    'status': 'filled'
        ...                },
        ...                {...},
        ...                {...}
        ...            ]
        """

        for order_stats in filled_orders:
            assert order_stats['status'] == 'filled', 'Only filled orders should be in filled_orders list'
            action, order_hash = order_stats['action'], order_stats['hash']
            if (
                (action.order_type in ('market_stoploss', 'market_stoploss_trail'))  # Order of Stoploss type
                and (order_hash not in self.orderhash_to_dfstoploss_map)  # df_position not already initialized
                and (action.square_off_id is None)  # Opening fresh order
            ):
                df_stoploss = self.create_df_stoploss(order_stats, df_stoploss_combined)
                self.orderhash_to_dfstoploss_map[order_hash] = df_stoploss

    def get_stoploss_hit_order_hashes(self, filled_orders) -> set:
        stoploss_hit_order_hashes = set()
        for order_stats in filled_orders:
            df_stoploss = self.orderhash_to_dfstoploss_map.get(order_stats['hash'], pd.DataFrame())
            if not df_stoploss.empty and df_stoploss.iloc[-1]['stoploss_hit']:  # If Last row's stoploss_hit is True then add order_hash to self.timestamp_to_squareoffids
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
            self.exit_timestamp_to_squareoffids_map[df_stoploss.index[-1]].add(order_hash)

    def get_combined_stoploss_dataframe(self, filled_orders: list[dict]) -> pd.DataFrame:

        ohlc_dataframes, trade_types = [], []
        fresh_orders = [order_stats for order_stats in filled_orders if order_stats['action'].square_off_id is None]

        if fresh_orders:

            # Assert all the order_stat['timestamp'] are same for fresh_orders
            timestamps = {order_stats['timestamp'] for order_stats in fresh_orders}
            assert len(timestamps) == 1, f'All timestamps in filled_orders must be same for fresh_orders. Found timestamps : {timestamps}'
            common_order_filling_timestamp = timestamps.pop()

            starting_deal_price = 0
            for order_stats in fresh_orders:
                action = order_stats['action']
                starting_deal_price = starting_deal_price + order_stats['price'] if order_stats['trade_type'] == 'buy' else starting_deal_price - order_stats['price']
                trade_types.append(order_stats['trade_type'])
                df_option = self.dbconnector.get_option_df(
                    option_type=action.option_type,
                    strike=action.strike,
                    expiry_date=action.expiry
                    )
                df_option = df_option[df_option.index >= common_order_filling_timestamp].copy()
                ohlc_dataframes.append(df_option)

            starting_stoploss_level = starting_deal_price - self.config.total_position_risk/self.config.lot_size
            df_stoploss = generate_combined_ohlc_dataframe(ohlc_dataframes, trade_types)

            df_stoploss = self.calculate_stoploss_levels(df=df_stoploss,
                                                        starting_stoploss_level=starting_stoploss_level,
                                                        position_type='long',
                                                        trail_stoploss=False)
        else:
            df_stoploss = pd.DataFrame()

        return df_stoploss


    def run(self) -> dict:
        self.valid_timestamps = self.dbconnector.df_spot.loc[self.config.start_date : self.config.end_date].index
        self.valid_timestamps = self.valid_timestamps.sort_values()
        self.initialize_portfolio_metrics_dataframe(timestamps=self.valid_timestamps)
        self.backtest_code = pd.Timestamp.now().strftime('%Y-%m-%d_%H:%M:%S')

        for current_timestamp in tqdm(self.valid_timestamps, desc='Running Backtest', unit='timestamp'):
            if current_timestamp.date() == pd.Timestamp('2024-11-01').date():
                continue  # Skip this timestamp as we don't have data for it.

            # 1. Get all actions at the current timestamp
            strategy_actions = self.strategy.action(current_timestamp)
            stoploss_actions = self.get_stoploss_actions(current_timestamp)
            actions = (strategy_actions or []) + (stoploss_actions or [])
            actions = list(set(actions))  # In case of multiple actions being same, keep only one

            # 2. Validate actions and convert them to orders
            if actions:
                validated_actions = self.validate_actions(actions)
                new_orders = self.get_orders_from_actions(validated_actions, current_timestamp)
                self.outstanding_orders.extend(new_orders)

            # 3. Process the 'self.outstanding_orders' at the current timestamp to get filled orders
            filled_orders = self.process_outstanding_orders(current_timestamp)

            # 3.1.1
            df_stoploss_combined = self.get_combined_stoploss_dataframe(filled_orders)
            self.initialize_stoploss_dataframes(filled_orders, df_stoploss_combined)
            stoploss_hit_order_hashes = self.get_stoploss_hit_order_hashes(filled_orders)
            if stoploss_hit_order_hashes:
                self.register_future_stoploss_hits(stoploss_hit_order_hashes)

            # 4. Inform strategy about the trade by passing the metadata of the trade.
            self.strategy.on_trade_execution(filled_orders, self.outstanding_orders)

            # 5. Update all the metrics for the time step by calling the update_metrics function.
            self.update_step_metrics(current_timestamp, filled_orders, self.valid_timestamps)

        # 6. When all the timesteps are done, then compute one-time metrics such as Sharpe ratio, Expectancy and more.
        self.update_final_metrics()
