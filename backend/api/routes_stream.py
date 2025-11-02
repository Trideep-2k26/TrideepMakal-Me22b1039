"""
API routes for stream management and WebSocket connections.
Endpoints: /stream/start, /stream/stop, /ws
"""
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Body
from pydantic import BaseModel, Field
from typing import List, Dict, Set
import asyncio
import json

from utils import log, normalize_symbol, settings
from core import data_manager, alerts_engine, analytics_engine
from core.websocket_client import WebSocketManager

router = APIRouter(prefix="/stream", tags=["stream"])

# Global WebSocket manager for Binance streams
ws_manager: WebSocketManager = None

# Active frontend WebSocket connections
frontend_connections: Set[WebSocket] = set()

# Redis pub/sub listener task
redis_pubsub_task: asyncio.Task = None


class StreamStartRequest(BaseModel):
    """Request model for starting streams."""
    symbols: List[str] = Field(..., description="List of symbols to stream")
    tick_mode: bool = Field(default=True, description="Enable tick-by-tick streaming")


class StreamStopRequest(BaseModel):
    """Request model for stopping streams."""
    symbols: List[str] = Field(..., description="List of symbols to stop")


async def handle_tick(tick: Dict):
    """
    Callback for handling incoming ticks from Binance WebSocket.
    Stores tick in data manager and broadcasts to frontend.
    """
    # Store tick
    await data_manager.add_tick(tick)
    
    # Broadcast to all connected frontend clients
    if frontend_connections:
        message = json.dumps({
            "type": "trade",
            "symbol": tick["symbol"],
            "price": tick["price"],
            "qty": tick["qty"],
            "ts": tick["ts"]
        })
        
        # Send to all connections
        disconnected = set()
        for websocket in frontend_connections:
            try:
                await websocket.send_text(message)
            except Exception as e:
                log.error(f"Error sending to WebSocket: {e}")
                disconnected.add(websocket)
        
        # Remove disconnected clients
        frontend_connections.difference_update(disconnected)


async def handle_ticker(ticker: Dict):
    """
    Callback for handling 24h ticker updates from Binance WebSocket.
    Broadcasts 24h statistics to frontend clients.
    """
    # Broadcast 24h ticker stats to all connected frontend clients
    if frontend_connections:
        message = json.dumps({
            "type": "ticker",
            "symbol": ticker["symbol"],
            "priceChange": ticker["priceChange"],
            "priceChangePercent": ticker["priceChangePercent"],
            "lastPrice": ticker["lastPrice"],
            "openPrice": ticker["openPrice"],
            "highPrice": ticker["highPrice"],
            "lowPrice": ticker["lowPrice"],
            "volume": ticker["volume"],
            "quoteVolume": ticker["quoteVolume"],
            "ts": ticker["ts"]
        })
        
        # Send to all connections
        disconnected = set()
        for websocket in frontend_connections:
            try:
                await websocket.send_text(message)
            except Exception as e:
                log.error(f"Error sending ticker to WebSocket: {e}")
                disconnected.add(websocket)
        
        # Remove disconnected clients
        frontend_connections.difference_update(disconnected)


async def broadcast_alert(notification):
    """Broadcast alert notification to frontend clients."""
    if frontend_connections:
        message = json.dumps({
            "type": "alert",
            "id": notification.id,
            "alert_id": notification.alert_id,
            "message": notification.message,
            "metric": notification.metric,
            "pair": notification.pair,
            "actual_value": notification.actual_value,
            "threshold_value": notification.threshold_value,
            "ts": notification.ts
        })
        
        disconnected = set()
        for websocket in frontend_connections:
            try:
                await websocket.send_text(message)
            except Exception:
                disconnected.add(websocket)
        
        frontend_connections.difference_update(disconnected)


def initialize_ws_manager():
    """Initialize the global WebSocket manager."""
    global ws_manager
    if ws_manager is None:
        ws_manager = WebSocketManager(on_tick=handle_tick, on_ticker=handle_ticker)
        log.info("Initialized Binance WebSocket Manager with ticker support")


async def start_redis_pubsub_listener():
    """
    Redis pub/sub listener - DISABLED (using in-memory mode).
    """
    log.info("Redis pub/sub listener disabled (in-memory mode)")
    return


async def stop_redis_pubsub_listener():
    """Stop Redis pub/sub listener - DISABLED."""
    log.debug("Redis pub/sub listener stop called (disabled)")
    return



