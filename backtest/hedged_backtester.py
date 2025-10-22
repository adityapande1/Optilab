import pandas as pd
from tqdm import tqdm
from backtest import Backtester
from connectors.dbconnector import DBConnector
from strategy import Strategy
from rich import print
from utils.data_utils import generate_combined_ohlc_dataframe


class HedgedBackTester(Backtester):
    """
    HedgedBackTester is responsible to keep track of the metrics.
    """

    def __init__(self, config, strategy: Strategy, dbconnector: DBConnector):
        super().__init__(config, strategy, dbconnector)

    def _create_df_stoploss_for_hedged_backtester(self, order_stats: dict, filled_orders=None) -> pd.DataFrame:
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

        if self.strategy.name in ('Straddle', 'StraddleDaily'):
            max_possible_exit_timestamp = pd.Timestamp.combine(entry_timestamp.date(), self.strategy.config.exit_time)  # Straddle exits on the same day
            df_option = df_option.loc[(df_option.index >= entry_timestamp) & (df_option.index <= max_possible_exit_timestamp)].copy()
            assert not df_option.empty, f'df_option is empty for order_stats : {order_stats}'
            entry_price = order_stats['price']
            risk_associated_in_capital = self.strategy.config.call_risk if order_stats['action'].option_type == 'CE' else self.strategy.config.put_risk
            risk_associated_in_points = risk_associated_in_capital / self.config.lot_size
            initial_stoploss_level = entry_price - risk_associated_in_points if order_stats['trade_type'] == 'long' else entry_price + risk_associated_in_points
            df_stoploss = self.get_dataframe_with_stoploss_info(
                df=df_option,
                starting_stoploss_level=initial_stoploss_level,
                trade_type=order_stats['trade_type'],
                trail_stoploss=(order_stats['action'].order_type == 'market_stoploss_trail'),
            )
        elif self.strategy.name == 'StrangleDaily':
            max_possible_exit_timestamp = pd.Timestamp.combine(entry_timestamp.date(), self.strategy.config.exit_time)  # StrangleDaily exits on the same day
            df_option = df_option.loc[(df_option.index >= entry_timestamp) & (df_option.index <= max_possible_exit_timestamp)].copy()
            assert not df_option.empty, f'df_option is empty for order_stats : {order_stats}'
            entry_price = order_stats['price']
            risk_associated_in_capital = self.strategy.config.otm_call_risk if order_stats['action'].option_type == 'CE' else self.strategy.config.otm_put_risk
            risk_associated_in_points = risk_associated_in_capital / self.config.lot_size
            initial_stoploss_level = entry_price - risk_associated_in_points if order_stats['trade_type'] == 'long' else entry_price + risk_associated_in_points
            df_stoploss = self.get_dataframe_with_stoploss_info(
                df=df_option,
                starting_stoploss_level=initial_stoploss_level,
                trade_type=order_stats['trade_type'],
                trail_stoploss=(order_stats['action'].order_type == 'market_stoploss_trail'),
            )
        elif self.strategy.name == 'IronCondorDaily':
            assert len(filled_orders) in (2, 4), 'IronCondorDaily should have 2 or 4 legs filled_orders to create df_stoploss for hedged backtester'
            current_option_type = order_stats['action'].option_type
            actions_of_same_option_type = [fo['action'] for fo in filled_orders if fo['action'].option_type == current_option_type]
            assert len(actions_of_same_option_type) == 2, 'There should be exactly 2 legs of same option type in IronCondorDaily'

            filling_timestamps = [fo['timestamp'] for fo in filled_orders if fo['action'].option_type == current_option_type]
            assert all(ts == filling_timestamps[0] for ts in filling_timestamps), 'All legs of same option type should have same filling timestamp'
            assert entry_timestamp == filling_timestamps[0], 'entry_timestamp should match filling timestamp of legs of same option type'

            # Assert all filling_timestamps are the same for legs of same option type
            max_possible_exit_timestamp = pd.Timestamp.combine(entry_timestamp.date(), self.strategy.config.exit_time)  # IronCondorDaily exits on the same day
            ohlc_dataframes_options, trade_types = [], []
            for action in actions_of_same_option_type:
                df_option = self.dbconnector.get_option_df(option_type=action.option_type, strike=action.strike, expiry_date=action.expiry)[['open', 'high', 'low', 'close']]
                df_option = df_option.loc[(df_option.index >= entry_timestamp) & (df_option.index <= max_possible_exit_timestamp)].copy()
                assert not df_option.empty, f'df_option is empty for action : {action}'
                ohlc_dataframes_options.append(df_option)
                trade_types.append(action.trade_type)
            df_option_combined = generate_combined_ohlc_dataframe(ohlc_dataframes=ohlc_dataframes_options, trade_types=trade_types)
            risk_associated_in_capital = self.strategy.config.put_credit_spread_risk if current_option_type == 'PE' else self.strategy.config.call_credit_spread_risk
            risk_associated_in_points = risk_associated_in_capital / self.config.lot_size

            import ipdb; ipdb.set_trace()
            print('IronCondorDaily df_stoploss creation not implemented yet.')

        elif self.strategy.name == 'StraddleWeekly':
            max_possible_exit_timestamp = self.strategy.entry_ts_to_exit_ts_map.get(self.strategy.latest_entry_timestamp)  # StraddleWeekly exits on the exit date mapped to the entry date
            df_option = df_option.loc[(df_option.index >= entry_timestamp) & (df_option.index <= max_possible_exit_timestamp)].copy()
            assert not df_option.empty, f'df_option is empty for order_stats : {order_stats}'
            entry_price = order_stats['price']
            risk_associated_in_capital = self.strategy.config.call_risk if order_stats['action'].option_type == 'CE' else self.strategy.config.put_risk
            risk_associated_in_points = risk_associated_in_capital / self.config.lot_size
            initial_stoploss_level = entry_price - risk_associated_in_points if order_stats['trade_type'] == 'long' else entry_price + risk_associated_in_points
            df_stoploss = self.get_dataframe_with_stoploss_info(
                df=df_option,
                starting_stoploss_level=initial_stoploss_level,
                trade_type=order_stats['trade_type'],
                trail_stoploss=(order_stats['action'].order_type == 'market_stoploss_trail'),
            )
        else:
            raise NotImplementedError(f'max_possible_exit_timestamp for Strategy {self.strategy.name} not implemented in BaseBackTester')

        return df_stoploss

    def _initialize_stoploss_dataframes(self, filled_orders: list[dict]) -> None:
        """
        Adds a stoploss_dataframe to `self.orderhash_to_dfstoploss_map` for each filled order in `filled_orders` if order type is either ('market_stoploss' or 'market_stoploss_trail')
            - If the df_stoploss for order_hash hits stoploss
        Args:
            filled_orders : A list of dictionaries containing order statistics for `filled` orders. See example below.
        Returns:
            None : This function modifies the `self.orderhash_to_dfstoploss_map` attribute in place.
        Examples:
        `filled_orders` list
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
                df_stoploss = self._create_df_stoploss_for_hedged_backtester(order_stats, filled_orders=filled_orders)
                self.orderhash_to_dfstoploss_map[order_hash] = df_stoploss

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
            if filled_orders:
                import ipdb

                ipdb.set_trace()

            # 3.1.1
            self._initialize_stoploss_dataframes(filled_orders)
            stoploss_hit_order_hashes = self.get_stoploss_hit_order_hashes(filled_orders)
            if stoploss_hit_order_hashes:
                self.register_future_stoploss_hits(stoploss_hit_order_hashes)

            # 4. Inform strategy about the trade by passing the metadata of the trade.
            self.strategy.on_trade_execution(filled_orders)

            # 5. Update all the metrics for the time step by calling the update_metrics function.
            self.update_step_metrics()

        # 6. When all the timesteps are done, then compute one-time metrics such as Sharpe ratio, Expectancy and more.
        self.update_final_metrics()
