"""
Utility helper functions for data processing and formatting.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List
import pandas as pd
import numpy as np


def normalize_symbol(symbol: str) -> str:
    """Normalize symbol to uppercase format."""
    return symbol.strip().upper()


def current_timestamp() -> str:
    """Get current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def parse_timestamp(ts: Any) -> datetime:
    """Parse various timestamp formats to datetime object."""
    if isinstance(ts, datetime):
        return ts
    elif isinstance(ts, (int, float)):
        # Assume milliseconds
        return datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
    elif isinstance(ts, str):
        return pd.to_datetime(ts, utc=True).to_pydatetime()
    else:
        raise ValueError(f"Cannot parse timestamp: {ts}")


def format_timestamp(dt: datetime) -> str:
    """Format datetime to ISO string."""
    if not dt.tzinfo:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def resample_to_ohlcv(
    ticks: List[Dict[str, Any]],
    timeframe: str
) -> pd.DataFrame:
    """
    Resample tick data to OHLCV format.
    
    Args:
        ticks: List of tick dictionaries with 'ts', 'price', 'qty'
        timeframe: Pandas resample rule (e.g., '1s', '1min', '5min')
    
    Returns:
        DataFrame with OHLCV columns
    """
    if not ticks:
        return pd.DataFrame(columns=['ts', 'open', 'high', 'low', 'close', 'volume'])
    
    # Convert to DataFrame
    df = pd.DataFrame(ticks)
    df['ts'] = pd.to_datetime(df['ts'], utc=True, format='ISO8601')
    df['price'] = df['price'].astype(float)
    df['qty'] = df['qty'].astype(float)
    
    # Set timestamp as index
    df = df.set_index('ts')
    
    # Resample to OHLCV
    ohlcv = df['price'].resample(timeframe).ohlc()
    ohlcv['volume'] = df['qty'].resample(timeframe).sum(min_count=1)
    
    # Drop periods with no price information
    ohlcv = ohlcv.dropna(how='all')
    
    if ohlcv.empty:
        return pd.DataFrame(columns=['ts', 'open', 'high', 'low', 'close', 'volume'])

    # Replace zero or missing price values and forward/back fill
    price_cols = ['open', 'high', 'low', 'close']
    ohlcv[price_cols] = ohlcv[price_cols].replace(0, np.nan)
    ohlcv[price_cols] = ohlcv[price_cols].ffill().bfill()

    # Ensure price hierarchy consistency after filling
    ohlcv['high'] = ohlcv[price_cols].max(axis=1)
    ohlcv['low'] = ohlcv[price_cols].min(axis=1)
    
    # Fill missing volumes with zero
    ohlcv['volume'] = ohlcv['volume'].fillna(0.0)
    
    # Reset index
    ohlcv = ohlcv.reset_index()
    ohlcv.columns = ['ts', 'open', 'high', 'low', 'close', 'volume']
    
    # Convert timestamp to ISO string
    ohlcv['ts'] = ohlcv['ts'].apply(lambda x: x.isoformat())
    
    return ohlcv


def calculate_returns(prices: pd.Series) -> pd.Series:
    """Calculate log returns from price series."""
    return np.log(prices / prices.shift(1))


def safe_division(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safely divide with default value for zero denominator."""
    if denominator == 0 or np.isnan(denominator) or np.isnan(numerator):
        return default
    return numerator / denominator


def timeframe_to_seconds(tf: str) -> int:
    """Convert timeframe string to seconds."""
    mapping = {
        '1s': 1,
        '1m': 60,
        '5m': 300,
        '15m': 900,
        '1h': 3600,
        '1d': 86400,
    }
    return mapping.get(tf.lower(), 60)


def timeframe_to_pandas_rule(tf: str) -> str:
    """Convert timeframe string to pandas resample rule."""
    mapping = {
        '1s': '1s',
        '1m': '1min',
        '5m': '5min',
        '15m': '15min',
        '1h': '1h',
        '1d': '1d',
    }
    return mapping.get(tf.lower(), '1min')
