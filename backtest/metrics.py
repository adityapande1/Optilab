"""
Mostly contains the functions used in evaluating backtest strategies.
"""
import pandas as pd
from backtest.backtest_analyzer import BacktestAnalyzer
import quantstats as qs  

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
        self.metrics = {}
        self._update_all_metrics()

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


    def _update_all_metrics(self):

        # Day Count & Trade Count Metrics
        self.metrics['total_days'] = {
            'help':'Total number of trading days',
            'value': len(self.df_portfolio_metrics_daily.index.normalize().unique())
        }
        self.metrics['positive_days'] = {
            'help':'Number of days with positive returns',
            'value': (self.df_portfolio_metrics_daily['daily_return'] > 0).sum()
        }
        self.metrics['negative_days'] = {
            'help':'Number of days with negative returns (including zero return days)',
            'value': (self.df_portfolio_metrics_daily['daily_return'] <= 0).sum()
        }
        self.metrics['win_rate'] = {
            'help':'The ratio of positive returns to total non-zero returns, providing a measure of how often the strategy generates profits.',
            'value': qs.stats.win_rate(returns=self.df_portfolio_metrics_daily['daily_return'])
        }
        self.metrics['win_loss_ratio'] = {
            'help' : ' (average win / average loss) : The ratio of average winning returns to average losing returns, providing insight into the reward-to-risk profile of individual trades or periods.',
            'value': qs.stats.win_loss_ratio(returns=self.df_portfolio_metrics_daily['daily_return'])
        }
        self.metrics['max_win_streak'] = {
            'help':'Maximum number of consecutive winning periods. The longest streak of positive returns, which helps assess the consistency of positive performance.',
            'value': qs.stats.consecutive_wins(returns=self.df_portfolio_metrics_daily['daily_return'])
        }
        self.metrics['max_loss_streak'] = {
            'help':'Maximum number of consecutive losing periods. The longest streak of negative returns, which helps assess the risk of prolonged drawdowns.',
            'value': qs.stats.consecutive_losses(returns=self.df_portfolio_metrics_daily['daily_return'])
        }
        self.metrics['highest_return'] = {
            'help':'Best (highest) daily return',
            'value': qs.stats.best(returns=self.df_portfolio_metrics_daily['daily_return'])
        }
        self.metrics['lowest_return'] = {
            'help':'Worst (lowest) daily return',
            'value': qs.stats.worst(returns=self.df_portfolio_metrics_daily['daily_return'])
        }


        # Drawdown details
        dd_series = qs.stats.to_drawdown_series(self.df_portfolio_metrics_daily['daily_return'])
        dd_details = qs.stats.drawdown_details(dd_series).sort_values(by='max drawdown',ascending=True)
        # Reindex from 0 --> 
        dd_details.index = range(len(dd_details))
        self.metrics['df_drawdown'] = {
            'help':'Detailed statistics about drawdowns, including duration and recovery time.',
            'value': dd_details
        }


        # Ratios
        self.metrics['sharpe_ratio'] = {
            'help':'The Sharpe ratio measures risk-adjusted returns by dividing excess returns (returns - risk-free rate) by the standard deviation of returns. Higher values indicate better risk-adjusted performance.',
            'value': qs.stats.sharpe(returns=self.df_portfolio_metrics_daily['daily_return'], rf=0.0)
        }
        self.metrics['sortino_ratio'] = {
            'help':'The Sortino ratio is a variation of the Sharpe ratio that focuses only on downside volatility. It is calculated by dividing excess returns by the standard deviation of negative returns. Higher values indicate better risk-adjusted performance with a focus on downside risk.',
            'value': qs.stats.sortino(returns=self.df_portfolio_metrics_daily['daily_return'], rf=0.0)
        }
        self.metrics['daily_VaR'] = {
            'help':'The daily Value at Risk (VaR) estimates the maximum expected loss over a one-day horizon at a specified confidence level[95%], using the variance-covariance method.',
            'value': float(qs.stats.value_at_risk(self.df_portfolio_metrics_daily['daily_return'], confidence=0.95))
        }
        self.metrics['cagr'] = {
            'help':'The Compound Annual Growth Rate (CAGR) represents the mean annual growth rate of an investment over a specified period of time, assuming the profits are reinvested at the end of each period. It provides a smoothed annualized return that accounts for compounding effects.',
            'value': qs.stats.cagr(returns=self.df_portfolio_metrics_daily['daily_return'])
        }
        self.metrics['recovery_factor'] = {
            'help':'The recovery factor measures how quickly a strategy recovers from drawdowns by comparing total returns to the maximum drawdown experienced. Higher values indicate better recovery characteristics.',
            'value': float(qs.stats.recovery_factor(self.df_portfolio_metrics_daily['daily_return']))
        }
        self.metrics['gain_to_pain_ratio'] = {
            'help':'Jack Schwager\'s Gain-to-Pain Ratio (GPR) measures the total gains divided by the total losses, providing a simple measure of how much profit is generated per unit of loss. Higher values indicate better performance.',
            'value': float(qs.stats.gain_to_pain_ratio(self.df_portfolio_metrics_daily['daily_return']))
        }
        self.metrics['avg_win'] = {
            'help':'Average of positive returns, indicating the typical size of winning periods.',
            'value': qs.stats.avg_win(returns=self.df_portfolio_metrics_daily['daily_return'])
        }
        self.metrics['avg_loss'] = {
            'help':'Average of negative returns, indicating the typical size of losing periods.',
            'value': qs.stats.avg_loss(returns=self.df_portfolio_metrics_daily['daily_return'])
        }
        




        

    


