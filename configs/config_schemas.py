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
            'call_risk': list(range(1500, 7501, 250)),
            'put_risk': list(range(1500, 7501, 250)),
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
            'call_risk': list(range(1500, 7501, 250)),
            'put_risk': list(range(1500, 7501, 250)),
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
            'otm_call_risk': list(range(1500, 7501, 250)),
            'otm_put_risk': list(range(1500, 7501, 250)),
            'trail_call_risk': [True, False],
            'trail_put_risk': [True, False],
            'entry_time': ['9:15:00', '9:20:00', '09:30:00'],
            'spread_width': [50, 100, 150, 200],
        }

    @classmethod
    def get_field_pairs_that_should_be_same_during_simulation(cls) -> list[tuple[str, str]]:
        matching_field_pairs = [
            ('otm_call_risk', 'otm_put_risk'),
            ('trail_call_risk', 'trail_put_risk'),
        ]
        return matching_field_pairs

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
            'otm_put_risk': list(range(2250, 7501, 750)),
            'trail_otm_put_risk': [True, False],
            'atm_put_risk': list(range(2250, 7501, 750)),
            'trail_atm_put_risk': [True, False],
            'atm_call_risk': list(range(2250, 7501, 750)),
            'trail_atm_call_risk': [True, False],
            'otm_call_risk': list(range(2250, 7501, 750)),
            'trail_otm_call_risk': [True, False],
            'wing_width': [50, 100, 150],
            'entry_time': ['9:15:00', '9:20:00', '09:30:00'],
        }

    @classmethod
    def get_field_pairs_that_should_be_same_during_simulation(cls) -> list[tuple[str, str]]:
        matching_field_pairs = [
            ('otm_put_risk', 'otm_call_risk'),
            ('trail_otm_put_risk', 'trail_otm_call_risk'),
            ('atm_put_risk', 'atm_call_risk'),
            ('trail_atm_put_risk', 'trail_atm_call_risk'),
        ]
        return matching_field_pairs

    @classmethod
    def get_name(cls):
        return 'ironbutterfly'


class IronButterflyHedgedConfig(BaseConfig):

    # Overall strategy configs
    name: str
    long_or_short: Literal['long', 'short']  # Either 'long' or 'short'
    entry_time: time
    exit_time: time
    lot_size: conint(gt=0)  # Integer >0
    wing_width: conint(gt=0, multiple_of=50)  # Constrained Integer > 0 and multiple of 50
    margin_required: confloat(gt=0)  # Float >0

    # Leg configs
    bull_put_spread_risk: confloat(ge=0)  # Float >=0
    trail_bull_put_spread_risk: bool
    bear_call_spread_risk: confloat(ge=0)  # Float >=0
    trail_bear_call_spread_risk: bool

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
        self.otm_put_order_type = 'market_stoploss_trail' if self.trail_bull_put_spread_risk else 'market_stoploss'
        self.atm_put_order_type = 'market_stoploss_trail' if self.trail_bull_put_spread_risk else 'market_stoploss'
        self.atm_call_order_type = 'market_stoploss_trail' if self.trail_bear_call_spread_risk else 'market_stoploss'
        self.otm_call_order_type = 'market_stoploss_trail' if self.trail_bear_call_spread_risk else 'market_stoploss'
        return self

    @classmethod
    def get_field_choices_for_simulation(self):
        return {
            'bull_put_spread_risk': list(range(750, 9001, 750)),
            'trail_bull_put_spread_risk': [True, False],
            'bear_call_spread_risk': list(range(750, 9001, 750)),
            'trail_bear_call_spread_risk': [True, False],
            'wing_width': [50, 100, 150],
            'entry_time': ['9:15:00', '9:20:00', '09:30:00'],
        }

    @classmethod
    def get_field_pairs_that_should_be_same_during_simulation(cls) -> list[tuple[str, str]]:
        matching_field_pairs = [
            ('bull_put_spread_risk', 'bear_call_spread_risk'),
            ('trail_bull_put_spread_risk', 'trail_bear_call_spread_risk'),
        ]
        return matching_field_pairs

    @classmethod
    def get_name(cls):
        return 'ironbutterfly_hedged'


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
    outer_otm_put_risk: confloat(ge=0)  # Float >=0
    trail_outer_otm_put_risk: bool
    inner_otm_put_risk: confloat(ge=0)  # Float >=0
    trail_inner_otm_put_risk: bool
    inner_otm_call_risk: confloat(ge=0)  # Float >=0
    trail_inner_otm_call_risk: bool
    outer_otm_call_risk: confloat(ge=0)  # Float >=0
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
            'outer_otm_put_risk': list(range(2250, 7501, 750)),
            'trail_outer_otm_put_risk': [True, False],
            'inner_otm_put_risk': list(range(2250, 7501, 750)),
            'trail_inner_otm_put_risk': [True, False],
            'inner_otm_call_risk': list(range(2250, 7501, 750)),
            'trail_inner_otm_call_risk': [True, False],
            'outer_otm_call_risk': list(range(2250, 7501, 750)),
            'trail_outer_otm_call_risk': [True, False],
            'body_width': [50, 100, 150],
            'wing_width': [50, 100, 150],
            'entry_time': ['9:15:00', '9:20:00', '09:30:00'],
        }

    @classmethod
    def get_field_pairs_that_should_be_same_during_simulation(cls) -> list[tuple[str, str]]:
        matching_field_pairs = [
            ('outer_otm_put_risk', 'outer_otm_call_risk'),
            ('trail_outer_otm_put_risk', 'trail_outer_otm_call_risk'),
            ('inner_otm_put_risk', 'inner_otm_call_risk'),
            ('trail_inner_otm_put_risk', 'trail_inner_otm_call_risk'),
        ]
        return matching_field_pairs

    @classmethod
    def get_name(cls):
        return 'ironcondor'


