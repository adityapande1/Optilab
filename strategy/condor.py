from strategy import Strategy, Action
from connectors.dbconnector import DBConnector
import pandas as pd
from utils.option_utils import get_lower_upper_strikes_around_spot


class Condor(Strategy):
    def __init__(self, config, dbconnector: DBConnector):
        super().__init__(config, dbconnector)
        self.name = self.__class__.__name__

    def action(self, timestamp: pd.Timestamp) -> list[Action] | None:
        actions = None
        if timestamp.time() == self.config.entry_time:

            spot = self.dbconnector.df_spot.loc[timestamp, 'close']
            closest_expiry = self.dbconnector.get_closest_expiry(timestamp)
            left_leg_strike, right_leg_strike = get_lower_upper_strikes_around_spot(spot=spot, strike_interval=50, width=self.config.body_width)
            leftmost_leg_strike = left_leg_strike - self.config.wing_width
            rightmost_leg_strike = right_leg_strike + self.config.wing_width

            leftmost_leg_action = Action(
                option_type=self.config.condor_option_type,
                strike=leftmost_leg_strike,
                expiry=closest_expiry,
                num_lots=1,
                trade_type=self.config.long_or_short,
                order_type=self.config.leftmost_leg_order_type,
                stoploss=self.config.leftmost_leg_risk,
            )

            left_leg_action = Action(
                option_type=self.config.condor_option_type,
                strike=left_leg_strike,
                expiry=closest_expiry,
                num_lots=1,
                trade_type='short' if self.config.long_or_short == 'long' else 'long',
                order_type=self.config.left_leg_order_type,
                stoploss=self.config.left_leg_risk,
            )

            right_leg_action = Action(
                option_type=self.config.condor_option_type,
                strike=right_leg_strike,
                expiry=closest_expiry,
                num_lots=1,
                trade_type='short' if self.config.long_or_short == 'long' else 'long',
                order_type=self.config.right_leg_order_type,
                stoploss=self.config.right_leg_risk,
            )

            rightmost_leg_action = Action(
                option_type=self.config.condor_option_type,
                strike=rightmost_leg_strike,
                expiry=closest_expiry,
                num_lots=1,
                trade_type=self.config.long_or_short,
                order_type=self.config.rightmost_leg_order_type,
                stoploss=self.config.rightmost_leg_risk,
            )

            actions = [leftmost_leg_action, left_leg_action, right_leg_action, rightmost_leg_action]

        elif timestamp.time() == self.config.exit_time:
            actions = self.square_off_actions()

        return actions

    def about(self) -> str:

        opposite_pos = 'short' if self.config.long_or_short == 'long' else 'long'

        left_leg_strik = f'Left Leg Strike'
        right_leg_strike = f'Right Leg Strike'
        leftmost_leg = f'{left_leg_strik} - {self.config.wing_width}'
        rightmost_leg = f'{right_leg_strike} + {self.config.wing_width}'

        if self.config.long_or_short == 'long':
            about_str = f'Name : {self.name} : __/‾‾\__ \n'
            desc = (
                "Range-bound strategy. Profits if price stays near the middle strike (ATM). "
                "Profits from low volatility. TimeDecay on our side. "
                "Profit : limited, Risk : limited"
            )
        elif self.config.long_or_short == 'short':
            about_str = f'Name : {self.name} : ‾‾\__/‾‾ \n'
            desc = (
                "Expects a sharp move away from the middle strike. "
                "Profits from high volatility and large price moves. "
                "TimeDecay against us. "
                "Profit : limited, Risk : limited"
            )

        about_str += f'Description : {desc}\n'
        about_str += f'Body Width = | {right_leg_strike} - {left_leg_strik} | = {self.config.body_width}\n'
        about_str += f'Wing Width = | Left Leg Strike - Leftmost Leg Strike | = | Rightmost Leg Strike - Right Leg Strike | = {self.config.wing_width}\n'

        about_str += f'\nEnter a Condor each day of (nearest) ATM at {self.config.entry_time.strftime("%H:%M:%S")} at close of underlying.\n'
        about_str += 'POSITIONS TABLE: \n\n'

        about_str += f'     | {"NAME":<15} | {"TYPE":<6} | {"POSITION":<12} | {"STOPLOSS":<8} | {"TRAIL STOPLOSS":<15} | {"ORDER_TYPE":<30} | {"STRIKE":<25} |\n'
        about_str += f'     | {"-"*15} | {"-"*6} | {"-"*12} | {"-"*8} | {"-"*15} | {"-"*30} | {"-"*25} |\n'
        about_str += f'     | {"Leftmost Leg":<15} | {self.config.condor_option_type:<6} | {self.config.long_or_short:<12} | {self.config.leftmost_leg_risk:<8} | {str(self.config.trail_leftmost_leg_risk):<15} | {self.config.leftmost_leg_order_type:<30} | {leftmost_leg:<25} |\n'
        about_str += f'     | {"Left Leg":<15} | {self.config.condor_option_type:<6} | {opposite_pos:<12} | {self.config.left_leg_risk:<8} | {str(self.config.trail_left_leg_risk):<15} | {self.config.left_leg_order_type:<30} | {left_leg_strik:<25} |\n'
        about_str += f'     | {"Right Leg":<15} | {self.config.condor_option_type:<6} | {opposite_pos:<12} | {self.config.right_leg_risk:<8} | {str(self.config.trail_right_leg_risk):<15} | {self.config.right_leg_order_type:<30} | {right_leg_strike:<25} |\n'
        about_str += f'     | {"Rightmost Leg":<15} | {self.config.condor_option_type:<6} | {self.config.long_or_short:<12} | {self.config.rightmost_leg_risk:<8} | {str(self.config.trail_rightmost_leg_risk):<15} | {self.config.rightmost_leg_order_type:<30} | {rightmost_leg:<25} |\n\n'

        about_str += f'Exit all positions at {self.config.exit_time.strftime("%H:%M:%S")} , if stoploss not hit.\n'

        return about_str
