from strategy import Strategy, Action
from connectors.dbconnector import DBConnector
import pandas as pd
from utils.option_utils import get_lower_upper_strikes_around_spot


class StrangleDaily(Strategy):
    def __init__(self, config, dbconnector: DBConnector):
        super().__init__(config, dbconnector)
        self.name = self.__class__.__name__

    def action(self, timestamp: pd.Timestamp) -> list[Action] | None:
        actions = None
        if timestamp.time() == self.config.entry_time:
            spot_price = self.dbconnector.df_spot.loc[timestamp, 'close']
            closest_expiry = self.dbconnector.get_closest_expiry(timestamp)
            otm_put_strike, otm_call_strike = get_lower_upper_strikes_around_spot(spot=spot_price, strike_interval=50, width=self.config.body_width)
            otm_call_action = Action(
                option_type='CE',
                strike=otm_call_strike,
                expiry=closest_expiry,
                num_lots=1,
                trade_type=self.config.long_or_short,
                order_type=self.config.otm_call_order_type,
                stoploss=self.config.otm_call_risk,
            )
            otm_put_action = Action(
                option_type='PE',
                strike=otm_put_strike,
                expiry=closest_expiry,
                num_lots=1,
                trade_type=self.config.long_or_short,
                order_type=self.config.otm_put_order_type,
                stoploss=self.config.otm_put_risk,
            )
            actions = [otm_put_action, otm_call_action]

        elif timestamp.time() == self.config.exit_time:
            actions = self.square_off_actions()

        return actions

    def about(self) -> str:
        opposite_pos = 'short' if self.config.long_or_short == 'long' else 'long'

        if self.config.long_or_short == 'short':
            about_str = f'Name : {self.name} : /\\ \n'
            desc = 'Neutral strategy. Profits from low volatility. Profits when the market is range-bound. TimeDecay on our side. Risk : unlimited'
        elif self.config.long_or_short == 'long':
            about_str = f'Name : {self.name} : \\/ \n'
            desc = 'Needs large price movements (in any side) to be profitable. Profits from high volatility. TimeDecay against us. Risk : limited'

        about_str += f'\nDescription : {desc}\n'
        about_str += f'Net Position : {self.config.long_or_short.upper()}\n\n'

        about_str += f'Body Width Definition: OTM CALL STRIKE - OTM PUT STRIKE → {self.config.body_width} points.\n'
        about_str += f'The OTM Call Strike and OTM Put Strike are chosen such that the middle point [(OTM Call Strike + OTM Put Strike)/2] is as close to Spot as possible.\n\n'

        about_str += 'POSITION DETAILS:\n'
        about_str += f'     | {"LEG":<10} | {"POSITION":<10} | {"STOPLOSS":<10} | {"TRAIL STOPLOSS":<15} |\n'
        about_str += f'     | {"OTM CALL":<10} | {self.config.long_or_short:<10} | {self.config.otm_call_risk:<10} | {str(self.config.trail_otm_call_risk):<15} |\n'
        about_str += f'     | {"OTM PUT":<10} | {self.config.long_or_short:<10} | {self.config.otm_put_risk:<10} | {str(self.config.trail_otm_put_risk):<15} |\n\n'

        about_str += f'Enter a Strangle each day of nearest OTM options at {self.config.entry_time.strftime("%H:%M:%S")}.\n'
        about_str += f'Exit all positions at {self.config.exit_time.strftime("%H:%M:%S")} , if stoploss not hit.\n\n'

        about_str += 'EXIT RULES:\n'
        about_str += f'     1. EXIT : If time is {self.config.exit_time.strftime("%H:%M:%S")}.\n'
        about_str += f'     2. EXIT CALL leg : StopLoss hit → {self.config.otm_call_risk} {"(trailing)" if self.config.trail_otm_call_risk else "(fixed)"}.\n'
        about_str += f'     3. EXIT PUT leg  : StopLoss hit → {self.config.otm_put_risk} {"(trailing)" if self.config.trail_otm_put_risk else "(fixed)"}.\n'
        about_str += f'\nMargin Required per lot : {self.config.margin_required}\n'

        return about_str
