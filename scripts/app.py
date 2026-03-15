#!/usr/bin/env python3
"""
Swarm Trading AI Dashboard
Web dashboard for real-time strategy monitoring
"""

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import json
import time
import threading
import logging
from datetime import datetime
import pandas as pd
import numpy as np
import plotly
import plotly.graph_objs as go
from plotly.subplots import make_subplots
import sys
import os

# Add paths
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'swarm_ai'))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'swarm-trading-secret-2026'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global state
dashboard_state = {
    'is_running': False,
    'strategies': {},
    'performance': {},
    'market_data': {},
    'agent_predictions': {},
    'trade_history': [],
    'last_update': None
}

# Mock data generator (in production, this would connect to real trading system)
class MockTradingSystem:
    def __init__(self):
        self.symbols = ['BTC', 'ETH', 'SOL']
        self.agents = ['trend', 'reversal', 'volatility', 'volume', 'sentiment']
        self.strategies = ['swarm_consensus', 'trend_following', 'mean_reversion']
        
    def generate_market_data(self):
        """Generate mock market data"""
        data = {}
        for symbol in self.symbols:
            # Generate realistic price data
            if symbol == 'BTC':
                price = 50000 + np.random.normal(0, 500)
            elif symbol == 'ETH':
                price = 3000 + np.random.normal(0, 50)
            else:  # SOL
                price = 100 + np.random.normal(0, 5)
            
            data[symbol] = {
                'price': round(price, 2),
                'change': round(np.random.normal(0, 0.02), 4),
                'volume': np.random.randint(1000, 10000),
                'timestamp': datetime.now().isoformat()
            }
        return data
    
    def generate_agent_predictions(self):
        """Generate mock agent predictions"""
        predictions = {}
        for agent in self.agents[:3]:  # Only implemented agents
            signal = np.random.choice(['BUY', 'SELL', 'HOLD'], p=[0.4, 0.3, 0.3])
            confidence = np.random.uniform(0.5, 0.95)
            
            predictions[agent] = {
                'signal': signal,
                'confidence': round(confidence, 3),
                'strength': round(np.random.uniform(0.3, 0.9), 3),
                'timestamp': datetime.now().isoformat()
            }
        return predictions
    
    def generate_swarm_consensus(self):
        """Generate mock swarm consensus"""
        signals = ['BUY', 'SELL', 'HOLD']
        weights = [0.4, 0.3, 0.3]
        
        return {
            'signal': np.random.choice(signals, p=weights),
            'strength': round(np.random.uniform(0.4, 0.9), 3),
            'confidence': round(np.random.uniform(0.6, 0.95), 3),
            'agreement': round(np.random.uniform(0.5, 0.9), 3),
            'buy_votes': np.random.randint(1, 4),
            'sell_votes': np.random.randint(0, 3),
            'hold_votes': np.random.randint(0, 2),
            'timestamp': datetime.now().isoformat()
        }
    
    def generate_performance_metrics(self):
        """Generate mock performance metrics"""
        return {
            'total_trades': np.random.randint(50, 200),
            'winning_trades': np.random.randint(30, 100),
            'losing_trades': np.random.randint(10, 50),
            'win_rate': round(np.random.uniform(0.55, 0.75), 3),
            'total_pnl': round(np.random.uniform(-500, 2000), 2),
            'sharpe_ratio': round(np.random.uniform(0.5, 2.5), 2),
            'max_drawdown': round(np.random.uniform(0.05, 0.15), 3),
            'current_drawdown': round(np.random.uniform(0, 0.08), 3)
        }
    
    def generate_trade_history(self, count=10):
        """Generate mock trade history"""
        trades = []
        symbols = ['BTC', 'ETH', 'SOL']
        sides = ['BUY', 'SELL']
        
        for i in range(count):
            trade_time = datetime.now() - pd.Timedelta(hours=i*2)
            symbol = np.random.choice(symbols)
            
            if symbol == 'BTC':
                price = 50000 + np.random.normal(0, 1000)
                size = np.random.uniform(0.01, 0.1)
            elif symbol == 'ETH':
                price = 3000 + np.random.normal(0, 100)
                size = np.random.uniform(0.1, 1)
            else:
                price = 100 + np.random.normal(0, 10)
                size = np.random.uniform(1, 10)
            
            side = np.random.choice(sides)
            pnl = np.random.uniform(-100, 300)
            
            trades.append({
                'id': f'trade_{i+1}',
                'symbol': symbol,
                'side': side,
                'entry_price': round(price, 2),
                'size': round(size, 4),
                'pnl': round(pnl, 2),
                'pnl_percent': round(pnl / (price * size) * 100, 2),
                'status': 'CLOSED' if i > 2 else 'OPEN',
                'entry_time': trade_time.isoformat(),
                'exit_time': (trade_time + pd.Timedelta(hours=1)).isoformat() if i > 2 else None
            })
        
        return trades

