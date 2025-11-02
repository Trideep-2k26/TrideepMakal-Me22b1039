"""
Configuration management for the Quant Analytics backend.
Loads settings from environment variables with sensible defaults.
"""
import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Server Configuration
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    
    # Data Configuration
    tick_buffer_size: int = Field(default=10000, env="TICK_BUFFER_SIZE")
    resample_intervals: str = Field(default="1s,1m,5m", env="RESAMPLE_INTERVALS")
    max_symbols: int = Field(default=2, env="MAX_SYMBOLS")
    
    # Binance WebSocket
    binance_ws_base: str = Field(
        default="wss://fstream.binance.com/ws",
        env="BINANCE_WS_BASE"
    )
    
    # Available Symbols
    available_symbols: str = Field(
        default="BTCUSDT,ETHUSDT,BNBUSDT,SOLUSDT,ADAUSDT",
        env="AVAILABLE_SYMBOLS"
    )
    
    # Analytics Configuration
    default_rolling_window: int = Field(default=60, env="DEFAULT_ROLLING_WINDOW")
    default_regression: str = Field(default="OLS", env="DEFAULT_REGRESSION")
    
    # CORS
    cors_origins: str = Field(
        default="http://localhost:8080,http://localhost:8081,http://localhost:8082,http://localhost:3000,http://localhost:5173",
        env="CORS_ORIGINS"
    )
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    @property
    def symbols_list(self) -> List[str]:
        """Parse available symbols as list."""
        return [s.strip().upper() for s in self.available_symbols.split(",")]
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins as list."""
        return [o.strip() for o in self.cors_origins.split(",")]
    
    @property
    def resample_intervals_list(self) -> List[str]:
        """Parse resample intervals as list."""
        return [i.strip() for i in self.resample_intervals.split(",")]


# Global settings instance
settings = Settings()
