from strategy import Strategy, Action
from connectors.dbconnector import DBConnector
import pandas as pd
from utils.option_utils import get_lower_upper_strikes_around_spot


class IronCondorDaily(Strategy):
    def __init__(self, config, dbconnector: DBConnector):
        super().__init__(config, dbconnector)
        self.name = self.__class__.__name__

    def action(self, timestamp: pd.Timestamp) -> list[Action] | None:
        actions = None
        if timestamp.time() == self.config.entry_time:
            spot_price = self.dbconnector.df_spot.loc[timestamp, 'close']
            closest_expiry = self.dbconnector.get_closest_expiry(timestamp)
            inner_put_strike, inner_call_strike = get_lower_upper_strikes_around_spot(spot=spot_price, strike_interval=50, width=self.config.body_width)
            outer_put_strike = inner_put_strike - self.config.wing_width
            outer_call_strike = inner_call_strike + self.config.wing_width

            outer_put_action = Action(
                option_type='PE',
                strike=outer_put_strike,
                expiry=closest_expiry,
                num_lots=1,
                trade_type='long' if self.config.long_or_short == 'short' else 'short',
                order_type=self.config.outer_put_order_type,
                stoploss=self.config.put_credit_spread_risk,  # Risk set here but it will not be used as the stoploss levels will be calculated based on the spread together with the inner put leg
            )

            inner_put_action = Action(
                option_type='PE',
                strike=inner_put_strike,
                expiry=closest_expiry,
                num_lots=1,
                trade_type=self.config.long_or_short,
                order_type=self.config.inner_put_order_type,
                stoploss=self.config.put_credit_spread_risk,  # Risk set here but it will not be used as the stoploss levels will be calculated based on the spread together with the outer put leg
            )

            inner_call_action = Action(
                option_type='CE',
                strike=inner_call_strike,
                expiry=closest_expiry,
                num_lots=1,
                trade_type=self.config.long_or_short,
                order_type=self.config.inner_call_order_type,
                stoploss=self.config.call_credit_spread_risk,  # Risk set here but it will not be used as the stoploss levels will be calculated based on the spread together with the outer call leg
            )

            outer_call_action = Action(
                option_type='CE',
                strike=outer_call_strike,
                expiry=closest_expiry,
                num_lots=1,
                trade_type='long' if self.config.long_or_short == 'short' else 'short',
                order_type=self.config.outer_call_order_type,
                stoploss=self.config.call_credit_spread_risk,  # Risk set here but it will not be used as the stoploss levels will be calculated based on the spread together with the inner call leg
            )
            actions = [outer_put_action, inner_put_action, inner_call_action, outer_call_action]

        elif timestamp.time() == self.config.exit_time:
            actions = self.square_off_actions()
        return actions

    def about(self) -> str:
        opposite_pos = 'short' if self.config.long_or_short == 'long' else 'long'

        if self.config.long_or_short == 'short':
            about_str = f'Name : {self.name} : __/‾‾\\__ \n'
            desc = 'Neutral strategy. Profits from low volatility. Profits when the market stays range-bound. TimeDecay on our side. Risk : limited.'
        elif self.config.long_or_short == 'long':
            about_str = f'Name : {self.name} : ‾‾\\__/‾‾ \n'
            desc = 'Needs large price movements (in either direction) to be profitable. Profits from high volatility. TimeDecay against us. Risk : limited.'

        about_str += f'\nDescription : {desc}\n'
        about_str += f'Net Position : {self.config.long_or_short.upper()}\n\n'

        about_str += (
            f'Body Width Definition: INNER CALL STRIKE - INNER PUT STRIKE → {self.config.body_width} points.\n'
            f'Wing Width Definition: (Outer - Inner) distance for each side (Call/Put) → {self.config.wing_width} points.\n'
            f'The inner strikes (OTM CALL & OTM PUT) define the body, and the outer strikes define the wings.\n'
            f'The midpoint of the body is chosen as close to Spot as possible.\n\n'
        )

        about_str += 'POSITION DETAILS:\n'
        about_str += f'     | {"LEG":<25} | {"POSITION":<15} | {"STRIKE":<20} | {"STOPLOSS":<15} | {"TRAIL STOPLOSS":<15} |\n'
        about_str += f'     | {"Outer PUT (hedge)":<25} | {opposite_pos:<15} | {"Inner OTM PUT - " + str(self.config.wing_width):<20} | {self.config.put_credit_spread_risk:<15} | {str(self.config.trail_put_credit_spread_risk):<15} |\n'
        about_str += f'     | {"Inner PUT (credit leg)":<25} | {self.config.long_or_short:<15} | {"Inner OTM PUT":<20} | {self.config.put_credit_spread_risk:<15} | {str(self.config.trail_put_credit_spread_risk):<15} |\n'
        about_str += f'     | {"Inner CALL (credit leg)":<25} | {self.config.long_or_short:<15} | {"Inner OTM CALL":<20} | {self.config.call_credit_spread_risk:<15} | {str(self.config.trail_call_credit_spread_risk):<15} |\n'
        about_str += f'     | {"Outer CALL (hedge)":<25} | {opposite_pos:<15} | {"Inner OTM CALL + " + str(self.config.wing_width):<20} | {self.config.call_credit_spread_risk:<15} | {str(self.config.trail_call_credit_spread_risk):<15} |\n\n'

        about_str += (
            'NOTE:\n'
            '  • PUT Credit Spread and CALL Credit Spread are traded and trailed together.\n'
            '  • Both Call/Put Legs are exited at the same time when either of the spreads hit their respective stoploss levels.\n\n'
        )

        about_str += f'Enter an Iron Condor each day with nearest OTM options at {self.config.entry_time.strftime("%H:%M:%S")}.\n'
        about_str += f'Exit all positions at {self.config.exit_time.strftime("%H:%M:%S")} , if stoploss not hit.\n\n'

        about_str += 'EXIT RULES:\n'
        about_str += f'     1. EXIT : If time is {self.config.exit_time.strftime("%H:%M:%S")}.\n'
        about_str += f'     2. EXIT PUT spread  : StopLoss hit → {self.config.put_credit_spread_risk} {"(trailing)" if self.config.trail_put_credit_spread_risk else "(fixed)"}.\n'
        about_str += f'     3. EXIT CALL spread : StopLoss hit → {self.config.call_credit_spread_risk} {"(trailing)" if self.config.trail_call_credit_spread_risk else "(fixed)"}.\n'
        about_str += f'\nMargin Required per lot : {self.config.margin_required}\n'

        return about_str
