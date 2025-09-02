"""
Mostly contains the functions used in evaluating backtest strategies.
"""
import pandas as pd


def update_metric_pnl(
    df: pd.DataFrame,
    trade_type: str,
    lot_size: int,
    per_lot_transaction_cost: float = 0,
    num_lots: int = 1
) -> None:
    assert trade_type in ("long", "short"), "trade_type must be 'long' or 'short'"
    assert lot_size > 0, "lot_size must be positive"
    assert 'price' in df.columns, "DataFrame must contain 'price' column"
    assert per_lot_transaction_cost >= 0, "per_lot_transaction_cost must be non-negative"
    assert num_lots > 0, "num_lots must be positive"

    # --- Gross PnL from price movement ---
    df.loc[:, 'gross_step_pnl'] = df['price'].diff() * lot_size * num_lots
    if trade_type == "short":
        df.loc[:, 'gross_step_pnl'] = -df['gross_step_pnl']

    # --- Transaction costs (open + close) ---
    df.loc[:, 'transaction_cost'] = 0.0
    df.loc[df.index[0], 'transaction_cost'] = per_lot_transaction_cost * num_lots   # open leg
    df.loc[df.index[-1], 'transaction_cost'] += per_lot_transaction_cost * num_lots # close leg # Note that += takes care of the rare case of a single-row DataFrame

    # --- Net interval PnL ---
    df.loc[:, 'net_step_pnl'] = df['gross_step_pnl'].fillna(0) - df['transaction_cost']

    # --- Cumulative PnL ---
    df.loc[:, 'pnl'] = df['net_step_pnl'].cumsum()







