from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
import json
from pathlib import Path
from typing import Union, Dict, Any
import datetime as dt
import pandas as pd
from connectors.dbconnector import DBConnector
from rich import print


@dataclass
class Action:
    option_type: str                   # must be "CE" or "PE"
    strike: Union[int, float]          # must be positive
    trade_type: str                    # must be "long" or "short"
    expiry: str                        # must be provided
    order_type: str                    # must be "market", "limit", "market_stoploss", or "market_stoploss_trail"
    num_lots: int = 1                  # positive integer, default = 1
    limit_price: Union[int, float, None] = None  # required only if order_type="limit"
    lot_type: str = "full"             # "full" or "split"
    lot_idx: int = 1                   # index always starts at 1
    square_off_id: Union[int, None] = None  # Unique hash for the action
    stoploss: Union[int, float, None] = None  # Stoploss value in points    
    target: Union[int, float, None] = None  # Target price


    def __post_init__(self):
        assert self.strike > 0, "strike must be positive"
        assert self.option_type in ("CE", "PE"), "option_type must be 'CE' or 'PE'"
        assert isinstance(self.num_lots, int) and self.num_lots > 0, "num_lots must be a positive integer"
        assert self.trade_type in ("long", "short"), "trade_type must be 'long' or 'short'"
        assert self.order_type in ("market", "limit", "market_stoploss", "market_stoploss_trail"), "order_type must be 'market', 'limit', 'market_stoploss', or 'market_stoploss_trail'"
        if self.order_type == "limit":
            assert self.limit_price is not None, "limit_price must be specified for limit orders"
        if self.order_type in ("market_stoploss", "market_stoploss_trail"):
            assert self.stoploss is not None, "Initial stoploss must be specified for stoploss orders"
        assert isinstance(self.expiry, str), "expiry must be a string format 'YYYY-MM-DD' "
        assert self.lot_type in ("full", "split"), "lot_type must be 'full' or 'split'"
        assert isinstance(self.lot_idx, int) and self.lot_idx > 0, "lot_idx must be a positive integer"

        # Create unique key
        lot_info = f"__lot_type={self.lot_type}__lot_idx={self.lot_idx}"
        
        self.key = (
            f"{self.trade_type}"
            f"__num_lots={self.num_lots}"
            f"__option_type={self.option_type}"
            f"__strike={int(self.strike)}"
            f"__expiry={self.expiry}"
            f"__order_type={self.order_type}"
            f"{lot_info}"
        )

        if self.order_type == "limit":
            self.key += f"__limit_price={round(self.limit_price, 6)}"

    def split(self):
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
                lot_type="split",
                lot_idx=i+1,   # always starts from 1
                square_off_id=None 
            )
            for i in range(self.num_lots)
        ]

    def opposite_action(self):
        return Action(
            option_type=self.option_type,   # keep same option type
            strike=self.strike,
            expiry=self.expiry,
            num_lots=self.num_lots,
            trade_type="short" if self.trade_type == "long" else "long",
            order_type=self.order_type,
            limit_price=self.limit_price,
            lot_type=self.lot_type,
            lot_idx=self.lot_idx,
            square_off_id=None,
            stoploss=self.stoploss,
            target=self.target
        )
    
    def save(self, savedir: str, filename: str = "action.json"):
        path = Path(savedir)
        path.mkdir(parents=True, exist_ok=True)

        data = asdict(self)
        # only convert Timestamps, not all strings
        for k, v in data.items():
            if isinstance(v, pd.Timestamp):
                data[k] = v.isoformat()

        file_path = path / filename
        with open(file_path, "w") as f:
            json.dump(data, f, indent=4)

    @classmethod
    def load(cls, action_json_path: str):
        with open(action_json_path, "r") as f:
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
    """Base class for all trading strategies."""

    def __init__(self, config, dbconnector: DBConnector):
        """Initialize strategy with config and database connector."""
        self.config = config
        self.dbconnector = dbconnector

    @abstractmethod
    def action(self, timestamp: pd.Timestamp) -> Union[list[Action], None]:
        """Execute trade action based on rules."""
        raise NotImplementedError("Subclasses must implement action()")

    @abstractmethod
    def on_trade_execution(self, timestamp: pd.Timestamp, metadata: list[dict]):
        """Handle trade execution event."""
        raise NotImplementedError("Subclasses must implement on_trade_execution()")
