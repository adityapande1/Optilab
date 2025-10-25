from strategy import Strategy, Action
from connectors.dbconnector import DBConnector
import pandas as pd
from utils.option_utils import get_lower_upper_strikes_around_spot


class IronCondorWeekly(Strategy):
    def __init__(self, config, dbconnector: DBConnector):
        super().__init__(config, dbconnector)
        self.name = self.__class__.__name__
        self.entry_ts_to_exit_ts_map = self.generate_entry_date_to_exit_date_map()
        self.latest_entry_timestamp = None

    def action(self, timestamp: pd.Timestamp) -> list[Action] | None:
        actions = None
        if timestamp in self.entry_ts_to_exit_ts_map:
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
            self.latest_entry_timestamp = timestamp

        elif timestamp in self.entry_ts_to_exit_ts_map.values():
            actions = self.square_off_actions()

        return actions

    def about(self) -> str:
        about_str = 'HELLO WORLD'
        return about_str
