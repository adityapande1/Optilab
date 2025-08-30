from dataclasses import dataclass
import os
import torch
import pandas as pd
import argparse

class ReadOnlyConfig:
    def __init__(self, data: dict):
        # store data in a private dict
        object.__setattr__(self, "_data", dict(data))

    def __getattr__(self, key):
        try:
            return self._data[key]
        except KeyError:
            raise AttributeError(f"No such config key: {key}")

    def __getitem__(self, key):
        return self._data[key]

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    def __repr__(self):
        return f"ReadOnlyConfig({self._data})"

    # Prevent setting new attributes
    def __setattr__(self, key, value):
        raise AttributeError("ReadOnlyConfig is immutable")

    # Expose as a dict if needed
    def as_dict(self):
        return dict(self._data)


class Parser:
    def __init__(self):

        self.parser = argparse.ArgumentParser(description="Options Strategy Config Parser")

        # --- Common args ---
        # Backtest configuration
        self.parser.add_argument("--start_date", type=str, default="2024-01-01", metavar="YYYY-MM-DD", help="Backtest start date")
        self.parser.add_argument("--end_date", type=str, default="2024-01-31", metavar="YYYY-MM-DD", help="Backtest end date")
        self.parser.add_argument("--transaction_cost", type=float, default=0.0, metavar="₹", help="Transaction cost per lot in rupees")
        # Common strategy configuration
        self.parser.add_argument("--strategy", type=str, choices=["straddle"], default="straddle", help="Strategy to use")
        self.parser.add_argument("--entry_time", type=str, default="9:15:00", metavar="HH:MM:SS", help="Time to enter positions each day")
        self.parser.add_argument("--exit_time", type=str, default="15:20:00", metavar="HH:MM:SS", help="Time to forcefully exit all positions each day")
        self.parser.add_argument("--lot_size", type=int, default=75, help="Lot size for trading")
        # ------------------

        # --- Straddle args ---
        # Call leg configuration
        straddle_group = self.parser.add_argument_group("straddle")
        straddle_group.add_argument("--straddle_call_risk", type=float, default=float("inf"), metavar="₹", help="Risk for the call leg in a straddle (₹). The leg gets cut if this risk is breached.")
        straddle_group.add_argument("--trail_call_risk", action="store_true", help="Whether to trail the stoploss risk for the call leg.")
        # Put leg configuration
        straddle_group.add_argument("--straddle_put_risk", type=float, default=float("inf"), metavar="₹", help="Risk for the put leg in a straddle (₹). The leg gets cut if this risk is breached.")
        straddle_group.add_argument("--trail_put_risk", action="store_true", help="Whether to trail the stoploss risk for the put leg.")
        # Overall straddle configuration
        straddle_group.add_argument("--straddle_long_or_short", type=str, choices=["long", "short"], default="short", help="Direction of the straddle position")
        # -------------------

    def parse_args(self):
        self.args = self.parser.parse_args()
        return self.args
        
    def get_backtest_config(self):
        return ReadOnlyConfig({
            "start_date": pd.Timestamp(self.args.start_date),
            "end_date": pd.Timestamp(self.args.end_date),
            "transaction_cost": self.args.transaction_cost
        })

    # --- Config getters ---
    def get_straddle_config(self):
        config_dict = {

            "long_or_short": self.args.straddle_long_or_short,
            
            "call_risk": self.args.straddle_call_risk,
            "trail_call_risk": self.args.trail_call_risk,

            "put_risk": self.args.straddle_put_risk,
            "trail_put_risk": self.args.trail_put_risk,
            
            "lot_size": self.args.lot_size,
            "entry_timestamp": pd.Timestamp(self.args.entry_time),
            "exit_timestamp": pd.Timestamp(self.args.exit_time)
        }

        config_dict['call_order_type'] = 'market_stoploss_trail' if config_dict['trail_call_risk'] else 'market_stoploss'   # If the trail_call_risk is False it means we are using a regular stoploss
        config_dict['put_order_type'] = 'market_stoploss_trail' if config_dict['trail_put_risk'] else 'market_stoploss'     # If the trail_put_risk is False it means we are using a regular stoploss

        return ReadOnlyConfig(config_dict)


if __name__ == "__main__":
    parser = Parser()
    args = parser.parse_args()
    print("Straddle Config:", parser.get_straddle_config())




    
