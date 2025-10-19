from strategy import Strategy, Action
from connectors.dbconnector import DBConnector
import pandas as pd

class IronButterflyHedged(Strategy):
    def __init__(self, config, dbconnector: DBConnector):
        super().__init__(config, dbconnector)
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
                stoploss=float('inf'),  # The sl for OTM Put is managed as part of Bull Put Spread risk
            )
            atm_put_action = Action(
                option_type='PE',
                strike=atm_strike,
                expiry=closest_expiry,
                num_lots=1,
                trade_type=self.config.long_or_short,
                order_type=self.config.atm_put_order_type,
                stoploss=float('inf'),  # The sl for ATM Put is managed as part of Bull Put Spread risk
            )
            atm_call_action = Action(
                option_type='CE',
                strike=atm_strike,
                expiry=closest_expiry,
                num_lots=1,
                trade_type=self.config.long_or_short,
                order_type=self.config.atm_call_order_type,
                stoploss=float('inf'),  # The sl for ATM Call is managed as part of Bear Call Spread risk
            )
            otm_call_action = Action(
                option_type='CE',
                strike=otm_call_strike,
                expiry=closest_expiry,
                num_lots=1,
                trade_type='long' if self.config.long_or_short == 'short' else 'short',
                order_type=self.config.otm_call_order_type,
                stoploss=float('inf'),  # The sl for OTM Call is managed as part of Bear Call Spread risk
            )

            actions = [otm_put_action, atm_put_action, atm_call_action, otm_call_action]

        elif timestamp.time() == self.config.exit_time:
            actions = self.square_off_actions()

        return actions

    def about(self) -> str:
        opposite_pos = 'short' if self.config.long_or_short == 'long' else 'long'

        # Header
        if self.config.long_or_short == 'short':
            about_str = f'Name : {self.name} : _/\\_ \n'
        else:
            about_str = f'Name : {self.name} : ‾\\/‾\n'

        # Description
        if self.config.long_or_short == 'short':
            desc = (
                'Neutral strategy. Profits from low volatility. '
                'Profits when the market is range-bound. TimeDecay on our side. '
                'Profit : limited, Risk : limited.'
            )
        else:
            desc = (
                'Needs large price movements (in any side) to be profitable. '
                'Profits from high volatility. TimeDecay against us. '
                'Profit : limited, Risk : limited.'
            )

        about_str += f'\nDescription : {desc}\n'
        about_str += (
            f'Wing Width = [OTM Call Strike - ATM Strike] = '
            f'[ATM Strike - OTM Put Strike] = {self.config.wing_width}\n\n'
        )

        about_str += (
            f'Enter an Iron Butterfly each day of (nearest) ATM at '
            f'{self.config.entry_time.strftime("%H:%M:%S")} at close of underlying.\n'
            f'Exit all positions at {self.config.exit_time.strftime("%H:%M:%S")} , '
            f'if stoploss not hit.\n\n'
        )

        about_str += f'NET POSITION:\n'
        about_str += f'     {self.config.long_or_short.upper()} : [ATM Call and ATM Put]\n'
        about_str += f'     {opposite_pos.upper()} : [OTM Put and OTM Call]\n\n'

        # === Bull Put Spread (BPS) ===
        about_str += 'BULL PUT SPREAD (BPS):\n'
        about_str += (
            f'     Traded Together : [ATM PUT ({self.config.long_or_short}) + '
            f'OTM PUT ({opposite_pos})]\n'
        )
        about_str += f'     Total Risk : ₹{self.config.bull_put_spread_risk}\n'
        about_str += (
            f'     Stoploss Trigger : bull_put_spread_loss >= {self.config.bull_put_spread_risk}\n'
            f'     Exit Type        : {("TRAILING" if self.config.trail_bull_put_spread_risk else "FIXED")} STOPLOSS\n\n'
        )
        about_str += (
            f'     | {"LEG":<12} | {"POSITION":<8} | {"STRIKE":<24} |\n'
            f'     | {"ATM PUT":<12} | {self.config.long_or_short:<8} | {"ATM Strike":<24} |\n'
            f'     | {"OTM PUT":<12} | {opposite_pos:<8} | {"ATM Strike - " + str(self.config.wing_width):<24} |\n\n'
        )

        # === Bear Call Spread (BCS) ===
        about_str += 'BEAR CALL SPREAD (BCS):\n'
        about_str += (
            f'     Traded Together : [ATM CALL ({self.config.long_or_short}) + '
            f'OTM CALL ({opposite_pos})]\n'
        )
        about_str += f'     Total Risk : ₹{self.config.bear_call_spread_risk}\n'
        about_str += (
            f'     Stoploss Trigger : bear_call_spread_loss >= {self.config.bear_call_spread_risk}\n'
            f'     Exit Type        : {("TRAILING" if self.config.trail_bear_call_spread_risk else "FIXED")} STOPLOSS\n\n'
        )
        about_str += (
            f'     | {"LEG":<12} | {"POSITION":<8} | {"STRIKE":<24} |\n'
            f'     | {"ATM CALL":<12} | {self.config.long_or_short:<8} | {"ATM Strike":<24} |\n'
            f'     | {"OTM CALL":<12} | {opposite_pos:<8} | {"ATM Strike + " + str(self.config.wing_width):<24} |\n\n'
        )

        return about_str
