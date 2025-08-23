from strategy import Strategy
import pandas as pd
from .base_class import Action


class MorningStraddle(Strategy):
    def __init__(self, configs, dbconnector):
        super().__init__(configs, dbconnector)
        
    def action(self, timestamp: pd.Timestamp):
        if timestamp.time() == pd.Timestamp("09:30:00").time():
            self.strike = self.dbconnector.get_ATM_strike(timestamp=timestamp, field='close')
            expiry = self.dbconnector.get_expiry(timestamp=timestamp)

            return [
                Action(option_type="CE", strike=self.strike, expiry=expiry, num_lots=self.config.lot_size, trade_type="sell", order_type="market"),
                Action(option_type="PE", strike=self.strike, expiry=expiry, num_lots=self.config.lot_size, trade_type="sell", order_type="market")
            ]
    
        elif timestamp.time() == pd.Timestamp("15:15:00").time():
            expiry = self.dbconnector.get_expiry(timestamp=timestamp)

            return [
                Action(option_type="CE", strike=self.strike, expiry=expiry, num_lots=self.config.lot_size, trade_type="buy", order_type="market"),
                Action(option_type="PE", strike=self.strike, expiry=expiry, num_lots=self.config.lot_size, trade_type="buy", order_type="market")
            ]
        
        # elif 

        return None


    def on_trade_execution(self, timestamp, metadata):
        if metadata:
            self.metadata = metadata
        else:
            return
        
