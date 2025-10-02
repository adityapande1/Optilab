from strategy import Strategy, Action
from connectors.dbconnector import DBConnector
import pandas as pd


class IronButterfly(Strategy):
    def __init__(self, config, dbconnector: DBConnector):
        super().__init__(config, dbconnector)

        assert self.config.long_or_short in ['long', 'short'], f"Position must be either 'long' or 'short'. Given {self.config.long_or_short}"
        assert self.config.otm_put_risk > 0, f'otm_put_risk must be positive. Given {self.config.otm_put_risk}'
        assert self.config.atm_put_risk > 0, f'atm_put_risk must be positive. Given {self.config.atm_put_risk}'
        assert self.config.atm_call_risk > 0, f'atm_call_risk must be positive. Given {self.config.atm_call_risk}'
        assert self.config.otm_call_risk > 0, f'otm_call_risk must be positive. Given {self.config.otm_call_risk}'
        assert self.config.wing_width > 0 and self.config.wing_width % 50 == 0, f'wing_width must be positive and multiple of strike_interval (50). Given {self.config.wing_width}'
        self.name = self.__class__.__name__

    def action(self, timestamp: pd.Timestamp) -> list[Action] | None:
        actions = None
        if timestamp.time() == self.config.entry_time:

            atm_strike = self.dbconnector.get_ATM_strike(timestamp)
            otm_put_strike = atm_strike - self.config.wing_width
            otm_call_strike = atm_strike + self.config.wing_width
            closest_expiry = self.dbconnector.get_closest_expiry(timestamp)

            otm_put_action = Action(
                option_type='PE',
                strike=otm_put_strike,
                expiry=closest_expiry,
                num_lots=1,
                trade_type='long' if self.config.long_or_short == 'short' else 'short',
                order_type=self.config.otm_put_order_type,
                stoploss=self.config.otm_put_risk,
            )
            atm_put_action = Action(
                option_type='PE',
                strike=atm_strike,
                expiry=closest_expiry,
                num_lots=1,
                trade_type=self.config.long_or_short,
                order_type=self.config.atm_put_order_type,
                stoploss=self.config.atm_put_risk,
            )
            atm_call_action = Action(
                option_type='CE',
                strike=atm_strike,
                expiry=closest_expiry,
                num_lots=1,
                trade_type=self.config.long_or_short,
                order_type=self.config.atm_call_order_type,
                stoploss=self.config.atm_call_risk,
            )
            otm_call_action = Action(
                option_type='CE',
                strike=otm_call_strike,
                expiry=closest_expiry,
                num_lots=1,
                trade_type='long' if self.config.long_or_short == 'short' else 'short',
                order_type=self.config.otm_call_order_type,
                stoploss=self.config.otm_call_risk,
            )

            actions = [otm_put_action, atm_put_action, atm_call_action, otm_call_action]

        elif timestamp.time() == self.config.exit_time:
            actions = self.square_off_actions()

        return actions

    def about(self) -> str:
        if self.config.long_or_short == 'short':
            about_str = f'Name : {self.name} : _/\_ \n'
        elif self.config.long_or_short == 'long':
            about_str = f'Name : {self.name} : ‾\/‾\n'

        if self.config.long_or_short == 'short':
            desc = 'Neutral strategy. Profits from low volatility. Profits when the market is range-bound. TimeDecay on our side. Profit : limited, Risk : limited'
        elif self.config.long_or_short == 'long':
            desc = 'Needs large price movements (in any side) to be profitable. Profits from high volatility. TimeDecay against us. Profit : limited, Risk : limited'

        about_str += f'Description : {desc}\n'
        about_str += f'Wing Width = [OTM Call Strike - ATM Strike] = [ATM Strike - OTM Put Strike] = {self.config.wing_width}\n'

        about_str += 'For each day, If market is open\n'
        about_str += (
            f'     Enter an Iron Butterfly of (nearest) ATM at {self.config.entry_time.strftime("%H:%M:%S")} at close of underlying. The OTM call strikes are : ATM Strike ± {self.config.wing_width}\n'
        )

        if self.config.long_or_short == 'short':
            opposite_pos = 'long'
        elif self.config.long_or_short == 'long':
            opposite_pos = 'short'

        about_str += f'NET POSTITON: \n'
        about_str += f'     {self.config.long_or_short.upper()} : [ATM Call and ATM Put] and {opposite_pos.upper()} [OTM Put and OTM Call] according to close at {self.config.entry_time.strftime("%H:%M:%S")}\n'
        about_str += f'     EXIT ALL LEGS AUTOMATICALLY at EXIT TIME : {self.config.exit_time.strftime("%H:%M:%S")}\n'

        about_str += f'     The Legs are : \n'
        about_str += f'     1. OTM PUT of strike = ATM Strike - {self.config.wing_width}\n'
        about_str += f'          POS : {opposite_pos.upper()} | RISK : ₹ {self.config.otm_call_risk}\n'
        about_str += f'          StopLoss condition : If otm_put_leg_loss >= {self.config.otm_put_risk} \n'
        about_str += f'          Exit Type : {"TRAILING STOPLOSS" if self.config.trail_otm_put_risk else "FIXED STOPLOSS"}\n'
        about_str += f'     2. ATM PUT of strike = ATM Strike\n'
        about_str += f'          POS : {self.config.long_or_short.upper()} | RISK : ₹ {self.config.atm_put_risk}\n'
        about_str += f'          StopLoss condition : If atm_put_leg_loss >= {self.config.atm_put_risk} \n'
        about_str += f'          Exit Type : {"TRAILING STOPLOSS" if self.config.trail_atm_put_risk else "FIXED STOPLOSS"}\n'
        about_str += f'     3. ATM CALL of strike = ATM Strike\n'
        about_str += f'          POS : {self.config.long_or_short.upper()} | RISK : ₹ {self.config.atm_call_risk}\n'
        about_str += f'          StopLoss condition : If atm_call_leg_loss >= {self.config.atm_call_risk} \n'
        about_str += f'          Exit Type : {"TRAILING STOPLOSS" if self.config.trail_atm_call_risk else "FIXED STOPLOSS"}\n'
        about_str += f'     4. OTM CALL of strike = ATM Strike + {self.config.wing_width}\n'
        about_str += f'          POS : {opposite_pos.upper()} | RISK : ₹ {self.config.otm_call_risk}\n'
        about_str += f'          StopLoss condition : If otm_call_leg_loss >= {self.config.otm_call_risk} \n'
        about_str += f'          Exit Type : {"TRAILING STOPLOSS" if self.config.trail_otm_call_risk else "FIXED STOPLOSS"}\n'

        return about_str
