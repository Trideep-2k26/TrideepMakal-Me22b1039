"""
API routes for analytics operations.
Endpoints: /analytics/pair, /analytics/adf
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from utils import log, settings
from core import analytics_engine, data_manager

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/pair")
async def get_pair_analytics(
    pair: str = Query(..., description="Pair in format SYMBOL_A-SYMBOL_B"),
    tf: str = Query(default="1m", description="Timeframe (1s, 1m, 5m)"),
    window: int = Query(default=60, description="Rolling window size"),
    regression: str = Query(default="OLS", description="Regression method (OLS, Huber, Theil-Sen, Kalman)")
):
    """
    Compute comprehensive analytics for a trading pair.
    
    Args:
        pair: Trading pair in format "BTCUSDT-ETHUSDT"
        tf: Timeframe for data resampling
        window: Rolling window size for calculations
        regression: Regression method for hedge ratio
        
    Returns:
        Dictionary containing:
        - hedge_ratio: List of {ts, value}
        - spread: List of {ts, value}
        - zscore: List of {ts, value}
        - rolling_corr: List of {ts, value}
        - adf: {pvalue, stat}
    """
    try:
        # Validate timeframe
        if tf not in settings.resample_intervals_list:
            raise HTTPException(
                status_code=400,
                detail=f"Timeframe {tf} not supported. Available: {settings.resample_intervals_list}"
            )
        
        # Validate regression method
        valid_methods = ["OLS", "HUBER", "THEIL-SEN", "KALMAN"]
        if regression.upper() not in valid_methods:
            raise HTTPException(
                status_code=400,
                detail=f"Regression method {regression} not supported. Available: {valid_methods}"
            )
        
        # Validate window
        if window < 2:
            raise HTTPException(
                status_code=400,
                detail="Window size must be at least 2"
            )
        
        # Compute analytics
        analytics = analytics_engine.compute_pair_analytics(
            pair=pair,
            timeframe=tf,
            window=window,
            regression=regression
        )
        
        if not analytics:
            raise HTTPException(
                status_code=404,
                detail=f"No data available for pair {pair}"
            )
        
        if "error" in analytics:
            raise HTTPException(
                status_code=500,
                detail=analytics["error"]
            )
        
        log.debug(f"Computed analytics for {pair} @ {tf}")
        
        return analytics
    
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error computing pair analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/adf")
async def get_adf_test(
    pair: str = Query(..., description="Pair in format SYMBOL_A-SYMBOL_B"),
    tf: str = Query(default="1m", description="Timeframe (1s, 1m, 5m)"),
    window: int = Query(default=60, description="Rolling window size"),
    regression: str = Query(default="OLS", description="Regression method")
):
    """
    Perform Augmented Dickey-Fuller stationarity test on pair spread.
    
    Args:
        pair: Trading pair
        tf: Timeframe
        window: Window size
        regression: Regression method
        
    Returns:
        Dictionary with:
        - pvalue: P-value of ADF test
        - stat: Test statistic
        - is_stationary: Boolean (pvalue < 0.05)
    """
    try:
        # Compute ADF test
        adf_result = analytics_engine.compute_adf_test(
            symbol_a=pair.split("-")[0],
            symbol_b=pair.split("-")[1],
            timeframe=tf,
            window=window,
            method=regression
        )
        
        # Add interpretation
        adf_result["is_stationary"] = adf_result["pvalue"] < 0.05
        adf_result["interpretation"] = (
            "Spread is stationary (mean-reverting)" if adf_result["is_stationary"]
            else "Spread is non-stationary"
        )
        
        log.debug(f"ADF test for {pair}: p-value={adf_result['pvalue']:.4f}")
        
        return adf_result
    
    except Exception as e:
        log.error(f"Error in ADF test: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/hedge-ratio")
async def get_hedge_ratio(
    symbol_a: str = Query(..., description="First symbol"),
    symbol_b: str = Query(..., description="Second symbol"),
    tf: str = Query(default="1m", description="Timeframe"),
    window: int = Query(default=60, description="Rolling window size"),
    method: str = Query(default="OLS", description="Regression method")
):
    """
    Compute hedge ratio between two symbols.
    
    Returns:
        List of {ts, value} dictionaries
    """
    try:
        hedge_ratio = analytics_engine.compute_hedge_ratio(
            symbol_a=symbol_a,
            symbol_b=symbol_b,
            timeframe=tf,
            window=window,
            method=method
        )
        
        return {"hedge_ratio": hedge_ratio}
    
    except Exception as e:
        log.error(f"Error computing hedge ratio: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/spread")
async def get_spread(
    symbol_a: str = Query(..., description="First symbol"),
    symbol_b: str = Query(..., description="Second symbol"),
    tf: str = Query(default="1m", description="Timeframe"),
    window: int = Query(default=60, description="Rolling window size"),
    method: str = Query(default="OLS", description="Regression method")
):
    """
    Compute spread between two symbols.
    
    Returns:
        List of {ts, value} dictionaries
    """
    try:
        spread = analytics_engine.compute_spread(
            symbol_a=symbol_a,
            symbol_b=symbol_b,
            timeframe=tf,
            window=window,
            method=method
        )
        
        return {"spread": spread}
    
    except Exception as e:
        log.error(f"Error computing spread: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/zscore")
async def get_zscore(
    symbol_a: str = Query(..., description="First symbol"),
    symbol_b: str = Query(..., description="Second symbol"),
    tf: str = Query(default="1m", description="Timeframe"),
    window: int = Query(default=60, description="Rolling window size"),
    method: str = Query(default="OLS", description="Regression method")
):
    """
    Compute z-score of spread between two symbols.
    
    Returns:
        List of {ts, value} dictionaries
    """
    try:
        zscore = analytics_engine.compute_zscore(
            symbol_a=symbol_a,
            symbol_b=symbol_b,
            timeframe=tf,
            window=window,
            method=method
        )
        
        return {"zscore": zscore}
    
    except Exception as e:
        log.error(f"Error computing z-score: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/correlation")
async def get_correlation(
    symbol_a: str = Query(..., description="First symbol"),
    symbol_b: str = Query(..., description="Second symbol"),
    tf: str = Query(default="1m", description="Timeframe"),
    window: int = Query(default=60, description="Rolling window size")
):
    """
    Compute rolling correlation between two symbols.
    
    Returns:
        List of {ts, value} dictionaries
    """
    try:
        correlation = analytics_engine.compute_rolling_correlation(
            symbol_a=symbol_a,
            symbol_b=symbol_b,
            timeframe=tf,
            window=window
        )
        
        return {"correlation": correlation}
    
    except Exception as e:
        log.error(f"Error computing correlation: {e}")
        raise HTTPException(status_code=500, detail=str(e))
