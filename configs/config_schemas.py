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
            'call_risk': list(range(1500, 12001, 250)),
            'put_risk': list(range(1500, 12001, 250)),
            'trail_call_risk': [True, False],
            'trail_put_risk': [True, False],
            'entry_time': ['9:15:00', '9:20:00', '09:30:00'],
        }

    @classmethod
    def get_field_pairs_that_should_be_same_during_simulation(cls) -> list[tuple[str, str]]:
        matching_field_pairs = [
            ('call_risk', 'put_risk'),
            ('trail_call_risk', 'trail_put_risk'),
        ]
        return matching_field_pairs

    @classmethod
    def get_name(cls):
        return 'straddle'

class StraddleDailyConfig(BaseConfig):
    name: str
    long_or_short: Literal['long', 'short']  # Either 'long' or 'short'
    entry_time: time
    exit_time: time
    lot_size: conint(gt=0)  # Integer >0
    call_risk: confloat(gt=0)  # Float >0
    put_risk: confloat(gt=0)  # Float >0
    trail_call_risk: bool
    trail_put_risk: bool

    # These will be set in model_validator
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
            'call_risk': list(range(500, 12001, 250)),
            'put_risk': list(range(500, 12001, 250)),
            'trail_call_risk': [True, False],
            'trail_put_risk': [True, False],
            'entry_time': ['9:15:00', '9:20:00', '09:30:00'],
        }

    @classmethod
    def get_field_pairs_that_should_be_same_during_simulation(cls) -> list[tuple[str, str]]:
        matching_field_pairs = [
            ('call_risk', 'put_risk'),
            ('trail_call_risk', 'trail_put_risk'),
        ]
        return matching_field_pairs

    @classmethod
    def get_name(cls):
        return 'straddle_daily'

class StraddleWeeklyConfig(BaseConfig):
    name: str
    long_or_short: Literal['long', 'short']  # Either 'long' or 'short'
    entry_time: time
    exit_time: time
    lot_size: conint(gt=0)  # Integer >0
    call_risk: confloat(gt=0)  # Float >0
    put_risk: confloat(gt=0)  # Float >0
    trail_call_risk: bool
    trail_put_risk: bool

    # These will be set in model_validator
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
            'call_risk': list(range(500, 18001, 250)),
            'put_risk': list(range(500, 18001, 250)),
            'trail_call_risk': [True, False],
            'trail_put_risk': [True, False],
            'entry_time': ['9:15:00', '9:20:00', '09:30:00'],
        }

    @classmethod
    def get_field_pairs_that_should_be_same_during_simulation(cls) -> list[tuple[str, str]]:
        matching_field_pairs = [
            ('call_risk', 'put_risk'),
            ('trail_call_risk', 'trail_put_risk'),
        ]
        return matching_field_pairs

    @classmethod
    def get_name(cls):
        return 'straddle_weekly'

class StrangleDailyConfig(BaseConfig):
    name: str
    long_or_short: Literal['long', 'short']  # Either 'long' or 'short'
    entry_time: time
    exit_time: time
    lot_size: conint(gt=0)  # Integer >0
    body_width: conint(gt=0, multiple_of=50)  # Integer >0 and multiple of 50
    otm_call_risk: confloat(gt=0)  # Float >0
    trail_otm_call_risk: bool
    otm_put_risk: confloat(gt=0)  # Float >0
    trail_otm_put_risk: bool

    # These will be set in model_validator
    otm_call_order_type: str = None
    otm_put_order_type: str = None

    @field_validator('entry_time', 'exit_time', mode='before')
    def parse_time(cls, v):
        return datetime.strptime(v, '%H:%M:%S').time()

    @model_validator(mode='after')
    def make_order_types(self):
        self.otm_call_order_type = 'market_stoploss_trail' if self.trail_otm_call_risk else 'market_stoploss'
        self.otm_put_order_type = 'market_stoploss_trail' if self.trail_otm_put_risk else 'market_stoploss'
        return self

    @classmethod
    def get_field_choices_for_simulation(self):
        return {
            'otm_call_risk': list(range(1500, 12001, 250)),
            'otm_put_risk': list(range(1500, 12001, 250)),
            'trail_otm_call_risk': [True, False],
            'trail_otm_put_risk': [True, False],
            'body_width': [50, 100, 150, 200, 250],
            'entry_time': ['9:15:00', '9:20:00', '09:30:00'],
        }

    @classmethod
    def get_field_pairs_that_should_be_same_during_simulation(cls) -> list[tuple[str, str]]:
        matching_field_pairs = [
            ('otm_call_risk', 'otm_put_risk'),
            ('trail_otm_call_risk', 'trail_otm_put_risk'),
        ]
        return matching_field_pairs

    @classmethod
    def get_name(cls):
        return 'strangle_daily'

