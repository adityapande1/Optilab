import pandas as pd
from tqdm import tqdm
from backtest import Backtester
from connectors.dbconnector import DBConnector
from strategy import Strategy
from utils.data_utils import generate_combined_ohlc_dataframe
from rich import print

class HedgedBackTester(Backtester):
    """
    PositionalBackTester is responsible to keep track of the metrics.
    """

    def __init__(self, config, strategy: Strategy, dbconnector: DBConnector):
        super().__init__(config, strategy, dbconnector)
        assert strategy.name in ('IronButterflyHedged'), f'\nStrategy {strategy.name} not supported in HedgedBackTester'
        self.coupled_orderhashes_to_df_coupled_stoploss_map = dict()    # Map of frozenset of coupled order hashes to their combined stoploss DataFrame

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

        if self.strategy.name in ('IronButterflyHedged'):
            max_possible_exit_timestamp = pd.Timestamp.combine(entry_timestamp.date(), self.strategy.config.exit_time)  # Straddle exits on the same day
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

    def _initialize_stoploss_dataframes_for_each_orderhash_of_coupled_orderhashes(self, filled_orders: list[dict], coupled_orderhashes: frozenset, df_coupled_stoploss: pd.DataFrame) -> set:
        """
        Initialize a stoploss DataFrame for each `stoploss` type order in `filled_orders` belonging to `coupled_orderhashes`.
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

        selected_filled_orders = [order_stats for order_stats in filled_orders if order_stats['hash'] in coupled_orderhashes]
        for order_stats in selected_filled_orders:
            assert order_stats['status'] == 'filled', 'Only filled orders should be in filled_orders list'
            action, order_hash = order_stats['action'], order_stats['hash']
            if (
                (action.order_type in ('market_stoploss', 'market_stoploss_trail'))  # Order of Stoploss type
                and (order_hash not in self.orderhash_to_dfstoploss_map)  # df_stoploss not already initialized
                and (action.square_off_id is None)  # Opening fresh order i.e. not a square-off order
            ):
                df_stoploss = self._create_df_stoploss(order_stats, df_coupled_stoploss)
                self.orderhash_to_dfstoploss_map[order_hash] = df_stoploss

    def _get_combined_stoploss_dataframe_for_coupled_orders(self, coupled_orderhashes: frozenset, risk_for_coupled_position: float, filled_orders: list[dict]) -> pd.DataFrame:
        ohlc_dataframes, trade_types = [], []
        coupled_order_stats = [order_stats for order_stats in filled_orders if order_stats['action'].square_off_id is None and order_stats['hash'] in coupled_orderhashes]

        if coupled_order_stats:
            # Assert all the order_stat['timestamp'] are same for fresh_orders
            timestamps = {order_stats['timestamp'] for order_stats in coupled_order_stats}
            assert len(timestamps) == 1, f'All timestamps in filled_orders must be same for fresh_orders. Found timestamps : {timestamps}'
            common_order_filling_timestamp = timestamps.pop()

            starting_deal_price = 0
            for order_stats in coupled_order_stats:
                action = order_stats['action']
                starting_deal_price = starting_deal_price + order_stats['price'] if order_stats['trade_type'] == 'long' else starting_deal_price - order_stats['price']
                trade_types.append(order_stats['trade_type'])
                df_option = self.dbconnector.get_option_df(option_type=action.option_type, strike=action.strike, expiry_date=action.expiry)
                df_option = df_option[df_option.index >= common_order_filling_timestamp].copy()
                ohlc_dataframes.append(df_option)

            df_option_combined = generate_combined_ohlc_dataframe(ohlc_dataframes, trade_types)
            starting_stoploss_level = starting_deal_price - risk_for_coupled_position / self.config.lot_size
            df_coupled_stoploss = self.calculate_stoploss_levels(df=df_option_combined, starting_stoploss_level=starting_stoploss_level, position_type='long', trail_stoploss=False)

        else:
            df_coupled_stoploss = pd.DataFrame()

        return df_coupled_stoploss

    def _get_coupled_orderhashes_to_risk_map(self, filled_orders: list[dict], strategy: Strategy) -> dict:

        assert strategy.name in ('IronButterflyHedged'), f'Strategy {strategy.name} not supported in PositionalBackTester._get_coupled_orderhashes_to_risk_map'

        coupled_orderhashes_to_risk_map = {}
        if strategy.name == 'IronButterflyHedged':
            call_leg_hashes, put_leg_hashes = [], []
            for order_stats in filled_orders:
                action, order_hash = order_stats['action'], order_stats['hash']
                if action.option_type == 'CE' and action.square_off_id is None:
                    call_leg_hashes.append(order_hash)
                elif action.option_type == 'PE' and action.square_off_id is None:
                    put_leg_hashes.append(order_hash)
            if call_leg_hashes:
                coupled_orderhashes_to_risk_map[frozenset(call_leg_hashes)] = strategy.config.bear_call_spread_risk
            if put_leg_hashes:
                coupled_orderhashes_to_risk_map[frozenset(put_leg_hashes)] = strategy.config.bull_put_spread_risk

        return coupled_orderhashes_to_risk_map

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
            if filled_orders:
                # import ipdb; ipdb.set_trace()
                coupled_orderhashes_to_risk_map = self._get_coupled_orderhashes_to_risk_map(filled_orders, strategy=self.strategy)
                for coupled_orderhashes, coupled_risk in coupled_orderhashes_to_risk_map.items():
                    self.coupled_orderhashes_to_df_coupled_stoploss_map[coupled_orderhashes] = self._get_combined_stoploss_dataframe_for_coupled_orders(coupled_orderhashes, coupled_risk, filled_orders)
                    self._initialize_stoploss_dataframes_for_each_orderhash_of_coupled_orderhashes(filled_orders, coupled_orderhashes, self.coupled_orderhashes_to_df_coupled_stoploss_map[coupled_orderhashes])


            # 3.1.2
            stoploss_hit_order_hashes = self.get_stoploss_hit_order_hashes(filled_orders)
            if stoploss_hit_order_hashes:
                self.register_future_stoploss_hits(stoploss_hit_order_hashes)

            # 4. Inform strategy about the trade by passing the metadata of the trade.
            self.strategy.on_trade_execution(filled_orders)

            # 5. Update all the metrics for the time step by calling the update_metrics function.
            self.update_step_metrics()

        import ipdb; ipdb.set_trace()
        # 6. When all the timesteps are done, then compute one-time metrics such as Sharpe ratio, Expectancy and more.
        self.update_final_metrics()
