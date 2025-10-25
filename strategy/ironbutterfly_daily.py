from strategy import Strategy, Action
from connectors.dbconnector import DBConnector
import pandas as pd


class IronButterflyDaily(Strategy):
    def __init__(self, config, dbconnector: DBConnector):
        super().__init__(config, dbconnector)
        self.name = self.__class__.__name__

    def action(self, timestamp: pd.Timestamp) -> list[Action] | None:
        actions = None
        if timestamp.time() == self.config.entry_time:
            atm_strike = self.dbconnector.get_ATM_strike(timestamp)
            closest_expiry = self.dbconnector.get_closest_expiry(timestamp)
            inner_put_strike = atm_strike
            outer_put_strike = inner_put_strike - self.config.wing_width
            inner_call_strike = atm_strike
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
            about_str = f'Name : {self.name} : __/\\__ \n'
            desc = 'Neutral strategy centered at ATM. Profits from low volatility when price remains near strike center. TimeDecay works in our favor. Risk : limited. Reward : limited.'
        elif self.config.long_or_short == 'long':
            about_str = f'Name : {self.name} : ‾‾\\/‾‾ \n'
            desc = 'Directional volatility strategy. Profits from large price moves in either direction. TimeDecay works against us. Risk : limited. Reward : limited.'

        about_str += f'\nDescription : {desc}\n'
        about_str += f'Net Position : {self.config.long_or_short.upper()}\n\n'

        about_str += (
            f'Wing Width Definition: Distance between ATM strike and each outer strike → {self.config.wing_width} points.\n'
            f'The ATM strike serves as the center (body) of the Iron Butterfly.\n'
            f'Outer strikes (on both CALL and PUT sides) define the wings at equal distance from ATM.\n'
            f'The strategy is symmetrical around the ATM strike.\n\n'
        )

        about_str += 'POSITION DETAILS:\n'
        about_str += f'     | {"LEG":<25} | {"POSITION":<15} | {"STRIKE":<20} | {"STOPLOSS":<15} | {"TRAIL STOPLOSS":<15} |\n'
        about_str += f'     | {"Outer PUT (hedge)":<25} | {opposite_pos:<15} | {"ATM PUT - " + str(self.config.wing_width):<20} | {self.config.put_credit_spread_risk:<15} | {str(self.config.trail_put_credit_spread_risk):<15} |\n'
        about_str += f'     | {"ATM PUT (credit leg)":<25} | {self.config.long_or_short:<15} | {"ATM PUT":<20} | {self.config.put_credit_spread_risk:<15} | {str(self.config.trail_put_credit_spread_risk):<15} |\n'
        about_str += f'     | {"ATM CALL (credit leg)":<25} | {self.config.long_or_short:<15} | {"ATM CALL":<20} | {self.config.call_credit_spread_risk:<15} | {str(self.config.trail_call_credit_spread_risk):<15} |\n'
        about_str += f'     | {"Outer CALL (hedge)":<25} | {opposite_pos:<15} | {"ATM CALL + " + str(self.config.wing_width):<20} | {self.config.call_credit_spread_risk:<15} | {str(self.config.trail_call_credit_spread_risk):<15} |\n\n'

        about_str += (
            'NOTE:\n'
            '  • PUT and CALL Credit Spreads are entered together forming a symmetrical Iron Butterfly.\n'
            '  • Both spreads are monitored and call/put legs exited together when either side hits its respective stoploss.\n'
            '  • The position is entered around ATM, ensuring equal distance on both wings.\n\n'
        )

        about_str += f'Enter an Iron Butterfly each day at {self.config.entry_time.strftime("%H:%M:%S")} using nearest ATM options.\n'
        about_str += f'Exit all positions at {self.config.exit_time.strftime("%H:%M:%S")} if stoploss not triggered.\n\n'

        about_str += 'EXIT RULES:\n'
        about_str += f'     1. EXIT : If time is {self.config.exit_time.strftime("%H:%M:%S")}.\n'
        about_str += f'     2. EXIT PUT spread  : StopLoss hit → {self.config.put_credit_spread_risk} {"(trailing)" if self.config.trail_put_credit_spread_risk else "(fixed)"}.\n'
        about_str += f'     3. EXIT CALL spread : StopLoss hit → {self.config.call_credit_spread_risk} {"(trailing)" if self.config.trail_call_credit_spread_risk else "(fixed)"}.\n'

        return about_str
