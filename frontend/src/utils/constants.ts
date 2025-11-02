export const AVAILABLE_SYMBOLS = [
  'BTCUSDT',
  'ETHUSDT',
  'BNBUSDT',
  'SOLUSDT',
  'ADAUSDT',
];

export const TIMEFRAMES = [
  { value: '1s', label: '1 Second' },
  { value: '1m', label: '1 Minute' },
  { value: '5m', label: '5 Minutes' },
  { value: '15m', label: '15 Minutes' },
  { value: '30m', label: '30 Minutes' },
  { value: '1h', label: '1 Hour' },
  { value: '14h', label: '14 Hours' },
];

export const REGRESSION_TYPES = [
  { value: 'OLS', label: 'OLS (Ordinary Least Squares)' },
  { value: 'Huber', label: 'Huber (Robust)' },
  { value: 'Theil-Sen', label: 'Theil-Sen' },
  { value: 'Kalman', label: 'Kalman Filter' },
];

export const DEFAULT_ROLLING_WINDOW = 20;
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
export const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/stream/ws';
