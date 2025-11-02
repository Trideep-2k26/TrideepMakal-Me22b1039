"""
Binance Futures WebSocket client for real-time tick data and 24h ticker stats.
Connects to:
- wss://fstream.binance.com/ws/{symbol}@trade (trade stream)
- wss://fstream.binance.com/ws/{symbol}@ticker (24h ticker stream)
"""
import asyncio
import json
from datetime import datetime, timezone
from typing import Callable, Dict, Optional
import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

from utils import log, normalize_symbol, settings
from core.db import insert_tick


class BinanceWebSocketClient:
    """
    WebSocket client for Binance Futures tick data and 24h ticker streams.
    
    Connects to individual symbol streams and processes trade + ticker events.
    """
    
    def __init__(self, symbol: str, on_tick: Callable, on_ticker: Optional[Callable] = None):
        """
        Initialize WebSocket client for a symbol.
        
        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT')
            on_tick: Callback function to handle incoming ticks
            on_ticker: Optional callback for 24h ticker updates
        """
        self.symbol = normalize_symbol(symbol)
        self.on_tick = on_tick
        self.on_ticker = on_ticker
        
        # Combined stream URL for both trade and 24h ticker
        symbol_lower = self.symbol.lower()
        self.ws_url = f"{settings.binance_ws_base}/stream?streams={symbol_lower}@trade/{symbol_lower}@ticker"
        
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.task: Optional[asyncio.Task] = None
        self.is_running = False
        self.reconnect_delay = 1  # seconds
        self.max_reconnect_delay = 60  # seconds
        
    async def connect(self):
        """Establish WebSocket connection and start listening."""
        self.is_running = True
        self.task = asyncio.create_task(self._listen())
        log.info(f"Started WebSocket stream for {self.symbol}")
        
    async def _listen(self):
        """Main loop for WebSocket connection with automatic reconnection."""
        while self.is_running:
            try:
                async with websockets.connect(
                    self.ws_url,
                    ping_interval=20,
                    ping_timeout=10,
                    close_timeout=10,
                ) as websocket:
                    self.websocket = websocket
                    log.info(f"WebSocket connected: {self.symbol}")
                    self.reconnect_delay = 1  # Reset delay on successful connection
                    
                    # Listen for messages
                    async for message in websocket:
                        if not self.is_running:
                            break
                            
                        try:
                            data = json.loads(message)
                            await self._handle_message(data)
                        except json.JSONDecodeError as e:
                            log.error(f"JSON decode error for {self.symbol}: {e}")
                        except Exception as e:
                            log.error(f"Error processing message for {self.symbol}: {e}")
                            
            except ConnectionClosed as e:
                log.warning(f"WebSocket connection closed for {self.symbol}: {e}")
            except WebSocketException as e:
                log.error(f"WebSocket error for {self.symbol}: {e}")
            except Exception as e:
                log.error(f"Unexpected error in WebSocket for {self.symbol}: {e}")
            
            # Reconnection logic with exponential backoff
            if self.is_running:
                log.info(f"Reconnecting {self.symbol} in {self.reconnect_delay}s...")
                await asyncio.sleep(self.reconnect_delay)
                self.reconnect_delay = min(
                    self.reconnect_delay * 2,
                    self.max_reconnect_delay
                )
    
    async def _handle_message(self, data: Dict):
        """
        Parse and handle incoming trade or ticker message.
        
        Binance combined stream format wraps messages:
        {
            "stream": "btcusdt@trade" or "btcusdt@ticker",
            "data": { ... }
        }
        
        Trade message format (in data):
        {
            "e": "trade",       # Event type
            "E": 1698751245947, # Event time
            "s": "BTCUSDT",     # Symbol
            "t": 123456,        # Trade ID
            "p": "34200.50",    # Price
            "q": "0.002",       # Quantity
            "T": 1698751245947, # Trade time
            ...
        }
        
        24h Ticker message format (in data):
        {
            "e": "24hrTicker",  # Event type
            "E": 1698751245947, # Event time
            "s": "BTCUSDT",     # Symbol
            "p": "1518.55",     # Price change
            "P": "1.41",        # Price change percent
            "c": "109588.74",   # Last price
            "o": "108070.19",   # Open price (24h ago)
            "h": "111190.00",   # High price (24h)
            "l": "106304.34",   # Low price (24h)
            "v": "23955.49",    # Total traded base asset volume (24h)
            "q": "2613422945.88", # Total traded quote asset volume (24h)
            ...
        }
        """
        # Handle combined stream format
        if "stream" in data and "data" in data:
            inner_data = data["data"]
            stream_name = data["stream"]
            
            if "@trade" in stream_name and inner_data.get("e") == "trade":
                await self._handle_trade(inner_data)
            elif "@ticker" in stream_name and inner_data.get("e") == "24hrTicker":
                await self._handle_ticker(inner_data)
        else:
            # Fallback for non-combined stream format
            if data.get("e") == "trade":
                await self._handle_trade(data)
            elif data.get("e") == "24hrTicker":
                await self._handle_ticker(data)
    
    async def _handle_trade(self, data: Dict):
        """Handle trade event."""
        try:
            # Extract timestamp
            trade_timestamp = datetime.fromtimestamp(
                data["T"] / 1000,  # Convert ms to seconds
                tz=timezone.utc
            )
            
            # Extract and normalize tick data
            tick = {
                "symbol": data["s"],
                "price": float(data["p"]),
                "qty": float(data["q"]),
                "ts": trade_timestamp.isoformat(),
            }
            
            # Store in database (async to avoid blocking)
            try:
                insert_tick(
                    symbol=tick["symbol"],
                    price=tick["price"],
                    volume=tick["qty"],
                    timestamp=trade_timestamp.replace(tzinfo=None)  # SQLite uses naive datetime
                )
            except Exception as db_error:
                log.error(f"Database insert failed for {self.symbol}: {db_error}")
            
            # Call the tick handler
            await self.on_tick(tick)
            
        except KeyError as e:
            log.error(f"Missing field in trade message for {self.symbol}: {e}")
        except ValueError as e:
            log.error(f"Invalid value in trade message for {self.symbol}: {e}")
        except Exception as e:
            log.error(f"Error handling trade message for {self.symbol}: {e}")
    
    async def _handle_ticker(self, data: Dict):
        """Handle 24h ticker event."""
        if not self.on_ticker:
            return
            
        try:
            # Extract 24h ticker stats
            ticker = {
                "symbol": data["s"],
                "priceChange": float(data["p"]),
                "priceChangePercent": float(data["P"]),
                "lastPrice": float(data["c"]),
                "openPrice": float(data["o"]),
                "highPrice": float(data["h"]),
                "lowPrice": float(data["l"]),
                "volume": float(data["v"]),
                "quoteVolume": float(data["q"]),
                "ts": datetime.fromtimestamp(
                    data["E"] / 1000,
                    tz=timezone.utc
                ).isoformat(),
            }
            
            # Call the ticker handler
            await self.on_ticker(ticker)
            
        except KeyError as e:
            log.error(f"Missing field in ticker message for {self.symbol}: {e}")
        except ValueError as e:
            log.error(f"Invalid value in ticker message for {self.symbol}: {e}")
        except Exception as e:
            log.error(f"Error handling ticker message for {self.symbol}: {e}")
    
    async def disconnect(self):
        """Stop the WebSocket connection gracefully."""
        self.is_running = False
        
        if self.websocket and not self.websocket.closed:
            await self.websocket.close()
        
        if self.task and not self.task.done():
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        
        log.info(f"Disconnected WebSocket for {self.symbol}")