class StrangleWeeklyConfig(BaseConfig):
    name: str
    long_or_short: Literal['long', 'short']  # Either 'long' or 'short'
    entry_time: time
    exit_time: time
    lot_size: conint(gt=0)  # Integer >0
    body_width: conint(gt=0, multiple_of=50)  # Integer >0 and multiple of 50
    otm_call_risk: confloat(gt=0)  # Float >0
    trail_otm_call_risk: bool
    otm_put_risk: confloat(gt=0)  # Float >0
    trail_otm_put_risk: bool

    # These will be set in model_validator
    otm_call_order_type: str = None
    otm_put_order_type: str = None

    @field_validator('entry_time', 'exit_time', mode='before')
    def parse_time(cls, v):
        return datetime.strptime(v, '%H:%M:%S').time()

    @model_validator(mode='after')
    def make_order_types(self):
        self.otm_call_order_type = 'market_stoploss_trail' if self.trail_otm_call_risk else 'market_stoploss'
        self.otm_put_order_type = 'market_stoploss_trail' if self.trail_otm_put_risk else 'market_stoploss'
        return self

    @classmethod
    def get_field_choices_for_simulation(self):
        return {
            'otm_call_risk': list(range(1500, 18001, 250)),
            'otm_put_risk': list(range(1500, 18001, 250)),
            'trail_otm_call_risk': [True, False],
            'trail_otm_put_risk': [True, False],
            'body_width': [50, 100, 150, 200, 250],
            'entry_time': ['9:15:00', '9:20:00'],
        }

    @classmethod
    def get_field_pairs_that_should_be_same_during_simulation(cls) -> list[tuple[str, str]]:
        matching_field_pairs = [
            ('otm_call_risk', 'otm_put_risk'),
            ('trail_otm_call_risk', 'trail_otm_put_risk'),
        ]
        return matching_field_pairs

    @classmethod
    def get_name(cls):
        return 'strangle_weekly'

class IronCondorDailyConfig(BaseConfig):
    name: str
    long_or_short: Literal['long', 'short']  # Either 'long' or 'short'
    entry_time: time
    exit_time: time
    lot_size: conint(gt=0)  # Integer >0
    body_width: conint(gt=0, multiple_of=50)  # Integer >0 and multiple of 50
    wing_width: conint(gt=0, multiple_of=50)  # Integer >0 and multiple of 50
    call_credit_spread_risk: confloat(gt=0)  # Float >0
    trail_call_credit_spread_risk: bool
    put_credit_spread_risk: confloat(gt=0)  # Float >0
    trail_put_credit_spread_risk: bool

    # These will be set in model_validator
    outer_put_order_type: str = None
    inner_put_order_type: str = None
    inner_call_order_type: str = None
    outer_call_order_type: str = None

    @field_validator('entry_time', 'exit_time', mode='before')
    def parse_time(cls, v):
        return datetime.strptime(v, '%H:%M:%S').time()

    @model_validator(mode='after')
    def make_order_types(self):
        self.outer_put_order_type = 'market_stoploss_trail' if self.trail_put_credit_spread_risk else 'market_stoploss'
        self.inner_put_order_type = 'market_stoploss_trail' if self.trail_put_credit_spread_risk else 'market_stoploss'
        self.inner_call_order_type = 'market_stoploss_trail' if self.trail_call_credit_spread_risk else 'market_stoploss'
        self.outer_call_order_type = 'market_stoploss_trail' if self.trail_call_credit_spread_risk else 'market_stoploss'
        return self

    @classmethod
    def get_field_choices_for_simulation(self):
        return {
            'call_credit_spread_risk': list(range(500, 8001, 250)),
            'trail_call_credit_spread_risk': [True, False],
            'put_credit_spread_risk': list(range(500, 8001, 250)),
            'trail_put_credit_spread_risk': [True, False],
            'body_width': [50, 100, 150, 200, 250],
            'wing_width': [50, 100, 150, 200, 250],
            'entry_time': ['9:15:00', '9:20:00', '09:30:00'],
        }

    @classmethod
    def get_field_pairs_that_should_be_same_during_simulation(cls) -> list[tuple[str, str]]:
        matching_field_pairs = [
            ('call_credit_spread_risk', 'put_credit_spread_risk'),
            ('trail_call_credit_spread_risk', 'trail_put_credit_spread_risk'),
        ]
        return matching_field_pairs

    @classmethod
    def get_name(cls):
        return 'ironcondor_daily'

