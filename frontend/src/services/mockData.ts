// Mock data service for development without backend

interface PriceData {
  ts: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface AnalyticsData {
  pair: string;
  hedge_ratio: Array<{ ts: string; value: number }>;
  spread: Array<{ ts: string; value: number }>;
  zscore: Array<{ ts: string; value: number }>;
  rolling_corr: Array<{ ts: string; value: number }>;
  adf: { pvalue: number; stat: number };
}

// Generate synthetic price data
export const generatePriceData = (
  symbol: string,
  basePrice: number,
  count: number = 100,
  stepMs: number = 60_000,
  endTimestamp: number = Date.now()
): PriceData[] => {
  const data: PriceData[] = [];
  const startTimestamp = endTimestamp - Math.max((count - 1) * stepMs, 0);
  
  for (let i = 0; i < count; i++) {
    const timestamp = new Date(startTimestamp + i * stepMs);
    const variation = Math.sin(i / 10) * basePrice * 0.02 + (Math.random() - 0.5) * basePrice * 0.01;
    const open = basePrice + variation;
    const high = open + Math.random() * basePrice * 0.005;
    const low = open - Math.random() * basePrice * 0.005;
    const close = low + Math.random() * (high - low);
    
    data.push({
      ts: timestamp.toISOString(),
      open,
      high,
      low,
      close,
      volume: Math.random() * 100 + 10,
    });
  }
  
  return data;
};

// Generate analytics data for a pair
export const generateAnalyticsData = (pair: string, count: number = 100): AnalyticsData => {
  const now = Date.now();
  const hedge_ratio: Array<{ ts: string; value: number }> = [];
  const spread: Array<{ ts: string; value: number }> = [];
  const zscore: Array<{ ts: string; value: number }> = [];
  const rolling_corr: Array<{ ts: string; value: number }> = [];
  
  for (let i = 0; i < count; i++) {
    const timestamp = new Date(now - (count - i) * 60000).toISOString();
    
    // Simulate hedge ratio around 1.0 with some variation
    hedge_ratio.push({
      ts: timestamp,
      value: 1.0 + Math.sin(i / 20) * 0.1 + (Math.random() - 0.5) * 0.05,
    });
    
    // Simulate mean-reverting spread
    const meanReversionForce = -spread[i - 1]?.value || 0;
    const newSpread = (spread[i - 1]?.value || 0) + meanReversionForce * 0.1 + (Math.random() - 0.5) * 5;
    spread.push({
      ts: timestamp,
      value: newSpread,
    });
    
    // Z-score calculation (simplified)
    const recentSpreads = spread.slice(Math.max(0, i - 20), i + 1).map(s => s.value);
    const mean = recentSpreads.reduce((a, b) => a + b, 0) / recentSpreads.length;
    const std = Math.sqrt(
      recentSpreads.reduce((sq, n) => sq + Math.pow(n - mean, 2), 0) / recentSpreads.length
    );
    zscore.push({
      ts: timestamp,
      value: std > 0 ? (newSpread - mean) / std : 0,
    });
    
    // Simulate rolling correlation
    rolling_corr.push({
      ts: timestamp,
      value: 0.7 + Math.sin(i / 15) * 0.2 + (Math.random() - 0.5) * 0.1,
    });
  }
  
  return {
    pair,
    hedge_ratio,
    spread,
    zscore,
    rolling_corr,
    adf: {
      pvalue: Math.random() * 0.1, // Random p-value < 0.1 (stationary)
      stat: -3.5 - Math.random() * 2,
    },
  };
};

// Mock API responses
export const mockApi = {
  getSymbols: () => Promise.resolve(['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT']),
  
  startStream: (_body: { symbols: string[]; tick_mode?: boolean }) => 
    Promise.resolve({ status: 'ok', started: true }),
  
  stopStream: (_body: { symbols: string[] }) => 
    Promise.resolve({ status: 'ok', stopped: true }),
  
  getData: (
    symbol: string,
    timeframe: string = '1m',
    from?: string,
    to?: string
  ) => {
    const basePrices: Record<string, number> = {
      BTCUSDT: 34000,
      ETHUSDT: 2200,
      BNBUSDT: 300,
      SOLUSDT: 100,
      ADAUSDT: 0.5,
    };
    const stepMap: Record<string, number> = {
      '1s': 1_000,
      '1m': 60_000,
      '5m': 5 * 60_000,
      '15m': 15 * 60_000,
      '1h': 60 * 60_000,
      '3h': 3 * 60 * 60_000,
      '6h': 6 * 60 * 60_000,
      '1d': 24 * 60 * 60_000,
    };

    const stepMs = stepMap[timeframe] ?? 60_000;
    const endTimestamp = to ? new Date(to).getTime() : Date.now();
    const startTimestamp = from ? new Date(from).getTime() : endTimestamp - 100 * stepMs;
    const rangeMs = Math.max(endTimestamp - startTimestamp, stepMs * 50);
    const count = Math.min(2000, Math.max(50, Math.floor(rangeMs / stepMs)));

    return Promise.resolve(
      generatePriceData(
        symbol,
        basePrices[symbol] || 1000,
        count,
        stepMs,
        endTimestamp
      )
    );
  },
  
  getAnalytics: (pair: string) => {
    return Promise.resolve(generateAnalyticsData(pair));
  },
};

// Simulate live tick updates
export class MockWebSocket {
  private intervalId: NodeJS.Timeout | null = null;
  private listeners: Map<string, (payload: unknown) => void> = new Map();
  
  connect() {
    console.log('Mock WebSocket connected');
  }
  
  subscribe(symbols: string[]) {
    console.log('Mock WebSocket subscribed to:', symbols);
    
    // Emit mock ticks every 500ms
    this.intervalId = setInterval(() => {
      symbols.forEach(symbol => {
        const basePrices: Record<string, number> = {
          BTCUSDT: 34000,
          ETHUSDT: 2200,
          BNBUSDT: 300,
          SOLUSDT: 100,
          ADAUSDT: 0.5,
        };
        
        const basePrice = basePrices[symbol] || 1000;
        const price = basePrice + (Math.random() - 0.5) * basePrice * 0.001;
        
        const tick = {
          type: 'trade',
          symbol,
          price,
          qty: Math.random() * 0.1,
          ts: new Date().toISOString(),
        };
        
        this.listeners.get('tick')?.(tick);
      });
    }, 500);
  }
  
  on(event: string, callback: (payload: unknown) => void) {
    this.listeners.set(event, callback);
  }
  
  disconnect() {
    if (this.intervalId) {
      clearInterval(this.intervalId);
    }
    console.log('Mock WebSocket disconnected');
  }
}
