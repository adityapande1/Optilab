from dataclasses import dataclass
from strategy import Action
import pandas as pd
import hashlib
from utils.data_utils import generate_positive_hash
import os
from abc import ABC, abstractmethod
from connectors.dbconnector import DBConnector
from strategy import Strategy
from constants import BACKTEST_RESULTS_FOLDERPATH


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

    @abstractmethod
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

    @abstractmethod
    def validate_actions(self, actions: list[Action]) -> list[Action]:
        """
        Validate a list of actions. Check square_off_id validity if it is a square_off action.

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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
    def save_results(self, foldername: str = None):
        """Saves the backtest results to the specified directory"""

        folder_path = os.path.join(
            BACKTEST_RESULTS_FOLDERPATH,
            f'{self.strategy.name}__{self.backtest_code}' if foldername is None else foldername,
        )
        os.makedirs(folder_path, exist_ok=True)

        # Configs
        self.strategy.config.save(filepath=os.path.join(folder_path, 'strategy_config.pkl'))
        self.config.save(filepath=os.path.join(folder_path, 'backtester_config.pkl'))

        # All positions
        positions_folder = os.path.join(folder_path, 'positions')
        os.makedirs(positions_folder, exist_ok=True)
        for hash, df_position in self.orderhash_to_dfposition_map.items():  # Save df_position
            df_position.to_parquet(os.path.join(positions_folder, f'df_position_{hash}.parquet'))

        # final portfolio metrics
        self.df_portfolio_metrics.to_parquet(os.path.join(folder_path, 'df_portfolio_metrics.parquet'))  # Save portfolio metrics

        # All actions
        actions_folder = os.path.join(folder_path, 'actions')
        os.makedirs(actions_folder, exist_ok=True)
        # Position tally data
        for hash, position_dict in self.strategy.position_tally.items():
            position_dict['opened']['action'].save(savedir=actions_folder, filename=f'action_{hash}.json')

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

    @abstractmethod
    def run(self):
        """Backtests the run loop."""
        raise NotImplementedError('Subclasses must implement run()')
