"""
Analytics engine for quantitative trading calculations.
Computes hedge ratios, spreads, z-scores, correlations, and statistical tests.
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from scipy import stats
from statsmodels.tsa.stattools import adfuller
from statsmodels.regression.linear_model import OLS
from sklearn.linear_model import HuberRegressor, TheilSenRegressor

from utils import log, safe_division
from core.data_manager import data_manager


class AnalyticsEngine:
    """
    Quantitative analytics calculations for pair trading strategies.
    
    Supports:
    - Hedge ratio estimation (OLS, Huber, Theil-Sen, Kalman)
    - Spread calculation and z-score normalization
    - Rolling correlation
    - Augmented Dickey-Fuller stationarity test
    - Risk metrics and performance statistics
    """
    
    def __init__(self):
        """Initialize analytics engine."""
        log.info("Analytics Engine initialized")
    
    def compute_hedge_ratio(
        self,
        symbol_a: str,
        symbol_b: str,
        timeframe: str = "1m",
        window: int = 60,
        method: str = "OLS"
    ) -> List[Dict[str, Any]]:
        """
        Compute rolling hedge ratio between two symbols.
        
        Args:
            symbol_a: First symbol (dependent variable)
            symbol_b: Second symbol (independent variable)
            timeframe: Data timeframe
            window: Rolling window size
            method: Regression method (OLS, Huber, Theil-Sen, Kalman)
            
        Returns:
            List of {ts, value} dictionaries
        """
        # Get price series
        prices_a = data_manager.get_price_series(
            symbol_a,
            timeframe,
            limit=max(window * 3, window + 20),
            force_resample=True,
        )
        prices_b = data_manager.get_price_series(
            symbol_b,
            timeframe,
            limit=max(window * 3, window + 20),
            force_resample=True,
        )
        
        if min(len(prices_a), len(prices_b)) < 2:
            log.warning(
                "Not enough price data for hedge ratio: {}/{} window={} len_a={} len_b={}",
                symbol_a,
                symbol_b,
                window,
                len(prices_a),
                len(prices_b),
            )
            return []
        
        # Align series
        df = pd.DataFrame({'a': prices_a, 'b': prices_b}).dropna()
        
        if len(df) < 2:
            log.warning(
                "Aligned price frame too small for hedge ratio: {}/{} window={} len_df={}",
                symbol_a,
                symbol_b,
                window,
                len(df),
            )
            return []

        effective_window = min(window, len(df))

        if effective_window < window:
            log.debug(
                "Using reduced window for hedge ratio: {}/{} requested={} effective={}",
                symbol_a,
                symbol_b,
                window,
                effective_window,
            )
        
        hedge_ratios = []
        
        # Rolling window calculation
        for i in range(effective_window, len(df) + 1):
            window_data = df.iloc[i-effective_window:i]
            
            try:
                if method.upper() == "OLS":
                    ratio = self._ols_hedge_ratio(
                        window_data['a'].values,
                        window_data['b'].values
                    )
                elif method.upper() == "HUBER":
                    ratio = self._huber_hedge_ratio(
                        window_data['a'].values,
                        window_data['b'].values
                    )
                elif method.upper() == "THEIL-SEN":
                    ratio = self._theilsen_hedge_ratio(
                        window_data['a'].values,
                        window_data['b'].values
                    )
                elif method.upper() == "KALMAN":
                    # Simplified Kalman - use OLS for now
                    ratio = self._ols_hedge_ratio(
                        window_data['a'].values,
                        window_data['b'].values
                    )
                else:
                    ratio = 1.0
                
                hedge_ratios.append({
                    "ts": window_data.index[-1].isoformat(),
                    "value": float(ratio)
                })
            except Exception as e:
                log.error(f"Error computing hedge ratio at index {i}: {e}")
                continue
        
        return hedge_ratios
    
    def _ols_hedge_ratio(self, y: np.ndarray, x: np.ndarray) -> float:
        """OLS regression to compute hedge ratio."""
        x_with_const = np.column_stack([np.ones(len(x)), x])
        model = OLS(y, x_with_const).fit()
        return model.params[1]
    
    def _huber_hedge_ratio(self, y: np.ndarray, x: np.ndarray) -> float:
        """Huber regression (robust) to compute hedge ratio."""
        x_reshaped = x.reshape(-1, 1)
        model = HuberRegressor().fit(x_reshaped, y)
        return model.coef_[0]
    
    def _theilsen_hedge_ratio(self, y: np.ndarray, x: np.ndarray) -> float:
        """Theil-Sen regression to compute hedge ratio."""
        x_reshaped = x.reshape(-1, 1)
        model = TheilSenRegressor(random_state=42).fit(x_reshaped, y)
        return model.coef_[0]
    
    def compute_spread(
        self,
        symbol_a: str,
        symbol_b: str,
        timeframe: str = "1m",
        window: int = 60,
        method: str = "OLS"
    ) -> List[Dict[str, Any]]:
        """
        Compute spread between two symbols using hedge ratio.
        
        Spread = Price_A - (Hedge_Ratio * Price_B)
        
        Args:
            symbol_a: First symbol
            symbol_b: Second symbol
            timeframe: Data timeframe
            window: Rolling window for hedge ratio
            method: Regression method
            
        Returns:
            List of {ts, value} dictionaries
        """
        # Get hedge ratios
        hedge_ratios = self.compute_hedge_ratio(
            symbol_a, symbol_b, timeframe, window, method
        )
        
        if not hedge_ratios:
            log.warning(
                "No hedge ratios computed for spread: {}/{} window={}",
                symbol_a,
                symbol_b,
                window,
            )
            return []
        
        # Get price series
        prices_a = data_manager.get_price_series(
            symbol_a,
            timeframe,
            limit=max(window * 3, window + 20),
            force_resample=True,
        )
        prices_b = data_manager.get_price_series(
            symbol_b,
            timeframe,
            limit=max(window * 3, window + 20),
            force_resample=True,
        )
        
        # Compute spread
        spreads = []
        for hr in hedge_ratios:
            ts = pd.Timestamp(hr["ts"])
            
            if ts not in prices_a.index or ts not in prices_b.index:
                continue
            
            spread = prices_a[ts] - (hr["value"] * prices_b[ts])
            
            spreads.append({
                "ts": ts.isoformat(),
                "value": float(spread)
            })
        
        return spreads
    
    def compute_zscore(
        self,
        symbol_a: str,
        symbol_b: str,
        timeframe: str = "1m",
        window: int = 60,
        method: str = "OLS"
    ) -> List[Dict[str, Any]]:
        """
        Compute z-score of the spread.
        
        Z-Score = (Spread - Mean(Spread)) / StdDev(Spread)
        
        Args:
            symbol_a: First symbol
            symbol_b: Second symbol
            timeframe: Data timeframe
            window: Rolling window size
            method: Regression method
            
        Returns:
            List of {ts, value} dictionaries
        """
        spreads = self.compute_spread(symbol_a, symbol_b, timeframe, window, method)
        
        if len(spreads) < 2:
            log.warning(
                "Insufficient spread history for zscore: {}/{} window={} len_spreads={}",
                symbol_a,
                symbol_b,
                window,
                len(spreads),
            )
            return []
        
        # Convert to pandas Series
        df = pd.DataFrame(spreads)
        df['ts'] = pd.to_datetime(df['ts'])
        df = df.set_index('ts')

        effective_window = min(window, len(df))

        if effective_window < window:
            log.debug(
                "Using reduced window for zscore: {}/{} requested={} effective={}",
                symbol_a,
                symbol_b,
                window,
                effective_window,
            )
        
        # Rolling z-score
        rolling_mean = df['value'].rolling(window=effective_window, min_periods=effective_window).mean()
        rolling_std = df['value'].rolling(window=effective_window, min_periods=effective_window).std()
        
        z_scores = []
        for idx in df.index:
            if pd.notna(rolling_mean[idx]) and pd.notna(rolling_std[idx]):
                zscore = safe_division(
                    df['value'][idx] - rolling_mean[idx],
                    rolling_std[idx],
                    default=0.0
                )
                z_scores.append({
                    "ts": idx.isoformat(),
                    "value": float(zscore)
                })
        
        return z_scores
    
    def compute_rolling_correlation(
        self,
        symbol_a: str,
        symbol_b: str,
        timeframe: str = "1m",
        window: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Compute rolling correlation between two symbols.
        
        Args:
            symbol_a: First symbol
            symbol_b: Second symbol
            timeframe: Data timeframe
            window: Rolling window size
            
        Returns:
            List of {ts, value} dictionaries
        """
        # Get price series
        prices_a = data_manager.get_price_series(
            symbol_a,
            timeframe,
            limit=max(window * 3, window + 20),
            force_resample=True,
        )
        prices_b = data_manager.get_price_series(
            symbol_b,
            timeframe,
            limit=max(window * 3, window + 20),
            force_resample=True,
        )
        
        # Align series
        df = pd.DataFrame({'a': prices_a, 'b': prices_b}).dropna()
        
        if len(df) < 2:
            log.warning(
                "Insufficient overlapping prices for rolling corr: {}/{} window={} len_df={}",
                symbol_a,
                symbol_b,
                window,
                len(df),
            )
            return []

        effective_window = min(window, len(df))

        if effective_window < window:
            log.debug(
                "Using reduced window for rolling corr: {}/{} requested={} effective={}",
                symbol_a,
                symbol_b,
                window,
                effective_window,
            )
        
        # Rolling correlation
        rolling_corr = df['a'].rolling(
            window=effective_window,
            min_periods=effective_window,
        ).corr(df['b'])
        
        correlations = []
        for idx, corr in rolling_corr.items():
            if pd.notna(corr):
                correlations.append({
                    "ts": idx.isoformat(),
                    "value": float(corr)
                })
        
        return correlations
    
    def compute_adf_test(
        self,
        symbol_a: str,
        symbol_b: str,
        timeframe: str = "1m",
        window: int = 60,
        method: str = "OLS"
    ) -> Dict[str, float]:
        """
        Perform Augmented Dickey-Fuller test on the spread.
        Tests for stationarity (mean reversion).
        
        Args:
            symbol_a: First symbol
            symbol_b: Second symbol
            timeframe: Data timeframe
            window: Window for hedge ratio
            method: Regression method
            
        Returns:
            Dict with pvalue and stat
        """
        spreads = self.compute_spread(symbol_a, symbol_b, timeframe, window, method)
        
        if len(spreads) < 20:  # Minimum required for ADF test
            return {"pvalue": 1.0, "stat": 0.0}
        
        # Extract spread values
        spread_values = [s["value"] for s in spreads]
        
        try:
            # Perform ADF test
            result = adfuller(spread_values, autolag='AIC')
            
            return {
                "stat": float(result[0]),      # Test statistic
                "pvalue": float(result[1]),    # P-value
            }
        except Exception as e:
            log.error(f"Error in ADF test: {e}")
            return {"pvalue": 1.0, "stat": 0.0}
    
    def compute_pair_analytics(
        self,
        pair: str,
        timeframe: str = "1m",
        window: int = 60,
        regression: str = "OLS"
    ) -> Dict[str, Any]:
        """
        Compute comprehensive analytics for a trading pair.
        
        Args:
            pair: Pair string in format "SYMBOL_A-SYMBOL_B"
            timeframe: Data timeframe
            window: Rolling window size
            regression: Regression method
            
        Returns:
            Dict with all analytics (hedge_ratio, spread, zscore, correlation, adf)
        """
        # Parse pair
        try:
            symbol_a, symbol_b = pair.split("-")
        except ValueError:
            log.error(f"Invalid pair format: {pair}")
            return {}
        
        log.info(f"Computing analytics for {pair} @ {timeframe}")
        
        try:
            # Compute all analytics
            hedge_ratio = self.compute_hedge_ratio(
                symbol_a, symbol_b, timeframe, window, regression
            )
            spread = self.compute_spread(
                symbol_a, symbol_b, timeframe, window, regression
            )
            zscore = self.compute_zscore(
                symbol_a, symbol_b, timeframe, window, regression
            )
            rolling_corr = self.compute_rolling_correlation(
                symbol_a, symbol_b, timeframe, window
            )
            adf = self.compute_adf_test(
                symbol_a, symbol_b, timeframe, window, regression
            )
            
            return {
                "pair": pair,
                "hedge_ratio": hedge_ratio,
                "spread": spread,
                "zscore": zscore,
                "rolling_corr": rolling_corr,
                "adf": adf,
            }
        except Exception as e:
            log.error(f"Error computing pair analytics: {e}")
            return {"pair": pair, "error": str(e)}


# Global analytics engine instance
analytics_engine = AnalyticsEngine()
