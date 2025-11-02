"""
SQLite Database Module for Market Data Storage

Provides persistent storage for tick data with resampling capabilities.
Uses SQLite3 from Python standard library - no external dependencies needed.
"""

import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Tuple
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)


class MarketDatabase:
    """
    SQLite database manager for market tick data.
    
    Provides methods for:
    - Storing real-time tick data
    - Querying historical data
    - Resampling to OHLCV format
    - Data retention management
    """
    
    def __init__(self, db_path: str = "market_data.db"):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Database initialized at: {self.db_path}")
        
    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections.
        
        Ensures proper connection cleanup and auto-commit.
        """
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database transaction failed: {e}")
            raise
        finally:
            conn.close()
    
    def init_db(self) -> None:
        """
        Initialize database schema.
        
        Creates the 'ticks' table if it doesn't exist.
        Includes indexes for efficient querying by symbol and timestamp.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Create ticks table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ticks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    symbol TEXT NOT NULL,
                    price REAL NOT NULL,
                    volume REAL NOT NULL
                )
            """)
            
            # Create indexes for fast queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_symbol_timestamp 
                ON ticks(symbol, timestamp)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON ticks(timestamp)
            """)
            
            logger.info("Database schema initialized successfully")
    
    def insert_tick(
        self, 
        symbol: str, 
        price: float, 
        volume: float, 
        timestamp: Optional[datetime] = None
    ) -> int:
        """
        Insert a single tick into the database.
        
        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT')
            price: Trade price
            volume: Trade volume
            timestamp: Trade timestamp (defaults to now if None)
            
        Returns:
            Row ID of inserted tick
        """
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO ticks (timestamp, symbol, price, volume) VALUES (?, ?, ?, ?)",
                (timestamp, symbol, price, volume)
            )
            row_id = cursor.lastrowid
            
        return row_id
    
    def insert_ticks_batch(
        self, 
        ticks: List[Tuple[str, float, float, datetime]]
    ) -> int:
        """
        Batch insert multiple ticks for better performance.
        
        Args:
            ticks: List of (symbol, price, volume, timestamp) tuples
            
        Returns:
            Number of rows inserted
        """
        if not ticks:
            return 0
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(
                "INSERT INTO ticks (symbol, price, volume, timestamp) VALUES (?, ?, ?, ?)",
                ticks
            )
            count = cursor.rowcount
            
        logger.info(f"Batch inserted {count} ticks")
        return count
    
    def get_ticks(
        self,
        symbol: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Fetch tick data for a given symbol and time range.
        
        Args:
            symbol: Trading symbol
            start_time: Start of time range (inclusive)
            end_time: End of time range (inclusive)
            limit: Maximum number of rows to return
            
        Returns:
            DataFrame with columns: timestamp, symbol, price, volume
        """
        query = "SELECT timestamp, symbol, price, volume FROM ticks WHERE symbol = ?"
        params = [symbol]
        
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time)
        
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time)
        
        query += " ORDER BY timestamp ASC"
        
        if limit:
            query += f" LIMIT {limit}"
        
        with self.get_connection() as conn:
            df = pd.read_sql_query(query, conn, params=params)
        
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            logger.info(f"Fetched {len(df)} ticks for {symbol}")
        else:
            logger.warning(f"No ticks found for {symbol}")
        
        return df
    
    def get_resampled_data(
        self,
        symbol: str,
        timeframe: str = '1T',
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> pd.DataFrame:
        """
        Resample tick data into OHLCV format.
        
        Supported timeframes:
        - '1S': 1 second
        - '1T' or '1min': 1 minute
        - '5T' or '5min': 5 minutes
        - '15T' or '15min': 15 minutes
        - '30T' or '30min': 30 minutes
        - '1H': 1 hour
        - '1D': 1 day
        
        Args:
            symbol: Trading symbol
            timeframe: Pandas resample frequency string
            start_time: Start of time range
            end_time: End of time range
            
        Returns:
            DataFrame with OHLCV columns and timestamp index
        """
        # Fetch raw tick data
        df = self.get_ticks(symbol, start_time, end_time)
        
        if df.empty:
            logger.warning(f"No data available for resampling {symbol} at {timeframe}")
            return pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])
        
        # Set timestamp as index for resampling
        df.set_index('timestamp', inplace=True)
        
        # Resample to OHLCV
        ohlcv = df['price'].resample(timeframe).ohlc()  # open, high, low, close
        volume = df['volume'].resample(timeframe).sum()  # total volume
        
        # Combine into single DataFrame
        result = ohlcv.copy()
        result['volume'] = volume
        
        # Drop rows with no data (NaN)
        result.dropna(subset=['open'], inplace=True)
        
        # Reset index to make timestamp a column
        result.reset_index(inplace=True)
        result.rename(columns={'timestamp': 'ts'}, inplace=True)
        
        logger.info(f"Resampled {symbol} to {timeframe}: {len(result)} candles")
        
        return result
    
    def delete_old_data(self, hours: int = 24) -> int:
        """
        Delete ticks older than specified retention period.
        
        Args:
            hours: Retention period in hours (default: 24)
            
        Returns:
            Number of rows deleted
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM ticks WHERE timestamp < ?",
                (cutoff_time,)
            )
            deleted_count = cursor.rowcount
        
        logger.info(f"Deleted {deleted_count} ticks older than {hours} hours")
        return deleted_count
    
    def get_database_stats(self) -> dict:
        """
        Get statistics about the database.
        
        Returns:
            Dictionary with database metrics
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Total tick count
            cursor.execute("SELECT COUNT(*) FROM ticks")
            total_ticks = cursor.fetchone()[0]
            
            # Ticks per symbol
            cursor.execute("""
                SELECT symbol, COUNT(*) as count 
                FROM ticks 
                GROUP BY symbol
            """)
            symbol_counts = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Time range
            cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM ticks")
            min_time, max_time = cursor.fetchone()
            
            # Database file size
            db_size_mb = self.db_path.stat().st_size / (1024 * 1024) if self.db_path.exists() else 0
        
        return {
            "total_ticks": total_ticks,
            "symbol_counts": symbol_counts,
            "time_range": {
                "start": min_time,
                "end": max_time
            },
            "database_size_mb": round(db_size_mb, 2)
        }
    
    def export_to_csv(
        self,
        symbol: str,
        timeframe: str,
        output_path: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> str:
        """
        Export resampled data to CSV file.
        
        Args:
            symbol: Trading symbol
            timeframe: Resample frequency
            output_path: Custom output path (defaults to data/{symbol}_{timeframe}.csv)
            start_time: Start of time range
            end_time: End of time range
            
        Returns:
            Path to exported CSV file
        """
        # Get resampled data
        df = self.get_resampled_data(symbol, timeframe, start_time, end_time)
        
        if df.empty:
            logger.warning(f"No data to export for {symbol} at {timeframe}")
            return ""
        
        # Determine output path
        if output_path is None:
            output_dir = Path("data/exports")
            output_dir.mkdir(parents=True, exist_ok=True)
            timestamp_str = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            output_path = output_dir / f"{symbol}_{timeframe}_{timestamp_str}.csv"
        else:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Export to CSV
        df.to_csv(output_path, index=False)
        logger.info(f"Exported {len(df)} rows to {output_path}")
        
        return str(output_path)
    
    def vacuum(self) -> None:
        """
        Optimize database by reclaiming unused space.
        
        Should be called periodically after large deletions.
        """
        with self.get_connection() as conn:
            conn.execute("VACUUM")
        
        logger.info("Database vacuum completed")
    
    def clear_all_data(self) -> None:
        """
        Delete all tick data from database.
        
        WARNING: This is irreversible!
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM ticks")
            deleted = cursor.rowcount
        
        logger.warning(f"Cleared all data: {deleted} ticks deleted")
        self.vacuum()


