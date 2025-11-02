"""
Quick test script for SQLite database implementation.

Run this to verify the database module works correctly.
"""
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from datetime import datetime, timedelta
from core.db import MarketDatabase


def test_database():
    """Test all database functionality."""
    print("=" * 60)
    print("SQLite Database Module Test")
    print("=" * 60)
    
    # Initialize database
    print("\n1. Initializing database...")
    db = MarketDatabase("test_market_data.db")
    db.init_db()
    print("   ✓ Database initialized")
    
    # Clear any existing data
    print("\n2. Clearing existing data...")
    db.clear_all_data()
    print("   ✓ Database cleared")
    
    # Insert sample ticks
    print("\n3. Inserting sample ticks...")
    base_time = datetime.utcnow() - timedelta(minutes=10)
    
    for i in range(600):  # 10 minutes of data at 1 tick/second
        timestamp = base_time + timedelta(seconds=i)
        
        # Simulate realistic price movement
        price = 50000 + (i * 0.5) + (i % 10) * 10
        volume = 0.1 + (i % 5) * 0.05
        
        db.insert_tick("BTCUSDT", price, volume, timestamp)
    
    print(f"   ✓ Inserted 600 ticks")
    
    # Get database stats
    print("\n4. Database statistics...")
    stats = db.get_database_stats()
    print(f"   Total ticks: {stats['total_ticks']}")
    print(f"   Symbols: {list(stats['symbol_counts'].keys())}")
    print(f"   Time range: {stats['time_range']['start']} to {stats['time_range']['end']}")
    print(f"   Database size: {stats['database_size_mb']} MB")
    
    # Query raw ticks
    print("\n5. Querying raw ticks...")
    ticks_df = db.get_ticks("BTCUSDT", limit=10)
    print(f"   ✓ Retrieved {len(ticks_df)} ticks")
    print("\n   Sample data:")
    print(ticks_df[['timestamp', 'price', 'volume']].head())
    
    # Test resampling - 1 minute candles
    print("\n6. Resampling to 1-minute candles...")
    ohlcv_1m = db.get_resampled_data("BTCUSDT", "1T")
    print(f"   ✓ Created {len(ohlcv_1m)} candles")
    print("\n   Sample OHLCV:")
    print(ohlcv_1m[['ts', 'open', 'high', 'low', 'close', 'volume']].head())
    
    # Test resampling - 5 minute candles
    print("\n7. Resampling to 5-minute candles...")
    ohlcv_5m = db.get_resampled_data("BTCUSDT", "5T")
    print(f"   ✓ Created {len(ohlcv_5m)} candles")
    
    # Export to CSV
    print("\n8. Exporting to CSV...")
    csv_path = db.export_to_csv("BTCUSDT", "1T")
    print(f"   ✓ Exported to: {csv_path}")
    
    # Test batch insert
    print("\n9. Testing batch insert...")
    batch_ticks = []
    for i in range(100):
        timestamp = datetime.utcnow() + timedelta(seconds=i)
        batch_ticks.append(("ETHUSDT", 3000.0 + i, 0.5, timestamp))
    
    count = db.insert_ticks_batch(batch_ticks)
    print(f"   ✓ Batch inserted {count} ticks")
    
    # Final stats
    print("\n10. Final statistics...")
    final_stats = db.get_database_stats()
    print(f"   Total ticks: {final_stats['total_ticks']}")
    print(f"   Symbols: {list(final_stats['symbol_counts'].keys())}")
    for symbol, count in final_stats['symbol_counts'].items():
        print(f"      - {symbol}: {count} ticks")
    
    # Test cleanup
    print("\n11. Testing old data cleanup...")
    deleted = db.delete_old_data(hours=0.1)  # Delete data older than 6 minutes
    print(f"   ✓ Deleted {deleted} old ticks")
    
    # Vacuum database
    print("\n12. Optimizing database...")
    db.vacuum()
    print("   ✓ Database optimized")
    
    print("\n" + "=" * 60)
    print("✅ All tests passed successfully!")
    print("=" * 60)
    
    # Cleanup test database
    import os
    if os.path.exists("test_market_data.db"):
        os.remove("test_market_data.db")
        print("\n✓ Test database cleaned up")


if __name__ == "__main__":
    try:
        test_database()
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
