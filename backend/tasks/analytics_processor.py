"""
Background task for computing analytics periodically.
Consumes in-memory tick data, computes analytics, and stores the latest results.
"""
import asyncio
from typing import Dict, Any, List
from datetime import datetime

from utils import log
from core import data_manager, analytics_engine


class AnalyticsProcessor:
    """
    Background processor for computing analytics on active trading pairs using
    the in-memory data manager. Runs periodically to:
    1. Fetch symbols with buffered ticks
    2. Compute analytics (spreads, z-scores, correlations)
    3. Cache the latest results locally for reuse
    """
    
    def __init__(self, interval: int = 10):
        """
        Initialize the analytics processor.
        
        Args:
            interval: Processing interval in seconds (default: 10s)
        """
        self.interval = interval
        self.running = False
        self.task = None
        self.latest_results: Dict[str, Dict[str, Any]] = {}
    
    async def start(self):
        """Start the background processing task."""
        if self.running:
            log.warning("Analytics processor already running")
            return
        
        self.running = True
        self.task = asyncio.create_task(self._process_loop())
        log.info(f"Analytics processor started (interval: {self.interval}s)")
    
    async def stop(self):
        """Stop the background processing task."""
        if not self.running:
            return
        
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        
        log.info("Analytics processor stopped")
    
    async def _process_loop(self):
        """Main processing loop."""
        while self.running:
            try:
                await self._process_all_pairs()
            except Exception as e:
                log.error(f"Analytics processing error: {e}")
            
            # Wait for next interval
            await asyncio.sleep(self.interval)
    
    async def _process_all_pairs(self):
        """Process all configured trading pairs."""
        try:
            # Determine active symbols with buffered ticks
            symbols = data_manager.get_active_symbols()
            if len(symbols) < 2:
                log.debug("Not enough symbols with data for pair analytics")
                return
            
            # Generate all pairs from available symbols
            pairs = self._generate_pairs(list(symbols))
            
            log.debug(f"Processing {len(pairs)} pairs: {pairs[:3]}..." if len(pairs) > 3 else f"Processing {len(pairs)} pairs")
            
            # Process each pair
            for pair in pairs:
                try:
                    await self._process_pair(pair)
                except Exception as e:
                    log.error(f"Error processing pair {pair}: {e}")
        
        except Exception as e:
            log.error(f"Error in _process_all_pairs: {e}")
    
    def _generate_pairs(self, symbols: List[str]) -> List[str]:
        """
        Generate trading pairs from available symbols.
        
        Args:
            symbols: List of trading symbols
            
        Returns:
            List of pair strings in format "SYMBOL_A-SYMBOL_B"
        """
        pairs = []
        for i, sym_a in enumerate(symbols):
            for sym_b in symbols[i+1:]:
                pairs.append(f"{sym_a}-{sym_b}")
        return pairs
    
    async def _process_pair(self, pair: str):
        """
        Process a single trading pair.
        
        Args:
            pair: Trading pair in format "SYMBOL_A-SYMBOL_B"
        """
        try:
            # Default parameters (can be made configurable)
            timeframe = "1m"
            window = 60
            regression = "OLS"
            
            # Check if analytics are already cached and fresh
            cache_key = f"{pair}:{timeframe}:{window}:{regression}"
            cached = self.latest_results.get(pair)
            
            if cached and cached.get("cache_key") == cache_key:
                log.debug(f"Skipping {pair} - analytics already cached in-memory")
                return
            
            # Compute analytics
            analytics = analytics_engine.compute_pair_analytics(
                pair=pair,
                timeframe=timeframe,
                window=window,
                regression=regression
            )
            
            if not analytics or "error" in analytics:
                log.debug(f"No analytics for {pair}: {analytics.get('error', 'No data')}")
                return
            
            # Cache result in-memory for quick reuse
            self.latest_results[pair] = {
                "cache_key": cache_key,
                "data": analytics,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            log.debug(f"Processed analytics for {pair}")
        
        except Exception as e:
            log.error(f"Error processing pair {pair}: {e}")


# Global instance
analytics_processor = AnalyticsProcessor(interval=10)
