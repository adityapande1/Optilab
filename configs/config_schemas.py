from datetime import datetime, time, date
from typing import Literal
import pandas as pd
import pickle
import json
from pydantic import BaseModel, conint, confloat, field_validator, model_validator


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
# STRATEGY Configs
#########################################################################################


class StraddleConfig(BaseConfig):
    name: str
    call_risk: float
    trail_call_risk: bool
    put_risk: float
    trail_put_risk: bool
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

    @classmethod
    def get_field_choices_for_simulation(self):
        return {
            'call_risk': list(range(1000, 8001, 500)),
            'put_risk': list(range(1000, 8001, 500)),
            'trail_call_risk': [True, False],
            'trail_put_risk': [True, False],
            'entry_time': ['9:15:00', '9:30:00', '10:00:00'],
        }

    @classmethod
    def get_name(cls):
        return 'straddle'


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

    @classmethod
    def get_field_choices_for_simulation(self):
        return {
            'call_risk': list(range(1000, 8001, 500)),
            'put_risk': list(range(1000, 8001, 500)),
            'trail_call_risk': [True, False],
            'trail_put_risk': [True, False],
            'entry_time': ['9:15:00', '9:30:00', '10:00:00'],
        }

    @classmethod
    def get_name(cls):
        return 'weekly_straddle'


class StrangleConfig(BaseConfig):
    name: str
    long_or_short: str
    otm_call_risk: float
    trail_call_risk: bool
    otm_put_risk: float
    trail_put_risk: bool
    entry_time: time
    exit_time: time
    lot_size: int
    strike_interval: int
    spread_width: int
    otm_call_order_type: str = None
    otm_put_order_type: str = None

    @field_validator('entry_time', 'exit_time', mode='before')
    def parse_time(cls, v):
        return datetime.strptime(v, '%H:%M:%S').time()

    @model_validator(mode='after')
    def make_order_types(self):
        self.otm_call_order_type = 'market_stoploss_trail' if self.trail_call_risk else 'market_stoploss'
        self.otm_put_order_type = 'market_stoploss_trail' if self.trail_put_risk else 'market_stoploss'
        return self

    @classmethod
    def get_field_choices_for_simulation(self):
        return {
            'otm_call_risk': list(range(1000, 8001, 500)),
            'otm_put_risk': list(range(1000, 8001, 500)),
            'trail_call_risk': [True, False],
            'trail_put_risk': [True, False],
            'entry_time': ['9:15:00', '9:30:00', '10:00:00'],
            'spread_width': [50, 100, 150, 200],
        }

    @classmethod
    def get_name(cls):
        return 'strangle'


class IronButterflyConfig(BaseConfig):
    # Overall strategy configs
    name: str
    long_or_short: str
    entry_time: time
    exit_time: time
    lot_size: int
    wing_width: int

    # Leg configs
    otm_put_risk: float
    trail_otm_put_risk: bool
    atm_put_risk: float
    trail_atm_put_risk: bool
    atm_call_risk: float
    trail_atm_call_risk: bool
    otm_call_risk: float
    trail_otm_call_risk: bool

    # These will be set in model_validator
    otm_put_order_type: str = None
    atm_call_order_type: str = None
    atm_put_order_type: str = None
    otm_call_order_type: str = None

    @field_validator('entry_time', 'exit_time', mode='before')
    def parse_time(cls, v):
        return datetime.strptime(v, '%H:%M:%S').time()

    @model_validator(mode='after')
    def make_order_types(self):
        self.otm_put_order_type = 'market_stoploss_trail' if self.trail_otm_put_risk else 'market_stoploss'
        self.atm_put_order_type = 'market_stoploss_trail' if self.trail_atm_put_risk else 'market_stoploss'
        self.atm_call_order_type = 'market_stoploss_trail' if self.trail_atm_call_risk else 'market_stoploss'
        self.otm_call_order_type = 'market_stoploss_trail' if self.trail_otm_call_risk else 'market_stoploss'
        return self

    @classmethod
    def get_field_choices_for_simulation(self):
        return {
            'otm_put_risk': list(range(1000, 5001, 500)),
            'trail_otm_put_risk': [True, False],
            'atm_put_risk': list(range(1000, 5001, 500)),
            'trail_atm_put_risk': [True, False],
            'atm_call_risk': list(range(1000, 5001, 500)),
            'trail_atm_call_risk': [True, False],
            'otm_call_risk': list(range(1000, 5001, 500)),
            'trail_otm_call_risk': [True, False],
            'wing_width': [50, 100, 150],
            'entry_time': ['9:15:00', '9:30:00', '10:00:00'],
        }

    @classmethod
    def get_name(cls):
        return 'ironbutterfly'


