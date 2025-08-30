from typing import Union
from strategy import Strategy, Action
from connectors.dbconnector import DBConnector
import pandas as pd
import copy

# Sample Strategy
# For each day, If market is open
#     - Enter a ATM straddle of the nearest expiry at 9:30 close of NIFTY
#     - Exit if time is 15:20 is reached

class SampleStrategy(Strategy):
    def __init__(self, config, dbconnector: DBConnector):
        super().__init__(config, dbconnector)
        self.name = self.__class__.__name__
        self.position = [] # will contain orders that are 'filled'
        self.outstanding_orders = None # will change later according to orders other than filled
        self.position_tally = {}    #AP

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

    def action(self, timestamp: pd.Timestamp) -> list[Action] | None:

        actions = None
        if timestamp.time() == pd.Timestamp("09:20").time(): 
            strike = self.dbconnector.get_ATM_strike(timestamp)
            closest_expiry = self.dbconnector.get_closest_expiry(timestamp)
            sell_call = Action(option_type="CE", strike=strike, expiry=closest_expiry, num_lots=1, trade_type="short", order_type="market")
            sell_put  = Action(option_type="PE", strike=strike, expiry=closest_expiry, num_lots=1, trade_type="short", order_type="market")
            actions = [sell_call, sell_put]

        elif timestamp.time() == pd.Timestamp("15:20").time():
            actions = self.square_off_actions()

        return actions

    def on_trade_execution(self, metadata: list[dict], outstanding_orders: list):
        '''
        metadata: `filled` orders.
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
                self.position_tally[filled_position['action'].square_off_id]['closed'] = filled_position #AP
                self.position.remove(position_to_remove)
            # 2. Else, simply add to self.position
            else:
                self.position.append(filled_position)

                self.position_tally[filled_position['hash']] = {}   #AP
                self.position_tally[filled_position['hash']]['opened'] = filled_position #AP
                self.position_tally[filled_position['hash']]['closed'] = None #AP

    def about(self):
        about_str  = f"Name: {self.name}\n"
        about_str += f"For each day, If market is open\n"
        about_str += f"     Enter a ATM straddle of the nearest expiry at 9:30 close of NIFTY\n"
        about_str += f"     Exit if time is 15:20 is reached\n"
        return about_str