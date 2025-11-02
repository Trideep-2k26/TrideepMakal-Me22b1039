import { useCallback, useEffect, useMemo, useState, memo, useRef } from 'react';
import Plot from 'react-plotly.js';
import { ArrowDownRight, ArrowUpRight, Dot, Star, StarOff } from 'lucide-react';
import type { PlotData, PlotRelayoutEvent, PlotlyHTMLElement } from 'plotly.js';

import { Card, CardContent, CardHeader } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { AssetLogo } from './AssetLogo';

import { cn } from '@/lib/utils';
import {
  formatCompactCurrency,
  formatCompactNumber,
  formatNumber,
  formatPrice,
  formatSignedPercent,
} from '@/utils/formatters';
import { getAssetMeta } from '@/utils/assets';

const MOVING_AVERAGE_WINDOWS = [7, 25, 99] as const;
const MOVING_AVERAGE_COLORS = ['#facc15', '#c084fc', '#60a5fa']; // Yellow, purple, blue like Binance
const DEFAULT_TIMEFRAME_OPTIONS = [
  { value: '1s', label: '1s' },
  { value: '1m', label: '1m' },
  { value: '5m', label: '5m' },
  { value: '15m', label: '15m' },
  { value: '30m', label: '30m' },
  { value: '1h', label: '1h' },
  { value: '14h', label: '14h' },
] as const;

type TimeframeOption = typeof DEFAULT_TIMEFRAME_OPTIONS[number];

type PriceData = {
  ts: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
};

type TickerSnapshot = {
  priceChange: number;
  priceChangePercent: number;
  lastPrice: number;
  openPrice: number;
  highPrice: number;
  lowPrice: number;
  volume: number;
  quoteVolume: number;
};

interface PriceChartProps {
  data: PriceData[];
  symbol: string;
  timeframe: string;
  onTimeframeChange?: (value: string) => void;
  timeframeOptions?: ReadonlyArray<TimeframeOption>;
  isLive?: boolean;
  onStartLive?: () => void;
  onStopLive?: () => void;
  showLiveToggle?: boolean;
  tickerData?: TickerSnapshot | null;
}

const computeSMA = (values: number[], window: number): Array<number | null> => {
  const result: Array<number | null> = new Array(values.length).fill(null);
  if (window <= 0 || values.length === 0) {
    return result;
  }

  let sum = 0;
  for (let i = 0; i < values.length; i++) {
    sum += values[i];
    if (i >= window) {
      sum -= values[i - window];
    }
    if (i >= window - 1) {
      result[i] = sum / window;
    }
  }

  return result;
};
const computeCandleWidth = (timestamps: string[], timeframe: string): number | undefined => {
  if (!timestamps || timestamps.length < 2) return undefined;

  const deltas: number[] = [];
  for (let i = 1; i < timestamps.length; i++) {
    const current = Date.parse(timestamps[i]);
    const previous = Date.parse(timestamps[i - 1]);
    const delta = current - previous;
    if (Number.isFinite(delta) && delta > 0) {
      deltas.push(delta);
    }
  }

  if (deltas.length === 0) return undefined;

  const average = deltas.reduce((acc, value) => acc + value, 0) / deltas.length;
  
  // For 1s timeframe, keep thick candles (0.90)
  // For other timeframes (1m, 5m, etc.), make narrower candles (0.35)
  const widthMultiplier = timeframe === '1s' ? 0.90 : 0.35;
  
  return average * widthMultiplier;
};

interface ChartCanvasProps {
  data: PriceData[];
  symbol: string;
  timeframe: string;
}

const MAX_VISIBLE_CANDLES = 500;

