# Quant Analytics Dashboard

A professional real-time quantitative analytics dashboard for cryptocurrency trading analysis. Built with React, TypeScript, and Plotly for advanced financial visualizations.

## 🚀 Features

- **Real-time Price Charts**: Candlestick charts with live updates
- **TradingView-style Candles**: Dynamic candle widths, moving averages, and volume overlays powered by Plotly
- **Spread Analysis**: Track price spreads between trading pairs
- **Z-Score Monitoring**: Statistical analysis for mean reversion strategies
- **Rolling Correlation**: Monitor correlation between assets over time
- **Alert System**: Create custom alerts for trading signals
- **Multiple Timeframes**: 1s, 1m, 5m data resolution
- **Regression Analysis**: OLS, Huber, Theil-Sen, Kalman filter support
- **ADF Stationarity Test**: Test for mean reversion opportunities
- **Data Export**: Download analytics as CSV for further analysis

## 🛠️ Tech Stack

- **React 18** with TypeScript
- **Vite** for fast development
- **Plotly.js** for interactive charts
- **Tailwind CSS** for styling
- **Shadcn/ui** for UI components
- **Axios** for API communication
- **Socket.io** for WebSocket streaming

## 📦 Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
```

## 🔧 Configuration

The dashboard can connect to a Python backend or run in mock mode:

### Mock Mode (Default)
Perfect for development and testing. Uses synthetic data generation.

### Backend Mode
Set environment variables to connect to your backend:

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws
VITE_USE_MOCK=false
```

## 🎯 Usage

1. **Select Symbols**: Choose up to 5 trading pairs from the symbol panel
2. **Configure Parameters**: 
   - Timeframe (1s/1m/5m)
   - Rolling window size
   - Regression type
3. **Start Stream**: Click "Start" to begin live data streaming
4. **Monitor Analytics**: View real-time charts and statistics
5. **Set Alerts**: Create custom alerts for z-score, spread, or correlation thresholds
6. **Export Data**: Download analytics data as CSV for offline analysis

## � TradingView-style Candlestick Chart

- Candlestick bodies automatically resize based on zoom level for TradingView-like readability
- Moving averages (7/25/99) render as smooth overlays with unified hover interactions
- Volume histogram shares the same x-axis and adopts bullish/bearish coloring
- Crosshair spikes and sticky hover tooltips streamline candle inspection
- Backend endpoint `/visualization/candles/{symbol}` returns the full Plotly figure spec for embedding in other surfaces

## �📊 Dashboard Layout

- **Left Panel**: Controls, symbol selection, parameters, and alerts
- **Right Panel**: Statistics cards, price charts, spread analysis
- **Top Bar**: Connection status, live tick counter

## 🔌 Backend API Contract

The dashboard expects the following endpoints:

- `GET /symbols` - List available symbols
- `POST /stream/start` - Start data stream
- `POST /stream/stop` - Stop data stream
- `GET /data/{symbol}` - Get historical OHLCV data
- `GET /analytics/pair` - Get pair analytics (spread, z-score, correlation)
- `GET /visualization/candles/{symbol}` - Plotly candlestick figure spec with optional moving averages
- `POST /alerts` - Create new alert
- `GET /export` - Export data as CSV

WebSocket messages:
- Subscribe: `{action: "subscribe", symbols: ["BTCUSDT"]}`
- Tick: `{type: "trade", symbol: "BTCUSDT", price: 34000, ...}`

## 🎨 Design System

The dashboard uses a professional trading platform aesthetic:

- **Dark theme** optimized for extended viewing
- **Cyan accents** for primary actions
- **Green/Red** for gains/losses
- **Monospace fonts** for numerical precision
- **Smooth animations** for real-time updates

## 📱 Responsive Design

Fully responsive layout that adapts to:
- Desktop (1920px+)
- Laptop (1280px+)
- Tablet (768px+)
- Mobile (320px+)

## 🔐 Security

- All API calls include error handling
- WebSocket reconnection with exponential backoff
- Input validation on all forms
- No sensitive data stored in localStorage

## 🚀 Deployment

Build the production-ready application:

```bash
npm run build
```

The production build is optimized and ready for deployment to any static hosting service (Vercel, Netlify, AWS S3, etc.).

### Deployment Options:
- **Vercel**: Connect your repository and deploy automatically
- **Netlify**: Drag and drop the `dist` folder or connect via Git
- **AWS S3 + CloudFront**: Upload the `dist` folder to S3 and serve via CloudFront
- **Docker**: Use the provided Dockerfile for containerized deployment

## 📝 License

MIT License - feel free to use this dashboard for your trading analysis needs.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

## 📧 Support

For questions and support, please open an issue in the repository.
