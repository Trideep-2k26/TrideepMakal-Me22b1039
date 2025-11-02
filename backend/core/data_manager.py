"""
Data Manager for tick buffering, resampling, and storage.
Maintains in-memory tick buffers with Redis caching layer.
"""
import asyncio
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import pandas as pd
from threading import Lock

from utils import (
    log,
    normalize_symbol,
    resample_to_ohlcv,
    timeframe_to_pandas_rule,
    settings,
)


class DataManager:
    """
    Manages tick data buffering and resampling for multiple symbols.
    
    Features:
    - Redis-first caching for tick data (when enabled)
    - Fallback in-memory buffers (deques)
    - Real-time OHLCV resampling (1s, 1m, 5m)
    - Thread-safe operations
    - Automatic Redis persistence
    """
    
    def __init__(self):
        """Initialize data manager with empty buffers."""
        # Tick buffers: symbol -> deque of tick dicts (fallback)
        self.tick_buffers: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=settings.tick_buffer_size)
        )
        
        # Resampled OHLCV cache: (symbol, timeframe) -> DataFrame
        self.ohlcv_cache: Dict[tuple, pd.DataFrame] = {}
        
        # Locks for thread-safe operations
        self.tick_locks: Dict[str, Lock] = defaultdict(Lock)
        self.ohlcv_lock = Lock()
        
        # Statistics
        self.tick_counts: Dict[str, int] = defaultdict(int)
        self.last_tick_time: Dict[str, datetime] = {}
        
        log.info("Data Manager initialized (in-memory mode)")
    
    async def add_tick(self, tick: Dict[str, Any]):
        """
        Add a new tick to the buffer.
        
        Args:
            tick: Dict with keys: symbol, price, qty, ts
        """
        symbol = normalize_symbol(tick["symbol"])
        
        # Store in memory
        with self.tick_locks[symbol]:
            self.tick_buffers[symbol].append(tick)
            self.tick_counts[symbol] += 1
            self.last_tick_time[symbol] = datetime.now(timezone.utc)
        
        # Log every 1000 ticks
        if self.tick_counts[symbol] % 1000 == 0:
            log.debug(f"{symbol}: {self.tick_counts[symbol]} ticks received")
    
    async def get_ticks(
        self,
        symbol: str,
        limit: Optional[int] = None,
        from_ts: Optional[str] = None,
        to_ts: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get tick data for a symbol with optional filters.
        
        Args:
            symbol: Trading symbol
            limit: Maximum number of ticks to return (most recent)
            from_ts: ISO timestamp to filter from
            to_ts: ISO timestamp to filter to
            
        Returns:
            List of tick dictionaries
        """
        symbol = normalize_symbol(symbol)
        
        # Get from memory
        with self.tick_locks[symbol]:
            ticks = list(self.tick_buffers[symbol])
        
        # Apply time filters
        if from_ts:
            ticks = [t for t in ticks if t["ts"] >= from_ts]
        if to_ts:
            ticks = [t for t in ticks if t["ts"] <= to_ts]
        
        # Apply limit
        if limit:
            ticks = ticks[-limit:]
        
        return ticks
    
    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1m",
        limit: Optional[int] = None,
        from_ts: Optional[str] = None,
        to_ts: Optional[str] = None,
        force_resample: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get OHLCV data for a symbol by resampling ticks.
        
        Args:
            symbol: Trading symbol
            timeframe: Resample timeframe (1s, 1m, 5m)
            limit: Maximum number of candles to return
            from_ts: ISO timestamp to filter from
            to_ts: ISO timestamp to filter to
            force_resample: Force resampling even if cached
            
        Returns:
            List of OHLCV dictionaries
        """
        symbol = normalize_symbol(symbol)
        cache_key = (symbol, timeframe)
        
        # Check memory cache
        if not force_resample and cache_key in self.ohlcv_cache:
            df = self.ohlcv_cache[cache_key]
        else:
            # Get ticks and resample
            ticks = await self.get_ticks(symbol, from_ts=from_ts, to_ts=to_ts)
            
            if not ticks:
                return []
            
            # Convert timeframe to pandas rule
            pandas_rule = timeframe_to_pandas_rule(timeframe)
            df = resample_to_ohlcv(ticks, pandas_rule)
            
            # Cache the result in memory
            with self.ohlcv_lock:
                self.ohlcv_cache[cache_key] = df
        
        # Apply time filters to cached data
        if from_ts:
            df = df[df['ts'] >= from_ts]
        if to_ts:
            df = df[df['ts'] <= to_ts]
        
        # Apply limit
        if limit:
            df = df.tail(limit)
        
        # Convert to list of dicts
        candles = df.to_dict('records')
        
        return candles
    
    def get_latest_price(self, symbol: str) -> Optional[float]:
        """Get the most recent price for a symbol."""
        symbol = normalize_symbol(symbol)
        
        with self.tick_locks[symbol]:
            if not self.tick_buffers[symbol]:
                return None
            return self.tick_buffers[symbol][-1]["price"]
    
    def get_statistics(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """
        Get buffer statistics.
        
        Args:
            symbol: Specific symbol or None for all symbols
            
        Returns:
            Dict with statistics
        """
        if symbol:
            symbol = normalize_symbol(symbol)
            return {
                "symbol": symbol,
                "tick_count": self.tick_counts.get(symbol, 0),
                "buffer_size": len(self.tick_buffers.get(symbol, [])),
                "last_tick": self.last_tick_time.get(symbol),
                "latest_price": self.get_latest_price(symbol),
            }
        else:
            return {
                "symbols": list(self.tick_buffers.keys()),
                "total_ticks": sum(self.tick_counts.values()),
                "active_symbols": len([
                    s for s in self.tick_buffers.keys()
                    if len(self.tick_buffers[s]) > 0
                ]),
                "tick_counts": dict(self.tick_counts),
            }

    def get_active_symbols(self) -> List[str]:
        """Return symbols that currently have buffered ticks."""
        active_symbols: List[str] = []
        for symbol in list(self.tick_buffers.keys()):
            with self.tick_locks[symbol]:
                if self.tick_buffers[symbol]:
                    active_symbols.append(symbol)
        return active_symbols
    
    def clear_buffer(self, symbol: Optional[str] = None):
        """
        Clear tick buffers.
        
        Args:
            symbol: Specific symbol to clear, or None to clear all
        """
        if symbol:
            symbol = normalize_symbol(symbol)
            with self.tick_locks[symbol]:
                self.tick_buffers[symbol].clear()
                self.tick_counts[symbol] = 0
            
            # Clear cached OHLCV for this symbol
            with self.ohlcv_lock:
                keys_to_remove = [
                    k for k in self.ohlcv_cache.keys() if k[0] == symbol
                ]
                for key in keys_to_remove:
                    del self.ohlcv_cache[key]
            
            log.info(f"Cleared buffer for {symbol}")
        else:
            # Clear all buffers
            for sym in list(self.tick_buffers.keys()):
                with self.tick_locks[sym]:
                    self.tick_buffers[sym].clear()
                    self.tick_counts[sym] = 0
            
            with self.ohlcv_lock:
                self.ohlcv_cache.clear()
            
            log.info("Cleared all buffers")
    
    def get_price_series(
        self,
        symbol: str,
        timeframe: str = "1m",
        limit: Optional[int] = None,
        force_resample: bool = False
    ) -> pd.Series:
        """
        Get close price series as pandas Series.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe for resampling
            limit: Maximum number of points
            
        Returns:
            Pandas Series with timestamp index and price values
        """
        symbol = normalize_symbol(symbol)
        cache_key = (symbol, timeframe)

        df: Optional[pd.DataFrame] = None

        if not force_resample:
            with self.ohlcv_lock:
                df = self.ohlcv_cache.get(cache_key)

        if df is None:
            # Pull current ticks snapshot
            with self.tick_locks[symbol]:
                ticks = list(self.tick_buffers[symbol])

            if not ticks:
                return pd.Series(dtype=float)

            pandas_rule = timeframe_to_pandas_rule(timeframe)
            df = resample_to_ohlcv(ticks, pandas_rule)

            if df.empty:
                return pd.Series(dtype=float)

            # Store fresh copy in cache for other consumers
            with self.ohlcv_lock:
                self.ohlcv_cache[cache_key] = df.copy()

        # Work on a copy to avoid mutating cached dataframe
        df_local = df.copy()

        if limit:
            df_local = df_local.tail(limit)

        if df_local.empty:
            return pd.Series(dtype=float)

        df_local['ts'] = pd.to_datetime(df_local['ts'])
        df_local = df_local.set_index('ts')

        return df_local['close']
    
    async def resample_loop(self, interval: int = 60):
        """
        Background task to periodically resample and cache OHLCV data.
        
        Args:
            interval: Resample interval in seconds
        """
        while True:
            try:
                await asyncio.sleep(interval)
                
                # Resample all active symbols
                for symbol in list(self.tick_buffers.keys()):
                    for timeframe in settings.resample_intervals_list:
                        try:
                            await self.get_ohlcv(symbol, timeframe, force_resample=True)
                        except Exception as e:
                            log.error(f"Error resampling {symbol} @ {timeframe}: {e}")
                
                log.debug("Completed periodic resample")
                
            except asyncio.CancelledError:
                log.info("Resample loop cancelled")
                break
            except Exception as e:
                log.error(f"Error in resample loop: {e}")


# Global data manager instance
data_manager = DataManager()