class IronCondorConfig(BaseConfig):
    # Overall strategy configs
    name: str
    long_or_short: Literal['long', 'short']  # Either 'long' or 'short'
    entry_time: time
    exit_time: time
    lot_size: conint(gt=0)  # Integer >0
    body_width: conint(gt=0, multiple_of=50)  # Constrained Integer > 0 and multiple of 50
    wing_width: conint(gt=0, multiple_of=50)  # Constrained Integer > 0 and multiple of 50

    # Leg configs
    outer_otm_put_risk: confloat(ge=0) # Float >=0
    trail_outer_otm_put_risk: bool
    inner_otm_put_risk: confloat(ge=0) # Float >=0
    trail_inner_otm_put_risk: bool
    inner_otm_call_risk: confloat(ge=0) # Float >=0
    trail_inner_otm_call_risk: bool
    outer_otm_call_risk: confloat(ge=0) # Float >=0
    trail_outer_otm_call_risk: bool

    # These will be set in model_validator
    outer_otm_put_order_type: str = None
    inner_otm_put_order_type: str = None
    inner_otm_call_order_type: str = None
    outer_otm_call_order_type: str = None

    # --- Field Validators ---
    @field_validator('entry_time', 'exit_time', mode='before')
    def parse_time(cls, v):
        if isinstance(v, str):
            return datetime.strptime(v, '%H:%M:%S').time()
        return v

    # --- Model Validator ---
    @model_validator(mode='after')
    def make_order_types(self):
        self.outer_otm_put_order_type = 'market_stoploss_trail' if self.trail_outer_otm_put_risk else 'market_stoploss'
        self.inner_otm_put_order_type = 'market_stoploss_trail' if self.trail_inner_otm_put_risk else 'market_stoploss'
        self.inner_otm_call_order_type = 'market_stoploss_trail' if self.trail_inner_otm_call_risk else 'market_stoploss'
        self.outer_otm_call_order_type = 'market_stoploss_trail' if self.trail_outer_otm_call_risk else 'market_stoploss'
        return self

    @classmethod
    def get_field_choices_for_simulation(self):
        return {
            'outer_otm_put_risk': list(range(1000, 5001, 500)),
            'trail_outer_otm_put_risk': [True, False],
            'inner_otm_put_risk': list(range(1000, 5001, 500)),
            'trail_inner_otm_put_risk': [True, False],
            'inner_otm_call_risk': list(range(1000, 5001, 500)),
            'trail_inner_otm_call_risk': [True, False],
            'outer_otm_call_risk': list(range(1000, 5001, 500)),
            'trail_outer_otm_call_risk': [True, False],
            'body_width': [50, 100, 150],
            'wing_width': [50, 100, 150],
            'entry_time': ['9:15:00', '9:30:00', '10:00:00'],
        }

    @classmethod
    def get_name(cls):
        return 'ironcondor'


STRATEGY_NAME_TO_STRATEGY_CONFIG_MAP = {
    'straddle': StraddleConfig,
    'weekly_straddle': WeeklyStraddleConfig,
    'strangle': StrangleConfig,
    'ironbutterfly': IronButterflyConfig,
    'ironcondor': IronCondorConfig,
}

###############################################################
# Backtester Configs
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

    @classmethod
    def get_field_choices_for_simulation(self):
        return {}

    @classmethod
    def get_name(cls):
        return 'base_backtester'


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

    @classmethod
    def get_field_choices_for_simulation(self):
        return {'total_position_risk': list(range(1000, 20001, 1000))}

    @classmethod
    def get_name(cls):
        return 'positional_backtester'


BACKTESTER_NAME_TO_BACKTESTER_CONFIG_MAP = {
    'base_backtester': BaseBacktesterConfig,
    'positional_backtester': PositionalBacktesterConfig,
}
