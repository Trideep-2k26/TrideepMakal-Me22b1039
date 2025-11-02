"""
Main FastAPI application for Quant Analytics Backend.
Real-time quantitative trading analytics with Binance Futures data.
"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from utils import log, settings
from core import data_manager, alerts_engine
from api import (
    data_router,
    analytics_router,
    alerts_router,
    export_router,
    stream_router,
    visualization_router,
    database_router,
)


# Background tasks
background_tasks = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    log.info("=" * 60)
    log.info("Starting Quant Analytics Backend")
    log.info("=" * 60)
    log.info(f"Host: {settings.host}:{settings.port}")
    log.info(f"Available symbols: {settings.symbols_list}")
    log.info(f"Timeframes: {settings.resample_intervals_list}")
    log.info(f"CORS origins: {settings.cors_origins_list}")
    
    # Initialize database
    log.info("Initializing SQLite database...")
    from core.db import init_db
    init_db()
    log.info("✓ Database initialized")
    
    # Start background tasks
    log.info("Starting background tasks...")
    
    # 1. Periodic resampling task
    resample_task = asyncio.create_task(data_manager.resample_loop(interval=60))
    background_tasks.append(resample_task)
    log.info("✓ Started periodic resampling task (60s interval)")
    
    # 2. Alert monitoring task
    await alerts_engine.start_monitoring(interval=0.5)
    log.info("✓ Started alert monitoring task (500ms interval)")
    
    log.info("=" * 60)
    log.info("Backend is ready to accept requests!")
    log.info("=" * 60)
    
    yield
    
    # Shutdown
    log.info("=" * 60)
    log.info("Shutting down Quant Analytics Backend")
    log.info("=" * 60)
    
    # Stop alert monitoring
    await alerts_engine.stop_monitoring()
    log.info("✓ Stopped alert monitoring")
    
    # Cancel background tasks
    for task in background_tasks:
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
    log.info("✓ Cancelled background tasks")
    
    # Cleanup WebSocket connections
    from api.routes_stream import ws_manager
    if ws_manager:
        await ws_manager.disconnect_all()
        log.info("✓ Closed Binance WebSocket connections")
    
    log.info("=" * 60)
    log.info("Shutdown complete")
    log.info("=" * 60)


# Create FastAPI application
app = FastAPI(
    title="Quant Analytics API",
    description="Real-time quantitative trading analytics with Binance Futures data",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors."""
    log.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": str(exc)
        }
    )


# Health check endpoint
@app.get("/", tags=["health"])
async def root():
    """Root endpoint - health check."""
    return {
        "status": "ok",
        "service": "Quant Analytics API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health", tags=["health"])
async def health_check():
    """Detailed health check endpoint."""
    from api.routes_stream import ws_manager
    
    return {
        "status": "healthy",
        "binance_ws_active": ws_manager.get_active_symbols() if ws_manager else [],
        "data_buffer_stats": data_manager.get_statistics(),
        "active_alerts": len(alerts_engine.get_active_alerts()),
        "triggered_alerts": len(alerts_engine.get_triggered_alerts()),
    }


# Register routers
app.include_router(data_router)
app.include_router(analytics_router)
app.include_router(alerts_router)
app.include_router(export_router)
app.include_router(stream_router)
app.include_router(visualization_router)
app.include_router(database_router)


# WebSocket route (needs to be added separately)
from api.routes_stream import websocket_endpoint
app.add_api_websocket_route("/ws", websocket_endpoint)


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        log_level=settings.log_level.lower(),
    )
