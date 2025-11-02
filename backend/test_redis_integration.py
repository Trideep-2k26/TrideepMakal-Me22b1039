"""
Integration tests for the in-memory data pipeline.
Validates that the data manager stores ticks and the analytics engine
produces metrics without relying on Redis.
"""
from datetime import datetime, timedelta, timezone

import pytest

from core import data_manager, analytics_engine


def _iso(ts: datetime) -> str:
    """Return ISO timestamp string with Z suffix."""
    return ts.replace(microsecond=0).isoformat().replace("+00:00", "Z")


@pytest.mark.asyncio
async def test_data_manager_tick_flow():
    symbol = "TESTAUSDT"
    data_manager.clear_buffer(symbol)

    base_time = datetime.now(timezone.utc) - timedelta(seconds=5)
    ticks = []
    for i in range(5):
        ts = _iso(base_time + timedelta(seconds=i))
        tick = {
            "symbol": symbol,
            "price": 100.0 + i,
            "qty": 1.0 + i * 0.1,
            "ts": ts,
        }
        ticks.append(tick)
        await data_manager.add_tick(tick)

    stored_ticks = await data_manager.get_ticks(symbol)
    assert len(stored_ticks) == len(ticks)
    assert stored_ticks[-1]["price"] == ticks[-1]["price"]

    active_symbols = data_manager.get_active_symbols()
    assert symbol in active_symbols

    candles = await data_manager.get_ohlcv(symbol, "1s", limit=5)
    assert len(candles) > 0

    data_manager.clear_buffer(symbol)


@pytest.mark.asyncio
async def test_analytics_engine_pair_computation():
    symbol_a = "PAIR_AUSDT"
    symbol_b = "PAIR_BUSDT"
    data_manager.clear_buffer(symbol_a)
    data_manager.clear_buffer(symbol_b)

    base_time = datetime.now(timezone.utc) - timedelta(seconds=300)
    for i in range(120):
        ts = _iso(base_time + timedelta(seconds=i))
        tick_a = {
            "symbol": symbol_a,
            "price": 100.0 + i * 0.2,
            "qty": 1.0,
            "ts": ts,
        }
        tick_b = {
            "symbol": symbol_b,
            "price": 50.0 + i * 0.15,
            "qty": 1.0,
            "ts": ts,
        }
        await data_manager.add_tick(tick_a)
        await data_manager.add_tick(tick_b)

    analytics = analytics_engine.compute_pair_analytics(
        f"{symbol_a}-{symbol_b}", timeframe="1s", window=30, regression="OLS"
    )

    assert analytics.get("hedge_ratio")
    assert analytics.get("spread")
    assert analytics.get("zscore")

    data_manager.clear_buffer(symbol_a)
    data_manager.clear_buffer(symbol_b)