class WebSocketManager:
    """
    Manages multiple Binance WebSocket connections.
    Handles symbol subscription/unsubscription and connection lifecycle.
    """
    
    def __init__(self, on_tick: Callable, on_ticker: Optional[Callable] = None):
        """
        Initialize WebSocket manager.
        
        Args:
            on_tick: Callback function to handle incoming ticks from all symbols
            on_ticker: Optional callback for 24h ticker updates
        """
        self.on_tick = on_tick
        self.on_ticker = on_ticker
        self.clients: Dict[str, BinanceWebSocketClient] = {}
    
    async def subscribe(self, symbol: str):
        """
        Subscribe to a symbol's tick stream.
        
        Args:
            symbol: Trading symbol to subscribe
        """
        symbol = normalize_symbol(symbol)
        
        if symbol in self.clients:
            log.warning(f"Already subscribed to {symbol}")
            return
        
        # Create and start new client
        client = BinanceWebSocketClient(symbol, self.on_tick, self.on_ticker)
        await client.connect()
        self.clients[symbol] = client
        log.info(f"Subscribed to {symbol}")
    
    async def unsubscribe(self, symbol: str):
        """
        Unsubscribe from a symbol's tick stream.
        
        Args:
            symbol: Trading symbol to unsubscribe
        """
        symbol = normalize_symbol(symbol)
        
        if symbol not in self.clients:
            log.warning(f"Not subscribed to {symbol}")
            return
        
        # Stop and remove client
        await self.clients[symbol].disconnect()
        del self.clients[symbol]
        log.info(f"Unsubscribed from {symbol}")
    
    async def subscribe_multiple(self, symbols: list[str]):
        """Subscribe to multiple symbols concurrently."""
        tasks = [self.subscribe(symbol) for symbol in symbols]
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def unsubscribe_multiple(self, symbols: list[str]):
        """Unsubscribe from multiple symbols concurrently."""
        tasks = [self.unsubscribe(symbol) for symbol in symbols]
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def disconnect_all(self):
        """Disconnect all active WebSocket connections."""
        symbols = list(self.clients.keys())
        await self.unsubscribe_multiple(symbols)
        log.info("All WebSocket connections closed")
    
    def get_active_symbols(self) -> list[str]:
        """Get list of currently subscribed symbols."""
        return list(self.clients.keys())
    
    def is_subscribed(self, symbol: str) -> bool:
        """Check if subscribed to a symbol."""
        return normalize_symbol(symbol) in self.clients
