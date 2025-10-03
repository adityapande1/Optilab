from strategy import Strategy, Action
from connectors.dbconnector import DBConnector
import pandas as pd


class Butterfly(Strategy):
    def __init__(self, config, dbconnector: DBConnector):
        super().__init__(config, dbconnector)
        self.name = self.__class__.__name__

    def action(self, timestamp: pd.Timestamp) -> list[Action] | None:
        actions = None
        if timestamp.time() == self.config.entry_time:

            atm_strike = self.dbconnector.get_ATM_strike(timestamp)
            otm_strike = atm_strike + self.config.wing_width if self.config.butterfly_option_type == 'CE' else atm_strike - self.config.wing_width
            itm_strike = atm_strike - self.config.wing_width if self.config.butterfly_option_type == 'CE' else atm_strike + self.config.wing_width
            closest_expiry = self.dbconnector.get_closest_expiry(timestamp)

            # butterfly always executed 1 X 2 X 1 legs
            otm_action = Action(
                option_type=self.config.butterfly_option_type,
                strike=otm_strike,
                expiry=closest_expiry,
                num_lots=1,
                trade_type=self.config.long_or_short,
                order_type=self.config.otm_order_type,
                stoploss=self.config.otm_risk,
            )
            atm_action = Action(
                option_type=self.config.butterfly_option_type,
                strike=atm_strike,
                expiry=closest_expiry,
                num_lots=2,
                trade_type='short' if self.config.long_or_short == 'long' else 'long',
                order_type=self.config.atm_order_type,
                stoploss=self.config.atm_risk,
            )
            itm_action = Action(
                option_type=self.config.butterfly_option_type,
                strike=itm_strike,
                expiry=closest_expiry,
                num_lots=1,
                trade_type=self.config.long_or_short,
                order_type=self.config.itm_order_type,
                stoploss=self.config.itm_risk,
            )

            actions = [otm_action, atm_action, itm_action]

        elif timestamp.time() == self.config.exit_time:
            actions = self.square_off_actions()

        return actions

    def about(self) -> str:

        opposite_pos = 'short' if self.config.long_or_short == 'long' else 'long'
        otm_strike = f'ATM Strike + {self.config.wing_width}' if self.config.butterfly_option_type == 'CE' else f'ATM Strike - {self.config.wing_width}'
        itm_strike = f'ATM Strike - {self.config.wing_width}' if self.config.butterfly_option_type == 'CE' else f'ATM Strike + {self.config.wing_width}'

        if self.config.long_or_short == 'long':
            about_str = f'Name : {self.name} : _/\_ \n'
            desc = (
                "Range-bound strategy. Profits if price stays near the middle strike (ATM). "
                "Profits from low volatility. TimeDecay on our side. "
                "Profit : limited, Risk : limited"
            )
        elif self.config.long_or_short == 'short':
            about_str = f'Name : {self.name} : ‾\/‾\n'
            desc = (
                "Expects a sharp move away from the middle strike. "
                "Profits from high volatility and large price moves. "
                "TimeDecay against us. "
                "Profit : limited, Risk : limited"
            )

        about_str += f'Description : {desc}\n'
        about_str += f'Wing Width = | OTM Call Strike - ATM Strike | = | ATM Strike - ITM Strike | = {self.config.wing_width}\n'

        about_str += f'\nEnter a Butterfly each day of (nearest) ATM at {self.config.entry_time.strftime("%H:%M:%S")} at close of underlying.\n'
        about_str += 'POSITIONS TABLE: \n\n'

        about_str += f'     | {"NAME":<15} | {"TYPE":<6} | {"POSITION":<12} | {"STOPLOSS":<8} | {"TRAIL STOPLOSS":<15} | {"ORDER_TYPE":<30} | {"STRIKE":<20} |\n'
        about_str += f'     | {"-"*15} | {"-"*6} | {"-"*12} | {"-"*8} | {"-"*15} | {"-"*30} | {"-"*20} |\n'
        about_str += f'     | {"LEFT LEG":<15} | {self.config.butterfly_option_type:<6} | {"1 X " + self.config.long_or_short:<12} | {self.config.otm_risk:<8} | {self.config.trail_otm_risk:<15} | {self.config.otm_order_type:<30} | {otm_strike:<20} |\n'
        about_str += f'     | {"MIDDLE LEG":<15} | {self.config.butterfly_option_type:<6} | {"2 X " + opposite_pos:<12} | {self.config.atm_risk:<8} | {self.config.trail_atm_risk:<15} | {self.config.atm_order_type:<30} | {"ATM Strike":<20} |\n'
        about_str += f'     | {"RIGHT LEG":<15} | {self.config.butterfly_option_type:<6} | {"1 X " + self.config.long_or_short:<12} | {self.config.itm_risk:<8} | {self.config.trail_itm_risk:<15} | {self.config.itm_order_type:<30} | {itm_strike:<20} |\n\n'

        about_str += f'Exit all positions at {self.config.exit_time.strftime("%H:%M:%S")} , if stoploss not hit.\n'

        return about_str
