from typing import Union
from strategy import Strategy, Action
from connectors.dbconnector import DBConnector
import pandas as pd
import copy
from rich import print


class Straddle(Strategy):
    def __init__(self, config, dbconnector: DBConnector):
        super().__init__(config, dbconnector)

        assert self.config.long_or_short in ['long', 'short'], f"Position must be either 'long' or 'short'. Given {self.config.long_or_short}"
        assert self.config.call_risk > 0, f'call_risk must be positive. Given {self.config.call_risk}'
        assert self.config.put_risk > 0, f'put_risk must be positive. Given {self.config.put_risk}'

        # Straddle Params
        self.name = self.__class__.__name__
        self.strike = None  # Will be set at the time of action

    def action(self, timestamp: pd.Timestamp) -> list[Action] | None:
        actions = None
        if timestamp.time() == self.config.entry_time:
            self.strike = self.dbconnector.get_ATM_strike(timestamp)
            closest_expiry = self.dbconnector.get_closest_expiry(timestamp)
            atm_call_action = Action(
                option_type='CE', strike=self.strike, expiry=closest_expiry, num_lots=1, trade_type=self.config.long_or_short, order_type=self.config.call_order_type, stoploss=self.config.call_risk
            )
            atm_put_action = Action(
                option_type='PE', strike=self.strike, expiry=closest_expiry, num_lots=1, trade_type=self.config.long_or_short, order_type=self.config.put_order_type, stoploss=self.config.put_risk
            )
            actions = [atm_call_action, atm_put_action]

        elif timestamp.time() == self.config.exit_time:
            actions = self.square_off_actions()

        return actions

    def about(self) -> str:
        if self.config.long_or_short == 'short':
            about_str = f'Name : {self.name} : /\ \n'
        elif self.config.long_or_short == 'long':
            about_str = f'Name : {self.name} : \/ \n'

        if self.config.long_or_short == 'short':
            desc = 'Neutral strategy. Profits from low volatility. Profits when the market is range-bound. TimeDecay on our side. Risk : unlimited'
        elif self.config.long_or_short == 'long':
            desc = 'Needs large price movements (in any side) to be profitable. Profits from high volatility. TimeDecay against us. Risk : limited'
        about_str += f'Description : {desc}\n'

        about_str += f'Our Net Position : {self.config.long_or_short.upper()}\n'
        about_str += f'ATM CALL Params: '
        about_str += f'RISK : ₹ {self.config.call_risk}, TRAIL_RISK : {self.config.trail_call_risk} |\n'
        about_str += f'ATM PUT  Params: '
        about_str += f'RISK : ₹ {self.config.put_risk}, TRAIL_RISK : {self.config.trail_put_risk} |\n'

        about_str += f'For each day, If market is open\n'
        about_str += f'     Enter an Straddle of (nearest) ATM at {self.config.entry_time.strftime("%H:%M:%S")} at close of underlying\n'
        if self.config.long_or_short == 'short':
            opposite_pos = 'LONG'
        elif self.config.long_or_short == 'long':
            opposite_pos = 'SHORT'
        about_str += f'     Net position: \n'
        about_str += f'        {self.config.long_or_short.upper()} : [ATM Call and ATM Put] of strike according to close at {self.config.entry_time.strftime("%H:%M:%S")} (X2)\n'
        about_str += f'     1. EXIT : If time is {self.config.exit_time.strftime("%H:%M:%S")} is reached\n'

        about_str += f'     2. EXIT call_leg : \n'
        about_str += f'             StopLoss condition : If call_leg_loss >= {self.config.call_risk} {"(trailing)" if self.config.trail_call_risk else "(fixed)"}\n'

        about_str += f'     3. EXIT put_leg : \n'
        about_str += f'             StopLoss condition : If put_leg_loss >= {self.config.put_risk} {"(trailing)" if self.config.trail_put_risk else "(fixed)"}\n'

        return about_str
