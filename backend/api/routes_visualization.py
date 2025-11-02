"""Visualization endpoints providing Plotly-ready chart specifications."""
from __future__ import annotations

from typing import Optional, Sequence

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from utils import log, settings, normalize_symbol
from core import data_manager
from visualization.candlestick import MovingAverageSpec, plot_candles

router = APIRouter(prefix="/visualization", tags=["visualization"])

_PALETTE = [
    "#f59e0b",
    "#8b5cf6",
    "#38bdf8",
    "#14b8a6",
    "#f97316",
    "#ec4899",
]


def _parse_ma_specs(ma_param: Optional[str]) -> Optional[Sequence[MovingAverageSpec]]:
    """Parse a comma-delimited moving-average window string."""
    if not ma_param:
        return None

    specs: list[MovingAverageSpec] = []
    for idx, token in enumerate(ma_param.split(",")):
        token = token.strip()
        if not token:
            continue
        try:
            window = int(token)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid moving average window: '{token}'"
            )
        if window <= 0:
            raise HTTPException(
                status_code=400,
                detail="Moving average windows must be positive integers",
            )
        color = _PALETTE[idx % len(_PALETTE)]
        specs.append(MovingAverageSpec(window=window, name=f"MA {window}", color=color))

    return specs if specs else None


@router.get("/candles/{symbol}")
async def get_candlestick_chart(
    symbol: str,
    tf: str = Query("1m", description="Timeframe (1s, 1m, 5m)"),
    limit: Optional[int] = Query(200, ge=1, le=2000, description="Maximum candles"),
    from_ts: Optional[str] = Query(None, alias="from", description="ISO start timestamp"),
    to_ts: Optional[str] = Query(None, alias="to", description="ISO end timestamp"),
    ma: Optional[str] = Query(None, description="Comma-separated moving average windows (e.g. '7,25,99')"),
):
    """Return a Plotly candlestick chart spec for the requested symbol."""

    normalized = normalize_symbol(symbol)

    if normalized not in settings.symbols_list:
        raise HTTPException(
            status_code=400,
            detail=f"Symbol {normalized} not supported. Available: {settings.symbols_list}",
        )

    if tf not in settings.resample_intervals_list:
        raise HTTPException(
            status_code=400,
            detail=f"Timeframe {tf} not supported. Available: {settings.resample_intervals_list}",
        )

    candles = await data_manager.get_ohlcv(
        symbol=normalized,
        timeframe=tf,
        limit=limit,
        from_ts=from_ts,
        to_ts=to_ts,
    )

    if not candles:
        raise HTTPException(status_code=404, detail="No OHLCV data available")

    df = pd.DataFrame(candles)
    if df.empty:
        raise HTTPException(status_code=404, detail="No OHLCV data available")

    if "volume" not in df.columns:
        df["volume"] = 0.0

    df = df.rename(columns={"ts": "timestamp"})

    # Ensure column ordering expected by plot_candles
    df = df[["timestamp", "open", "high", "low", "close", "volume"]]

    ma_specs = _parse_ma_specs(ma)

    try:
        figure = (
            plot_candles(df, timeframe=tf, moving_averages=ma_specs)
            if ma_specs
            else plot_candles(df, timeframe=tf)
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive logging
        log.exception("Failed to build candlestick figure")
        raise HTTPException(status_code=500, detail="Failed to render chart") from exc

    payload = figure.to_dict()
    payload.setdefault("layout", {})
    payload["layout"].setdefault("title", {"text": f"{normalized} @ {tf}"})

    return payload