const ChartCanvas = memo(({ data, symbol, timeframe }: ChartCanvasProps) => {
  const [candleWidth, setCandleWidth] = useState<number | undefined>();
  const prevDataRef = useRef<PriceData[]>([]);
  const plotRef = useRef<PlotlyHTMLElement | null>(null);

  const visibleData = useMemo<PriceData[]>(() => {
    if (!data || data.length === 0) return [];
    if (data.length <= MAX_VISIBLE_CANDLES) return data;
    return data.slice(data.length - MAX_VISIBLE_CANDLES);
  }, [data]);

  const dataLength = visibleData.length;

  useEffect(() => {
    if (!visibleData || dataLength < 2) {
      setCandleWidth(undefined);
      return;
    }

    if (dataLength < 10 || dataLength % 10 === 0) {
      const width = computeCandleWidth(visibleData.map(candle => candle.ts), timeframe);
      setCandleWidth(width);
    }
  }, [visibleData, dataLength, timeframe]);

  useEffect(() => {
    // Reset candle width when symbol or timeframe changes
    setCandleWidth(undefined);
  }, [symbol, timeframe]);

  const timestamps = useMemo(() => visibleData.map(candle => candle.ts), [visibleData]);

  const volumeColors = useMemo(() => {
    if (!visibleData || visibleData.length === 0) return [] as string[];
    return visibleData.map((candle, index) => {
      const previousClose = index > 0 ? visibleData[index - 1].close : candle.open;
      return candle.close >= previousClose
        ? 'rgba(14, 203, 129, 0.6)' // Binance green - more transparent for volume
        : 'rgba(246, 70, 93, 0.6)';  // Binance red - more transparent for volume
    });
  }, [visibleData]);

  const closingPrices = useMemo(() => visibleData.map(candle => candle.close), [visibleData]);

  const movingAverageTraces = useMemo<PlotData[]>(() => {
    if (!visibleData || visibleData.length === 0) return [];

    const overlays: PlotData[] = [];

    MOVING_AVERAGE_WINDOWS.forEach((window, index) => {
      if (visibleData.length < window) {
        return;
      }

      const series = computeSMA(closingPrices, window);
      const color = MOVING_AVERAGE_COLORS[index % MOVING_AVERAGE_COLORS.length];

      overlays.push({
        type: 'scatter',
        mode: 'lines',
        x: timestamps,
        y: series,
        name: `MA(${window})`, // Binance format
        line: { 
          color, 
          width: 1.5, // Thinner like Binance
          shape: 'linear', // Straight lines, not spline
        },
        hovertemplate: `MA(${window}): %{y:,.2f}<extra></extra>`,
        legendgroup: 'overlays',
        opacity: 0.9,
      } as PlotData);
    });

    return overlays;
  }, [closingPrices, timestamps, visibleData]);

  const chartData = useMemo<PlotData[]>(() => {
    if (!visibleData || visibleData.length === 0) return [];

    const baseTraces: PlotData[] = [
      {
        type: 'candlestick',
        x: timestamps,
        open: visibleData.map(d => d.open),
        high: visibleData.map(d => d.high),
        low: visibleData.map(d => d.low),
        close: visibleData.map(d => d.close),
        increasing: {
          line: { color: '#0ecb81', width: 2 }, // Thick borders like Binance
          fillcolor: '#0ecb81', // Solid green fill
        },
        decreasing: {
          line: { color: '#f6465d', width: 2 }, // Thick borders like Binance
          fillcolor: '#f6465d', // Solid red fill
        },
        hovertemplate:
          '<b>%{x|%H:%M:%S}</b><br>' +
          'O: <b>%{open:,.2f}</b> | ' +
          'H: <b>%{high:,.2f}</b><br>' +
          'L: <b>%{low:,.2f}</b> | ' +
          'C: <b>%{close:,.2f}</b><extra></extra>',
        name: symbol,
        legendgroup: 'price',
        width: candleWidth,
        whiskerwidth: 0.3, // Very thin wicks like Binance
      } as PlotData,
      {
        type: 'bar',
        x: timestamps,
        y: visibleData.map(d => d.volume || 0),
        marker: {
          color: volumeColors,
          line: { width: 0 },
        },
        opacity: 1, // Full opacity like Binance
        yaxis: 'y2',
        name: 'Volume',
        legendgroup: 'volume',
        width: candleWidth,
        hovertemplate: '<b>Vol:</b> %{y:,.3f}<extra></extra>',
      } as PlotData,
    ];

    return [...baseTraces, ...movingAverageTraces];
  }, [candleWidth, movingAverageTraces, symbol, timestamps, visibleData, volumeColors]);

  // Get current price for live price line
  const currentPrice = useMemo(() => {
    if (!visibleData || visibleData.length === 0) return null;
    return visibleData[visibleData.length - 1].close;
  }, [visibleData]);

  // Add live price indicator line
  const chartDataWithPriceLine = useMemo<PlotData[]>(() => {
    if (!currentPrice || !timestamps || timestamps.length === 0) return chartData;
    
    const priceLineTrace: PlotData = {
      type: 'scatter',
      mode: 'lines',
      x: [timestamps[0], timestamps[timestamps.length - 1]],
      y: [currentPrice, currentPrice],
      line: {
        color: '#facc15', // Binance yellow
        width: 2,
        dash: 'dot',
      },
      hovertemplate: `<b>Current Price:</b> $${currentPrice.toFixed(2)}<extra></extra>`,
      showlegend: false,
      name: 'Live Price',
    } as PlotData;
    
    return [...chartData, priceLineTrace];
  }, [chartData, currentPrice, timestamps]);

  const layout = useMemo(() => ({
    paper_bgcolor: '#161a1e', // Binance dark background
    plot_bgcolor: '#161a1e', // Match Binance exactly
    font: { color: '#848e9c', family: 'Roboto, sans-serif' }, // Binance font
    xaxis: {
      gridcolor: 'rgba(43, 47, 53, 0.5)', // Binance grid color
      showgrid: true,
      type: 'date' as const,
      zeroline: false,
      ticksuffix: ' ',
      rangeslider: { visible: false },
      showspikes: true,
      spikecolor: 'rgba(250, 204, 21, 0.6)',
      spikethickness: 1,
      spikemode: 'across',
      tickfont: { size: 11, color: '#848e9c' },
      tickformat: '%H:%M', // Show only time for intraday
    },
    yaxis: {
      gridcolor: 'rgba(43, 47, 53, 0.5)', // Binance grid color
      showgrid: true,
      zeroline: false,
      tickprefix: '',
      ticksuffix: ' ',
      domain: [0.22, 1], // More space for candles
      color: '#848e9c',
      tickfont: { size: 11, color: '#848e9c' },
      side: 'right' as const,
      fixedrange: false,
    },
    yaxis2: {
      domain: [0, 0.18], // Smaller volume area like Binance
      showgrid: false,
      zeroline: false,
      tickfont: { color: '#848e9c', size: 9 },
      ticksuffix: ' ',
      side: 'right' as const,
      fixedrange: false,
    },
    legend: {
      orientation: 'h',
      yanchor: 'top',
      y: 1,
      xanchor: 'left',
      x: 0,
      font: { color: '#848e9c', size: 10 },
      bgcolor: 'rgba(22, 26, 30, 0.0)',
    },
    margin: { l: 10, r: 65, t: 30, b: 35 }, // Binance margins
    height: 550, // Taller like Binance
    hovermode: 'x unified' as const,
    dragmode: 'pan' as const,
    showlegend: true,
    bargap: timeframe === '1s' ? 0.2 : 0.5, // Wider gap for non-1s timeframes to make candles appear narrower
    bargroupgap: 0,
    hoverlabel: {
      bgcolor: '#2b2f35',
      bordercolor: '#848e9c',
      font: { color: '#ffffff', size: 11 },
    },
    uirevision: `price-chart-${symbol}-${timeframe}`,
    transition: {
      duration: 0,
      easing: 'linear',
    },
  }), [symbol, timeframe]);

  const priceRange = useMemo(() => {
    if (!visibleData || visibleData.length === 0) {
      return null;
    }

    let min = Number.POSITIVE_INFINITY;
    let max = Number.NEGATIVE_INFINITY;

    for (const candle of visibleData) {
      if (candle.low < min) min = candle.low;
      if (candle.high > max) max = candle.high;
    }

    if (!Number.isFinite(min) || !Number.isFinite(max)) {
      return null;
    }

    const spread = Math.max(max - min, 1e-9);
    const pad = Math.max(spread * 0.05, max * 0.0005, 1e-6);
    const lower = min - pad;
    const upper = max + pad;

    return [lower, upper] as [number, number];
  }, [visibleData]);

  useEffect(() => {
    return () => {
      plotRef.current = null;
    };
  }, []);

  const config = useMemo(() => ({
    displayModeBar: true,
    displaylogo: false,
    responsive: true,
    scrollZoom: true,
    doubleClick: 'reset' as const,
    modeBarButtonsToRemove: ['lasso2d', 'select2d', 'toImage'],
    frameMargins: 0,
    staticPlot: false, // Allow interactions
  }), []);

  const handleRelayout = useCallback((event: PlotRelayoutEvent) => {
    const start = (event['xaxis.range[0]'] ?? event['xaxis.range0']) as string | undefined;
    const end = (event['xaxis.range[1]'] ?? event['xaxis.range1']) as string | undefined;

    if (!start || !end) {
      return;
    }

    const startMs = Date.parse(start);
    const endMs = Date.parse(end);

    if (!Number.isFinite(startMs) || !Number.isFinite(endMs) || endMs <= startMs) {
      return;
    }

    const visibleCandles = visibleData.filter(candle => {
      const ts = Date.parse(candle.ts);
      return Number.isFinite(ts) && ts >= startMs && ts <= endMs;
    });

    if (visibleCandles.length < 2) {
      return;
    }

    const updatedWidth = computeCandleWidth(visibleCandles.map(candle => candle.ts), timeframe);

    if (typeof updatedWidth === 'number' && Number.isFinite(updatedWidth)) {
      setCandleWidth(updatedWidth);
    }
  }, [visibleData, timeframe]);

  if (visibleData.length === 0) {
    return (
      <div className="h-[480px] flex items-center justify-center text-muted-foreground bg-slate-950/50 rounded-lg">
        <div className="text-center">
          <p className="text-lg">No data available</p>
          <p className="text-sm text-slate-500 mt-1">Start streaming to see live data</p>
        </div>
      </div>
    );
  }

  return (
    <Plot
      key={`chart-${symbol}-${timeframe}`}
      data={chartDataWithPriceLine}
      layout={layout}
      config={config}
      onInitialized={figure => {
        plotRef.current = figure as PlotlyHTMLElement;
      }}
      onUpdate={figure => {
        plotRef.current = figure as PlotlyHTMLElement;
      }}
      onRelayout={handleRelayout}
      style={{ width: '100%', height: '100%' }}
      useResizeHandler
      divId={`plotly-chart-${symbol}-${timeframe}`}
    />
  );
}, (prevProps, nextProps) => {
  // Custom comparison function to prevent unnecessary re-renders
  // Return TRUE to skip re-render (props are same)
  // Return FALSE to re-render (props changed)
  
  // Always re-render if symbol or timeframe changed
  if (prevProps.symbol !== nextProps.symbol || prevProps.timeframe !== nextProps.timeframe) {
    return false;
  }

  // If lengths differ by more than 2, update (new candles added)
  if (Math.abs(prevProps.data.length - nextProps.data.length) > 2) {
    return false;
  }

  // Empty arrays are equal
  if (prevProps.data.length === 0 && nextProps.data.length === 0) {
    return true;
  }

  // If no data, don't update
  if (prevProps.data.length === 0 || nextProps.data.length === 0) {
    return false;
  }

  // Compare last candle to detect meaningful changes
  const prevLast = prevProps.data[prevProps.data.length - 1];
  const nextLast = nextProps.data[nextProps.data.length - 1];

  if (!prevLast || !nextLast) {
    return false;
  }

  // Skip re-render if changes are too small (prevents flickering)
  // Higher thresholds = less frequent updates = smoother chart
  const priceThreshold = 1.0; // Only update if price changes by $1+
  const volumeThreshold = 5.0; // Only update if volume changes by 5+
  
  const areEqual = (
    prevLast.ts === nextLast.ts &&
    Math.abs(prevLast.open - nextLast.open) < priceThreshold &&
    Math.abs(prevLast.high - nextLast.high) < priceThreshold &&
    Math.abs(prevLast.low - nextLast.low) < priceThreshold &&
    Math.abs(prevLast.close - nextLast.close) < priceThreshold &&
    Math.abs((prevLast.volume || 0) - (nextLast.volume || 0)) < volumeThreshold
  );

  return areEqual; // true = skip render, false = do render
});