# Initialize mock system
mock_system = MockTradingSystem()

# Background thread for data updates
def background_data_updater():
    """Background thread to update dashboard data"""
    while True:
        if dashboard_state['is_running']:
            try:
                # Update all data
                dashboard_state['market_data'] = mock_system.generate_market_data()
                dashboard_state['agent_predictions'] = mock_system.generate_agent_predictions()
                dashboard_state['strategies']['swarm_consensus'] = mock_system.generate_swarm_consensus()
                dashboard_state['performance'] = mock_system.generate_performance_metrics()
                
                # Update trade history periodically
                if len(dashboard_state['trade_history']) < 20:
                    new_trades = mock_system.generate_trade_history(5)
                    dashboard_state['trade_history'] = new_trades + dashboard_state['trade_history'][:15]
                
                dashboard_state['last_update'] = datetime.now().isoformat()
                
                # Emit update via WebSocket
                socketio.emit('data_update', {
                    'market_data': dashboard_state['market_data'],
                    'agent_predictions': dashboard_state['agent_predictions'],
                    'swarm_consensus': dashboard_state['strategies'].get('swarm_consensus', {}),
                    'timestamp': dashboard_state['last_update']
                })
                
                logger.info(f"Dashboard data updated at {dashboard_state['last_update']}")
                
            except Exception as e:
                logger.error(f"Error updating dashboard data: {e}")
        
        time.sleep(5)  # Update every 5 seconds

# Start background thread
data_thread = threading.Thread(target=background_data_updater, daemon=True)
data_thread.start()

# Routes
@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')

@app.route('/api/status')
def get_status():
    """Get dashboard status"""
    return jsonify({
        'status': 'running' if dashboard_state['is_running'] else 'stopped',
        'last_update': dashboard_state['last_update'],
        'symbols': list(dashboard_state['market_data'].keys()),
        'agents': list(dashboard_state['agent_predictions'].keys())
    })

@app.route('/api/market-data')
def get_market_data():
    """Get current market data"""
    return jsonify(dashboard_state['market_data'])

@app.route('/api/agent-predictions')
def get_agent_predictions():
    """Get agent predictions"""
    return jsonify(dashboard_state['agent_predictions'])

@app.route('/api/swarm-consensus')
def get_swarm_consensus():
    """Get swarm consensus"""
    return jsonify(dashboard_state['strategies'].get('swarm_consensus', {}))

@app.route('/api/performance')
def get_performance():
    """Get performance metrics"""
    return jsonify(dashboard_state['performance'])

@app.route('/api/trade-history')
def get_trade_history():
    """Get trade history"""
    return jsonify(dashboard_state['trade_history'][:20])

@app.route('/api/start', methods=['POST'])
def start_dashboard():
    """Start dashboard updates"""
    dashboard_state['is_running'] = True
    return jsonify({'status': 'started', 'message': 'Dashboard updates started'})

@app.route('/api/stop', methods=['POST'])
def stop_dashboard():
    """Stop dashboard updates"""
    dashboard_state['is_running'] = False
    return jsonify({'status': 'stopped', 'message': 'Dashboard updates stopped'})

