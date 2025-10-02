from typing import Union


def intrinsic_value(option_type: str, strike: Union[int, float], underlying_price: Union[int, float]) -> float:
    """
    Calculate the intrinsic value of an option.

    Args
    ________
        option_type (str): 'CE' for Call Option, 'PE' for Put Option
        strike (int | float): Strike price of the option
        underlying_price (int | float): Current price of the underlying asset
    Returns
    ________
        float: The intrinsic value of the option
    """

    assert option_type in ('CE', 'PE'), "option_type must be 'CE' or 'PE'"
    assert strike > 0, 'strike must be positive'
    assert underlying_price > 0, 'underlying_price must be positive'

    if option_type == 'CE':
        return max(0, underlying_price - strike)
    else:  # 'PE'
        return max(0, strike - underlying_price)


def get_lower_upper_strikes_around_spot(spot: float, strike_interval: int = 50, width: int = 100):
    """
    Get the `lower_strike` and `upper_strike` such that the midpoint [(lower_strike + upper_strike) / 2] is as close to the `spot` price as possible, and the distance between lower and upper strikes is equal to `width`.

    Args
    ----
    spot (float) : Current underlying price.
    strike_interval (int) : Distance between consecutive strikes in the option chain (e.g., 50 in NIFTY).
    width (int) : Distance between upper and lower strikes  = | upper_strike - lower_strike | (e.g., 150).

    Returns
    -----
    lower_strike (int) : Selected lower strike price.
    upper_strike (int) : Selected upper strike price.
    """
    if spot % strike_interval == 0:
        spot -= 1e-6  # avoid edge-case ambiguity

    approx_lower = spot - width / 2
    lower_strike = round(approx_lower / strike_interval) * strike_interval
    upper_strike = lower_strike + width

    return lower_strike, upper_strike
