#!/bin/bash

# Simple Dashboard Launcher
# Starts web dashboard for real-time strategy monitoring

echo "=================================================="
echo "SWARM TRADING AI DASHBOARD"
echo "=================================================="
echo ""

# Get VPS IP address
VPS_IP=$(hostname -I | awk '{print $1}')
echo "🌐 VPS IP Address: $VPS_IP"
echo "📊 Dashboard URL: http://$VPS_IP:5000"
echo ""
echo "⚠️  IMPORTANT: Make sure port 5000 is open!"
echo "   If using AWS/GCP/Azure, check security group rules."
echo ""

# Check if virtual environment exists
if [ ! -d "../dashboard-env" ]; then
    echo "❌ Virtual environment not found. Creating..."
    python3 -m venv ../dashboard-env
    source ../dashboard-env/bin/activate
    pip install flask flask-socketio plotly pandas numpy
    deactivate
fi

# Activate virtual environment
echo "🔧 Activating Python virtual environment..."
source ../dashboard-env/bin/activate

# Create necessary directories
mkdir -p logs

# Start dashboard
echo ""
echo "🚀 Starting dashboard server..."
echo "=================================================="
echo "Dashboard is now running!"
echo ""
echo "Access from your browser: http://$VPS_IP:5000"
echo ""
echo "Features available:"
echo "  • Real-time market data (mock)"
echo "  • Agent predictions"
echo "  • Swarm consensus"
echo "  • Interactive charts"
echo "  • Trade history"
echo ""
echo "Press Ctrl+C to stop the dashboard"
echo "=================================================="

# Run dashboard
python app.py

# Deactivate virtual environment
deactivate

echo ""
echo "=================================================="
echo "Dashboard stopped"
echo "=================================================="