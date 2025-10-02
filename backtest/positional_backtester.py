import pandas as pd
from tqdm import tqdm
from backtest import Backtester
from connectors.dbconnector import DBConnector
from strategy import Strategy
from utils.data_utils import generate_combined_ohlc_dataframe


class PositionalBackTester(Backtester):
    """
    PositionalBackTester is responsible to keep track of the metrics.
    """

    def __init__(self, config, strategy: Strategy, dbconnector: DBConnector):
        super().__init__(config, strategy, dbconnector)

    def _create_df_stoploss(self, order_stats: dict, df_stoploss_combined: pd.DataFrame) -> pd.DataFrame:
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

        df_option = self.dbconnector.get_option_df(
            option_type=order_stats['action'].option_type,
            strike=order_stats['action'].strike,
            expiry_date=order_stats['action'].expiry,
        )[['open', 'high', 'low', 'close']]
        entry_timestamp = order_stats['timestamp']  # start_timestamp is the entry time when order was filled

        if self.strategy.name in ('Straddle', 'Strangle', 'IronButterfly'):
            max_possible_exit_timestamp = pd.Timestamp.combine(entry_timestamp.date(), self.strategy.config.exit_time)  # Straddle exits on the same day
        elif self.strategy.name == 'WeeklyStraddle':
            max_possible_exit_timestamp = self.strategy.entry_ts_to_exit_ts_map.get(self.strategy.latest_entry_timestamp, None)  # WeeklyStraddle exits on a future date
        else:
            raise NotImplementedError(f'max_possible_exit_timestamp for Strategy {self.strategy.name} not implemented in PositionalBackTester')

        exit_timestamp = max_possible_exit_timestamp
        if not df_stoploss_combined.empty and df_stoploss_combined.iloc[-1]['stoploss_hit']:
            exit_timestamp = min(max_possible_exit_timestamp, df_stoploss_combined.index[-1])

        df_option = df_option.loc[(df_option.index >= entry_timestamp) & (df_option.index <= exit_timestamp)].copy()

        assert not df_option.empty, f'df_option is empty for order_stats : {order_stats}'
        df_stoploss = self.calculate_stoploss_levels(
            df=df_option,
            starting_stoploss_level=order_stats['stoploss_price_level'],
            position_type=order_stats['trade_type'],
            trail_stoploss=(order_stats['action'].order_type == 'market_stoploss_trail'),
        )

        return df_stoploss

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
                and (order_hash not in self.orderhash_to_dfstoploss_map)  # df_stoploss not already initialized
                and (action.square_off_id is None)  # Opening fresh order i.e. not a square-off order
            ):
                df_stoploss = self._create_df_stoploss(order_stats, df_stoploss_combined)
                self.orderhash_to_dfstoploss_map[order_hash] = df_stoploss

    def _get_combined_stoploss_dataframe(self, filled_orders: list[dict]) -> pd.DataFrame:
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
                df_option = self.dbconnector.get_option_df(option_type=action.option_type, strike=action.strike, expiry_date=action.expiry)
                df_option = df_option[df_option.index >= common_order_filling_timestamp].copy()
                ohlc_dataframes.append(df_option)

            df_option_combined = generate_combined_ohlc_dataframe(ohlc_dataframes, trade_types)
            starting_stoploss_level = starting_deal_price - self.config.total_position_risk / self.config.lot_size
            df_stoploss_combined = self.calculate_stoploss_levels(df=df_option_combined, starting_stoploss_level=starting_stoploss_level, position_type='long', trail_stoploss=False)

        else:
            df_stoploss_combined = pd.DataFrame()

        return df_stoploss_combined

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
            df_stoploss_combined = self._get_combined_stoploss_dataframe(filled_orders)
            self.initialize_stoploss_dataframes(filled_orders, df_stoploss_combined)
            stoploss_hit_order_hashes = self.get_stoploss_hit_order_hashes(filled_orders)
            if stoploss_hit_order_hashes:
                self.register_future_stoploss_hits(stoploss_hit_order_hashes)

            # 4. Inform strategy about the trade by passing the metadata of the trade.
            self.strategy.on_trade_execution(filled_orders)

            # 5. Update all the metrics for the time step by calling the update_metrics function.
            self.update_step_metrics(current_timestamp, filled_orders, self.valid_timestamps)

        # 6. When all the timesteps are done, then compute one-time metrics such as Sharpe ratio, Expectancy and more.
        self.update_final_metrics()
