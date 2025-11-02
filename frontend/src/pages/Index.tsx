import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { toast } from 'sonner';
import { Navbar } from '@/components/Navbar';
import { ControlPanel } from '@/components/ControlPanel';
import { PriceChart } from '@/components/PriceChart';
import { SpreadChart } from '@/components/SpreadChart';
import { StatsCard } from '@/components/StatsCard';
import { AlertsPanel } from '@/components/AlertsPanel';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { startStream, stopStream, getData, getAnalytics, postAlert } from '@/services/api';
import { WS_URL } from '@/utils/constants';

const timeframeToMs = (tf: string): number | null => {
  const match = tf.match(/(\d+)([smhd])/i);
  if (!match) return null;
  const value = Number(match[1]);
  const unit = match[2].toLowerCase();
  const unitMap: Record<string, number> = {
    s: 1000,
    m: 60 * 1000,
    h: 60 * 60 * 1000,
    d: 24 * 60 * 60 * 1000,
  };
  return unitMap[unit] ? value * unitMap[unit] : null;
};

const DEFAULT_CANDLE_LOOKBACK = 480;
const MAX_LOOKBACK_WINDOW_MS = 14 * 24 * 60 * 60 * 1000; // cap at two weeks of history

const getLookbackDurationMs = (tf: string): number | null => {
  const intervalMs = timeframeToMs(tf);
  if (!intervalMs) {
    return null;
  }

  const duration = intervalMs * DEFAULT_CANDLE_LOOKBACK;
  return Math.min(duration, MAX_LOOKBACK_WINDOW_MS);
};

type Candle = {
  ts: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
};

type SeriesPoint = {
  ts: string;
  value: number;
};

interface AnalyticsSnapshot {
  pair: string;
  hedge_ratio: SeriesPoint[];
  spread: SeriesPoint[];
  zscore: SeriesPoint[];
  rolling_corr: SeriesPoint[];
  adf?: {
    pvalue: number;
    stat: number;
  };
}

