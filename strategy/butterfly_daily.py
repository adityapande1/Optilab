from strategy import Strategy, Action
from connectors.dbconnector import DBConnector
import pandas as pd


class ButterflyDaily(Strategy):
    def __init__(self, config, dbconnector: DBConnector):
        super().__init__(config, dbconnector)
        self.name = self.__class__.__name__

    def action(self, timestamp: pd.Timestamp) -> list[Action] | None:
        actions = None
        if timestamp.time() == self.config.entry_time:
            atm_strike = self.dbconnector.get_ATM_strike(timestamp)
            closest_expiry = self.dbconnector.get_closest_expiry(timestamp)
            middle_option_strike = atm_strike
            left_option_strike = middle_option_strike - self.config.wing_width
            right_option_strike = middle_option_strike + self.config.wing_width

            left_option_action = Action(
                option_type=self.config.butterfly_option_type,
                strike=left_option_strike,
                expiry=closest_expiry,
                num_lots=1,
                trade_type= self.config.long_or_short,
                order_type='market_stoploss_trail', # order type is set to trail stoploss but actual stoploss levels will be calculated based on the spread
                stoploss=float('inf'),  # Risk set here but it will not be used as the stoploss levels will be calculated based on the spread together with the inner put leg
            )

            middle_option_action = Action(
                option_type=self.config.butterfly_option_type,
                strike=middle_option_strike,
                expiry=closest_expiry,
                num_lots=2,
                trade_type= 'short' if self.config.long_or_short == 'long' else 'long',
                order_type='market_stoploss_trail', # order type is set to trail stoploss but actual stoploss levels will be calculated based on the spread
                stoploss=float('inf'),  # Risk set here but it will not be used as the stoploss levels will be calculated based on the spread
            )

            outer_call_action = Action(
                option_type=self.config.butterfly_option_type,
                strike=right_option_strike,
                expiry=closest_expiry,
                num_lots=1,
                trade_type='long' if self.config.long_or_short == 'short' else 'short',
                order_type='market_stoploss_trail', # order type is set to trail stoploss but actual stoploss levels will be calculated based on the spread
                stoploss=float('inf'),  # Risk set here but it will not be used as the stoploss levels will be calculated based on the spread together with the inner put leg
            )
            actions = [left_option_action, middle_option_action, outer_call_action]

        elif timestamp.time() == self.config.exit_time:
            actions = self.square_off_actions()
        return actions

    def about(self) -> str:
        about_str = "HELLO"
        return about_str
