from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
import json
from pathlib import Path
from typing import Union
import datetime as dt
import pandas as pd
from connectors.dbconnector import DBConnector

@dataclass
class StrategyConfig:
    risk_per_trade: float    
    reward_to_risk: float    
    lot_size: int = 75

    def __post_init__(self):
        assert self.risk_per_trade > 0, "risk_per_trade must be positive"
        assert self.reward_to_risk > 0, "reward_to_risk must be positive"
        assert self.lot_size > 0, "lot_size must be positive"
        self.reward_per_trade = self.risk_per_trade * self.reward_to_risk

    def __repr__(self):
        return f"StrategyConfig(risk_per_trade={self.risk_per_trade}, reward_to_risk={self.reward_to_risk}, reward_per_trade={self.reward_per_trade}, lot_size={self.lot_size})"

    def save(self, savedir: str):
        path = Path(savedir)
        path.mkdir(parents=True, exist_ok=True)

        data = asdict(self)
        for k, v in data.items():
            if isinstance(v, pd.Timestamp):
                data[k] = v.isoformat()

        filename = path / "strategy_config.json"
        with open(filename, "w") as f:
            json.dump(data, f, indent=4)
    
    @classmethod
    def load(cls, strategy_config_json_path):
        with open(strategy_config_json_path, "r") as f:
            data = json.load(f)
        for k, v in data.items():
            if isinstance(v, str):
                try:
                    data[k] = pd.Timestamp(v)
                except ValueError:
                    pass
        return cls(**data)

@dataclass
class Action:
    option_type: str                   # must be "CE" or "PE"
    strike: Union[int, float]          # must be positive
    trade_type: str                      # must be "buy" or "sell"
    expiry: Union[str, dt.date, pd.Timestamp]   # must be provided
    order_type: str                    # must be "market" or "limit"
    num_lots: int = 1                  # positive integer, default = 1
    limit_price: Union[int, float, None] = None  # required only if order_type="limit"
    lot_type: str = "full"             # "full" or "split"
    lot_idx: int = 1                   # index always starts at 1
    square_off_id: Union[int, None] = None  # Unique hash for the action
    stoploss: Union[int, float, None] = None  # Stoploss price
    target: Union[int, float, None] = None  # Target price

    def __post_init__(self):
        assert self.strike > 0, "strike must be positive"
        assert self.option_type in ("CE", "PE"), "option_type must be 'CE' or 'PE'"
        assert isinstance(self.num_lots, int) and self.num_lots > 0, "num_lots must be a positive integer"
        assert self.trade_type in ("buy", "sell"), "position must be 'buy' or 'sell'"
        assert self.order_type in ("market", "limit"), "order_type must be 'market' or 'limit'"
        if self.order_type == "limit":
            assert self.limit_price is not None, "limit_price must be specified for limit orders"
        assert isinstance(self.expiry, (str, dt.date, pd.Timestamp)), "expiry must be str, date, or Timestamp"
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

    def to_dict(self):
        return asdict(self)

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
            trade_type="sell" if self.trade_type == "buy" else "buy",
            order_type=self.order_type,
            limit_price=self.limit_price,
            lot_type=self.lot_type,
            lot_idx=self.lot_idx,
            square_off_id=None
        )



class Strategy(ABC):
    """Base class for all trading strategies."""

    def __init__(self, config: StrategyConfig, dbconnector: DBConnector):
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