class IronCondorWeeklyConfig(BaseConfig):
    name: str
    long_or_short: Literal['long', 'short']  # Either 'long' or 'short'
    entry_time: time
    exit_time: time
    lot_size: conint(gt=0)  # Integer >0
    body_width: conint(gt=0, multiple_of=50)  # Integer >0 and multiple of 50
    wing_width: conint(gt=0, multiple_of=50)  # Integer >0 and multiple of 50
    call_credit_spread_risk: confloat(gt=0)  # Float >0
    trail_call_credit_spread_risk: bool
    put_credit_spread_risk: confloat(gt=0)  # Float >0
    trail_put_credit_spread_risk: bool

    # These will be set in model_validator
    outer_put_order_type: str = None
    inner_put_order_type: str = None
    inner_call_order_type: str = None
    outer_call_order_type: str = None

    @field_validator('entry_time', 'exit_time', mode='before')
    def parse_time(cls, v):
        return datetime.strptime(v, '%H:%M:%S').time()

    @model_validator(mode='after')
    def make_order_types(self):
        self.outer_put_order_type = 'market_stoploss_trail' if self.trail_put_credit_spread_risk else 'market_stoploss'
        self.inner_put_order_type = 'market_stoploss_trail' if self.trail_put_credit_spread_risk else 'market_stoploss'
        self.inner_call_order_type = 'market_stoploss_trail' if self.trail_call_credit_spread_risk else 'market_stoploss'
        self.outer_call_order_type = 'market_stoploss_trail' if self.trail_call_credit_spread_risk else 'market_stoploss'
        return self

    @classmethod
    def get_field_choices_for_simulation(self):
        return {
            'call_credit_spread_risk': list(range(500, 8001, 250)),
            'trail_call_credit_spread_risk': [True, False],
            'put_credit_spread_risk': list(range(500, 8001, 250)),
            'trail_put_credit_spread_risk': [True, False],
            'body_width': [50, 100, 150, 200, 250],
            'wing_width': [50, 100, 150, 200, 250],
            'entry_time': ['9:15:00', '9:20:00', '09:30:00'],
        }

    @classmethod
    def get_field_pairs_that_should_be_same_during_simulation(cls) -> list[tuple[str, str]]:
        matching_field_pairs = [
            ('call_credit_spread_risk', 'put_credit_spread_risk'),
            ('trail_call_credit_spread_risk', 'trail_put_credit_spread_risk'),
        ]
        return matching_field_pairs

    @classmethod
    def get_name(cls):
        return 'ironcondor_weekly'

