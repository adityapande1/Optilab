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

        # --- Common ---
        self.parser.add_argument("--strategy", type=str, choices=["straddle"], default="straddle", help="Strategy to use")

        # Backtest configuration
        self.parser.add_argument("--start_date", type=str, default="2024-01-01", metavar="YYYY-MM-DD", help="Backtest start date")
        self.parser.add_argument("--end_date", type=str, default="2024-02-28", metavar="YYYY-MM-DD", help="Backtest end date")

        # Entry-Exit rules
        self.parser.add_argument("--entry_time", type=str, default="9:20:00", metavar="HH:MM:SS", help="Time to enter positions each day")
        self.parser.add_argument("--exit_time", type=str, default="15:20:00", metavar="HH:MM:SS", help="Time to forcefully exit all positions each day")

        # Position sizing
        self.parser.add_argument("--lot_size", type=int, default=75, help="Lot size for trading")

        # Transaction costs
        self.parser.add_argument("--transaction_cost", type=float, default=0.0, metavar="₹", help="Transaction cost per lot in rupees")

        # Risk management
        # To be discussed
        # self.parser.add_argument("--risk_per_trade", type=float, default=1000.0, metavar="₹", help="Risk per trade in rupees")
        # self.parser.add_argument("--reward_to_risk", type=float, default=1.0, help="Reward-to-risk ratio")
        # To be discussed

        # --- Straddle ---
        straddle_group = self.parser.add_argument_group("straddle")
        straddle_group.add_argument("--straddle_call_risk", type=float, default=float("inf"), metavar="₹", 
                                    help="Risk for the call leg in a straddle (₹). The leg gets cut if this risk is breached.")
        straddle_group.add_argument("--straddle_put_risk", type=float, default=float("inf"), metavar="₹", 
                                    help="Risk for the put leg in a straddle (₹). The leg gets cut if this risk is breached.")
        # long_or_short
        straddle_group.add_argument("--straddle_long_or_short", type=str, choices=["long", "short"], default="short", help="Direction of the straddle position")

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
        return ReadOnlyConfig({
            "call_risk": self.args.straddle_call_risk,
            "put_risk": self.args.straddle_put_risk,
            "long_or_short": self.args.straddle_long_or_short,
            "lot_size": self.args.lot_size,
            "entry_timestamp": pd.Timestamp(self.args.entry_time),
            "exit_timestamp": pd.Timestamp(self.args.exit_time)
        })


if __name__ == "__main__":
    parser = Parser()
    args = parser.parse_args()
    print("Straddle Config:", parser.get_straddle_config())




    
