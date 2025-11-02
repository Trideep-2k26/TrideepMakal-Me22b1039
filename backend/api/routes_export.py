"""
API routes for data export.
Endpoints: /export
"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from typing import Optional
import io
import csv
from datetime import datetime

from utils import log, settings
from core import analytics_engine, data_manager

router = APIRouter(prefix="/export", tags=["export"])


@router.get("")
async def export_data(
    pair: str = Query(..., description="Pair in format SYMBOL_A-SYMBOL_B"),
    tf: str = Query(default="1m", description="Timeframe"),
    format: str = Query(default="csv", description="Export format (csv)"),
    window: int = Query(default=60, description="Rolling window size"),
    regression: str = Query(default="OLS", description="Regression method")
):
    """
    Export analytics data as CSV file.
    
    Args:
        pair: Trading pair
        tf: Timeframe
        format: Export format (currently only csv supported)
        window: Window size
        regression: Regression method
        
    Returns:
        CSV file download
    """
    try:
        if format.lower() != "csv":
            raise HTTPException(
                status_code=400,
                detail="Only CSV format is currently supported"
            )
        
        # Compute analytics
        analytics = analytics_engine.compute_pair_analytics(
            pair=pair,
            timeframe=tf,
            window=window,
            regression=regression
        )
        
        if not analytics or "error" in analytics:
            raise HTTPException(
                status_code=404,
                detail="No data available for export"
            )
        
        # Prepare CSV data
        csv_buffer = io.StringIO()
        writer = csv.writer(csv_buffer)
        
        # Write header
        writer.writerow([
            "timestamp",
            "hedge_ratio",
            "spread",
            "zscore",
            "rolling_correlation"
        ])
        
        # Find the maximum length among all series
        max_len = max(
            len(analytics.get("hedge_ratio", [])),
            len(analytics.get("spread", [])),
            len(analytics.get("zscore", [])),
            len(analytics.get("rolling_corr", []))
        )
        
        # Write rows
        for i in range(max_len):
            hedge_ratio_val = (
                analytics["hedge_ratio"][i]["value"]
                if i < len(analytics.get("hedge_ratio", []))
                else ""
            )
            spread_val = (
                analytics["spread"][i]["value"]
                if i < len(analytics.get("spread", []))
                else ""
            )
            zscore_val = (
                analytics["zscore"][i]["value"]
                if i < len(analytics.get("zscore", []))
                else ""
            )
            corr_val = (
                analytics["rolling_corr"][i]["value"]
                if i < len(analytics.get("rolling_corr", []))
                else ""
            )
            
            # Use timestamp from first available series
            ts = ""
            if i < len(analytics.get("hedge_ratio", [])):
                ts = analytics["hedge_ratio"][i]["ts"]
            elif i < len(analytics.get("spread", [])):
                ts = analytics["spread"][i]["ts"]
            elif i < len(analytics.get("zscore", [])):
                ts = analytics["zscore"][i]["ts"]
            elif i < len(analytics.get("rolling_corr", [])):
                ts = analytics["rolling_corr"][i]["ts"]
            
            writer.writerow([ts, hedge_ratio_val, spread_val, zscore_val, corr_val])
        
        # Add ADF test results as footer
        writer.writerow([])
        writer.writerow(["ADF Test Results"])
        writer.writerow(["P-value", analytics["adf"]["pvalue"]])
        writer.writerow(["Test Statistic", analytics["adf"]["stat"]])
        writer.writerow([
            "Interpretation",
            "Stationary (mean-reverting)" if analytics["adf"]["pvalue"] < 0.05
            else "Non-stationary"
        ])
        
        # Create response
        csv_buffer.seek(0)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{pair.replace('-', '_')}_{tf}_{timestamp}.csv"
        
        log.info(f"Exporting data to {filename}")
        
        return StreamingResponse(
            iter([csv_buffer.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error exporting data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ohlcv")
async def export_ohlcv(
    symbol: str = Query(..., description="Trading symbol"),
    tf: str = Query(default="1m", description="Timeframe"),
    limit: Optional[int] = Query(default=None, description="Maximum rows")
):
    """
    Export OHLCV data as CSV.
    
    Args:
        symbol: Trading symbol
        tf: Timeframe
        limit: Maximum rows
        
    Returns:
        CSV file download
    """
    try:
        # Get OHLCV data
        ohlcv = await data_manager.get_ohlcv(symbol, tf, limit)
        
        if not ohlcv:
            raise HTTPException(
                status_code=404,
                detail="No data available for export"
            )
        
        # Prepare CSV
        csv_buffer = io.StringIO()
        writer = csv.writer(csv_buffer)
        
        # Write header
        writer.writerow(["timestamp", "open", "high", "low", "close", "volume"])
        
        # Write data
        for candle in ohlcv:
            writer.writerow([
                candle["ts"],
                candle["open"],
                candle["high"],
                candle["low"],
                candle["close"],
                candle["volume"]
            ])
        
        # Create response
        csv_buffer.seek(0)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{symbol}_{tf}_ohlcv_{timestamp}.csv"
        
        log.info(f"Exporting OHLCV to {filename}")
        
        return StreamingResponse(
            iter([csv_buffer.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error exporting OHLCV: {e}")
        raise HTTPException(status_code=500, detail=str(e))