ChartCanvas.displayName = 'ChartCanvas';

const PriceChartComponent = ({
  data,
  symbol,
  timeframe,
  onTimeframeChange,
  timeframeOptions = DEFAULT_TIMEFRAME_OPTIONS,
  isLive = false,
  onStartLive,
  onStopLive,
  showLiveToggle = true,
  tickerData = null,
}: PriceChartProps) => {
  const [isWatchlisted, setIsWatchlisted] = useState(false);

  const meta = useMemo(() => getAssetMeta(symbol), [symbol]);
  const liveTicker = isLive && tickerData ? tickerData : null;

  const summary = useMemo(() => {
    if (!liveTicker) {
      return null;
    }

    return {
      price: liveTicker.lastPrice,
      change: liveTicker.priceChange,
      changePercent: liveTicker.priceChangePercent,
      high: liveTicker.highPrice,
      low: liveTicker.lowPrice,
      volume: liveTicker.volume,
    };
  }, [liveTicker]);

  const hasLiveSummary = Boolean(summary);

  const handleToggleWatchlist = () => setIsWatchlisted(prev => !prev);

  const handleLiveToggle = () => {
    if (isLive) {
      onStopLive?.();
    } else {
      onStartLive?.();
    }
  };

  const handleTimeframeClick = (value: string) => {
    if (value !== timeframe) {
      onTimeframeChange?.(value);
    }
  };

  const changeBadgeClass = hasLiveSummary
    ? summary!.changePercent >= 0
      ? 'bg-emerald-500/10 text-emerald-400'
      : 'bg-rose-500/10 text-rose-400'
    : 'bg-slate-800 text-muted-foreground';

  const stats = useMemo(
    () => [
      {
        label: 'Market cap',
        value:
          hasLiveSummary && typeof meta.marketCap === 'number'
            ? formatCompactCurrency(meta.marketCap)
            : '--',
        change:
          hasLiveSummary && typeof meta.marketCapChange === 'number'
            ? meta.marketCapChange
            : undefined,
      },
      {
        label: 'Volume (24h)',
        value:
          hasLiveSummary && typeof meta.volume24h === 'number'
            ? formatCompactCurrency(meta.volume24h)
            : '--',
        change:
          hasLiveSummary && typeof meta.volume24hChange === 'number'
            ? meta.volume24hChange
            : undefined,
      },
      {
        label: 'FDV',
        value:
          hasLiveSummary && typeof meta.fullyDilutedValuation === 'number'
            ? formatCompactCurrency(meta.fullyDilutedValuation)
            : '--',
      },
      {
        label: 'Vol/Mkt Cap (24h)',
        value:
          hasLiveSummary && meta.marketCap && meta.volume24h
            ? `${formatNumber((meta.volume24h / meta.marketCap) * 100, 2)}%`
            : '--',
        muted: true,
      },
      {
        label: 'Total supply',
        value:
          meta.totalSupply !== undefined && meta.totalSupply !== null
            ? `${formatCompactNumber(meta.totalSupply)} ${meta.ticker}`
            : '∞',
      },
      {
        label: 'Circulating supply',
        value:
          meta.circulatingSupply !== undefined && meta.circulatingSupply !== null
            ? `${formatCompactNumber(meta.circulatingSupply)} ${meta.ticker}`
            : '--',
      },
    ],
    [meta, hasLiveSummary]
  );

  return (
    <Card className="bg-gradient-card border-border/50 shadow-card overflow-hidden">
      <CardHeader className="space-y-6 bg-slate-900/40 border-b border-border/40">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-4">
            <AssetLogo symbol={symbol} size="lg" />
            <div className="space-y-1">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-xl font-semibold text-foreground">
                  {meta.name}
                </span>
                <Badge variant="secondary">{meta.ticker}</Badge>
                {typeof meta.rank === 'number' && (
                  <Badge variant="outline">#{meta.rank}</Badge>
                )}
              </div>
              <div className="text-xs text-muted-foreground">
                {meta.watchlistCount ? `${meta.watchlistCount} watchlists` : 'Watchlist data unavailable'}
              </div>
            </div>
          </div>
          <Button
            variant="ghost"
            size="icon"
            className={cn(
              'rounded-full border border-border/60 bg-slate-950/40',
              isWatchlisted && 'text-yellow-400'
            )}
            onClick={handleToggleWatchlist}
            aria-label="Toggle watchlist"
          >
            {isWatchlisted ? <Star className="h-5 w-5 fill-yellow-400" /> : <StarOff className="h-5 w-5" />}
          </Button>
        </div>

        <div className="flex flex-wrap items-end justify-between gap-6">
          <div className="space-y-2">
            <div className="text-4xl font-semibold tracking-tight text-foreground">
              {hasLiveSummary ? `$${formatPrice(summary!.price)}` : '--'}
            </div>
            <div className="flex items-center gap-2 text-sm">
              <span
                className={cn(
                  'inline-flex items-center gap-1 rounded-full px-2 py-1 font-medium text-xs',
                  changeBadgeClass
                )}
              >
                {hasLiveSummary ? (
                  summary!.changePercent >= 0 ? (
                    <ArrowUpRight className="h-4 w-4" />
                  ) : (
                    <ArrowDownRight className="h-4 w-4" />
                  )
                ) : (
                  <Dot className="h-4 w-4" />
                )}
                {hasLiveSummary ? formatSignedPercent(summary!.changePercent) : '--'}
              </span>
              <span className="text-xs text-muted-foreground">(24h)</span>
            </div>
            <div className="text-xs text-muted-foreground">
              24h Low: {hasLiveSummary ? `$${formatPrice(summary!.low)}` : '--'} · High: {hasLiveSummary ? `$${formatPrice(summary!.high)}` : '--'} · Volume: {hasLiveSummary ? formatCompactNumber(summary!.volume, 2) : '--'}
            </div>
          </div>

          {showLiveToggle && (
            <div className="flex items-center gap-3">
              <Badge
                variant="outline"
                className={cn(
                  'flex items-center gap-1 border border-border/60 text-xs',
                  isLive ? 'text-emerald-400 border-emerald-500/40' : 'text-muted-foreground'
                )}
              >
                <Dot className={cn('h-4 w-4', isLive ? 'text-emerald-400 animate-pulse' : 'text-muted-foreground')} />
                {isLive ? 'Live updating' : 'Live paused'}
              </Badge>
              <Button
                variant={isLive ? 'secondary' : 'default'}
                onClick={handleLiveToggle}
                className="min-w-[104px]"
              >
                {isLive ? 'Stop live' : 'Start live'}
              </Button>
            </div>
          )}
        </div>

        {hasLiveSummary ? (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            {stats.map((stat, index) => (
              <div key={index} className="rounded-lg border border-border/40 bg-slate-900/60 p-3">
                <div className="text-[10px] uppercase tracking-wide text-muted-foreground mb-1">
                  {stat.label}
                </div>
                <div className={cn('text-sm font-semibold text-foreground', stat.muted && 'text-muted-foreground')}>
                  {stat.value}
                </div>
                {typeof stat.change === 'number' && !stat.muted && (
                  <div
                    className={cn(
                      'text-[11px] font-medium flex items-center gap-1',
                      stat.change >= 0 ? 'text-emerald-400' : 'text-rose-400'
                    )}
                  >
                    {stat.change >= 0 ? <ArrowUpRight className="h-3 w-3" /> : <ArrowDownRight className="h-3 w-3" />}
                    {formatSignedPercent(stat.change)}
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="rounded-lg border border-dashed border-border/40 bg-slate-900/40 p-4 text-xs text-muted-foreground">
            Live market stats are available when streaming is active.
          </div>
        )}
      </CardHeader>
      <CardContent className="pt-6">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
          <div className="inline-flex items-center gap-2 rounded-full border border-border/50 bg-slate-900/60 p-1">
            {timeframeOptions.map(option => (
              <button
                key={option.value}
                className={cn(
                  'px-3 py-1 text-xs font-medium rounded-full transition-colors',
                  timeframe === option.value
                    ? 'bg-slate-800 text-foreground shadow'
                    : 'text-muted-foreground hover:text-foreground'
                )}
                onClick={() => handleTimeframeClick(option.value)}
              >
                {option.label}
              </button>
            ))}
          </div>
          <div className="text-xs text-muted-foreground">
            Drag to pan · Scroll to zoom · Double-click to reset
          </div>
        </div>
        <ChartCanvas data={data} symbol={symbol} timeframe={timeframe} />
      </CardContent>
    </Card>
  );
};

export const PriceChart = PriceChartComponent;