class ButterflyConfig(BaseConfig):
    # Overall strategy configs
    name: str
    long_or_short: Literal['long', 'short']  # Either 'long' or 'short'
    entry_time: time
    exit_time: time
    lot_size: conint(gt=0)  # Integer >0
    wing_width: conint(gt=0, multiple_of=50)  # Constrained Integer > 0 and multiple of 50
    butterfly_option_type: Literal['CE', 'PE']  # Either 'CE' or 'PE'

    # Leg configs
    atm_risk: confloat(ge=0)  # Float >=0
    trail_atm_risk: bool
    otm_risk: confloat(ge=0)  # Float >=0
    trail_otm_risk: bool
    itm_risk: confloat(ge=0)  # Float >=0
    trail_itm_risk: bool

    # These will be set in model_validator
    atm_order_type: str = None
    otm_order_type: str = None
    itm_order_type: str = None

    # --- Field Validators ---
    @field_validator('entry_time', 'exit_time', mode='before')
    def parse_time(cls, v):
        if isinstance(v, str):
            return datetime.strptime(v, '%H:%M:%S').time()
        return v

    # --- Model Validator ---
    @model_validator(mode='after')
    def make_order_types(self):
        self.atm_order_type = 'market_stoploss_trail' if self.trail_atm_risk else 'market_stoploss'
        self.otm_order_type = 'market_stoploss_trail' if self.trail_otm_risk else 'market_stoploss'
        self.itm_order_type = 'market_stoploss_trail' if self.trail_itm_risk else 'market_stoploss'
        return self

    @classmethod
    def get_field_choices_for_simulation(self):
        return {
            'atm_risk': list(range(2250, 7501, 750)),
            'trail_atm_risk': [True, False],
            'otm_risk': list(range(2250, 7501, 750)),
            'trail_otm_risk': [True, False],
            'itm_risk': list(range(2250, 7501, 750)),
            'trail_itm_risk': [True, False],
            'wing_width': [50, 100, 150],
            'butterfly_option_type': ['CE', 'PE'],
            'entry_time': ['9:15:00', '9:20:00', '09:30:00'],
        }

    @classmethod
    def get_field_pairs_that_should_be_same_during_simulation(cls) -> list[tuple[str, str]]:
        matching_field_pairs = [
            ('otm_risk', 'itm_risk'),
            ('trail_otm_risk', 'trail_itm_risk'),
        ]
        return matching_field_pairs

    @classmethod
    def get_name(cls):
        return 'butterfly'


