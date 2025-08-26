from typing import Union
from strategy import Strategy, Action
from connectors.dbconnector import DBConnector
import pandas as pd
import copy

class Straddle(Strategy):
    def __init__(self, config, dbconnector: DBConnector):
        super().__init__(config, dbconnector)

        assert self.config.long_or_short in ["long", "short"], f"Position must be either 'long' or 'short'. Given {self.config.long_or_short}"
        assert self.config.call_risk > 0, f"call_risk must be positive. Given {self.config.call_risk}"
        assert self.config.put_risk > 0, f"put_risk must be positive. Given {self.config.put_risk}"

        # Straddle Params
        self.name = self.__class__.__name__
        self.strike = None  # Will be set at the time of action

        # Params common to all strategies
        self.position = [] # will contain orders that are 'filled'
        self.outstanding_orders = None # will change later according to orders other than filled
        self.position_tally = {}    # Will contain the tally of each filled --> squared of position

    def square_off_actions(self, square_off_ids: set[int] | None = None) -> list[Action]:
        '''Return all the actions required to square off the open positions at market order'''
        
        actions = []
        if square_off_ids is None:
            for pos in self.position:
                opposite_action: Action = pos['action'].opposite_action()
                opposite_action.square_off_id = pos['hash']
                actions.append(opposite_action)
        elif square_off_ids and len(square_off_ids) > 0:
            for pos in self.position:
                if pos['hash'] in square_off_ids:
                    opposite_action = pos['action'].opposite_action()
                    opposite_action.square_off_id = pos['hash']
                    actions.append(opposite_action)

        return actions
    
    def _check_exit_condition(self, pos: dict, timestamp: pd.Timestamp) -> bool:
        '''Check if the exit condition is met for a given position at a specific timestamp'''
        # This will be different for each strategy

        action = pos['action']
        filled_price = pos['price']
        current_price = self.dbconnector.get_option_price(strike=action.strike, option_type=action.option_type, expiry_date=action.expiry, timestamp=timestamp)
        pos_pnl = (current_price - filled_price) * self.config.lot_size
        pos_pnl = pos_pnl if action.trade_type == "long" else -pos_pnl

        if action.option_type == "CE":
            check = pos_pnl <= -self.config.call_risk   # exit if call leg loss >= call_risk
        elif action.option_type == "PE":
            check = pos_pnl <= -self.config.put_risk    # exit if put leg loss >= put_risk
        else:
            raise ValueError(f"Unknown option type: {action.option_type}")

        return check

    def action(self, timestamp: pd.Timestamp) -> list[Action] | None:

        actions = None
        if timestamp.time() == self.config.entry_timestamp.time(): 
            
            self.strike = self.dbconnector.get_ATM_strike(timestamp)
            closest_expiry = self.dbconnector.get_closest_expiry(timestamp)    
            atm_call_action = Action(option_type="CE", strike=self.strike, expiry=closest_expiry, num_lots=1, trade_type=self.config.long_or_short, order_type="market")
            atm_put_action = Action(option_type="PE", strike=self.strike, expiry=closest_expiry, num_lots=1, trade_type=self.config.long_or_short, order_type="market")
            actions = [atm_call_action, atm_put_action]

        elif timestamp.time() == self.config.exit_timestamp.time(): 
            actions = self.square_off_actions()
        else:

            square_off_ids = set()
            for pos in self.position:
                if self._check_exit_condition(pos, timestamp):      # Will be different for each strategy
                    square_off_ids.add(pos['hash'])

            if len(square_off_ids) > 0:           
                actions = self.square_off_actions(square_off_ids)

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
        
        if self.config.long_or_short == "short":
            about_str  = f"Name : {self.name} : /\ \n"
        elif self.config.long_or_short == "long":
            about_str  = f"Name : {self.name} : \/ \n"

        about_str += f"Our Net Position : {self.config.long_or_short.upper()}\n"
        
        if self.config.long_or_short == "short":
            desc = "Neutral strategy. Profits from low volatility. Profits when the market is range-bound. TimeDecay on our side. Risk : unlimited"
        elif self.config.long_or_short == "long":
            desc = "Needs large price movements (in any side) to be profitable. Profits from high volatility. TimeDecay against us. Risk : limited"
        about_str += f"Description : {desc}\n"
        
        about_str += f"For each day, If market is open\n"
        about_str += f"     Enter an Straddle of (nearest) ATM at {self.config.entry_timestamp.time().strftime('%H:%M:%S')} at close of underlying\n"
        if self.config.long_or_short == "short":
            opposite_pos = "LONG"
        elif self.config.long_or_short == "long":
            opposite_pos = "SHORT"
        about_str += f"     Net position: \n"
        about_str += f"         {self.config.long_or_short.upper()}: [ATM Call and ATM Put] of strike according to close at {self.config.entry_timestamp.time().strftime('%H:%M:%S')} (X2)\n"
        about_str += f"     Exit if time is {self.config.exit_timestamp.time().strftime('%H:%M:%S')} is reached\n"
        about_str += f"     Exit call_leg if call_loss >= {self.config.call_risk}\n"
        about_str += f"     Exit put_leg if put_loss >= {self.config.put_risk}\n"
        return about_str

