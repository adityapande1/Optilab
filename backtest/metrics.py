"""
Mostly contains the functions used in evaluating backtest strategies.
"""
import pandas as pd
from backtest.backtest_analyzer import BacktestAnalyzer

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


class MetricEngine:
    def __init__(self, btanalyzer: BacktestAnalyzer, initial_capital: float):
        self.btanalyzer = btanalyzer
        self.initial_capital = initial_capital
        self.df_portfolio_metrics = self.btanalyzer.get_df_portfolio_metrics()
        self.df_portfolio_metrics_daily = self.make_daily_df(self.df_portfolio_metrics, self.initial_capital)

    def make_daily_df(self, df: pd.DataFrame, initial_capital: float) -> pd.DataFrame:

        assert 'pnl' in df.columns, "DataFrame must contain 'pnl' column"
        portfolio_value = initial_capital + df['pnl']
        df_daily = (
            portfolio_value
            .resample('1D')               # (1) group data into 1-day buckets
            .last()                       # (2) pick the last value in each day (EOD portfolio value)
            .dropna()                     # (3) remove days that don’t have any data (holidays, weekends, etc.)
            .to_frame('portfolio_value')  # (4) turn the Series back into a DataFrame with this column name
        )

        # daily returns with initial capital as baseline
        df_daily['daily_return'] = df_daily['portfolio_value'].pct_change()
        first_day_return = (df_daily['portfolio_value'].iloc[0] - initial_capital) / initial_capital
        df_daily.loc[df_daily.index[0], 'daily_return'] = first_day_return
        return df_daily


    def get_all_metrics(self):

        pass



