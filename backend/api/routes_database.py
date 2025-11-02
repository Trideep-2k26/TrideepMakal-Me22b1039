"""
API routes for database operations.

Provides endpoints for:
- Querying historical tick data
- Getting resampled OHLCV data
- Exporting data to CSV
- Database statistics and management
"""

from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from core.db import (
    get_db,
    get_ticks,
    get_resampled_data,
    delete_old_data,
    export_to_csv,
    get_database_stats,
)
from utils import log

router = APIRouter(prefix="/database", tags=["Database"])


class TicksQueryRequest(BaseModel):
    """Request model for querying tick data."""
    symbol: str = Field(..., description="Trading symbol (e.g., BTCUSDT)")
    start_time: Optional[str] = Field(None, description="Start time (ISO format)")
    end_time: Optional[str] = Field(None, description="End time (ISO format)")
    limit: Optional[int] = Field(None, ge=1, le=100000, description="Maximum rows to return")


class ResampleRequest(BaseModel):
    """Request model for resampling data."""
    symbol: str = Field(..., description="Trading symbol")
    timeframe: str = Field(
        "1T",
        description="Resample frequency: 1S, 1T/1min, 5T/5min, 15T, 30T, 1H, 1D"
    )
    start_time: Optional[str] = Field(None, description="Start time (ISO format)")
    end_time: Optional[str] = Field(None, description="End time (ISO format)")


class ExportRequest(BaseModel):
    """Request model for CSV export."""
    symbol: str = Field(..., description="Trading symbol")
    timeframe: str = Field("1T", description="Resample frequency")
    start_time: Optional[str] = Field(None, description="Start time (ISO format)")
    end_time: Optional[str] = Field(None, description="End time (ISO format)")


@router.get("/stats")
async def get_db_stats():
    """
    Get database statistics.
    
    Returns information about:
    - Total tick count
    - Ticks per symbol
    - Time range covered
    - Database file size
    """
    try:
        stats = get_database_stats()
        return {
            "status": "ok",
            "stats": stats
        }
    except Exception as e:
        log.error(f"Error getting database stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ticks/{symbol}")
async def get_historical_ticks(
    symbol: str,
    start_time: Optional[str] = Query(None, description="Start time (ISO format)"),
    end_time: Optional[str] = Query(None, description="End time (ISO format)"),
    limit: Optional[int] = Query(1000, ge=1, le=100000, description="Max rows"),
):
    """
    Get historical tick data for a symbol.
    
    Args:
        symbol: Trading symbol (e.g., BTCUSDT)
        start_time: Optional start time in ISO format
        end_time: Optional end time in ISO format
        limit: Maximum number of rows (default: 1000)
        
    Returns:
        DataFrame as JSON with tick data
    """
    try:
        # Parse timestamps
        start_dt = datetime.fromisoformat(start_time) if start_time else None
        end_dt = datetime.fromisoformat(end_time) if end_time else None
        
        # Query database
        df = get_ticks(symbol.upper(), start_dt, end_dt, limit)
        
        if df.empty:
            return {
                "status": "ok",
                "symbol": symbol,
                "count": 0,
                "data": []
            }
        
        # Convert to JSON-friendly format
        data = df.to_dict(orient="records")
        
        return {
            "status": "ok",
            "symbol": symbol,
            "count": len(data),
            "time_range": {
                "start": str(df['timestamp'].min()),
                "end": str(df['timestamp'].max())
            },
            "data": data
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid timestamp format: {e}")
    except Exception as e:
        log.error(f"Error fetching ticks for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ohlcv")
async def get_ohlcv_data(request: ResampleRequest):
    """
    Get resampled OHLCV data.
    
    Resamples raw tick data into candlestick format.
    
    Supported timeframes:
    - 1S: 1 second
    - 1T or 1min: 1 minute
    - 5T or 5min: 5 minutes
    - 15T: 15 minutes
    - 30T: 30 minutes
    - 1H: 1 hour
    - 1D: 1 day
    """
    try:
        # Parse timestamps
        start_dt = datetime.fromisoformat(request.start_time) if request.start_time else None
        end_dt = datetime.fromisoformat(request.end_time) if request.end_time else None
        
        # Get resampled data
        df = get_resampled_data(
            symbol=request.symbol.upper(),
            timeframe=request.timeframe,
            start_time=start_dt,
            end_time=end_dt
        )
        
        if df.empty:
            return {
                "status": "ok",
                "symbol": request.symbol,
                "timeframe": request.timeframe,
                "count": 0,
                "data": []
            }
        
        # Convert to JSON
        data = df.to_dict(orient="records")
        
        return {
            "status": "ok",
            "symbol": request.symbol,
            "timeframe": request.timeframe,
            "count": len(data),
            "time_range": {
                "start": str(df['ts'].min()),
                "end": str(df['ts'].max())
            },
            "data": data
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid request: {e}")
    except Exception as e:
        log.error(f"Error resampling data for {request.symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/export")
async def export_data(request: ExportRequest):
    """
    Export resampled data to CSV file.
    
    Returns a downloadable CSV file with OHLCV data.
    """
    try:
        # Parse timestamps
        start_dt = datetime.fromisoformat(request.start_time) if request.start_time else None
        end_dt = datetime.fromisoformat(request.end_time) if request.end_time else None
        
        # Export to CSV
        csv_path = export_to_csv(
            symbol=request.symbol.upper(),
            timeframe=request.timeframe,
            start_time=start_dt,
            end_time=end_dt
        )
        
        if not csv_path:
            raise HTTPException(status_code=404, detail="No data available to export")
        
        # Return file for download
        return FileResponse(
            path=csv_path,
            media_type="text/csv",
            filename=f"{request.symbol}_{request.timeframe}.csv"
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid request: {e}")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Export file not found")
    except Exception as e:
        log.error(f"Error exporting data for {request.symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/cleanup")
async def cleanup_old_data(
    hours: int = Query(24, ge=1, le=720, description="Delete data older than N hours")
):
    """
    Delete old tick data to prevent database bloating.
    
    Args:
        hours: Retention period in hours (default: 24, max: 720/30 days)
        
    Returns:
        Number of rows deleted
    """
    try:
        deleted_count = delete_old_data(hours)
        
        # Optimize database after deletion
        db = get_db()
        db.vacuum()
        
        return {
            "status": "ok",
            "deleted_rows": deleted_count,
            "retention_hours": hours,
            "message": f"Deleted {deleted_count} ticks older than {hours} hours"
        }
        
    except Exception as e:
        log.error(f"Error cleaning up old data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/vacuum")
async def vacuum_database():
    """
    Optimize database by reclaiming unused space.
    
    Should be called after large deletions to reduce file size.
    """
    try:
        db = get_db()
        db.vacuum()
        
        stats = get_database_stats()
        
        return {
            "status": "ok",
            "message": "Database optimized successfully",
            "database_size_mb": stats["database_size_mb"]
        }
        
    except Exception as e:
        log.error(f"Error vacuuming database: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/clear")
async def clear_database():
    """
    ⚠️ WARNING: Delete ALL data from database.
    
    This operation is irreversible!
    Use with caution - typically only for testing or resetting.
    """
    try:
        db = get_db()
        db.clear_all_data()
        
        return {
            "status": "ok",
            "message": "All data cleared from database"
        }
        
    except Exception as e:
        log.error(f"Error clearing database: {e}")
        raise HTTPException(status_code=500, detail=str(e))
