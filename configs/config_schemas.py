import pandas as pd
from pydantic import BaseModel, field_validator, model_validator
from datetime import datetime, time, date
import pickle
import json
from typing import Literal

# ------------------------------
# BaseConfig: common save/load
# ------------------------------


class BaseConfig(BaseModel):
    model_config = {'arbitrary_types_allowed': True}

    def save(self, filepath: str):
        with open(filepath, 'wb') as f:
            pickle.dump(self, f)

    @classmethod
    def load(cls, filepath: str):
        with open(filepath, 'rb') as f:
            obj = pickle.load(f)
        if not isinstance(obj, cls):
            raise TypeError(f'Expected {cls.__name__}, got {type(obj).__name__}')
        return obj

    def as_str(self):
        """
        Returns a JSON string representation of the config.
        """
        return json.dumps(self.model_dump(), sort_keys=True, default=str)

    def as_dict(self):
        """
        Returns a dictionary representation of the config.
        """
        return self.model_dump()


#########################################################################################
# ------------------------------
# STRATEGY Configs
# ------------------------------
#########################################################################################


class StraddleConfig(BaseConfig):
    name: str
    call_risk: float
    trail_call_risk: bool
    put_risk: float
    trail_put_risk: int
    long_or_short: str
    entry_time: time
    exit_time: time
    lot_size: int
    call_order_type: str = None
    put_order_type: str = None

    @field_validator('entry_time', 'exit_time', mode='before')
    def parse_time(cls, v):
        return datetime.strptime(v, '%H:%M:%S').time()

    @model_validator(mode='after')
    def make_order_types(self):
        self.call_order_type = 'market_stoploss_trail' if self.trail_call_risk else 'market_stoploss'
        self.put_order_type = 'market_stoploss_trail' if self.trail_put_risk else 'market_stoploss'
        return self


class WeeklyStraddleConfig(BaseConfig):
    name: str
    long_or_short: str
    call_risk: float
    trail_call_risk: bool
    put_risk: float
    trail_put_risk: bool
    entry_time: time
    exit_time: time
    lot_size: int
    call_order_type: str = None
    put_order_type: str = None

    @field_validator('entry_time', 'exit_time', mode='before')
    def parse_time(cls, v):
        return datetime.strptime(v, '%H:%M:%S').time()

    @model_validator(mode='after')
    def make_order_types(self):
        self.call_order_type = 'market_stoploss_trail' if self.trail_call_risk else 'market_stoploss'
        self.put_order_type = 'market_stoploss_trail' if self.trail_put_risk else 'market_stoploss'
        return self


STRATEGY_NAME_TO_STRATEGY_CONFIG_MAP = {'straddle': StraddleConfig, 'weekly_straddle': WeeklyStraddleConfig}

###############################################################
# ------------------------------
# Backtester Configs
# ------------------------------
###############################################################


class BaseBacktesterConfig(BaseConfig):
    name: str
    start_date: date
    end_date: date
    per_lot_transaction_cost: float
    lot_size: int
    results_dir: str

    @field_validator('start_date', 'end_date', mode='before')
    def parse_dates(cls, v):
        return pd.Timestamp(v).date()

class PositionalBacktesterConfig(BaseConfig):
    name: str
    start_date: date
    end_date: date
    per_lot_transaction_cost: float
    lot_size: int
    results_dir: str
    total_position_risk: float

    @field_validator('start_date', 'end_date', mode='before')
    def parse_dates(cls, v):
        return pd.Timestamp(v).date()


BACKTESTER_NAME_TO_BACKTESTER_CONFIG_MAP = {
    'base_backtester': BaseBacktesterConfig,
    'positional_backtester': PositionalBacktesterConfig,
}
