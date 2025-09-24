import copy
import datetime as dt
import json
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Union

import pandas as pd
from rich import print

from connectors.dbconnector import DBConnector


@dataclass
class Action:
    option_type: str  # must be "CE" or "PE"
    strike: Union[int, float]  # must be positive
    trade_type: str  # must be "long" or "short"
    expiry: str  # must be provided
    order_type: str  # must be "market", "limit", "market_stoploss", or "market_stoploss_trail"
    num_lots: int = 1  # positive integer, default = 1
    limit_price: Union[int, float, None] = None  # required only if order_type="limit"
    lot_type: str = 'full'  # "full" or "split"
    lot_idx: int = 1  # index always starts at 1
    square_off_id: Union[int, None] = None  # Unique hash for the action
    stoploss: Union[int, float, None] = None  # Stoploss value in points
    target: Union[int, float, None] = None  # Target price

    def __post_init__(self):
        assert self.strike > 0, 'strike must be positive'
        assert self.option_type in ('CE', 'PE'), "option_type must be 'CE' or 'PE'"
        assert isinstance(self.num_lots, int) and self.num_lots > 0, 'num_lots must be a positive integer'
        assert self.trade_type in ('long', 'short'), "trade_type must be 'long' or 'short'"
        assert self.order_type in (
            'market',
            'limit',
            'market_stoploss',
            'market_stoploss_trail',
        ), "order_type must be 'market', 'limit', 'market_stoploss', or 'market_stoploss_trail'"
        if self.order_type == 'limit':
            assert self.limit_price is not None, 'limit_price must be specified for limit orders'
        if self.order_type in ('market_stoploss', 'market_stoploss_trail'):
            assert self.stoploss is not None, 'Initial stoploss must be specified for stoploss orders'
        assert isinstance(self.expiry, str), "expiry must be a string format 'YYYY-MM-DD' "
        assert self.lot_type in ('full', 'split'), "lot_type must be 'full' or 'split'"
        assert isinstance(self.lot_idx, int) and self.lot_idx > 0, 'lot_idx must be a positive integer'

        # Create unique key
        lot_info = f'__lot_type={self.lot_type}__lot_idx={self.lot_idx}'

        self.key = f'{self.trade_type}__num_lots={self.num_lots}__option_type={self.option_type}__strike={int(self.strike)}__expiry={self.expiry}__order_type={self.order_type}{lot_info}'

        if self.order_type == 'limit':
            self.key += f'__limit_price={round(self.limit_price, 6)}'

    def __hash__(self):
        return hash(self.key)

    def __eq__(self, other):
        if not isinstance(other, Action):
            return False
        return self.key == other.key

    def split_to_single_lots(self) -> list['Action']:
        """Return a list of Actions with num_lots=1, lot_type='split', and unique lot_idx."""
        if self.num_lots <= 1:
            return [self]
        return [
            Action(
                option_type=self.option_type,
                strike=self.strike,
                expiry=self.expiry,
                num_lots=1,
                trade_type=self.trade_type,
                order_type=self.order_type,
                limit_price=self.limit_price,
                lot_type='split',
                lot_idx=i + 1,  # always starts from 1
                square_off_id=None,
            )
            for i in range(self.num_lots)
        ]

    def opposite_action(self):
        return Action(
            option_type=self.option_type,  # keep same option type
            strike=self.strike,
            expiry=self.expiry,
            num_lots=self.num_lots,
            trade_type='short' if self.trade_type == 'long' else 'long',
            order_type=self.order_type,
            limit_price=self.limit_price,
            lot_type=self.lot_type,
            lot_idx=self.lot_idx,
            square_off_id=None,
            stoploss=self.stoploss,
            target=self.target,
        )

    def save(self, savedir: str, filename: str = 'action.json'):
        path = Path(savedir)
        path.mkdir(parents=True, exist_ok=True)

        data = asdict(self)
        # only convert Timestamps, not all strings
        for k, v in data.items():
            if isinstance(v, pd.Timestamp):
                data[k] = v.isoformat()

        file_path = path / filename
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=4)

    @classmethod
    def load(cls, action_json_path: str):
        with open(action_json_path, 'r') as f:
            data = json.load(f)

        # safely restore timestamps only if they look like ISO timestamps
        for k, v in data.items():
            if isinstance(v, str):
                try:
                    ts = pd.Timestamp(v)
                    # keep only if valid ISO string, not words like "long" or "CE"
                    if v == ts.isoformat():
                        data[k] = ts
                except Exception:
                    pass
        return cls(**data)


