# Quant Analytics Backend - Quick Start

Write-Host "=" -ForegroundColor Cyan -NoNewline; Write-Host ("=" * 59) -ForegroundColor Cyan
Write-Host " Quant Analytics Backend - Starting..." -ForegroundColor Cyan
Write-Host "=" -ForegroundColor Cyan -NoNewline; Write-Host ("=" * 59) -ForegroundColor Cyan
Write-Host ""

# Check if virtual environment exists
if (-Not (Test-Path "venv")) {
    Write-Host "[1/4] Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
    Write-Host "      ✓ Virtual environment created" -ForegroundColor Green
} else {
    Write-Host "[1/4] Virtual environment already exists" -ForegroundColor Green
}

# Activate virtual environment
Write-Host "[2/4] Activating virtual environment..." -ForegroundColor Yellow
& ".\venv\Scripts\Activate.ps1"
Write-Host "      ✓ Virtual environment activated" -ForegroundColor Green

# Install dependencies
Write-Host "[3/4] Installing dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt --quiet
Write-Host "      ✓ Dependencies installed" -ForegroundColor Green

# Create .env if it doesn't exist
if (-Not (Test-Path ".env")) {
    Write-Host "      Creating .env file from template..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "      ✓ .env file created" -ForegroundColor Green
}

# Create logs directory
if (-Not (Test-Path "logs")) {
    New-Item -ItemType Directory -Path "logs" | Out-Null
    Write-Host "      ✓ Logs directory created" -ForegroundColor Green
}

Write-Host ""
Write-Host "[4/4] Starting FastAPI server..." -ForegroundColor Yellow
Write-Host ""
Write-Host "=" -ForegroundColor Cyan -NoNewline; Write-Host ("=" * 59) -ForegroundColor Cyan
Write-Host " Server will start on http://localhost:8000" -ForegroundColor Cyan
Write-Host " API Docs: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host " Press Ctrl+C to stop the server" -ForegroundColor Cyan
Write-Host "=" -ForegroundColor Cyan -NoNewline; Write-Host ("=" * 59) -ForegroundColor Cyan
Write-Host ""

# Start the server
python app.py