@app.route('/api/charts/price-history')
def get_price_history_chart():
    """Generate price history chart"""
    # Generate mock price history
    dates = pd.date_range(end=datetime.now(), periods=100, freq='H')
    
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('BTC Price History', 'ETH Price History', 
                       'SOL Price History', 'Market Correlation'),
        vertical_spacing=0.15,
        horizontal_spacing=0.1
    )
    
    # BTC chart
    btc_prices = 50000 + np.cumsum(np.random.normal(0, 100, 100))
    fig.add_trace(
        go.Scatter(x=dates, y=btc_prices, mode='lines', name='BTC',
                  line=dict(color='#F7931A', width=2)),
        row=1, col=1
    )
    
    # ETH chart
    eth_prices = 3000 + np.cumsum(np.random.normal(0, 20, 100))
    fig.add_trace(
        go.Scatter(x=dates, y=eth_prices, mode='lines', name='ETH',
                  line=dict(color='#627EEA', width=2)),
        row=1, col=2
    )
    
    # SOL chart
    sol_prices = 100 + np.cumsum(np.random.normal(0, 2, 100))
    fig.add_trace(
        go.Scatter(x=dates, y=sol_prices, mode='lines', name='SOL',
                  line=dict(color='#00FFA3', width=2)),
        row=2, col=1
    )
    
    # Correlation heatmap
    corr_matrix = np.array([
        [1.0, 0.75, 0.65],
        [0.75, 1.0, 0.55],
        [0.65, 0.55, 1.0]
    ])
    
    fig.add_trace(
        go.Heatmap(
            z=corr_matrix,
            x=['BTC', 'ETH', 'SOL'],
            y=['BTC', 'ETH', 'SOL'],
            colorscale='RdBu',
            zmin=-1, zmax=1,
            showscale=True
        ),
        row=2, col=2
    )
    
    # Update layout
    fig.update_layout(
        height=800,
        showlegend=True,
        title_text="Market Analysis Dashboard",
        template="plotly_dark"
    )
    
    return jsonify(json.loads(fig.to_json()))

@app.route('/api/charts/agent-performance')
def get_agent_performance_chart():
    """Generate agent performance chart"""
    agents = ['Trend Agent', 'Reversal Agent', 'Volatility Agent']
    accuracy = [0.85, 0.78, 0.82]
    confidence = [0.88, 0.75, 0.80]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=agents,
        y=accuracy,
        name='Accuracy',
        marker_color='#2E86AB'
    ))
    
    fig.add_trace(go.Bar(
        x=agents,
        y=confidence,
        name='Confidence',
        marker_color='#A23B72'
    ))
    
    fig.update_layout(
        title='Agent Performance Metrics',
        xaxis_title='Agent',
        yaxis_title='Score',
        barmode='group',
        template="plotly_dark",
        height=500
    )
    
    return jsonify(json.loads(fig.to_json()))

# WebSocket events
@socketio.on('connect')
def handle_connect():
    """Handle WebSocket connection"""
    logger.info('Client connected')
    emit('connected', {'status': 'connected', 'timestamp': datetime.now().isoformat()})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnection"""
    logger.info('Client disconnected')

@socketio.on('request_update')
def handle_request_update():
    """Handle update request from client"""
    emit('data_update', {
        'market_data': dashboard_state['market_data'],
        'agent_predictions': dashboard_state['agent_predictions'],
        'swarm_consensus': dashboard_state['strategies'].get('swarm_consensus', {}),
        'timestamp': dashboard_state['last_update']
    })

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('trading/dashboard/templates', exist_ok=True)
    
    # Start dashboard updates
    dashboard_state['is_running'] = True
    
    logger.info("Starting Swarm Trading AI Dashboard...")
    logger.info("Dashboard will be available at: http://<VPS_IP>:5000")
    logger.info("Press Ctrl+C to stop")
    
    # Run Flask app
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)