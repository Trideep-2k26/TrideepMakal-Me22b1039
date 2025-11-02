"""API package initialization."""
from .routes_data import router as data_router
from .routes_analytics import router as analytics_router
from .routes_alerts import router as alerts_router
from .routes_export import router as export_router
from .routes_stream import router as stream_router
from .routes_visualization import router as visualization_router
from .routes_database import router as database_router

__all__ = [
    "data_router",
    "analytics_router",
    "alerts_router",
    "export_router",
    "stream_router",
    "visualization_router",
    "database_router",
]