class CondorConfig(BaseConfig):
    # Overall strategy configs
    name: str
    long_or_short: Literal['long', 'short']  # Either 'long' or 'short'
    entry_time: time
    exit_time: time
    lot_size: conint(gt=0)  # Integer >0
    body_width: conint(gt=0, multiple_of=50)  # Constrained Integer > 0 and multiple of 50
    wing_width: conint(gt=0, multiple_of=50)  # Constrained Integer > 0 and multiple of 50
    condor_option_type: Literal['CE', 'PE']  # Either 'CE' or 'PE'

    # Leg configs
    leftmost_leg_risk: confloat(ge=0)  # Float >=0
    trail_leftmost_leg_risk: bool
    left_leg_risk: confloat(ge=0)  # Float >=0
    trail_left_leg_risk: bool
    right_leg_risk: confloat(ge=0)  # Float >=0
    trail_right_leg_risk: bool
    rightmost_leg_risk: confloat(ge=0)  # Float >=0
    trail_rightmost_leg_risk: bool

    # These will be set in model_validator
    leftmost_leg_order_type: str = None
    left_leg_order_type: str = None
    right_leg_order_type: str = None
    rightmost_leg_order_type: str = None

    # --- Field Validators ---
    @field_validator('entry_time', 'exit_time', mode='before')
    def parse_time(cls, v):
        if isinstance(v, str):
            return datetime.strptime(v, '%H:%M:%S').time()
        return v

    # --- Model Validator ---
    @model_validator(mode='after')
    def make_order_types(self):
        self.leftmost_leg_order_type = 'market_stoploss_trail' if self.trail_leftmost_leg_risk else 'market_stoploss'
        self.left_leg_order_type = 'market_stoploss_trail' if self.trail_left_leg_risk else 'market_stoploss'
        self.right_leg_order_type = 'market_stoploss_trail' if self.trail_right_leg_risk else 'market_stoploss'
        self.rightmost_leg_order_type = 'market_stoploss_trail' if self.trail_rightmost_leg_risk else 'market_stoploss'
        return self

    @classmethod
    def get_field_choices_for_simulation(self):
        return {
            'leftmost_leg_risk': list(range(2250, 7501, 750)),
            'trail_leftmost_leg_risk': [True, False],
            'left_leg_risk': list(range(2250, 7501, 750)),
            'trail_left_leg_risk': [True, False],
            'right_leg_risk': list(range(2250, 7501, 750)),
            'trail_right_leg_risk': [True, False],
            'rightmost_leg_risk': list(range(2250, 7501, 750)),
            'trail_rightmost_leg_risk': [True, False],
            'body_width': [50, 100, 150],
            'wing_width': [50, 100, 150],
            'condor_option_type': ['CE', 'PE'],
            'entry_time': ['9:15:00', '9:20:00', '09:30:00'],
        }

    @classmethod
    def get_field_pairs_that_should_be_same_during_simulation(cls) -> list[tuple[str, str]]:
        matching_field_pairs = [
            ('leftmost_leg_risk', 'rightmost_leg_risk'),
            ('trail_leftmost_leg_risk', 'trail_rightmost_leg_risk'),
            ('left_leg_risk', 'right_leg_risk'),
            ('trail_left_leg_risk', 'trail_right_leg_risk'),
        ]
        return matching_field_pairs

    @classmethod
    def get_name(cls):
        return 'condor'


STRATEGY_NAME_TO_STRATEGY_CONFIG_MAP = {
    'straddle': StraddleConfig,
    'weekly_straddle': WeeklyStraddleConfig,
    'strangle': StrangleConfig,
    'butterfly': ButterflyConfig,
    'ironbutterfly': IronButterflyConfig,
    'condor': CondorConfig,
    'ironcondor': IronCondorConfig,
    'ironbutterfly_hedged': IronButterflyHedgedConfig,
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
    trail_total_position_risk: bool

    @field_validator('start_date', 'end_date', mode='before')
    def parse_dates(cls, v):
        return pd.Timestamp(v).date()

    @classmethod
    def get_field_choices_for_simulation(self):
        return {
            'total_position_risk': list(range(1000, 20001, 1000)),
            'trail_total_position_risk': [True, False],
        }

    @classmethod
    def get_name(cls):
        return 'positional_backtester'

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
        return 'positional_backtester'




BACKTESTER_NAME_TO_BACKTESTER_CONFIG_MAP = {
    'base_backtester': BaseBacktesterConfig,
    'positional_backtester': PositionalBacktesterConfig,
    'hedged_backtester': HedgedBacktesterConfig,
}
