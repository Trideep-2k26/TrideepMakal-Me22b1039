# Quant Analytics Backend

Production-grade Python FastAPI backend for real-time quantitative trading analytics using Binance Futures data.

## 🚀 Features

- **Real-time Data Ingestion**: Connects to Binance Futures WebSocket streams for live tick data
- **Data Management**: In-memory tick buffering with automatic OHLCV resampling (1s, 1m, 5m)
- **Advanced Analytics**:
  - Hedge ratio calculation (OLS, Huber, Theil-Sen, Kalman)
  - Spread computation and z-score normalization
  - Rolling correlation analysis
  - Augmented Dickey-Fuller (ADF) stationarity test
- **Alert System**: User-defined alerts with real-time monitoring
- **WebSocket API**: Bidirectional communication for live updates to frontend
- **Data Export**: CSV export for processed analytics
- **Production Ready**: CORS, error handling, logging, graceful shutdown

## 📁 Project Structure

```
backend/
├── app.py                      # Main FastAPI application
├── requirements.txt            # Python dependencies
├── .env.example               # Environment configuration template
├── core/                      # Core business logic
│   ├── websocket_client.py   # Binance WebSocket client
│   ├── data_manager.py       # Tick buffering and resampling
│   ├── analytics.py          # Quantitative analytics engine
│   └── alerts_engine.py      # Alert monitoring system
├── api/                       # FastAPI routes
│   ├── routes_data.py        # /symbols, /data endpoints
│   ├── routes_analytics.py   # /analytics endpoints
│   ├── routes_alerts.py      # /alerts endpoints
│   ├── routes_export.py      # /export CSV endpoint
│   └── routes_stream.py      # /stream, /ws endpoints
├── utils/                     # Utilities
│   ├── config.py             # Configuration management
│   ├── logger.py             # Logging setup
│   └── helpers.py            # Helper functions
├── data/                      # Data storage (optional)
└── reference/                 # Reference files
    └── binance_browser_collector_save_test.html
```

## 🛠️ Installation

### Prerequisites

- Python 3.9+
- pip or conda

### Setup

1. **Create virtual environment** (recommended):

```bash
# Using venv
python -m venv venv

# Activate (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Activate (Linux/Mac)
source venv/bin/activate
```

2. **Install dependencies**:

```bash
cd backend
pip install -r requirements.txt
```

3. **Configure environment** (optional):

```bash
# Copy example env file
cp .env.example .env

# Edit .env with your preferences
# Default values work fine for development
```

## 🚀 Running the Backend

### Development Mode

```bash
# From the backend directory
python app.py
```

Or using uvicorn directly:

```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### Production Mode

```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4
```

The API will be available at:
- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs (Swagger UI)
- **ReDoc**: http://localhost:8000/redoc

## 📡 API Endpoints

### Health & Info

- `GET /` - Root health check
- `GET /health` - Detailed health status

### Data Management

- `GET /symbols` - List available symbols
- `GET /data/{symbol}` - Get OHLCV data
  - Query params: `tf`, `from`, `to`, `limit`
- `GET /data/{symbol}/ticks` - Get raw tick data
- `GET /data/stats` - Get buffer statistics
- `POST /data/clear` - Clear buffers

### Stream Control

- `POST /stream/start` - Start Binance WebSocket streams
  - Body: `{"symbols": ["BTCUSDT", "ETHUSDT"], "tick_mode": true}`
- `POST /stream/stop` - Stop streams
  - Body: `{"symbols": ["BTCUSDT"]}`
- `GET /stream/status` - Get stream status
- `WS /ws` - WebSocket endpoint for frontend

### Analytics

- `GET /analytics/pair` - Comprehensive pair analytics
  - Query params: `pair`, `tf`, `window`, `regression`
  - Returns: hedge_ratio, spread, zscore, rolling_corr, adf
- `GET /analytics/adf` - ADF stationarity test
- `GET /analytics/hedge-ratio` - Hedge ratio only
- `GET /analytics/spread` - Spread only
- `GET /analytics/zscore` - Z-score only
- `GET /analytics/correlation` - Rolling correlation

### Alerts

- `POST /alerts` - Create alert
  - Body: `{"metric": "zscore", "pair": "BTCUSDT-ETHUSDT", "op": ">", "value": 2}`
- `GET /alerts` - List all alerts
- `GET /alerts/active` - Get triggered alerts
- `GET /alerts/{id}` - Get specific alert
- `DELETE /alerts/{id}` - Delete alert
- `POST /alerts/clear` - Clear triggered alerts

### Export

- `GET /export` - Export analytics as CSV
  - Query params: `pair`, `tf`, `format`, `window`, `regression`
- `GET /export/ohlcv` - Export OHLCV as CSV
  - Query params: `symbol`, `tf`, `limit`

## 🔌 WebSocket Protocol

### Frontend → Backend

**Subscribe to symbols:**
```json
{
  "action": "subscribe",
  "symbols": ["BTCUSDT", "ETHUSDT"]
}
```

**Unsubscribe:**
```json
{
  "action": "unsubscribe",
  "symbols": ["BTCUSDT"]
}
```

**Heartbeat:**
```json
{
  "action": "ping"
}
```

### Backend → Frontend

**Tick data:**
```json
{
  "type": "trade",
  "symbol": "BTCUSDT",
  "price": 34200.5,
  "qty": 0.002,
  "ts": "2025-10-31T10:30:45.123Z"
}
```

**Alert notification:**
```json
{
  "type": "alert",
  "id": "alert-123",
  "message": "zscore > 2 for BTCUSDT-ETHUSDT",
  "metric": "zscore",
  "pair": "BTCUSDT-ETHUSDT",
  "actual_value": 2.15,
  "threshold_value": 2.0,
  "ts": "2025-10-31T10:30:45.123Z"
}
```

**Subscription confirmation:**
```json
{
  "type": "subscription",
  "status": "subscribed",
  "symbols": ["BTCUSDT"]
}
```

## ⚙️ Configuration

Edit `.env` file or set environment variables:

```bash
# Server
HOST=0.0.0.0
PORT=8000

