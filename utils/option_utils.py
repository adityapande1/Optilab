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
