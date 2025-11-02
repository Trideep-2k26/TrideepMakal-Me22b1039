"""
API routes for data operations.
Endpoints: /symbols, /data/{symbol}
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from datetime import datetime

from utils import log, settings, normalize_symbol
from core import data_manager

router = APIRouter(prefix="", tags=["data"])


@router.get("/symbols")
async def get_symbols() -> List[str]:
    """
    Get list of available trading symbols.
    
    Returns:
        List of symbol strings
    """
    try:
        return settings.symbols_list
    except Exception as e:
        log.error(f"Error getting symbols: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data/{symbol}")
async def get_data(
    symbol: str,
    tf: str = Query(default="1m", description="Timeframe (1s, 1m, 5m)"),
    from_ts: Optional[str] = Query(default=None, alias="from", description="Start timestamp (ISO)"),
    to_ts: Optional[str] = Query(default=None, alias="to", description="End timestamp (ISO)"),
    limit: Optional[int] = Query(default=100, description="Maximum number of candles")
):
    """
    Get OHLCV data for a symbol.
    
    Args:
        symbol: Trading symbol (e.g., BTCUSDT)
        tf: Timeframe for resampling (1s, 1m, 5m)
        from_ts: Start timestamp filter (ISO format)
        to_ts: End timestamp filter (ISO format)
        limit: Maximum number of candles to return
        
    Returns:
        List of OHLCV dictionaries with keys: ts, open, high, low, close, volume
    """
    try:
        symbol = normalize_symbol(symbol)
        
        # Validate symbol
        if symbol not in settings.symbols_list:
            raise HTTPException(
                status_code=400,
                detail=f"Symbol {symbol} not supported. Available: {settings.symbols_list}"
            )
        
        # Validate timeframe
        if tf not in settings.resample_intervals_list:
            raise HTTPException(
                status_code=400,
                detail=f"Timeframe {tf} not supported. Available: {settings.resample_intervals_list}"
            )
        
        # Get OHLCV data
        data = await data_manager.get_ohlcv(
            symbol=symbol,
            timeframe=tf,
            limit=limit,
            from_ts=from_ts,
            to_ts=to_ts
        )
        
        log.debug(f"Returning {len(data)} candles for {symbol} @ {tf}")
        
        return data
    
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error getting data for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data/{symbol}/ticks")
async def get_ticks(
    symbol: str,
    limit: Optional[int] = Query(default=1000, description="Maximum number of ticks"),
    from_ts: Optional[str] = Query(default=None, alias="from", description="Start timestamp (ISO)"),
    to_ts: Optional[str] = Query(default=None, alias="to", description="End timestamp (ISO)")
):
    """
    Get raw tick data for a symbol.
    
    Args:
        symbol: Trading symbol
        limit: Maximum number of ticks
        from_ts: Start timestamp filter
        to_ts: End timestamp filter
        
    Returns:
        List of tick dictionaries with keys: ts, price, qty
    """
    try:
        symbol = normalize_symbol(symbol)
        
        if symbol not in settings.symbols_list:
            raise HTTPException(
                status_code=400,
                detail=f"Symbol {symbol} not supported"
            )
        
        ticks = await data_manager.get_ticks(
            symbol=symbol,
            limit=limit,
            from_ts=from_ts,
            to_ts=to_ts
        )
        
        log.debug(f"Returning {len(ticks)} ticks for {symbol}")
        
        return ticks
    
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error getting ticks for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data/stats")
async def get_stats(symbol: Optional[str] = None):
    """
    Get buffer statistics.
    
    Args:
        symbol: Optional symbol to get stats for (all symbols if None)
        
    Returns:
        Statistics dictionary
    """
    try:
        if symbol:
            symbol = normalize_symbol(symbol)
        
        stats = data_manager.get_statistics(symbol)
        return stats
    
    except Exception as e:
        log.error(f"Error getting statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/data/clear")
async def clear_buffer(symbol: Optional[str] = None):
    """
    Clear tick buffers.
    
    Args:
        symbol: Optional symbol to clear (all symbols if None)
        
    Returns:
        Success message
    """
    try:
        if symbol:
            symbol = normalize_symbol(symbol)
        
        data_manager.clear_buffer(symbol)
        
        return {
            "status": "ok",
            "message": f"Cleared buffer for {symbol if symbol else 'all symbols'}"
        }
    
    except Exception as e:
        log.error(f"Error clearing buffer: {e}")
        raise HTTPException(status_code=500, detail=str(e))
