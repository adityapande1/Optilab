import datetime
import os

def get_closest_expiry(df_instruments):
    
    unique_expiries = df_instruments[
        (df_instruments['name'] == 'NIFTY') & (df_instruments['instrument_type'] == 'CE')
    ].expiry.unique()
    unique_expiries = sorted(unique_expiries)
    return unique_expiries[0] if unique_expiries else None


def get_strike_list(central_price, range_pct=4, strike_gap=50):
    """
    Given an OHLC dataframe and a percentage range, returns the lower and upper strike limits and the strike list.
    """
    range_val = central_price * (range_pct / 100.0)
    lower_limit = ((central_price - range_val) // strike_gap) * strike_gap - strike_gap
    lower_limit = int(lower_limit)
    upper_limit = ((central_price + range_val) // strike_gap) * strike_gap + strike_gap
    upper_limit = int(upper_limit)
    strike_list = list(range(lower_limit, upper_limit + strike_gap, strike_gap))
    return strike_list

