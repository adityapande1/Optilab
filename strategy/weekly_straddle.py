import copy
from datetime import datetime
from typing import Union

import pandas as pd
from rich import print

from connectors.dbconnector import DBConnector
from strategy import Action, Strategy


class WeeklyStraddle(Strategy):
    def __init__(self, config, dbconnector: DBConnector):
        super().__init__(config, dbconnector)

        assert self.config.long_or_short in ["long", "short"], f"Position must be either 'long' or 'short'. Given {self.config.long_or_short}"

        # Straddle Params
        self.name = self.__class__.__name__
        self.strike = None  # Will be set at the time of action

        self.entry_ts_to_exit_ts_map = self._get_entry_ts_to_exit_ts_map()
        self.latest_entry_timestamp = None

    def _get_entry_ts_to_exit_ts_map(self) -> dict[pd.Timestamp, pd.Timestamp]:

        entry_ts_to_exit_ts_map = {}
        df_spot = self.dbconnector.df_spot
        all_available_expiry_dates = self.dbconnector.get_all_available_expiry_dates()
        exit_timestamps_series = [pd.Timestamp.combine(datetime.strptime(expiry_date, '%Y-%m-%d').date(), self.config.exit_time) for expiry_date in all_available_expiry_dates]
        exit_timestamps_series = pd.Series(exit_timestamps_series).sort_values()

        for expiry_date in all_available_expiry_dates:
            next_traded_date_after_expiry = df_spot[df_spot.index >= pd.to_datetime(expiry_date) + pd.DateOffset(days=1)].index[0].date()
            entry_timestamp = pd.Timestamp.combine(next_traded_date_after_expiry, self.config.entry_time)
            exit_timestamp_series_filtered = exit_timestamps_series[exit_timestamps_series >= entry_timestamp]

            if not exit_timestamp_series_filtered.empty:
                exit_timestamp = exit_timestamp_series_filtered.iloc[0]
                entry_ts_to_exit_ts_map[entry_timestamp] = exit_timestamp

        return entry_ts_to_exit_ts_map

    def action(self, timestamp: pd.Timestamp) -> list[Action] | None:

        actions = None

        if timestamp in self.entry_ts_to_exit_ts_map:

            self.strike = self.dbconnector.get_ATM_strike(timestamp)
            closest_expiry = self.dbconnector.get_closest_expiry(timestamp)
            atm_call_action = Action(option_type="CE", strike=self.strike, expiry=closest_expiry, num_lots=1, trade_type=self.config.long_or_short, order_type=self.config.call_order_type, stoploss=self.config.call_risk)
            atm_put_action = Action(option_type="PE", strike=self.strike, expiry=closest_expiry, num_lots=1, trade_type=self.config.long_or_short, order_type=self.config.put_order_type, stoploss=self.config.put_risk)
            actions = [atm_call_action, atm_put_action]
            self.latest_entry_timestamp = timestamp

        elif timestamp == self.entry_ts_to_exit_ts_map.get(self.latest_entry_timestamp, None):
            actions = self.square_off_actions()
            self.latest_entry_timestamp = None

        return actions

    def about(self) -> str:
        about_str = "Weekly Straddle Strategy"
        return about_str

