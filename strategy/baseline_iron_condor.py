from typing import Union
from strategy import Strategy, Action, StrategyConfig
from connectors.dbconnector import DBConnector
import pandas as pd
import copy

class BaselineIronCondor(Strategy):
    def __init__(self, 
                 config: StrategyConfig, 
                 dbconnector: DBConnector, 
                 long_or_short: str = "short",
                 strike_gap: Union[int, float] = 50,
                 left_strike_gap_multiple: Union[int, float] = 1,
                 leftmost_strike_gap_multiple: Union[int, float] = 2,
                 right_strike_gap_multiple: Union[int, float] = 1,
                 rightmost_strike_gap_multiple: Union[int, float] = 2,
                 entry_timestamp: pd.Timestamp = pd.Timestamp("09:15"),
                 exit_timestamp: pd.Timestamp = pd.Timestamp("15:20")
                 ):
        super().__init__(config, dbconnector)

        assert long_or_short in ["long", "short"], f"Position must be either 'long' or 'short'. Given {long_or_short}"
        assert isinstance(strike_gap, (int, float)) and strike_gap > 0, f"strike_gap must be a positive integer. Given {strike_gap}"
        assert isinstance(left_strike_gap_multiple, (int, float)) and left_strike_gap_multiple > 0, f"left_strike_gap_multiple must be a positive integer. Given {left_strike_gap_multiple}"
        assert isinstance(right_strike_gap_multiple, (int, float)) and right_strike_gap_multiple > 0, f"right_strike_gap_multiple must be a positive integer. Given {right_strike_gap_multiple}"
        assert isinstance(leftmost_strike_gap_multiple, (int, float)) and leftmost_strike_gap_multiple > left_strike_gap_multiple, f"leftmost_strike_gap_multiple {leftmost_strike_gap_multiple} must be a positive integer greater than left_strike_gap_multiple {left_strike_gap_multiple}."
        assert isinstance(rightmost_strike_gap_multiple, (int, float)) and rightmost_strike_gap_multiple > right_strike_gap_multiple, f"rightmost_strike_gap_multiple {rightmost_strike_gap_multiple} must be a positive integer greater than right_strike_gap_multiple {right_strike_gap_multiple}."
        # Iron Condor Params
        self.name = self.__class__.__name__
        self.left_strike = None # Will be set at the time of action
        self.leftmost_strike = None # Will be set at the time of action
        self.center_strike = None  # Will be set at the time of action
        self.right_strike = None # Will be set at the time of action
        self.rightmost_strike = None # Will be set at the time of action
        self.long_or_short = long_or_short
        self.strike_gap = strike_gap
        self.left_strike_gap_multiple = left_strike_gap_multiple
        self.leftmost_strike_gap_multiple = leftmost_strike_gap_multiple
        self.right_strike_gap_multiple = right_strike_gap_multiple
        self.rightmost_strike_gap_multiple = rightmost_strike_gap_multiple
        self.entry_timestamp = entry_timestamp
        self.exit_timestamp = exit_timestamp

        # Params common to all strategies
        self.position = [] # will contain orders that are 'filled'
        self.outstanding_orders = None # will change later according to orders other than filled
        self.position_tally = {}    # Will contain the tally of each filled --> squared of position

    def square_off_actions(self, square_off_ids: list[int] | None = None) -> list[Action]:
        '''Return all the actions required to square off the open positions at market order'''
        actions = []
        if square_off_ids: # In the case we want to square-off a subset of our current positions
            raise NotImplementedError()
        else:
            for position_dict in self.position:
                opposite_action: Action = position_dict['action'].opposite_action()
                opposite_action.square_off_id = position_dict['hash']
                actions.append(opposite_action)
        return actions
    
    def pnl_at_timestamp(self, timestamp: pd.Timestamp) -> float:
        '''Cumulative PnL for all positions at a specific timestamp'''
        pnl = 0.0
        for position_dict in self.position:
            assert position_dict['timestamp'] <= timestamp, f"Position timestamp {position_dict['timestamp']} is greater than query timestamp {timestamp}."
            action = position_dict['action'] 
            filling_price = position_dict['price']
            current_price = self.dbconnector.get_option_price(strike=action.strike, option_type=action.option_type, expiry_date=action.expiry, timestamp=timestamp)
            position_pnl = current_price - filling_price
            position_pnl = -position_pnl if action.trade_type == "sell" else position_pnl 
            pnl += position_pnl
        pnl = pnl * self.config.lot_size
        return pnl
    
    def _has_stoploss_or_target_hit(self, timestamp: pd.Timestamp) -> bool:
        pnl = self.pnl_at_timestamp(timestamp)
        stoploss_hit = (pnl <= -self.config.risk_per_trade)     # Note: StrategyConfig.risk_per_trade is asserted in dataclass definition > 0
        target_hit = (pnl >= self.config.reward_per_trade)      # Note: StrategyConfig.reward_per_trade is asserted > 0 (indirectly)
        return (stoploss_hit or target_hit)

    def action(self, timestamp: pd.Timestamp) -> list[Action] | None:

        actions = None
        if timestamp.time() == self.entry_timestamp.time(): 
            
            self.center_strike = self.dbconnector.get_ATM_strike(timestamp)
            self.leftmost_strike = self.center_strike - self.strike_gap * self.leftmost_strike_gap_multiple
            self.left_strike = self.center_strike - self.strike_gap * self.left_strike_gap_multiple
            self.right_strike = self.center_strike + self.strike_gap * self.right_strike_gap_multiple
            self.rightmost_strike = self.center_strike + self.strike_gap * self.rightmost_strike_gap_multiple
            assert self.leftmost_strike < self.left_strike < self.center_strike < self.right_strike < self.rightmost_strike, f"Strikes not in order: {self.leftmost_strike}, {self.left_strike}, {self.center_strike}, {self.right_strike}, {self.rightmost_strike}"

            closest_expiry = self.dbconnector.get_closest_expiry(timestamp)    
            if self.long_or_short == "short":
                long_leftmost_otm_put = Action(option_type="PE", strike=self.leftmost_strike, expiry=closest_expiry, num_lots=1, trade_type="buy", order_type="market") 
                short_left_otm_put = Action(option_type="PE", strike=self.left_strike, expiry=closest_expiry, num_lots=1, trade_type="sell", order_type="market") 
                short_right_otm_call = Action(option_type="CE", strike=self.right_strike, expiry=closest_expiry, num_lots=1, trade_type="sell", order_type="market") 
                long_rightmost_otm_call = Action(option_type="CE", strike=self.rightmost_strike, expiry=closest_expiry, num_lots=1, trade_type="buy", order_type="market")
                actions = [long_leftmost_otm_put, short_left_otm_put, short_right_otm_call, long_rightmost_otm_call]
            elif self.long_or_short == "long":
                short_leftmost_otm_put = Action(option_type="PE", strike=self.leftmost_strike, expiry=closest_expiry, num_lots=1, trade_type="sell", order_type="market") 
                long_left_otm_put = Action(option_type="PE", strike=self.left_strike, expiry=closest_expiry, num_lots=1, trade_type="buy", order_type="market") 
                long_right_otm_call = Action(option_type="CE", strike=self.right_strike, expiry=closest_expiry, num_lots=1, trade_type="buy", order_type="market") 
                short_rightmost_otm_call = Action(option_type="CE", strike=self.rightmost_strike, expiry=closest_expiry, num_lots=1, trade_type="sell", order_type="market")
                actions = [short_leftmost_otm_put, long_left_otm_put, long_right_otm_call, short_rightmost_otm_call]

        elif timestamp.time() == self.exit_timestamp.time() or self._has_stoploss_or_target_hit(timestamp):
            actions = self.square_off_actions()

        return actions
    
    def on_trade_execution(self, metadata: list[dict], outstanding_orders: list):
        '''
        metadata: List of `filled` orders.
        outstanding_orders: `unfulfilled` orders
        '''
        self.outstanding_orders = copy.deepcopy(outstanding_orders)

        for filled_position in metadata:
            # 1. If this is a square_off order, clear from self.position
            if filled_position['action'].square_off_id:
                position_to_remove = None
                for our_position in self.position:
                    if our_position['hash'] == filled_position['action'].square_off_id:
                        position_to_remove = our_position
                        break
                
                assert position_to_remove, f"INVALID SQUARE-OFF. A filled position does not exist in {self.position}."
                self.position_tally[filled_position['action'].square_off_id]['closed'] = filled_position 
                self.position.remove(position_to_remove)
            # 2. Else, simply add to self.position
            else:
                self.position.append(filled_position)
                self.position_tally[filled_position['hash']] = {}   
                self.position_tally[filled_position['hash']]['opened'] = filled_position 
                self.position_tally[filled_position['hash']]['closed'] = None 


    def about(self) -> str:
        about_str  = f"Name : {self.name} : __/‾‾\\__ \n"
        about_str += f"Our Net Position : {self.long_or_short.upper()}\n"

        if self.long_or_short == "short":
            desc = "Neutral strategy. Profits from low volatility. Profits when the market stays within a range. | Risk : limited | Profit : limited |"
        elif self.long_or_short == "long":
            desc = "Needs large price movements (in either direction) to be profitable. Profits from high volatility. | Risk : limited | Profit : limited |"

        about_str += f"Description : {desc}\n"
        about_str += f"For each day, If market is open\n"
        about_str += f"     Enter an Iron Condor around the ATM at {self.entry_timestamp.time().strftime('%H:%M:%S')} at close of underlying\n"
        about_str += f"     At {self.entry_timestamp.time().strftime('%H:%M:%S')} Find center_strike = ATM strike wrt underlying at this time: \n"

        if self.long_or_short == "short":
            opposite_pos = "LONG"
        elif self.long_or_short == "long":
            opposite_pos = "SHORT"

        about_str += f"     Net position: \n"
        about_str += f"         {opposite_pos}: [Far OTM PUT] leftmost_strike : (center_strike - {self.strike_gap} x {self.leftmost_strike_gap_multiple}) (X1)\n"
        about_str += f"         {self.long_or_short.upper()}: [Near OTM PUT] left_strike : (center_strike - {self.strike_gap} x {self.left_strike_gap_multiple}) (X1)\n"
        about_str += f"         {self.long_or_short.upper()}: [Near OTM CALL] right_strike : (center_strike + {self.strike_gap} x {self.right_strike_gap_multiple}) (X1)\n"
        about_str += f"         {opposite_pos}: [Far OTM CALL] rightmost_strike : (center_strike + {self.strike_gap} x {self.rightmost_strike_gap_multiple}) (X1)\n"
        about_str += f"     Exit if time is {self.exit_timestamp.time().strftime('%H:%M:%S')} is reached\n"

        return about_str
