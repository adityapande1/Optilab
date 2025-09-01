from connectors.dbconnector import DBConnector
import hashlib
from typing import Union
from strategy import Action, Strategy
import pandas as pd
from dataclasses import dataclass
from tqdm import tqdm
from rich import print
import os
from rich import print
import pickle
from constants import BACKTEST_RESULTS_FOLDERPATH

@dataclass
class Order:
    action: Action
    timestamp: pd.Timestamp
    status: str = "pending"   # e.g. pending, filled, cancelled, rejected

    def __post_init__(self):
        assert isinstance(self.action, Action), "action must be an Action instance"
        assert self.action.num_lots == 1, "Order must be created with exactly 1 lot"
        assert isinstance(self.timestamp, pd.Timestamp), "timestamp must be a pandas Timestamp"
        assert self.status in ("pending", "filled", "cancelled", "rejected"), "invalid status"

        # Build unique hash
        order_key = f"{self.action.key}__{self.timestamp}"
        self.hash = self._generate_positive_hash(order_key)

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
    def __init__(self, config, strategy: Strategy, dbconnector: DBConnector):
        self.config = config
        self.strategy = strategy
        self.dbconnector = dbconnector
        self.metric_list = [('interval_pnl', float, 0), ('pnl', float, 0)] 
        self.outstanding_orders = []
        self.hash2position_dfs = {}   # Stores dfs of each position (one for each filled order) with key as the hash of that position
        self.initialized_position_hashes = set()

    def initialize_metrics(self, timestamps: pd.DatetimeIndex):
        """
        Initialize portfolio metrics DataFrame : `self.df_portfolio_metrics` with a pandas datetime index of `timestamps`.
         - `df_portfolio_metrics` stores the portfolio's performance metrics over the whole backtesting period.
         - `self.metric_list` defines the metrics (columns) to be tracked, their initial values and types.

        Args
        ----------
        timestamps (pd.DatetimeIndex) : The timestamps for the backtesting period.

        Returns
        -------
        None

        """

        self.df_portfolio_metrics = pd.DataFrame(index=timestamps)
        self.df_portfolio_metrics.index.name = 'timestamp'

        for metric, metric_type, default_val in self.metric_list:
            self.df_portfolio_metrics[metric] = default_val
            self.df_portfolio_metrics[metric] = self.df_portfolio_metrics[metric].astype(metric_type)

    def validate_action(self, square_off_id: int) -> bool:
        """
        Validate whether a `square_off_id` corresponds to an existing position (filled and still open) in `self.strategy.position`.

        A `square_off_id` is valid if there exists a position dictionary in `self.strategy.position` where the `'hash'` key matches the given ID.

        Args
        ----------
        square_off_id (int) : The unique identifier of the position to validate.
        
        Returns
        -------
        bool : True if the `square_off_id` has a corresponding position in the current positions.

        Raises
        ------
        ValueError : If the square-off ID does not correspond to any existing position.
        """
        for position in self.strategy.position:
            if square_off_id == position['hash']:
                return True
        raise ValueError(f"{square_off_id} is an invalid hash for a square-off action.")

    def validate_actions(self, actions: list[Action]) -> list[Action]:
        """
        Validate a list of actions. Check square_off_id validity if it is a square_off action. 
        
        An action is considered valid if 
        - It is a fresh new action (with square_off_id as `None`)
        - It has a valid square_off_id i.e. it corresponds ( is opposite action to ) to a previously filled and still open position in `self.strategy.position`

        Args
        ----------
        actions (list[Action]) : The list of actions to be validated.

        Returns
        -------
        list[Action] : The list of validated actions.

        """

        validated_actions = []
        for action in actions:
            if action.square_off_id:
                validity = self.validate_action(action.square_off_id)
                if validity:
                    validated_actions.append(action)
            else:
                validated_actions.append(action)
        return validated_actions

    def collect_orders(self, actions: list[Action], timestamp: pd.Timestamp) -> list[Order]:
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
            action_list = [action] if action.num_lots == 1 else action.split()        # List containing only actions with num_lots=1
            for single_lot_action in action_list:
                order = Order(action=single_lot_action, timestamp=timestamp, status="pending")
                collected_orders.append(order)
        return collected_orders

    def process_order(self, order: Order, timestamp: pd.Timestamp) -> dict:
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
            'previous_highest_level': None,   
            'previous_lowest_level': None,         
            'stoploss_hit_timestamp': None,         # The timestamp at which stoploss hits(if it does)
        }

        market_price = self.dbconnector.get_option_price(strike=order.action.strike, option_type=order.action.option_type, expiry_date=order.action.expiry, timestamp=timestamp, field='close')
        highest_level = self.dbconnector.get_option_price(strike=order.action.strike, option_type=order.action.option_type, expiry_date=order.action.expiry, timestamp=timestamp, field='high')
        lowest_level = self.dbconnector.get_option_price(strike=order.action.strike, option_type=order.action.option_type, expiry_date=order.action.expiry, timestamp=timestamp, field='low')
        
        if order.action.order_type == "market":
            order.update_status("filled")
            order_stats['price'] = market_price
        elif order.action.order_type in ["market_stoploss", "market_stoploss_trail"]:
            order.update_status("filled")
            order_stats['price'] = market_price
            lot_size = self.strategy.config.lot_size
            stoploss_level = (market_price - order.action.stoploss/lot_size) if order.action.trade_type == "long" else (market_price + order.action.stoploss/lot_size)
            order_stats['stoploss_price_level'] = stoploss_level            # This is the initial stoploss level, if its a trail stoploss then this is updated in the backtest loop
            
            if order.action.order_type == "market_stoploss_trail":
                if order.action.trade_type == "long":
                    order_stats['previous_highest_level'] = highest_level
                elif order.action.trade_type == "short":
                    order_stats['previous_lowest_level'] = lowest_level

        elif order.action.order_type == "limit":
            raise NotImplementedError("Limit orders are not yet supported.")
        
        order_stats['status'] = order.status
        return order_stats

    def process_orders(self, timestamp: pd.Timestamp) -> list[dict]:
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
        
        metadata, still_outstanding = [], []

        for order in self.outstanding_orders:
            order_stats = self.process_order(order, timestamp)
            if order.status != "filled":
                still_outstanding.append(order)
            else:
                metadata.append(order_stats)
                
        self.outstanding_orders = still_outstanding
        return metadata

    def create_df_position(self, tally_dict: dict, hash: int, valid_timestamps: pd.Index) -> pd.DataFrame:
        """
        Creates a DataFrame `df_position` for the position based on the provided tally dictionary and valid timestamps.

        - `tally_dict`: A dictionary with order hash as keys and their opened and closed information (see example below).
        - The DataFrame is created by filtering the relevant timestamps from the `valid_timestamps` based on the opening and closing timestamps in the tally dictionary.
        - The DataFrame has one column: `price`, which contains the closing prices of the underlying option during the specified time range.
        - If `opening_action.order_type` is "market_stoploss" or "market_stoploss_trail", the last row's price is set to the stoploss price level.

        Args
        ----------
        tally_dict (dict) : The tally dictionary containing position information.
        hash (int) : The hash identifier for the position in tally_dict.
        valid_timestamps (pd.Index) : The valid timestamps for the position.

        Returns
        -------
        pd.DataFrame : A DataFrame containing the price information for the specified position.

        Example Tally Dictionary
        -------
        >>> tally_dict = {
        ...     "1234": {
        ...         "opened": {"timestamp": pd.Timestamp("2023-01-01 09:30:00"), "action": Action(...), ...},
        ...         "closed": {"timestamp": pd.Timestamp("2023-01-01 10:15:00"), "action": Action(...), ...}
        ...     },
        ...     "5678": {
        ...         "opened": {"timestamp": pd.Timestamp("2023-01-02 09:45:00"), "action": Action(...), ...},
        ...         "closed": {"timestamp": pd.Timestamp("2023-01-02 11:00:00"), "action": Action(...), ...}
        ...     }
        ... }

        
        """

        assert (tally_dict['opened'] is not None) and (tally_dict['closed'] is not None), "tally_dict must have both 'opened' and 'closed' entries to create df_position"
        start_timestamp = tally_dict['opened']['timestamp']
        opening_action = tally_dict['opened']['action']
        end_timestamp = tally_dict['closed']['timestamp']
        subset_timestamps = valid_timestamps[(valid_timestamps >= start_timestamp) & (valid_timestamps <= end_timestamp)]
        df_position = self.dbconnector.get_option_df(option_type=opening_action.option_type, strike=opening_action.strike, expiry_date=opening_action.expiry)
        df_position = df_position.loc[subset_timestamps]
        df_position = df_position[['close']]    # choose only the 'close' price
        df_position = df_position.rename(columns={'close': 'price'})    # rename it to price

        if opening_action.order_type in ["market_stoploss", "market_stoploss_trail"]:
            assert tally_dict['opened']['stoploss_price_level'] is not None, "Stoploss order_type must have a stoploss_price_level"
            if tally_dict['opened']['stoploss_hit_timestamp']:
                df_position.at[end_timestamp, 'price'] = tally_dict['opened']['stoploss_price_level']

        self.initialized_position_hashes.add(hash)
        return df_position.copy()

    def update_step_metrics(self, timestamp: pd.Timestamp, metadata, valid_timestamps: pd.Index):

        for hash, tally_dict in self.strategy.position_tally.items():
            if (tally_dict['closed'] is not None) and (hash not in self.initialized_position_hashes):    # meaning the open position has been closed and df_position can now be completely made
                df_position = self.create_df_position(tally_dict, hash, valid_timestamps)
                self.hash2position_dfs[hash] = df_position
    
    def _update_final_metric_interval_pnl(self):
        for hash, df_position in self.hash2position_dfs.items():
            if df_position is not None:
                position = self.strategy.position_tally[hash]['opened']['action'].trade_type
                df_position['interval_pnl'] = df_position['price'].diff() * self.strategy.config.lot_size
                # if trade_type is "short" Then do - interval pnl
                if position == "short":
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

    def save_results(self, foldername: str = None):
        '''Saves the backtest results to the specified directory'''

        folder_path = os.path.join(BACKTEST_RESULTS_FOLDERPATH, f"{self.strategy.name}__{self.backtest_code}" if foldername is None else foldername)
        os.makedirs(folder_path, exist_ok=True)

        strategy_config_dict = self.strategy.config.as_dict()
        with open(os.path.join(folder_path, "strategy_config.pkl"), "wb") as f:
            pickle.dump(strategy_config_dict, f)

        backtester_config_dict = self.config.as_dict()
        with open(os.path.join(folder_path, "backtester_config.pkl"), "wb") as f:
            pickle.dump(backtester_config_dict, f)

        self.df_portfolio_metrics.to_parquet(os.path.join(folder_path, "df_portfolio_metrics.parquet"))    # Save portfolio metrics

        positions_folder = os.path.join(folder_path, "positions")
        os.makedirs(positions_folder, exist_ok=True)
        for hash, df_position in self.hash2position_dfs.items():    # Save df_position
            df_position.to_parquet(os.path.join(positions_folder, f"df_position_{hash}.parquet"))


        actions_folder = os.path.join(folder_path, "actions")
        os.makedirs(actions_folder, exist_ok=True)
        # Position tally data
        for hash, position_dict in self.strategy.position_tally.items():
            position_dict['opened']['action'].save(savedir=actions_folder, filename=f"action_{hash}.json")

        if hasattr(self.strategy, "about") and callable(getattr(self.strategy, "about")):   # Save about strategy if about() function implemented
            with open(os.path.join(folder_path, "about_strategy.txt"), "w") as f:
                f.write(self.strategy.about())

        print(f"Backtest results saved to {folder_path}\n")

    def update_stoploss_price_level(self, pos: dict, timestamp: pd.Timestamp):
        """
        Update the stoploss price level for a given position dictionary.

        - If position's `action.trade_type` is "long", the stoploss is shifted upward (by `gap_up`) if the current candle high exceeds the previous high.
        - If position's `action.trade_type` is "short", the stoploss is shifted downward (by `gap_down`) if the current candle low is below the previous low.

        Parameters
        ----------
        pos : Position dictionary containing action and stoploss details.
        timestamp : Current timestamp to check for price updates.
        """
        action = pos['action']
        if action.trade_type == "long":
            current_highest_level = self.dbconnector.get_option_price(strike=action.strike, option_type=action.option_type, expiry_date=action.expiry, timestamp=timestamp, field='high')
            if current_highest_level > pos['previous_highest_level']:
                gap_up = current_highest_level - pos['previous_highest_level']
                pos['stoploss_price_level'] += gap_up
                pos['previous_highest_level'] = current_highest_level
        elif action.trade_type == "short":
            current_lowest_level = self.dbconnector.get_option_price(strike=action.strike, option_type=action.option_type, expiry_date=action.expiry, timestamp=timestamp, field='low')
            if current_lowest_level < pos['previous_lowest_level']:
                gap_down = pos['previous_lowest_level'] - current_lowest_level
                pos['stoploss_price_level'] -= gap_down
                pos['previous_lowest_level'] = current_lowest_level

    def check_stoploss_condition(self, stoploss_price_level: float, ohlc_list: list[float], trade_type: str):
        """
        Check whether the stoploss is hit given stoploss_level and OHLC prices.

        - For a long trade, the stoploss is considered hit if the lowest price falls below the stoploss level.
        - For a short trade, it is considered hit if the highest price rises above the stoploss level.

        Parameters
        ----------
        stoploss_price_level : The stoploss price level to check against.
        ohlc_list : A list containing the OHLC prices [open, high, low, close].
        trade_type : The type of trade ('long' or 'short').

        Returns
        -------
        bool : True if the stoploss is hit, otherwise False.
        """

        assert len(ohlc_list) == 4, "ohlc_list must contain 4 elements: (open, high, low, close)"
        assert trade_type in ["long", "short"], "trade_type must be either 'long' or 'short'"

        if stoploss_price_level is not None:
            (o, h, l, c) = ohlc_list
            if (trade_type == "long" and l <= stoploss_price_level) or (trade_type == "short" and h >= stoploss_price_level):
                return True
        return False

    def get_stoploss_actions(self, timestamp: pd.Timestamp) -> Union[list[Action], None]:
        """
        Get stoploss actions for the current strategy positions ( `self.strategy.position` ) at a given timestamp. 
        - For each position with `action.order_type` as "market_stoploss" or "market_stoploss_trail", check if the stoploss condition is met. 
        - If met, generate opposite actions to square off those positions.

        Parameters
        ----------
            timestamp : The timestamp at which to check for stoploss condition.

        Returns
        -------
            stoploss_actions : Actions required to square off the positions for which stoploss conditions were met.
        """

        square_off_ids = set()
        for pos in self.strategy.position:
            action = pos['action']
            if action.order_type in ["market_stoploss", "market_stoploss_trail"]:
                if action.order_type == "market_stoploss_trail":
                    self.update_stoploss_price_level(pos, timestamp)
                ohlc = self.dbconnector.get_option_df(option_type=action.option_type, strike=action.strike, expiry_date=action.expiry).loc[timestamp, ['open', 'high', 'low', 'close']].values
                stoploss_check = self.check_stoploss_condition(stoploss_price_level=pos['stoploss_price_level'], ohlc_list=ohlc, trade_type=action.trade_type)
                if stoploss_check:
                    square_off_ids.add(pos['hash'])
                    # print(f"Stoploss hit for position: {pos['hash']} at {timestamp}")
                    pos['stoploss_hit_timestamp'] = timestamp

        stoploss_actions = self.strategy.square_off_actions(square_off_ids=square_off_ids)

        return stoploss_actions

    def run(self) -> dict:
    
        self.valid_timestamps = self.dbconnector.df_spot.loc[self.config.start_date : self.config.end_date].index
        self.valid_timestamps = self.valid_timestamps.sort_values()
        self.initialize_metrics(timestamps=self.valid_timestamps)
        self.backtest_code = pd.Timestamp.now().strftime("%Y-%m-%d_%H:%M:%S")

        for current_timestamp in tqdm(self.valid_timestamps, desc="Running Backtest", unit="timestamp"):
            if current_timestamp.date() == pd.Timestamp("2024-11-01").date():
                continue  # Skip the timestamp for which we don't have data

            strategy_actions = self.strategy.action(current_timestamp)
            stoploss_actions = self.get_stoploss_actions(current_timestamp)     # Ask Nino : Abhi tak upar waley action self.positions mein add nai huwey hongey is that fine. I think ...
            actions = (strategy_actions or []) + (stoploss_actions or [])       # Python idiom !!! Pretty cool
            actions = list(set(actions))

            if actions:
                validated_actions = self.validate_actions(actions)                          # Checks all Action(s) with square_off_id(if not None) have corresponding filled_position in self.strategy.position
                new_orders = self.collect_orders(validated_actions, current_timestamp)     # Converts validated_actions(list[Action]) to new_orders(list[Order]) assigning them hash, timestamp, status:'pending'
                self.outstanding_orders.extend(new_orders)    

            # 3. Process the orders using process_orders function.            
            metadata = self.process_orders(current_timestamp)

            # if actions:
            #     import ipdb; ipdb.set_trace()

            # 4. Inform strategy about the trade by passing the metadata of the trade.            
            self.strategy.on_trade_execution(metadata, self.outstanding_orders)

            # 5. Update all the metrics for the time step by calling the update_metrics function.            
            self.update_step_metrics(current_timestamp, metadata, self.valid_timestamps)

        # 6. When all the timesteps are done, then compute one-time metrics such as Sharpe ratio, Expectancy and more.        
        self.update_final_metrics()

