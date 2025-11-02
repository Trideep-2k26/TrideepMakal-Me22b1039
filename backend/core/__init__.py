"""Core package initialization."""
from .websocket_client import BinanceWebSocketClient, WebSocketManager
from .data_manager import DataManager, data_manager
from .analytics import AnalyticsEngine, analytics_engine
from .alerts_engine import AlertsEngine, alerts_engine, Alert, AlertNotification

__all__ = [
    "BinanceWebSocketClient",
    "WebSocketManager",
    "DataManager",
    "data_manager",
    "AnalyticsEngine",
    "analytics_engine",
    "AlertsEngine",
    "alerts_engine",
    "Alert",
    "AlertNotification",
]