class IronButterflyDailyConfig(BaseConfig):
    name: str
    long_or_short: Literal['long', 'short']  # Either 'long' or 'short'
    entry_time: time
    exit_time: time
    lot_size: conint(gt=0)  # Integer >0
    wing_width: conint(gt=0, multiple_of=50)  # Integer >0 and multiple of 50
    call_credit_spread_risk: confloat(gt=0)  # Float >0
    trail_call_credit_spread_risk: bool
    put_credit_spread_risk: confloat(gt=0)  # Float >0
    trail_put_credit_spread_risk: bool

    # These will be set in model_validator
    outer_put_order_type: str = None
    inner_put_order_type: str = None
    inner_call_order_type: str = None
    outer_call_order_type: str = None

    @field_validator('entry_time', 'exit_time', mode='before')
    def parse_time(cls, v):
        return datetime.strptime(v, '%H:%M:%S').time()

    @model_validator(mode='after')
    def make_order_types(self):
        self.outer_put_order_type = 'market_stoploss_trail' if self.trail_put_credit_spread_risk else 'market_stoploss'
        self.inner_put_order_type = 'market_stoploss_trail' if self.trail_put_credit_spread_risk else 'market_stoploss'
        self.inner_call_order_type = 'market_stoploss_trail' if self.trail_call_credit_spread_risk else 'market_stoploss'
        self.outer_call_order_type = 'market_stoploss_trail' if self.trail_call_credit_spread_risk else 'market_stoploss'
        return self

    @classmethod
    def get_field_choices_for_simulation(self):
        return {
            'call_credit_spread_risk': list(range(250, 10001, 250)),
            'trail_call_credit_spread_risk': [True, False],
            'put_credit_spread_risk': list(range(250, 10001, 100)),
            'trail_put_credit_spread_risk': [True, False],
            'wing_width': [50, 100, 150, 200, 250],
            'entry_time': ['9:15:00', '9:20:00', '09:30:00'],
        }

    @classmethod
    def get_field_pairs_that_should_be_same_during_simulation(cls) -> list[tuple[str, str]]:
        matching_field_pairs = [
            ('call_credit_spread_risk', 'put_credit_spread_risk'),
            ('trail_call_credit_spread_risk', 'trail_put_credit_spread_risk'),
        ]
        return matching_field_pairs

    @classmethod
    def get_name(cls):
        return 'ironbutterfly_daily'

class ButterflyDailyConfig(BaseConfig):
    name: str
    butterfly_option_type: Literal['CE', 'PE']  # Either 'CE' or 'PE'
    long_or_short: Literal['long', 'short']  # Either 'long' or 'short'
    entry_time: time
    exit_time: time
    lot_size: conint(gt=0)  # Integer >0
    wing_width: conint(gt=0, multiple_of=50)  # Integer >0 and multiple of 50
    credit_spread_risk: confloat(gt=0)  # Float >0
    trail_credit_spread_risk: bool
    debit_spread_risk: confloat(gt=0)  # Float >0
    trail_debit_spread_risk: bool

    @field_validator('entry_time', 'exit_time', mode='before')
    def parse_time(cls, v):
        return datetime.strptime(v, '%H:%M:%S').time()

    @classmethod
    def get_field_choices_for_simulation(self):
        return {
            'butterfly_option_type': ['CE', 'PE'],
            'credit_spread_risk': list(range(250, 10001, 250)),
            'trail_credit_spread_risk': [True, False],
            'debit_spread_risk': list(range(250, 10001, 100)),
            'trail_debit_spread_risk': [True, False],
            'wing_width': [50, 100, 150, 200, 250],
            'entry_time': ['9:15:00', '9:20:00', '09:30:00'],
        }

    @classmethod
    def get_field_pairs_that_should_be_same_during_simulation(cls) -> list[tuple[str, str]]:
        matching_field_pairs = [
            ('credit_spread_risk', 'debit_spread_risk'),
            ('trail_credit_spread_risk', 'trail_debit_spread_risk'),
        ]
        return matching_field_pairs

    @classmethod
    def get_name(cls):
        return 'butterfly_daily'

###############################################################
###############################################################

STRATEGY_NAME_TO_STRATEGY_CONFIG_MAP = {
    'straddle': StraddleConfig,
    'straddle_daily': StraddleDailyConfig,
    'strangle_daily': StrangleDailyConfig,
    'straddle_weekly': StraddleWeeklyConfig,
    'strangle_weekly': StrangleWeeklyConfig,
    'ironcondor_daily': IronCondorDailyConfig,
    'ironcondor_weekly': IronCondorWeeklyConfig,
    'ironbutterfly_daily': IronButterflyDailyConfig,
    'butterfly_daily': ButterflyDailyConfig,
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

class HedgedBacktesterConfig(BaseConfig):
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
        return 'hedged_backtester'

BACKTESTER_NAME_TO_BACKTESTER_CONFIG_MAP = {
    'base_backtester': BaseBacktesterConfig,
    'hedged_backtester': HedgedBacktesterConfig,
}
