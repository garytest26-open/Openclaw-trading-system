#!/bin/bash

# Swarm Trading AI - Training Script
# Trains neural agents with 3 years of BTC, ETH, SOL data for 100 epochs

echo "=================================================="
echo "SWARM TRADING AI - TRAINING LAUNCHER"
echo "=================================================="
echo ""
echo "Training Parameters:"
echo "  • Epochs: 100"
echo "  • Historical data: 3 years"
echo "  • Symbols: BTC, ETH, SOL"
echo "  • Agents: Trend, Reversal, Volatility"
echo ""
echo "This will:"
echo "  1. Download 3 years of historical data"
echo "  2. Calculate technical features"
echo "  3. Train 3 neural agents (100 epochs each)"
echo "  4. Save trained models"
echo "  5. Generate training report"
echo ""
echo "Estimated time: 5-10 minutes"
echo "=================================================="
echo ""

# Check if virtual environment exists
if [ ! -d "../trading-env" ]; then
    echo "❌ Virtual environment not found. Please run ../setup.sh first"
    exit 1
fi

# Activate virtual environment
echo "🔧 Activating Python virtual environment..."
source ../trading-env/bin/activate

# Check Python packages
echo "📦 Checking Python packages..."
python -c "import yfinance, numpy, pandas, torch" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ Missing required packages. Installing..."
    pip install yfinance numpy pandas torch
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p models logs

# Start training
echo ""
echo "🚀 Starting training process..."
echo "=================================================="

# Run training script
python train_all.py

# Deactivate virtual environment
deactivate

echo ""
echo "=================================================="
echo "Training process completed!"
echo "Check trading/swarm_ai/models/ for trained models"
echo "Check trading/swarm_ai/logs/ for training logs"
echo "=================================================="