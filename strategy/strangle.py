from strategy import Strategy, Action
from connectors.dbconnector import DBConnector
import pandas as pd

class Strangle(Strategy):
    def __init__(self, config, dbconnector: DBConnector):
        super().__init__(config, dbconnector)

        assert self.config.long_or_short in ['long', 'short'], f"Position must be either 'long' or 'short'. Given {self.config.long_or_short}"
        assert self.config.otm_call_risk > 0, f'call_risk must be positive. Given {self.config.otm_call_risk}'
        assert self.config.otm_put_risk > 0, f'put_risk must be positive. Given {self.config.otm_put_risk}'

        # Strangle Params
        self.name = self.__class__.__name__
        self.otm_call_strike = None  # Will be set at the time of action
        self.otm_put_strike = None  # Will be set at the time of action

    def _get_lower_upper_strikes_for_spread(self, spot: float, strike_interval: int = 50, spread_width: int = 100):
        """
        Select the lower strike and upper strike for a straddle spread such that the midpoint [(lower_strike + upper_strike) / 2] is as close to the `spot` price as possible.

        Args
        ----
        spot : float
            Current underlying price.
        strike_interval : int
            Distance between consecutive strikes in the option chain (e.g., 50 in NIFTY).
        spread_width : int
            Distance between lower and upper strikes of the spread (e.g., 150).

        Returns
        -----
        lower_strike : int
            Selected lower strike price.
        upper_strike : int
            Selected upper strike price.
        """
        if spot % strike_interval == 0:
            spot -= 1e-6  # avoid edge-case ambiguity

        approx_lower = spot - spread_width / 2
        lower_strike = round(approx_lower / strike_interval) * strike_interval
        upper_strike = lower_strike + spread_width

        return lower_strike, upper_strike

    def action(self, timestamp: pd.Timestamp) -> list[Action] | None:
        actions = None
        if timestamp.time() == self.config.entry_time:
            spot = self.dbconnector.df_spot.loc[timestamp, 'close']
            self.otm_put_strike, self.otm_call_strike = self._get_lower_upper_strikes_for_spread(spot=spot, strike_interval=self.config.strike_interval, spread_width=self.config.spread_width)
            closest_expiry = self.dbconnector.get_closest_expiry(timestamp)

            otm_put_action = Action(
                option_type='PE',
                strike=self.otm_put_strike,
                expiry=closest_expiry,
                num_lots=1,
                trade_type=self.config.long_or_short,
                order_type=self.config.otm_put_order_type,
                stoploss=self.config.otm_put_risk,
            )

            otm_call_action = Action(
                option_type='CE',
                strike=self.otm_call_strike,
                expiry=closest_expiry,
                num_lots=1,
                trade_type=self.config.long_or_short,
                order_type=self.config.otm_call_order_type,
                stoploss=self.config.otm_call_risk,
            )

            actions = [otm_put_action, otm_call_action]

        elif timestamp.time() == self.config.exit_time:
            actions = self.square_off_actions()

        return actions

    def about(self) -> str:
        about_str = f'Name : {self.name}\n'
        return about_str