# Singleton instance
_db_instance: Optional[MarketDatabase] = None


def get_db(db_path: str = "market_data.db") -> MarketDatabase:
    """
    Get or create singleton database instance.
    
    Args:
        db_path: Path to database file
        
    Returns:
        MarketDatabase instance
    """
    global _db_instance
    if _db_instance is None:
        _db_instance = MarketDatabase(db_path)
        _db_instance.init_db()
    return _db_instance


# Convenience functions for direct access

def init_db(db_path: str = "market_data.db") -> None:
    """Initialize database schema."""
    db = get_db(db_path)
    db.init_db()


def insert_tick(
    symbol: str, 
    price: float, 
    volume: float, 
    timestamp: Optional[datetime] = None
) -> int:
    """Insert a single tick into the database."""
    db = get_db()
    return db.insert_tick(symbol, price, volume, timestamp)


def insert_ticks_batch(ticks: List[Tuple[str, float, float, datetime]]) -> int:
    """Batch insert multiple ticks."""
    db = get_db()
    return db.insert_ticks_batch(ticks)


def get_ticks(
    symbol: str,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: Optional[int] = None
) -> pd.DataFrame:
    """Fetch tick data for a symbol."""
    db = get_db()
    return db.get_ticks(symbol, start_time, end_time, limit)


def get_resampled_data(
    symbol: str,
    timeframe: str = '1T',
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None
) -> pd.DataFrame:
    """Get resampled OHLCV data."""
    db = get_db()
    return db.get_resampled_data(symbol, timeframe, start_time, end_time)


def delete_old_data(hours: int = 24) -> int:
    """Delete ticks older than specified hours."""
    db = get_db()
    return db.delete_old_data(hours)


def export_to_csv(
    symbol: str,
    timeframe: str,
    output_path: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None
) -> str:
    """Export resampled data to CSV."""
    db = get_db()
    return db.export_to_csv(symbol, timeframe, output_path, start_time, end_time)


def get_database_stats() -> dict:
    """Get database statistics."""
    db = get_db()
    return db.get_database_stats()


if __name__ == "__main__":
    # Example usage and testing
    logging.basicConfig(level=logging.INFO)
    
    # Initialize database
    db = MarketDatabase("test_market_data.db")
    db.init_db()
    
    # Insert sample data
    print("Inserting sample ticks...")
    for i in range(100):
        timestamp = datetime.utcnow() - timedelta(seconds=100-i)
        price = 50000 + (i * 10)
        volume = 0.1 + (i * 0.01)
        db.insert_tick("BTCUSDT", price, volume, timestamp)
    
    # Get stats
    stats = db.get_database_stats()
    print(f"\nDatabase Stats: {stats}")
    
    # Get resampled data
    print("\nResampling to 1-minute candles...")
    ohlcv = db.get_resampled_data("BTCUSDT", "1T")
    print(ohlcv.head())
    
    # Export to CSV
    print("\nExporting to CSV...")
    csv_path = db.export_to_csv("BTCUSDT", "1T")
    print(f"Exported to: {csv_path}")
    
    print("\n✅ Database module test completed!")
