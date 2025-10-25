from strategy import Strategy, Action
from connectors.dbconnector import DBConnector
import pandas as pd


class StraddleWeekly(Strategy):
    def __init__(self, config, dbconnector: DBConnector):
        super().__init__(config, dbconnector)
        self.name = self.__class__.__name__
        self.entry_ts_to_exit_ts_map = self.generate_entry_date_to_exit_date_map()
        self.latest_entry_timestamp = None

    def action(self, timestamp: pd.Timestamp) -> list[Action] | None:
        actions = None
        if timestamp in self.entry_ts_to_exit_ts_map:
            atm_strike = self.dbconnector.get_ATM_strike(timestamp)
            closest_expiry = self.entry_ts_to_exit_ts_map[timestamp].date().strftime('%Y-%m-%d')

            atm_call_action = Action(
                option_type='CE',
                strike=atm_strike,
                expiry=closest_expiry,
                num_lots=1,
                trade_type=self.config.long_or_short,
                order_type=self.config.call_order_type,
                stoploss=self.config.call_risk,
            )
            atm_put_action = Action(
                option_type='PE',
                strike=atm_strike,
                expiry=closest_expiry,
                num_lots=1,
                trade_type=self.config.long_or_short,
                order_type=self.config.put_order_type,
                stoploss=self.config.put_risk,
            )

            actions = [atm_call_action, atm_put_action]
            self.latest_entry_timestamp = timestamp

        elif timestamp in self.entry_ts_to_exit_ts_map.values():
            actions = self.square_off_actions()

        return actions

    def about(self) -> str:
        opposite_pos = 'short' if self.config.long_or_short == 'long' else 'long'
        if self.config.long_or_short == 'short':
            about_str = f'Name : {self.name} : /\\ \n'
        elif self.config.long_or_short == 'long':
            about_str = f'Name : {self.name} : \\/ \n'

        if self.config.long_or_short == 'short':
            desc = 'Neutral strategy. Profits from low volatility. Profits when the market is range-bound. TimeDecay on our side. Risk : unlimited'
        elif self.config.long_or_short == 'long':
            desc = 'Needs large price movements (in any side) to be profitable. Profits from high volatility. TimeDecay against us. Risk : limited'

        about_str += f'\nDescription : {desc}\n'
        about_str += f'Name : {self.name}\n'
        about_str += f'Net Position : {self.config.long_or_short.upper()}\n\n'

        about_str += 'POSITION DETAILS:\n'
        about_str += f'     | {"LEG":<10} | {"POSITION":<10} | {"STOPLOSS":<10} | {"TRAIL STOPLOSS":<15} |\n'
        about_str += f'     | {"ATM CALL":<10} | {self.config.long_or_short:<10} | {self.config.call_risk:<10} | {self.config.trail_call_risk:<15} |\n'
        about_str += f'     | {"ATM PUT":<10} | {self.config.long_or_short:<10} | {self.config.put_risk:<10} | {self.config.trail_put_risk:<15} |\n\n'

        about_str += f'Enter a Straddle right [ NEXT DAY OF EXPIRY ] of (nearest) ATM at {self.config.entry_time.strftime("%H:%M:%S")} at close of underlying.\n'
        about_str += f"Exit all positions at the entry week's [ EXPIRY DATE ] at {self.config.exit_time.strftime('%H:%M:%S')} , if stoploss not hit.\n\n"

        about_str += 'EXIT RULES:\n'
        about_str += f'     1. EXIT : If time is {self.config.exit_time.strftime("%H:%M:%S")} on [ EXPIRY DAY ].\n'
        about_str += f'     2. EXIT CALL leg : StopLoss hit → {self.config.call_risk} {"(trailing)" if self.config.trail_call_risk else "(fixed)"}.\n'
        about_str += f'     3. EXIT PUT leg  : StopLoss hit → {self.config.put_risk} {"(trailing)" if self.config.trail_put_risk else "(fixed)"}.\n'

        return about_str
