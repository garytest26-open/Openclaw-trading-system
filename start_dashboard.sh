#!/bin/bash

# Swarm Trading AI Dashboard Launcher
# Starts web dashboard for real-time strategy monitoring

echo "=================================================="
echo "SWARM TRADING AI DASHBOARD"
echo "=================================================="
echo ""
echo "This will start a web dashboard that you can access"
echo "from your browser to monitor trading strategies in"
echo "real-time."
echo ""
echo "Dashboard features:"
echo "  • Real-time market data"
echo "  • Agent predictions"
echo "  • Swarm consensus"
echo "  • Performance metrics"
echo "  • Trade history"
echo "  • Interactive charts"
echo ""
echo "Access URL: http://<VPS_IP>:5000"
echo ""
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

# Install required packages
echo "📦 Installing required packages..."
pip install flask flask-socketio plotly pandas numpy

# Get VPS IP address
VPS_IP=$(hostname -I | awk '{print $1}')
echo ""
echo "🌐 VPS IP Address: $VPS_IP"
echo "📊 Dashboard will be available at: http://$VPS_IP:5000"
echo ""
echo "⚠️  Important: Make sure port 5000 is open in your firewall!"
echo "   If using AWS/GCP/Azure, check security group rules."
echo ""

# Check if port 5000 is available
if lsof -Pi :5000 -sTCP:LISTEN -t >/dev/null ; then
    echo "✅ Port 5000 is available"
else
    echo "⚠️  Port 5000 might be blocked by firewall"
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p logs

# Start dashboard
echo ""
echo "🚀 Starting dashboard server..."
echo "=================================================="
echo "Press Ctrl+C to stop the dashboard"
echo ""

# Run dashboard
python app.py

# Deactivate virtual environment
deactivate

echo ""
echo "=================================================="
echo "Dashboard stopped"
echo "=================================================="