@router.post("/start")
async def start_stream(request: StreamStartRequest = Body(...)):
    """
    Start WebSocket streams for specified symbols.
    
    Args:
        request: Stream start configuration
        
    Returns:
        Success status
    """
    try:
        initialize_ws_manager()
        
        # Validate symbols
        invalid_symbols = [
            s for s in request.symbols
            if normalize_symbol(s) not in settings.symbols_list
        ]
        
        if invalid_symbols:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid symbols: {invalid_symbols}. Available: {settings.symbols_list}"
            )
        
        # Validate symbol count
        if len(request.symbols) > settings.max_symbols:
            raise HTTPException(
                status_code=400,
                detail=f"Too many symbols. Maximum: {settings.max_symbols}"
            )
        
        # Start streams
        await ws_manager.subscribe_multiple(request.symbols)
        
        log.info(f"Started streams for: {request.symbols}")
        
        return {
            "status": "ok",
            "started": True,
            "symbols": request.symbols,
            "active_symbols": ws_manager.get_active_symbols()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error starting streams: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_stream(request: StreamStopRequest = Body(...)):
    """
    Stop WebSocket streams for specified symbols.
    
    Args:
        request: Stream stop configuration
        
    Returns:
        Success status
    """
    try:
        if ws_manager is None:
            return {"status": "ok", "stopped": True, "message": "No active streams"}
        
        # Stop streams
        await ws_manager.unsubscribe_multiple(request.symbols)
        
        log.info(f"Stopped streams for: {request.symbols}")
        
        return {
            "status": "ok",
            "stopped": True,
            "symbols": request.symbols,
            "active_symbols": ws_manager.get_active_symbols()
        }
    
    except Exception as e:
        log.error(f"Error stopping streams: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_stream_status():
    """
    Get current stream status.
    
    Returns:
        Stream status information
    """
    try:
        if ws_manager is None:
            return {
                "active": False,
                "symbols": [],
                "frontend_connections": 0
            }
        
        return {
            "active": len(ws_manager.get_active_symbols()) > 0,
            "symbols": ws_manager.get_active_symbols(),
            "frontend_connections": len(frontend_connections),
            "buffer_stats": data_manager.get_statistics()
        }
    
    except Exception as e:
        log.error(f"Error getting stream status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for frontend connections.
    Handles subscription messages and broadcasts tick data.
    
    Message format:
    - Subscribe: {"action": "subscribe", "symbols": ["BTCUSDT"]}
    - Unsubscribe: {"action": "unsubscribe", "symbols": ["ETHUSDT"]}
    
    Broadcasts:
    - Tick: {"type": "trade", "symbol": "BTCUSDT", "price": 34000, ...}
    - Alert: {"type": "alert", "id": "...", "message": "..."}
    """
    await websocket.accept()
    frontend_connections.add(websocket)
    
    log.info(f"Frontend WebSocket connected. Total connections: {len(frontend_connections)}")
    
    try:
        while True:
            # Receive message from frontend
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                action = message.get("action")
                
                if action == "subscribe":
                    symbols = message.get("symbols", [])
                    if symbols:
                        initialize_ws_manager()
                        await ws_manager.subscribe_multiple(symbols)
                        
                        response = json.dumps({
                            "type": "subscription",
                            "status": "subscribed",
                            "symbols": symbols
                        })
                        await websocket.send_text(response)
                        
                        log.info(f"Frontend subscribed to: {symbols}")
                
                elif action == "unsubscribe":
                    symbols = message.get("symbols", [])
                    if symbols and ws_manager:
                        await ws_manager.unsubscribe_multiple(symbols)
                        
                        response = json.dumps({
                            "type": "subscription",
                            "status": "unsubscribed",
                            "symbols": symbols
                        })
                        await websocket.send_text(response)
                        
                        log.info(f"Frontend unsubscribed from: {symbols}")
                
                elif action == "ping":
                    # Heartbeat
                    await websocket.send_text(json.dumps({"type": "pong"}))
            
            except json.JSONDecodeError:
                log.error(f"Invalid JSON from frontend: {data}")
            except Exception as e:
                log.error(f"Error handling frontend message: {e}")
    
    except WebSocketDisconnect:
        log.info("Frontend WebSocket disconnected")
    except Exception as e:
        log.error(f"WebSocket error: {e}")
    finally:
        frontend_connections.discard(websocket)
        log.info(f"Frontend WebSocket removed. Remaining: {len(frontend_connections)}")
        
        # Stop Redis pub/sub listener if this was the last connection
        if len(frontend_connections) == 0:
            await stop_redis_pubsub_listener()



# Register alert callback on module load
alerts_engine.register_callback(broadcast_alert)
