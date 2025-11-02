#!/bin/bash

echo "============================================================"
echo " Quant Analytics Backend - Starting..."
echo "============================================================"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "[1/4] Creating virtual environment..."
    python3 -m venv venv
    echo "      ✓ Virtual environment created"
else
    echo "[1/4] Virtual environment already exists"
fi

# Activate virtual environment
echo "[2/4] Activating virtual environment..."
source venv/bin/activate
echo "      ✓ Virtual environment activated"

# Install dependencies
echo "[3/4] Installing dependencies..."
pip install -r requirements.txt --quiet
echo "      ✓ Dependencies installed"

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo "      Creating .env file from template..."
    cp .env.example .env
    echo "      ✓ .env file created"
fi

# Create logs directory
if [ ! -d "logs" ]; then
    mkdir logs
    echo "      ✓ Logs directory created"
fi

echo ""
echo "[4/4] Starting FastAPI server..."
echo ""
echo "============================================================"
echo " Server will start on http://localhost:8000"
echo " API Docs: http://localhost:8000/docs"
echo " Press Ctrl+C to stop the server"
echo "============================================================"
echo ""

# Start the server
python app.py
