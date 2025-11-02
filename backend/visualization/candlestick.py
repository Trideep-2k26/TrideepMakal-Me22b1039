"""Plotly candlestick utilities used by the Quant app.

This module exposes :func:`plot_candles` which mirrors the TradingView look-and-
feel, supports 1s/1m/5m resampling, and dynamically adjusts candle width based on
visible history. The figure works with Plotly in notebooks, Streamlit, or when
served to the React frontend.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Sequence

import numpy as np
import pandas as pd
import plotly.graph_objects as go

# Mapping between supported timeframes and pandas resample rules.
_TIMEFRAME_RULES = {
    "1s": "1s",
    "1m": "1min",
    "5m": "5min",
}


@dataclass(frozen=True)
class MovingAverageSpec:
    """Simple container describing a moving-average overlay."""

    window: int
    name: str
    color: str


_DEFAULT_MAS: Sequence[MovingAverageSpec] = (
    MovingAverageSpec(window=7, name="MA 7", color="#f59e0b"),
    MovingAverageSpec(window=25, name="MA 25", color="#8b5cf6"),
    MovingAverageSpec(window=99, name="MA 99", color="#38bdf8"),
)


def _resample(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    """Resample raw trade data to the requested timeframe.

    Parameters
    ----------
    df:
        Input DataFrame containing ``timestamp, open, high, low, close, volume``.
    timeframe:
        One of ``{"1s", "1m", "5m"}``. Defaults to ``1m`` when unsupported.
    """

    if df.empty:
        return df.copy()

    rule = _TIMEFRAME_RULES.get(timeframe, _TIMEFRAME_RULES["1m"])

    working = df.copy()
    if not np.issubdtype(working["timestamp"].dtype, np.datetime64):
        working["timestamp"] = pd.to_datetime(working["timestamp"], utc=True)

    working = working.set_index("timestamp").sort_index()

    ohlcv = working.resample(rule).agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        volume=("volume", "sum"),
    )

    # Forward-fill missing closes so line overlays stay continuous.
    ohlcv["close"] = ohlcv["close"].ffill()

    # Drop rows without trading activity.
    ohlcv = ohlcv.dropna(subset=["open", "high", "low", "close"], how="all")

    return ohlcv.reset_index()


def _compute_candle_width(index: pd.Index) -> Optional[float]:
    """Return an initial candle width in milliseconds.

    Plotly's candlestick width is expressed in milliseconds for date axes.
    We derive a width proportional to the mean distance between candles. When
    users zoom, we will recompute the width from the new visible range.
    """

    if len(index) < 2:
        return None

    # Typical spacing between consecutive timestamps.
    deltas = index.to_series().diff().dropna()
    if deltas.empty:
        return None

    avg_ms = deltas.mean() / pd.Timedelta(milliseconds=1)
    # We keep the body slightly thinner than the gap to mimic TradingView.
    return float(avg_ms * 0.75)


def _add_moving_averages(
    fig: go.Figure, df: pd.DataFrame, moving_averages: Sequence[MovingAverageSpec]
) -> None:
    closes = df["close"].astype(float)
    index = df["timestamp"]

    for ma in moving_averages:
        if len(closes) < ma.window:
            continue
        ma_values = closes.rolling(ma.window).mean()
        fig.add_trace(
            go.Scatter(
                x=index,
                y=ma_values,
                name=ma.name,
                mode="lines",
                line=dict(color=ma.color, width=1.6),
                hoverinfo="skip",
            )
        )


def plot_candles(
    df: pd.DataFrame,
    timeframe: str = "1m",
    moving_averages: Sequence[MovingAverageSpec] = _DEFAULT_MAS,
    title: Optional[str] = None,
) -> go.Figure:
    """Return a dark-themed Plotly candlestick chart with dynamic width.

    Parameters
    ----------
    df:
        DataFrame with columns ``timestamp, open, high, low, close, volume``.
    timeframe:
        Resampling interval ("1s", "1m", "5m").
    moving_averages:
        Optional sequence describing MA overlays.
    title:
        Optional chart title.

    Notes
    -----
    * Candle width is derived from the mean distance between timestamps.
      When embedding in Streamlit, pair this figure with ``plotly_events`` and
      recompute ``trace.width`` on ``relayout"`` events to keep widths in sync as
      users zoom. The figure exposes ``layout.meta['baseCandleWidthMs']`` for
      convenience.
    * ``layout.uirevision`` keeps zoom level while updating data in real time.
    """

    if df.empty:
        raise ValueError("plot_candles expects a non-empty DataFrame")

    ohlcv = _resample(df, timeframe)
    if ohlcv.empty:
        raise ValueError("No data available after resampling")

    ohlcv["timestamp"] = pd.to_datetime(ohlcv["timestamp"], utc=True)

    candle_width = _compute_candle_width(ohlcv["timestamp"])

    fig = go.Figure()

    fig.add_trace(
        go.Candlestick(
            x=ohlcv["timestamp"],
            open=ohlcv["open"],
            high=ohlcv["high"],
            low=ohlcv["low"],
            close=ohlcv["close"],
            increasing=dict(line=dict(color="#10b981", width=1.2)),
            decreasing=dict(line=dict(color="#ef4444", width=1.2)),
            name="Price",
            hovertext=[ts.strftime("%Y-%m-%d %H:%M:%S") for ts in ohlcv["timestamp"]],
            hovertemplate=(
                "<b>%{hovertext}</b><br>Open: %{open:.2f}<br>High: %{high:.2f}<br>"
                "Low: %{low:.2f}<br>Close: %{close:.2f}<extra></extra>"
            ),
            width=candle_width,
        )
    )

    colors = np.where(ohlcv["close"] >= ohlcv["open"], "rgba(16,185,129,0.7)", "rgba(239,68,68,0.7)")
    fig.add_trace(
        go.Bar(
            x=ohlcv["timestamp"],
            y=ohlcv["volume"],
            name="Volume",
            marker=dict(color=colors, line=dict(width=0)),
            opacity=0.8,
            yaxis="y2",
            width=candle_width,
            hoverinfo="skip",
        )
    )

    if moving_averages:
        _add_moving_averages(fig, ohlcv, moving_averages)

    fig.update_layout(
        title=dict(text=title, font=dict(color="#e2e8f0")) if title else None,
        paper_bgcolor="#0f172a",
        plot_bgcolor="#0f172a",
        hovermode="x unified",
        uirevision="candles",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    font=dict(color="#cbd5f5")),
        margin=dict(l=60, r=40, t=40, b=40),
        xaxis=dict(
            type="date",
            rangeslider=dict(visible=False),
            showgrid=True,
            gridcolor="#1f2a44",
            zeroline=False,
            showspikes=True,
            spikecolor="#38bdf8",
            spikemode="across",
            spikethickness=1,
            color="#cbd5f5",
        ),
        yaxis=dict(
            title="Price",
            showgrid=True,
            gridcolor="#1f2a44",
            zeroline=False,
            color="#cbd5f5",
            domain=[0.25, 1],
        ),
        yaxis2=dict(
            title="Volume",
            showgrid=False,
            zeroline=False,
            color="#94a3b8",
            domain=[0, 0.2],
        ),
        bargap=0,
    )

    fig.layout.meta = fig.layout.meta or {}
    fig.layout.meta["baseCandleWidthMs"] = candle_width

    # Comments for streamlit/callback usage are embedded here for quick reference.
    fig.add_annotation(
        text=(
            "Zoom & pan events can be captured via Plotly's relayout event. "
            "Recompute the candlestick trace's `width` using the helper in this "
            "module to maintain TradingView-style scaling."
        ),
        xref="paper",
        yref="paper",
        x=0,
        y=-0.18,
        showarrow=False,
        font=dict(size=10, color="#64748b"),
    )

    return fig


__all__ = ["plot_candles", "MovingAverageSpec"]
