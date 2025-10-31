from pricing_models import OptionPricingModel
import pandas as pd
from typing import Optional
from math import isnan
from py_vollib.black_scholes import black_scholes
from py_vollib.black_scholes.greeks.analytical import delta, gamma, theta, vega, rho
from py_vollib.black_scholes.implied_volatility import implied_volatility


class PyVollibBSMModel(OptionPricingModel):
    @staticmethod
    def _convert_option_type(option_type: str) -> str:
        """Convert 'CE'/'PE' → 'c'/'p' for py_vollib compatibility."""
        return {'CE': 'c', 'PE': 'p'}[option_type]

    # ---------- INTERNAL UTILS ----------

    def _prepare_inputs(self, option_type: str, expiry: pd.Timestamp, current: pd.Timestamp, risk_free_rate: Optional[float]):
        """Validate inputs and return (flag, tte, r)."""
        self._validate_option_type(option_type)
        flag = self._convert_option_type(option_type)
        r = self.DEFAULT_RISK_FREE_RATE if risk_free_rate is None else risk_free_rate
        tte = self._get_tte_in_years(expiry, current)
        return flag, tte, r

    # ---------- CORE METHODS ----------

    def get_option_price(
        self, option_type: str, spot: float, strike: float, expiry_timestamp: pd.Timestamp, current_timestamp: pd.Timestamp, volatility: float, risk_free_rate: Optional[float] = None
    ) -> float:
        flag, tte, r = self._prepare_inputs(option_type, expiry_timestamp, current_timestamp, risk_free_rate)
        return black_scholes(flag, spot, strike, tte, r, volatility)

    def get_iv(
        self, market_price: float, option_type: str, spot: float, strike: float, expiry_timestamp: pd.Timestamp, current_timestamp: pd.Timestamp, risk_free_rate: Optional[float] = None
    ) -> Optional[float]:
        flag, tte, r = self._prepare_inputs(option_type, expiry_timestamp, current_timestamp, risk_free_rate)
        try:
            iv = implied_volatility(market_price, spot, strike, tte, r, flag)
            return None if isnan(iv) else iv
        except Exception:
            return None

    def get_delta(
        self, option_type: str, spot: float, strike: float, expiry_timestamp: pd.Timestamp, current_timestamp: pd.Timestamp, volatility: float, risk_free_rate: Optional[float] = None
    ) -> float:
        flag, tte, r = self._prepare_inputs(option_type, expiry_timestamp, current_timestamp, risk_free_rate)
        return delta(flag, spot, strike, tte, r, volatility)

    def get_gamma(
        self, option_type: str, spot: float, strike: float, expiry_timestamp: pd.Timestamp, current_timestamp: pd.Timestamp, volatility: float, risk_free_rate: Optional[float] = None
    ) -> float:
        flag, tte, r = self._prepare_inputs(option_type, expiry_timestamp, current_timestamp, risk_free_rate)
        return gamma(flag, spot, strike, tte, r, volatility)

    def get_theta(
        self, option_type: str, spot: float, strike: float, expiry_timestamp: pd.Timestamp, current_timestamp: pd.Timestamp, volatility: float, risk_free_rate: Optional[float] = None
    ) -> float:
        flag, tte, r = self._prepare_inputs(option_type, expiry_timestamp, current_timestamp, risk_free_rate)
        return theta(flag, spot, strike, tte, r, volatility)

    def get_vega(
        self, option_type: str, spot: float, strike: float, expiry_timestamp: pd.Timestamp, current_timestamp: pd.Timestamp, volatility: float, risk_free_rate: Optional[float] = None
    ) -> float:
        flag, tte, r = self._prepare_inputs(option_type, expiry_timestamp, current_timestamp, risk_free_rate)
        return vega(flag, spot, strike, tte, r, volatility)

    def get_rho(
        self, option_type: str, spot: float, strike: float, expiry_timestamp: pd.Timestamp, current_timestamp: pd.Timestamp, volatility: float, risk_free_rate: Optional[float] = None
    ) -> float:
        flag, tte, r = self._prepare_inputs(option_type, expiry_timestamp, current_timestamp, risk_free_rate)
        return rho(flag, spot, strike, tte, r, volatility)
