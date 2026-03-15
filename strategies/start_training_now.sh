#!/bin/bash

# Swarm Trading AI - Training Script
# Trains agents with 100 epochs and 3 years of BTC/ETH/SOL data

echo "=================================================="
echo "SWARM TRADING AI - ENTRENAMIENTO"
echo "=================================================="
echo ""
echo "Parámetros:"
echo "  • Épocas: 100"
echo "  • Datos: 3 años históricos"
echo "  • Activos: BTC, ETH, SOL"
echo "  • Agentes: Trend, Reversal, Volatility"
echo ""
echo "Tiempo estimado: 30-60 minutos"
echo "=================================================="

# Check if virtual environment exists
if [ ! -d "../trading-env" ]; then
    echo "❌ Virtual environment not found. Creating..."
    python3 -m venv ../trading-env
    source ../trading-env/bin/activate
    pip install torch pandas numpy yfinance scikit-learn matplotlib tqdm
    deactivate
fi

# Activate virtual environment
echo "🔧 Activating Python virtual environment..."
source ../trading-env/bin/activate

# Create training directory
mkdir -p models logs

# Start training
echo ""
echo "🚀 Starting training..."
echo "=================================================="

# Run training
python train_all.py

# Deactivate virtual environment
deactivate

echo ""
echo "=================================================="
echo "✅ Training completed!"
echo "=================================================="
echo ""
echo "Models saved in: trading/swarm_ai/models/"
echo "Logs saved in: trading/swarm_ai/logs/"
echo ""
echo "Next steps:"
echo "1. Run backtesting: python backtest.py --years 2"
echo "2. Connect dashboard to real data"
echo "3. Test on Hyperliquid testnet"
echo "=================================================="