interface AlertInput {
  metric: string;
  pair: string;
  operator: string;
  value: number;
}
const Index = () => {
  const [isStreaming, setIsStreaming] = useState(false);
  const [tickCount, setTickCount] = useState(0);
  const [viewMode, setViewMode] = useState<'single' | 'comparison'>('single');
  const [selectedSymbols, setSelectedSymbols] = useState(['BTCUSDT', 'ETHUSDT']);
  const [timeframe, setTimeframe] = useState('1s'); // Default to 1 second for live trading
  const [rollingWindow, setRollingWindow] = useState(20);
  const [regressionType, setRegressionType] = useState('OLS');
  
  // Store price data for multiple symbols
  const [priceData, setPriceData] = useState<Record<string, Candle[]>>({});
  const [analyticsData, setAnalyticsData] = useState<AnalyticsSnapshot | null>(null);
  const [tickerData, setTickerData] = useState<Record<string, {
    priceChange: number;
    priceChangePercent: number;
    lastPrice: number;
    openPrice: number;
    highPrice: number;
    lowPrice: number;
    volume: number;
    quoteVolume: number;
  }>>({});
  const wsRef = useRef<WebSocket | null>(null);
  const refreshIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const analyticsIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const tickCounterRef = useRef(0);
  const lastTickUpdateRef = useRef(Date.now());
  
  // Add throttling refs for price updates - Aggressive throttling to prevent flickering
  const lastPriceUpdateRef = useRef<Record<string, number>>({});
  const PRICE_UPDATE_THROTTLE_MS = 2000; // Update charts max 1 time per 2 seconds (ultra smooth, no blinking)
  
  // Pending updates buffer
  const pendingUpdatesRef = useRef<Record<string, {
    price: number;
    qty: number;
    ts: string;
    time: Date;
  }>>({});
  
  // RAF for smooth batched updates
  const rafIdRef = useRef<number | null>(null);

  const getBucketedTimestamp = useCallback((date: Date, tf: string) => {
    const bucket = new Date(date);
    bucket.setUTCMilliseconds(0);

    // Live mode uses per-second buckets for real-time candles
    if (tf === 'live') {
      bucket.setUTCSeconds(bucket.getUTCSeconds(), 0);
      return bucket.toISOString();
    }

    const match = tf.match(/(\d+)([a-zA-Z]+)/);
    if (!match) {
      bucket.setSeconds(0, 0);
      return bucket.toISOString();
    }

    const [, sizeStr, unit] = match;
    const size = Number(sizeStr);

    if (unit === 's') {
      const seconds = Math.floor(bucket.getUTCSeconds() / size) * size;
      bucket.setUTCSeconds(seconds, 0);
    } else if (unit === 'm') {
      const minutes = Math.floor(bucket.getUTCMinutes() / size) * size;
      bucket.setUTCSeconds(0, 0);
      bucket.setUTCMinutes(minutes);
    } else if (unit === 'h') {
      const hours = Math.floor(bucket.getUTCHours() / size) * size;
      bucket.setUTCSeconds(0, 0);
      bucket.setUTCMinutes(0);
      bucket.setUTCHours(hours);
    } else {
      bucket.setUTCSeconds(0, 0);
    }

    return bucket.toISOString();
  }, []);

  // Fetch initial data for all selected symbols
  useEffect(() => {
    if (!isStreaming) {
      if (refreshIntervalRef.current) {
        clearInterval(refreshIntervalRef.current);
        refreshIntervalRef.current = null;
      }
      setPriceData({});
      setAnalyticsData(null);
      setTickerData({});
      return;
    }

    const fetchData = async () => {
      if (selectedSymbols.length > 0) {
        const toTs = new Date().toISOString();
        const lookbackDuration = getLookbackDurationMs(timeframe);
        const fromTs = lookbackDuration
          ? new Date(Date.now() - lookbackDuration).toISOString()
          : undefined;

        const dataPromises = selectedSymbols.map(symbol =>
          getData(symbol, timeframe, fromTs, toTs).catch(err => {
            console.error(`Error fetching ${symbol}:`, err);
            return [];
          })
        );

        const results = await Promise.all(dataPromises);
        const newPriceData: Record<string, Candle[]> = {};
        selectedSymbols.forEach((symbol, index) => {
          if (results[index] && results[index].length > 0) {
            newPriceData[symbol] = results[index]
              .map(candle => ({
                ...candle,
                ts: new Date(candle.ts).toISOString(),
              }))
              .sort((a, b) => new Date(a.ts).getTime() - new Date(b.ts).getTime());
          }
        });

        setPriceData(newPriceData);
      }

      // Calculate analytics for single currency (z-score of price itself)
      if (selectedSymbols.length >= 1) {
        try {
          // Use single symbol or pair format
          const pair = selectedSymbols.length === 1 
            ? `${selectedSymbols[0]}-${selectedSymbols[0]}` // Self-comparison for z-score
            : `${selectedSymbols[0]}-${selectedSymbols[1]}`; // Pair comparison
          
          const analytics = await getAnalytics(pair, timeframe, rollingWindow, regressionType);
          setAnalyticsData(analytics);
        } catch (error) {
          console.error('Error fetching analytics:', error);
        }
      }
    };

    fetchData();

    return () => {
      if (refreshIntervalRef.current) {
        clearInterval(refreshIntervalRef.current);
        refreshIntervalRef.current = null;
      }
    };
  }, [selectedSymbols, timeframe, rollingWindow, regressionType, isStreaming]);

  // WebSocket connection for live updates
  useEffect(() => {
    if (isStreaming) {
      // Connect to real backend WebSocket
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;
      
      ws.onopen = () => {
        console.log('WebSocket connected to backend');
        // Subscribe to selected symbols
        ws.send(JSON.stringify({
          action: 'subscribe',
          symbols: selectedSymbols
        }));
      };
      
      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          
          // Handle trade/tick messages from backend
          if (message.type === 'trade' || message.type === 'tick') {
            // Throttle tick count updates to every 100ms to reduce re-renders
            tickCounterRef.current += 1;
            const now = Date.now();
            if (now - lastTickUpdateRef.current > 100) {
              setTickCount(tickCounterRef.current);
              lastTickUpdateRef.current = now;
            }
            
            // Backend sends tick data directly (not in message.data)
            const tick = message.data || message; // Support both formats
            const tickSymbol = tick.symbol || message.symbol;
            const tickPrice = tick.price || message.price;
            if (!tickSymbol || typeof tickPrice !== 'number') {
              return;
            }
            const tickQty = tick.qty || message.qty || 0;
            const tickTs = tick.ts || message.ts;
            const tickTime = new Date(tickTs);
            
            // Throttle price data updates to reduce re-renders
            const lastUpdate = lastPriceUpdateRef.current[tickSymbol] || 0;
            
            // Store the pending update
            pendingUpdatesRef.current[tickSymbol] = {
              price: tickPrice,
              qty: tickQty,
              ts: tickTs,
              time: tickTime,
            };
            
            // Only process if enough time has passed (1000ms throttle for zero flickering)
            if (now - lastUpdate < PRICE_UPDATE_THROTTLE_MS) {
              return; // Skip this update, will use the latest pending update later
            }
            
            // Process the most recent pending update
            const pendingUpdate = pendingUpdatesRef.current[tickSymbol];
            if (!pendingUpdate) return;
            
            lastPriceUpdateRef.current[tickSymbol] = now;
            
            const effectiveTimeframe = timeframe || '1m';
            const bucketTs = getBucketedTimestamp(pendingUpdate.time, effectiveTimeframe);
            
            // Update price data for the specific symbol
            setPriceData(prev => {
              const symbolData = prev[tickSymbol] || [];
              
              // Check if we need to update at all
              if (symbolData.length > 0) {
                const last = symbolData[symbolData.length - 1];

                if (last.ts === bucketTs) {
                  // Update existing candle in same bucket
                  const updatedLast = {
                    ...last,
                    close: pendingUpdate.price,
                    high: Math.max(last.high, pendingUpdate.price),
                    low: Math.min(last.low, pendingUpdate.price),
                    volume: (last.volume || 0) + pendingUpdate.qty,
                  };
                  
                  // Check if values actually changed significantly (increased threshold to 0.1 to reduce updates)
                  const closeChanged = Math.abs(updatedLast.close - last.close) > 0.1;
                  const highChanged = Math.abs(updatedLast.high - last.high) > 0.1;
                  const lowChanged = Math.abs(updatedLast.low - last.low) > 0.1;
                  const volumeChanged = Math.abs(updatedLast.volume - last.volume) > 1;
                  
                  if (!closeChanged && !highChanged && !lowChanged && !volumeChanged) {
                    return prev; // No meaningful change, keep everything stable
                  }
                  
                  // Only create new array when values changed
                  const newData = [...symbolData];
                  newData[newData.length - 1] = updatedLast;
                  
                  return {
                    ...prev,
                    [tickSymbol]: newData,
                  };
                } else if (new Date(bucketTs).getTime() > new Date(last.ts).getTime()) {
                  // Append new bucket candle
                  const tfMs = timeframeToMs(effectiveTimeframe);
                  const lookbackMs = getLookbackDurationMs(effectiveTimeframe);
                  const maxCandles = tfMs && lookbackMs
                    ? Math.ceil(lookbackMs / tfMs) + 5
                    : DEFAULT_CANDLE_LOOKBACK;

                  const newData = [
                    ...symbolData,
                    {
                      ts: bucketTs,
                      open: pendingUpdate.price,
                      high: pendingUpdate.price,
                      low: pendingUpdate.price,
                      close: pendingUpdate.price,
                      volume: pendingUpdate.qty,
                    },
                  ]
                    .slice(-maxCandles)
                    .sort((a, b) => new Date(a.ts).getTime() - new Date(b.ts).getTime());

                  return {
                    ...prev,
                    [tickSymbol]: newData,
                  };
                }
                
                return prev; // No update needed
              } else {
                // Initialize first candle from tick
                return {
                  ...prev,
                  [tickSymbol]: [{
                    ts: bucketTs,
                    open: pendingUpdate.price,
                    high: pendingUpdate.price,
                    low: pendingUpdate.price,
                    close: pendingUpdate.price,
                    volume: pendingUpdate.qty,
                  }],
                };
              }
            });
          } else if (message.type === 'ticker') {
            // Handle 24h ticker updates from Binance - HEAVILY THROTTLED
            const ticker = message.data || message;
            const tickerSymbol = ticker.symbol || message.symbol;
            
            if (tickerSymbol) {
              const resolveNumber = (value: unknown, fallback: unknown = 0) => {
                if (typeof value === 'number') return value;
                const parsed = Number(value ?? fallback ?? 0);
                return Number.isFinite(parsed) ? parsed : 0;
              };

              const newTickerData = {
                priceChange: resolveNumber(ticker.priceChange, message.priceChange),
                priceChangePercent: resolveNumber(ticker.priceChangePercent, message.priceChangePercent),
                lastPrice: resolveNumber(ticker.lastPrice, message.lastPrice),
                openPrice: resolveNumber(ticker.openPrice, message.openPrice),
                highPrice: resolveNumber(ticker.highPrice, message.highPrice),
                lowPrice: resolveNumber(ticker.lowPrice, message.lowPrice),
                volume: resolveNumber(ticker.volume, message.volume),
                quoteVolume: resolveNumber(ticker.quoteVolume, message.quoteVolume),
              };

              setTickerData(prev => {
                const existing = prev[tickerSymbol];
                // Only update if price or percent changed significantly (increased threshold to 1.0)
                if (existing && 
                    Math.abs(existing.lastPrice - newTickerData.lastPrice) < 1.0 &&
                    Math.abs(existing.priceChangePercent - newTickerData.priceChangePercent) < 0.1) {
                  return prev; // No meaningful change
                }
                
                return {
                  ...prev,
                  [tickerSymbol]: newTickerData,
                };
              });
            }
          } else if (message.type === 'analytics') {
            setAnalyticsData(message.data || message);
          } else if (message.type === 'alert') {
            toast.warning(`Alert: ${message.message}`);
          } else if (message.type === 'subscription') {
            console.log('Subscription status:', message.status, message.symbols);
            toast.success(`Subscribed to ${message.symbols.join(', ')}`);
          }
        } catch (error) {
          console.error('WebSocket message error:', error);
        }
      };
      
      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        toast.error('WebSocket connection error');
      };
      
      ws.onclose = () => {
        console.log('WebSocket disconnected');
      };
      
      // Refresh analytics every 5 seconds when streaming
      const fetchAnalytics = async () => {
        if (selectedSymbols.length >= 1) {
          try {
            // Use single symbol or pair format
            const pair = selectedSymbols.length === 1 
              ? `${selectedSymbols[0]}-${selectedSymbols[0]}` // Self-comparison for z-score
              : `${selectedSymbols[0]}-${selectedSymbols[1]}`; // Pair comparison
            
            console.log(`[Analytics] Fetching for ${pair} (window: ${rollingWindow}, method: ${regressionType})`);
            const analytics = await getAnalytics(pair, timeframe, rollingWindow, regressionType);
            if (analytics) {
              const zscoreCount = analytics.zscore?.length || 0;
              const spreadCount = analytics.spread?.length || 0;
              const latestZScore = zscoreCount > 0 ? analytics.zscore[zscoreCount - 1].value : 'N/A';
              console.log(`[Analytics] Received - Spread points: ${spreadCount}, Z-score points: ${zscoreCount}, Latest Z: ${latestZScore}`);
              setAnalyticsData(analytics);
            } else {
              console.warn('[Analytics] No analytics data received');
            }
          } catch (error) {
            console.error('Error fetching analytics during stream:', error);
          }
        }
      };
      
      // Fetch analytics immediately
      fetchAnalytics();
      
      // Then refresh every 5 seconds
      analyticsIntervalRef.current = setInterval(fetchAnalytics, 5000);
    } else {
      // Disconnect WebSocket
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      if (analyticsIntervalRef.current) {
        clearInterval(analyticsIntervalRef.current);
        analyticsIntervalRef.current = null;
      }
    };
  }, [isStreaming, selectedSymbols, timeframe, rollingWindow, regressionType, getBucketedTimestamp]);

  const handleStartStream = async () => {
    try {
      await startStream(selectedSymbols);
      setIsStreaming(true);
      setTickCount(0);
      setPriceData({});
      setTickerData({});
      setAnalyticsData(null);
      // Keep current timeframe for analytics but use 6h buckets for display
      toast.success('Stream started - Live 6h candles');
    } catch (error) {
      toast.error('Failed to start stream');
    }
  };

  const handleStopStream = async () => {
    try {
      await stopStream(selectedSymbols);
      setIsStreaming(false);
      setPriceData({});
      setTickerData({});
      setAnalyticsData(null);
      toast.success('Stream stopped');
    } catch (error) {
      toast.error('Failed to stop stream');
    }
  };

  const handleClearBuffer = () => {
    setPriceData({});
    setAnalyticsData(null);
    setTickCount(0);
    toast.info('Buffer cleared');
  };

  const handleDownloadData = () => {
    if (!analyticsData || analyticsData.spread.length === 0) {
      toast.error('No data to download');
      return;
    }
    
    // Simple CSV export
    const csvData = analyticsData.spread.map((s, i) => ({
      timestamp: s.ts,
      spread: s.value,
      zscore: analyticsData.zscore[i]?.value ?? 0,
      correlation: analyticsData.rolling_corr[i]?.value ?? 0,
    }));

    const csvHeader = Object.keys(csvData[0]).join(',');
    const csvRows = csvData.map(row => Object.values(row).join(','));
    const csv = [csvHeader, ...csvRows].join('\n');
    
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `analytics-${Date.now()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    
    toast.success('Data exported');
  };

  const handleRunADF = () => {
    if (analyticsData?.adf) {
      const { pvalue, stat } = analyticsData.adf;
      const isStationary = pvalue < 0.05;
      const strength = pvalue < 0.01 ? 'strongly' : pvalue < 0.05 ? 'weakly' : 'not';
      
      const message = isStationary
        ? `✅ Spread is ${strength} stationary (mean-reverting)\nADF Statistic: ${stat.toFixed(4)}\nP-Value: ${pvalue.toFixed(4)} ${pvalue < 0.01 ? '(< 0.01)' : '(< 0.05)'}`
        : `⚠️ Spread is NOT stationary\nADF Statistic: ${stat.toFixed(4)}\nP-Value: ${pvalue.toFixed(4)} (> 0.05)\nMean reversion strategy may not be effective`;
      
      if (isStationary) {
        toast.success(message, { duration: 5000 });
      } else {
        toast.warning(message, { duration: 5000 });
      }
    } else {
      toast.warning('No analytics data available. Start streaming in comparison mode to run ADF test.');
    }
  };

  const handleAddAlert = async ({ metric, pair, operator, value }: AlertInput) => {
    try {
      await postAlert({ metric, pair, op: operator, value });
      toast.success('Alert created');
    } catch (error) {
      toast.error('Failed to create alert');
    }
  };

  const handleTimeframeChange = (tf: string) => {
    setTimeframe(tf);
    setPriceData({});
  };

  const currentSpread = analyticsData?.spread[analyticsData.spread.length - 1]?.value || 0;
  const currentZScore = analyticsData?.zscore[analyticsData.zscore.length - 1]?.value || 0;
  const currentCorr = analyticsData?.rolling_corr[analyticsData.rolling_corr.length - 1]?.value || 0;
  const adfPValue = analyticsData?.adf?.pvalue || 0;

  // Memoize chart data to prevent unnecessary re-renders
  const stableChartData = useMemo(() => {
    const result: Record<string, Candle[]> = {};
    Object.keys(priceData).forEach(symbol => {
      result[symbol] = priceData[symbol] || [];
    });
    return result;
  }, [priceData]);

  return (
    <div className="min-h-screen bg-background">
      <Navbar isStreaming={isStreaming} tickCount={tickCount} />
      
      <div className="container mx-auto px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Left Column - Controls */}
          <div className="lg:col-span-1 space-y-6">
            <ControlPanel
              isStreaming={isStreaming}
              onStartStream={handleStartStream}
              onStopStream={handleStopStream}
              onClearBuffer={handleClearBuffer}
              onDownloadData={handleDownloadData}
              selectedSymbols={selectedSymbols}
              onSymbolsChange={setSelectedSymbols}
              timeframe={timeframe}
              onTimeframeChange={handleTimeframeChange}
              rollingWindow={rollingWindow}
              onRollingWindowChange={setRollingWindow}
              regressionType={regressionType}
              onRegressionTypeChange={setRegressionType}
              onRunADF={handleRunADF}
            />
            
            <AlertsPanel onAddAlert={handleAddAlert} />
          </div>

          {/* Right Column - Charts and Stats */}
          <div className="lg:col-span-3 space-y-6">
            {/* Mode Toggle */}
            <Card className="bg-gradient-card border-border/50">
              <CardContent className="pt-6">
                <Tabs value={viewMode} onValueChange={(v) => setViewMode(v as 'single' | 'comparison')}>
                  <TabsList className="grid w-full grid-cols-2">
                    <TabsTrigger value="single">Price Chart</TabsTrigger>
                    <TabsTrigger value="comparison">Analytics View</TabsTrigger>
                  </TabsList>
                </Tabs>
                <p className="text-xs text-muted-foreground mt-2">
                  {viewMode === 'single' 
                    ? 'View live candlestick chart with moving averages'
                    : 'View z-score, spread, correlation and statistical analysis'}
                </p>
              </CardContent>
            </Card>

            {viewMode === 'single' && (
              <>
                {/* Single or Multiple Currency Price Charts */}
                {selectedSymbols.map((symbol, index) => (
                  <PriceChart
                    key={symbol}
                    data={stableChartData[symbol] || []}
                    symbol={symbol}
                    timeframe={timeframe}
                    onTimeframeChange={handleTimeframeChange}
                    isLive={isStreaming}
                    onStartLive={index === 0 ? handleStartStream : undefined}
                    onStopLive={index === 0 ? handleStopStream : undefined}
                    tickerData={tickerData[symbol] || null}
                  />
                ))}
              </>
            )}

            {viewMode === 'comparison' && (
              <>
                {/* Stats Cards for Analytics */}
                {selectedSymbols.length >= 1 && (
                  <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                    <StatsCard title="Spread" value={currentSpread} decimals={2} />
                    <StatsCard title="Z-Score" value={currentZScore} decimals={2} />
                    <StatsCard title="Correlation" value={currentCorr} decimals={4} />
                    <StatsCard title="ADF p-value" value={adfPValue} decimals={4} />
                  </div>
                )}

                {/* Spread & Z-Score Detail Chart */}
                {selectedSymbols.length >= 1 && analyticsData && analyticsData.spread && analyticsData.spread.length > 0 && (
                  <SpreadChart
                    spread={analyticsData.spread}
                    zscore={analyticsData.zscore}
                    pair={analyticsData.pair}
                  />
                )}
                
                {/* Show message if no analytics yet */}
                {selectedSymbols.length >= 1 && (!analyticsData || !analyticsData.spread || analyticsData.spread.length === 0) && (
                  <Card className="bg-gradient-card border-border/50 shadow-card">
                    <CardHeader>
                      <CardTitle className="text-lg">
                        Spread & Z-Score - {selectedSymbols[0]}{selectedSymbols[1] ? `-${selectedSymbols[1]}` : ''}
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="flex items-center justify-center h-[400px]">
                      <div className="text-center text-muted-foreground">
                        <p className="text-lg mb-2">Collecting data...</p>
                        <p className="text-sm">Analytics will appear once enough historical data is loaded</p>
                      </div>
                    </CardContent>
                  </Card>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Index;
