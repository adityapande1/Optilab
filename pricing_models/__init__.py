from abc import ABC, abstractmethod
from typing import Optional, Dict
import pandas as pd
import swifter
swifter.set_defaults(progress_bar=False)


class OptionPricingModel(ABC):
    def __init__(self):
        self.DEFAULT_RISK_FREE_RATE = 0.065  # 6.5%

    # ---------- ABSTRACT METHODS ----------
    @abstractmethod
    def get_option_price(self, option_type: str, spot: float, strike: float, expiry_timestamp: pd.Timestamp,
                         current_timestamp: pd.Timestamp, volatility: float,
                         risk_free_rate: Optional[float] = None) -> float:
        pass

    @abstractmethod
    def get_iv(self, market_price: float, option_type: str, spot: float, strike: float,
               expiry_timestamp: pd.Timestamp, current_timestamp: pd.Timestamp,
               risk_free_rate: Optional[float] = None) -> float:
        pass

    @abstractmethod
    def get_delta(self, option_type: str, spot: float, strike: float, expiry_timestamp: pd.Timestamp,
                  current_timestamp: pd.Timestamp, volatility: float,
                  risk_free_rate: Optional[float] = None) -> float:
        pass

    @abstractmethod
    def get_gamma(self, option_type: str, spot: float, strike: float, expiry_timestamp: pd.Timestamp,
                  current_timestamp: pd.Timestamp, volatility: float,
                  risk_free_rate: Optional[float] = None) -> float:
        pass

    @abstractmethod
    def get_theta(self, option_type: str, spot: float, strike: float, expiry_timestamp: pd.Timestamp,
                  current_timestamp: pd.Timestamp, volatility: float,
                  risk_free_rate: Optional[float] = None) -> float:
        pass

    @abstractmethod
    def get_vega(self, option_type: str, spot: float, strike: float, expiry_timestamp: pd.Timestamp,
                 current_timestamp: pd.Timestamp, volatility: float,
                 risk_free_rate: Optional[float] = None) -> float:
        pass

    @abstractmethod
    def get_rho(self, option_type: str, spot: float, strike: float, expiry_timestamp: pd.Timestamp,
                current_timestamp: pd.Timestamp, volatility: float,
                risk_free_rate: Optional[float] = None) -> float:
        pass

    # ---------- VECTORIZED VERSIONS ----------

    def get_option_prices_vectorized(self, df: pd.DataFrame):
        assert all(col in df.columns for col in
                   ['option_type', 'spot', 'strike', 'expiry_timestamp', 'current_timestamp', 'volatility']), \
            'Missing required columns for option price calculation'

        return df.swifter.apply(
            lambda row: self.get_option_price(
                option_type=row['option_type'],
                spot=row['spot'],
                strike=row['strike'],
                expiry_timestamp=row['expiry_timestamp'],
                current_timestamp=row['current_timestamp'],
                volatility=row['volatility'],
                risk_free_rate=(row['risk_free_rate']
                                if 'risk_free_rate' in df.columns and pd.notnull(row['risk_free_rate'])
                                else self.DEFAULT_RISK_FREE_RATE),
            ),
            axis=1,
        )

    def get_ivs_vectorized(self, df: pd.DataFrame):
        assert all(col in df.columns for col in
                   ['market_price', 'option_type', 'spot', 'strike', 'expiry_timestamp', 'current_timestamp']), \
            'Missing required columns for implied volatility calculation'

        return df.swifter.apply(
            lambda row: self.get_iv(
                market_price=row['market_price'],
                option_type=row['option_type'],
                spot=row['spot'],
                strike=row['strike'],
                expiry_timestamp=row['expiry_timestamp'],
                current_timestamp=row['current_timestamp'],
                risk_free_rate=(row['risk_free_rate']
                                if 'risk_free_rate' in df.columns and pd.notnull(row['risk_free_rate'])
                                else self.DEFAULT_RISK_FREE_RATE),
            ),
            axis=1,
        )

    def get_deltas_vectorized(self, df: pd.DataFrame):
        assert all(col in df.columns for col in
                   ['option_type', 'spot', 'strike', 'expiry_timestamp', 'current_timestamp', 'volatility']), \
            'Missing required columns for delta calculation'

        return df.swifter.apply(
            lambda row: self.get_delta(
                option_type=row['option_type'],
                spot=row['spot'],
                strike=row['strike'],
                expiry_timestamp=row['expiry_timestamp'],
                current_timestamp=row['current_timestamp'],
                volatility=row['volatility'],
                risk_free_rate=(row['risk_free_rate']
                                if 'risk_free_rate' in df.columns and pd.notnull(row['risk_free_rate'])
                                else self.DEFAULT_RISK_FREE_RATE),
            ),
            axis=1,
        )

    def get_gammas_vectorized(self, df: pd.DataFrame):
        assert all(col in df.columns for col in
                   ['option_type', 'spot', 'strike', 'expiry_timestamp', 'current_timestamp', 'volatility']), \
            'Missing required columns for gamma calculation'

        return df.swifter.apply(
            lambda row: self.get_gamma(
                option_type=row['option_type'],
                spot=row['spot'],
                strike=row['strike'],
                expiry_timestamp=row['expiry_timestamp'],
                current_timestamp=row['current_timestamp'],
                volatility=row['volatility'],
                risk_free_rate=(row['risk_free_rate']
                                if 'risk_free_rate' in df.columns and pd.notnull(row['risk_free_rate'])
                                else self.DEFAULT_RISK_FREE_RATE),
            ),
            axis=1,
        )

    def get_thetas_vectorized(self, df: pd.DataFrame):
        assert all(col in df.columns for col in
                   ['option_type', 'spot', 'strike', 'expiry_timestamp', 'current_timestamp', 'volatility']), \
            'Missing required columns for theta calculation'

        return df.swifter.apply(
            lambda row: self.get_theta(
                option_type=row['option_type'],
                spot=row['spot'],
                strike=row['strike'],
                expiry_timestamp=row['expiry_timestamp'],
                current_timestamp=row['current_timestamp'],
                volatility=row['volatility'],
                risk_free_rate=(row['risk_free_rate']
                                if 'risk_free_rate' in df.columns and pd.notnull(row['risk_free_rate'])
                                else self.DEFAULT_RISK_FREE_RATE),
            ),
            axis=1,
        )

    def get_vegas_vectorized(self, df: pd.DataFrame):
        assert all(col in df.columns for col in
                   ['option_type', 'spot', 'strike', 'expiry_timestamp', 'current_timestamp', 'volatility']), \
            'Missing required columns for vega calculation'

        return df.swifter.apply(
            lambda row: self.get_vega(
                option_type=row['option_type'],
                spot=row['spot'],
                strike=row['strike'],
                expiry_timestamp=row['expiry_timestamp'],
                current_timestamp=row['current_timestamp'],
                volatility=row['volatility'],
                risk_free_rate=(row['risk_free_rate']
                                if 'risk_free_rate' in df.columns and pd.notnull(row['risk_free_rate'])
                                else self.DEFAULT_RISK_FREE_RATE),
            ),
            axis=1,
        )

    def get_rhos_vectorized(self, df: pd.DataFrame):
        assert all(col in df.columns for col in
                   ['option_type', 'spot', 'strike', 'expiry_timestamp', 'current_timestamp', 'volatility']), \
            'Missing required columns for rho calculation'

        return df.swifter.apply(
            lambda row: self.get_rho(
                option_type=row['option_type'],
                spot=row['spot'],
                strike=row['strike'],
                expiry_timestamp=row['expiry_timestamp'],
                current_timestamp=row['current_timestamp'],
                volatility=row['volatility'],
                risk_free_rate=(row['risk_free_rate']
                                if 'risk_free_rate' in df.columns and pd.notnull(row['risk_free_rate'])
                                else self.DEFAULT_RISK_FREE_RATE),
            ),
            axis=1,
        )

    # ---------- VALIDATION & UTILS ----------
    @staticmethod
    def _validate_option_type(option_type: str):
        assert option_type in ('CE', 'PE'), "option_type must be 'CE' (Call European) or 'PE' (Put European)"

    @staticmethod
    def _get_tte_in_years(expiry_timestamp: pd.Timestamp, current_timestamp: pd.Timestamp) -> float:
        """Return time to expiry in years."""
        tte_years = (expiry_timestamp - current_timestamp).total_seconds() / (365 * 24 * 3600)
        assert tte_years >= 0, f'Expiry timestamp ({expiry_timestamp}) must be after or equal to current timestamp ({current_timestamp}).'
        return tte_years

    # ---------- CONVENIENCE METHODS ----------
    def get_model_outputs(
        self,
        option_type: str,
        spot: float,
        strike: float,
        expiry_timestamp: pd.Timestamp,
        current_timestamp: pd.Timestamp,
        volatility: float,
        market_price: Optional[float] = None,
        risk_free_rate: Optional[float] = None,
    ) -> Dict[str, Optional[float]]:
        self._validate_option_type(option_type)
        risk_free_rate = self.DEFAULT_RISK_FREE_RATE if risk_free_rate is None else risk_free_rate

        greeks_and_iv = {
            'theoretical_price': self.get_option_price(option_type, spot, strike, expiry_timestamp, current_timestamp, volatility, risk_free_rate),
            'delta': self.get_delta(option_type, spot, strike, expiry_timestamp, current_timestamp, volatility, risk_free_rate),
            'gamma': self.get_gamma(option_type, spot, strike, expiry_timestamp, current_timestamp, volatility, risk_free_rate),
            'theta': self.get_theta(option_type, spot, strike, expiry_timestamp, current_timestamp, volatility, risk_free_rate),
            'vega': self.get_vega(option_type, spot, strike, expiry_timestamp, current_timestamp, volatility, risk_free_rate),
            'rho': self.get_rho(option_type, spot, strike, expiry_timestamp, current_timestamp, volatility, risk_free_rate),
        }

        if market_price is not None:
            iv_value = self.get_iv(market_price, option_type, spot, strike, expiry_timestamp, current_timestamp, risk_free_rate)
            if iv_value is not None:
                implied_greeks = {
                    'market_price': market_price,
                    'iv': iv_value,
                    'delta_implied': self.get_delta(option_type, spot, strike, expiry_timestamp, current_timestamp, iv_value, risk_free_rate),
                    'gamma_implied': self.get_gamma(option_type, spot, strike, expiry_timestamp, current_timestamp, iv_value, risk_free_rate),
                    'theta_implied': self.get_theta(option_type, spot, strike, expiry_timestamp, current_timestamp, iv_value, risk_free_rate),
                    'vega_implied': self.get_vega(option_type, spot, strike, expiry_timestamp, current_timestamp, iv_value, risk_free_rate),
                    'rho_implied': self.get_rho(option_type, spot, strike, expiry_timestamp, current_timestamp, iv_value, risk_free_rate),
                }
                greeks_and_iv.update(implied_greeks)

        for key, val in greeks_and_iv.items():
            if val is not None and pd.notnull(val):
                greeks_and_iv[key] = float(round(val, 6))

        return greeks_and_iv

    def get_model_output_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        assert all(col in df.columns for col in
                   ['option_type', 'spot', 'strike', 'expiry_timestamp', 'current_timestamp', 'volatility']), \
            'Missing required columns for model output calculation'

        results = {
            'theoretical_price': self.get_option_prices_vectorized(df),
            'delta': self.get_deltas_vectorized(df),
            'gamma': self.get_gammas_vectorized(df),
            'theta': self.get_thetas_vectorized(df),
            'vega': self.get_vegas_vectorized(df),
            'rho': self.get_rhos_vectorized(df),
        }

        if 'market_price' in df.columns:
            results['market_price'] = df['market_price']
            iv_series = self.get_ivs_vectorized(df)
            results['iv'] = iv_series
            df_iv = df.assign(volatility=iv_series)
            results['delta_implied'] = self.get_deltas_vectorized(df_iv)
            results['gamma_implied'] = self.get_gammas_vectorized(df_iv)
            results['theta_implied'] = self.get_thetas_vectorized(df_iv)
            results['vega_implied'] = self.get_vegas_vectorized(df_iv)
            results['rho_implied'] = self.get_rhos_vectorized(df_iv)

        df_results = pd.DataFrame(results, index=df.index)
        df_results = df_results.round(6)
        return df_results
