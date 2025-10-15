from strategy import Strategy, Action
from connectors.dbconnector import DBConnector
import pandas as pd
from utils.option_utils import get_lower_upper_strikes_around_spot

class IronCondor(Strategy):
    def __init__(self, config, dbconnector: DBConnector):
        super().__init__(config, dbconnector)
        self.name = self.__class__.__name__

    def action(self, timestamp: pd.Timestamp) -> list[Action] | None:
        actions = None
        if timestamp.time() == self.config.entry_time:
            spot = self.dbconnector.df_spot.loc[timestamp, 'close']
            closest_expiry = self.dbconnector.get_closest_expiry(timestamp)
            inner_otm_put_strike, inner_otm_call_strike = get_lower_upper_strikes_around_spot(spot=spot, strike_interval=50, width=self.config.body_width)
            outer_otm_put_strike = inner_otm_put_strike - self.config.wing_width
            outer_otm_call_strike = inner_otm_call_strike + self.config.wing_width

            outer_otm_put_action = Action(
                option_type='PE',
                strike=outer_otm_put_strike,
                expiry=closest_expiry,
                num_lots=1,
                trade_type='long' if self.config.long_or_short == 'short' else 'short',
                order_type=self.config.outer_otm_put_order_type,
                stoploss=self.config.outer_otm_put_risk,
            )

            inner_otm_put_action = Action(
                option_type='PE',
                strike=inner_otm_put_strike,
                expiry=closest_expiry,
                num_lots=1,
                trade_type=self.config.long_or_short,
                order_type=self.config.inner_otm_put_order_type,
                stoploss=self.config.inner_otm_put_risk,
            )

            inner_otm_call_action = Action(
                option_type='CE',
                strike=inner_otm_call_strike,
                expiry=closest_expiry,
                num_lots=1,
                trade_type=self.config.long_or_short,
                order_type=self.config.inner_otm_call_order_type,
                stoploss=self.config.inner_otm_call_risk,
            )

            outer_otm_call_action = Action(
                option_type='CE',
                strike=outer_otm_call_strike,
                expiry=closest_expiry,
                num_lots=1,
                trade_type='long' if self.config.long_or_short == 'short' else 'short',
                order_type=self.config.outer_otm_call_order_type,
                stoploss=self.config.outer_otm_call_risk,
            )

            actions = [outer_otm_put_action, inner_otm_put_action, inner_otm_call_action, outer_otm_call_action]

        elif timestamp.time() == self.config.exit_time:
            actions = self.square_off_actions()

        return actions

    def about(self) -> str:
        opposite_pos = 'short' if self.config.long_or_short == 'long' else 'long'

        if self.config.long_or_short == 'short':
            about_str = f'Name : {self.name} : __/‾‾\__ \n'
        elif self.config.long_or_short == 'long':
            about_str = f'Name : {self.name} : ‾‾\__/‾‾ \n'

        if self.config.long_or_short == 'short':
            desc = 'Neutral strategy. Profits from low volatility. Profits when the market is range-bound. TimeDecay on our side. Profit : limited, Risk : limited'
        elif self.config.long_or_short == 'long':
            desc = 'Needs large price movements (in any side) to be profitable. Profits from high volatility. TimeDecay against us. Profit : limited, Risk : limited'

        about_str += f'\nDescription : {desc}\n'
        about_str += f'Body Width = [Inner OTM Call Strike - Inner OTM Put Strike] = {self.config.body_width}\n'
        about_str += f'Wing Width = [Inner OTM Put Strike - Outer OTM Put Strike] = [Outer OTM Call Strike - Inner OTM Call Strike] = {self.config.wing_width}\n'

        about_str += f'\nEnter an Iron Condor each day of (nearest) ATM at {self.config.entry_time.strftime("%H:%M:%S")} at close of underlying.\n'
        about_str += 'POSITIONS TABLE: \n'
        about_str += f'     | {"NAME":<15} | {"POSITION":<8} | {"STOPLOSS":<8} | {"TRAIL STOPLOSS":<15} | {"ORDER_TYPE":<30} | {"STRIKE":<28} |\n'
        about_str += f'     | {"Outer OTM Put":<15} | {opposite_pos:<8} | {self.config.outer_otm_put_risk:<8} | {self.config.trail_outer_otm_put_risk:<15} | {self.config.outer_otm_put_order_type:<30} | {"Inner OTM Put Strike - " + str(self.config.wing_width):<28} |\n'
        about_str += f'     | {"Inner OTM Put":<15} | {self.config.long_or_short:<8} | {self.config.inner_otm_put_risk:<8} | {self.config.trail_inner_otm_put_risk:<15} | {self.config.inner_otm_put_order_type:<30} | {"Inner OTM Put Strike":<28} |\n'
        about_str += f'     | {"Inner OTM Call":<15} | {self.config.long_or_short:<8} | {self.config.inner_otm_call_risk:<8} | {self.config.trail_inner_otm_call_risk:<15} | {self.config.inner_otm_call_order_type:<30} | {"Inner OTM Call Strike":<28} |\n'
        about_str += f'     | {"Outer OTM Call":<15} | {opposite_pos:<8} | {self.config.outer_otm_call_risk:<8} | {self.config.trail_outer_otm_call_risk:<15} | {self.config.outer_otm_call_order_type:<30} | {"Inner OTM Call Strike + " + str(self.config.wing_width):<28} |\n\n'

        about_str += f'Exit all positions at {self.config.exit_time.strftime("%H:%M:%S")} , if stoploss not hit.\n'

        return about_str