# Data
TICK_BUFFER_SIZE=10000
RESAMPLE_INTERVALS=1s,1m,5m
MAX_SYMBOLS=10

# Binance
BINANCE_WS_BASE=wss://fstream.binance.com/ws

# Symbols
AVAILABLE_SYMBOLS=BTCUSDT,ETHUSDT,BNBUSDT,SOLUSDT,ADAUSDT

# Analytics
DEFAULT_ROLLING_WINDOW=60
DEFAULT_REGRESSION=OLS

# CORS
CORS_ORIGINS=http://localhost:8080,http://localhost:3000,http://localhost:5173

# Logging
LOG_LEVEL=INFO
```

## 📊 Analytics Details

### Hedge Ratio

Computed using linear regression between two price series:
- **OLS**: Ordinary Least Squares
- **Huber**: Robust regression (outlier resistant)
- **Theil-Sen**: Robust estimator
- **Kalman**: Kalman filter (adaptive)

### Spread

```
Spread = Price_A - (Hedge_Ratio × Price_B)
```

### Z-Score

```
Z-Score = (Spread - Mean(Spread)) / StdDev(Spread)
```

Used for mean reversion strategies.

### ADF Test

Augmented Dickey-Fuller test for stationarity:
- **p-value < 0.05**: Spread is stationary (mean-reverting)
- **p-value ≥ 0.05**: Spread is non-stationary

## 🔒 Security Features

- **CORS**: Configurable allowed origins
- **Input Validation**: Pydantic models for all requests
- **Error Handling**: Comprehensive exception handling
- **Rate Limiting**: Can be added via middleware (TODO)
- **Authentication**: Can be added via JWT (TODO)

## 📝 Logging

Logs are stored in:
- **Console**: Colored output with timestamps
- **Files**: `logs/app_YYYY-MM-DD.log`
  - Rotation: Daily
  - Retention: 7 days
  - Compression: ZIP

## 🧪 Testing

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests (TODO)
pytest tests/
```

## 🐛 Debugging

Enable debug logging:

```bash
# In .env
LOG_LEVEL=DEBUG
```

Check application health:

```bash
curl http://localhost:8000/health
```

Monitor stream status:

```bash
curl http://localhost:8000/stream/status
```

## 🚀 Deployment

### Docker (recommended)

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:

```bash
docker build -t quant-backend .
docker run -p 8000:8000 quant-backend
```

### Production Checklist

- [ ] Set `LOG_LEVEL=WARNING` or `ERROR`
- [ ] Configure proper CORS origins
- [ ] Use multiple workers: `--workers 4`
- [ ] Set up reverse proxy (nginx)
- [ ] Enable HTTPS
- [ ] Add rate limiting
- [ ] Add authentication
- [ ] Set up monitoring (Prometheus, Grafana)
- [ ] Configure log aggregation

## 📚 Dependencies

Key libraries:
- **fastapi**: Web framework
- **uvicorn**: ASGI server
- **websockets**: WebSocket client
- **pandas**: Data manipulation
- **numpy/scipy**: Numerical computing
- **statsmodels**: Statistical analysis
- **scikit-learn**: Machine learning (regression)
- **loguru**: Logging
- **pydantic**: Data validation

## 🤝 Frontend Integration

The backend is designed to work with the React frontend in `../frontend`.

Frontend should:
1. Connect to `ws://localhost:8000/ws` for WebSocket
2. Use `http://localhost:8000` for REST API
3. Update `.env` in frontend:
   ```
   VITE_API_BASE_URL=http://localhost:8000
   VITE_WS_URL=ws://localhost:8000/ws
   VITE_USE_MOCK=false
   ```

## 📄 License

MIT License - feel free to use for your trading needs.

## 🐛 Known Issues

- Redis integration is prepared but not active (set `USE_REDIS=true` to enable)
- Kalman filter uses OLS as fallback (full implementation TODO)

## 🔄 Future Enhancements

- [ ] Redis persistence layer
- [ ] Historical data backfill
- [ ] More regression methods
- [ ] Advanced order book analytics
- [ ] Machine learning models
- [ ] Database support (PostgreSQL/TimescaleDB)
- [ ] Authentication & authorization
- [ ] Rate limiting
- [ ] Caching layer

## 📞 Support

For issues or questions, check:
- API docs: http://localhost:8000/docs
- Logs: `logs/app_*.log`
- Health: http://localhost:8000/health