class Strategy(ABC):
    """Base class for all trading strategies.

    Example for `self.position`
    -------
    >>> self.position
    [
    ...     {
    ...         'hash': 7435533710701754627,
    ...         'timestamp': Timestamp('2024-01-01 09:15:00'),
    ...         'action': Action(option_type='PE', strike=21700, trade_type='short',
    ...                          expiry='2024-01-04', order_type='market_stoploss',
    ...                          num_lots=1, limit_price=None, lot_type='full',
    ...                          lot_idx=1, square_off_id=None, stoploss=inf,
    ...                          target=None),
    ...         'trade_type': 'short',
    ...         'price': 110.85,
    ...         'stoploss_price_level': inf,
    ...         'stoploss_hit_timestamp': None,
    ...         'status': 'filled'
    ...     },
    ...     {
    ...         'hash': 2132882707902098704,
    ...         'timestamp': Timestamp('2024-01-01 09:15:00'),
    ...         'action': Action(option_type='CE', strike=21700, trade_type='short',
    ...                          expiry='2024-01-04', order_type='market_stoploss',
    ...                          num_lots=1, limit_price=None, lot_type='full',
    ...                          lot_idx=1, square_off_id=None, stoploss=inf,
    ...                          target=None),
    ...         'trade_type': 'short',
    ...         'price': 137.45,
    ...         'stoploss_price_level': inf,
    ...         'stoploss_hit_timestamp': None,
    ...         'status': 'filled'
    ...     }
    ... ]
    """

    def __init__(self, config, dbconnector: DBConnector):
        """Initialize strategy with config and database connector."""
        self.config = config
        self.dbconnector = dbconnector

        # Params common to all strategies
        self.position = []  # will contain orders that are 'filled'
        self.outstanding_orders = None  # will change later according to orders other than filled
        self.position_tally = {}  # Will contain the tally of each filled --> squared of position

    # Abstract methods to be implemented by subclasses
    @abstractmethod
    def action(self, timestamp: pd.Timestamp) -> Union[list[Action], None]:
        """Execute trade action based on rules."""
        raise NotImplementedError('Subclasses must implement action()')

    @abstractmethod
    def about(self) -> str:
        """Return a string describing the strategy."""
        raise NotImplementedError('Subclasses must implement about()')

    # Common methods for all strategies
    def square_off_actions(self, square_off_ids: set[int] | None = None) -> list[Action]:
        """Return all the actions required to square off the open positions at market order"""

        actions = []
        if square_off_ids is None:
            for pos in self.position:
                opposite_action: Action = pos['action'].opposite_action()
                opposite_action.square_off_id = pos['hash']
                actions.append(opposite_action)
        elif square_off_ids and len(square_off_ids) > 0:
            for pos in self.position:
                if pos['hash'] in square_off_ids:
                    opposite_action = pos['action'].opposite_action()
                    opposite_action.square_off_id = pos['hash']
                    actions.append(opposite_action)

        return actions

    def on_trade_execution(self, metadata: list[dict], outstanding_orders: list):
        """
        metadata: List of `filled` orders.
        outstanding_orders: `unfulfilled` orders
        """
        self.outstanding_orders = copy.deepcopy(outstanding_orders)

        for filled_position in metadata:
            # 1. If this is a square_off order, clear from self.position
            if filled_position['action'].square_off_id:
                position_to_remove = None
                for our_position in self.position:
                    if our_position['hash'] == filled_position['action'].square_off_id:
                        position_to_remove = our_position
                        break

                assert position_to_remove, f'INVALID SQUARE-OFF. A filled position does not exist in {self.position}.'
                self.position_tally[filled_position['action'].square_off_id]['closed'] = filled_position
                self.position.remove(position_to_remove)
            # 2. Else, simply add to self.position
            else:
                self.position.append(filled_position)
                self.position_tally[filled_position['hash']] = {}
                self.position_tally[filled_position['hash']]['opened'] = filled_position
                self.position_tally[filled_position['hash']]['closed'] = None
