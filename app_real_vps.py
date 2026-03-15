#!/usr/bin/env python3
"""
Dashboard REAL para Swarm Trading AI
Con sistema real de precios y agentes Swarm
"""

import os
import sys
import json
import time
import threading
import asyncio
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import pandas as pd
import numpy as np

# Importar sistema real de trading
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    from connect_real_system import real_system, start_real_system, REAL_SYSTEM_AVAILABLE
    print(f"✅ Sistema real importado - Modo: {'REAL' if REAL_SYSTEM_AVAILABLE else 'SIMULADO'}")
except ImportError as e:
    print(f"⚠️  Error importando sistema real: {e}")
    REAL_SYSTEM_AVAILABLE = False
    real_system = None

# Configuración de la aplicación
app = Flask(__name__)
app.config['SECRET_KEY'] = 'swarm-trading-ai-real-system-2026'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Estado del sistema
class DashboardState:
    def __init__(self):
        self.connected_clients = 0
        self.system_mode = 'REAL' if REAL_SYSTEM_AVAILABLE else 'SIMULATED'
        
    def get_dashboard_data(self):
        """Obtener datos del sistema real o simulado"""
        if real_system:
            return real_system.get_dashboard_data()
        else:
            # Fallback a datos simulados
            return self._get_simulated_data()
    
    def _get_simulated_data(self):
        """Datos simulados como fallback"""
        return {
            'portfolio': {'value': 25123.45, 'change': 2.8},
            'activeSignals': {'count': 3, 'details': '2 BUY, 1 SELL'},
            'winRate': 62.4,
            'sharpeRatio': 2.31,
            'profitFactor': 2.45,
            'maxDrawdown': 23.09,
            'annualReturn': 97.94,
            'swarmConfidence': 94,
            'prices': {
                'BTC': {'price': 68423.50, 'change': 1.8},
                'ETH': {'price': 3812.30, 'change': -0.9},
                'SOL': {'price': 142.56, 'change': 3.2}
            },
            'agents': {
                'trend': {'status': 'active', 'confidence': 88, 'last_update': datetime.now().isoformat()},
                'reversal': {'status': 'active', 'confidence': 76, 'last_update': datetime.now().isoformat()},
                'volatility': {'status': 'training', 'confidence': 45, 'last_update': datetime.now().isoformat()},
                'volume': {'status': 'offline', 'confidence': 0, 'last_update': None},
                'sentiment': {'status': 'offline', 'confidence': 0, 'last_update': None}
            },
            'signals': [],
            'priceHistory': {
                'BTC': {'times': ['10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00'],
                       'prices': [68000, 68200, 68400, 68300, 68500, 68423, 68450],
                       'volumes': [1000, 1200, 1100, 900, 1300, 1400, 1200]},
                'ETH': {'times': ['10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00'],
                       'prices': [3800, 3810, 3815, 3810, 3812, 3812, 3813],
                       'volumes': [500, 600, 550, 450, 650, 700, 600]},
                'SOL': {'times': ['10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00'],
                       'prices': [140, 141, 142, 141.5, 142, 142.5, 142.56],
                       'volumes': [2000, 2200, 2100, 1900, 2300, 2400, 2200]}
            },
            'timestamp': datetime.now().isoformat(),
            'systemMode': 'SIMULATED'
        }

# Instancia global del estado
dashboard_state = DashboardState()

# Rutas principales
@app.route('/')
def index():
    """Página principal del dashboard"""
    return render_template('index_modern.html')

@app.route('/modern')
def modern_dashboard():
    """Dashboard moderno con todas las funcionalidades"""
    return render_template('index_modern.html')

@app.route('/real')
def real_dashboard():
    """Dashboard con sistema real"""
    return render_template('index_modern.html')

@app.route('/api/dashboard-data')
def get_dashboard_data():
    """API para obtener datos del dashboard"""
    data = dashboard_state.get_dashboard_data()
    return jsonify(data)

@app.route('/api/generate-signal', methods=['POST'])
def generate_signal():
    """API para generar una nueva señal"""
    if real_system:
        signal = real_system.generate_real_signal()
    else:
        # Señal simulada
        signal = dashboard_state._generate_simulated_signal()
    
    # Emitir via WebSocket
    socketio.emit('signal_update', signal, broadcast=True)
    return jsonify({'success': True, 'signal': signal})

@app.route('/api/execute-signal/<signal_id>', methods=['POST'])
def execute_signal(signal_id):
    """API para ejecutar una señal"""
    if real_system:
        result = real_system.execute_signal(signal_id)
    else:
        # Ejecución simulada
        result = {'success': False, 'message': 'Sistema real no disponible'}
    
    if result.get('success'):
        # Emitir actualización
        socketio.emit('signal_executed', result['signal'], broadcast=True)
    
    return jsonify(result)

# Handlers de WebSocket
@socketio.on('connect')
def handle_connect():
    """Manejar conexión de cliente"""
    dashboard_state.connected_clients += 1
    print(f"Cliente conectado. Total: {dashboard_state.connected_clients}")
    
    # Enviar estado inicial
    emit('connected', {
        'message': f'Conectado al Swarm Trading AI - Modo: {dashboard_state.system_mode}',
        'timestamp': datetime.now().isoformat(),
        'systemMode': dashboard_state.system_mode
    })
    emit('initial_data', dashboard_state.get_dashboard_data())

@socketio.on('disconnect')
def handle_disconnect():
    """Manejar desconexión de cliente"""
    dashboard_state.connected_clients -= 1
    print(f"Cliente desconectado. Total: {dashboard_state.connected_clients}")

@socketio.on('generate_signal')
def handle_generate_signal():
    """Manejar solicitud de generación de señal"""
    if real_system:
        signal = real_system.generate_real_signal()
    else:
        signal = dashboard_state._generate_simulated_signal()
    
    emit('signal_update', signal, broadcast=True)
    emit('signal_generated', {
        'message': 'Nueva señal generada',
        'signal': signal,
        'systemMode': dashboard_state.system_mode
    })

@socketio.on('execute_signal')
def handle_execute_signal(data):
    """Manejar ejecución de señal"""
    signal_id = data.get('signalId')
    
    if real_system:
        result = real_system.execute_signal(signal_id)
    else:
        result = {'success': False, 'message': 'Sistema real no disponible'}
    
    if result.get('success'):
        emit('signal_executed', result['signal'], broadcast=True)
        emit('execution_result', {
            'success': True,
            'message': f"Señal {signal_id} ejecutada",
            'signal': result['signal'],
            'systemMode': dashboard_state.system_mode
        })
    else:
        emit('execution_result', {
            'success': False,
            'message': result.get('message', 'Error ejecutando señal'),
            'systemMode': dashboard_state.system_mode
        })

@socketio.on('timeframe_change')
def handle_timeframe_change(data):
    """Manejar cambio de timeframe en gráficos"""
    timeframe = data.get('timeframe', '1d')
    print(f"Cliente cambió timeframe a: {timeframe}")
    
    emit('timeframe_updated', {
        'timeframe': timeframe,
        'message': f'Gráfico actualizado a {timeframe}',
        'timestamp': datetime.now().isoformat(),
        'systemMode': dashboard_state.system_mode
    })

# Tarea en segundo plano para actualizaciones periódicas
def background_updates():
    """Tarea en segundo plano para actualizar precios y estado"""
    while True:
        try:
            # Enviar actualización a todos los clientes conectados
            if dashboard_state.connected_clients > 0:
                data = dashboard_state.get_dashboard_data()
                
                # Extraer solo datos de actualización frecuente
                update_data = {
                    'portfolio': data['portfolio'],
                    'activeSignals': data['activeSignals'],
                    'prices': data['prices'],
                    'timestamp': data['timestamp'],
                    'systemMode': data['systemMode']
                }
                
                socketio.emit('price_update', update_data)
            
            # Ocasionalmente generar señal automática
            if np.random.random() < 0.05:  # 5% de probabilidad cada ciclo
                if real_system:
                    signal = real_system.generate_real_signal()
                else:
                    signal = dashboard_state._generate_simulated_signal()
                
                if signal:
                    socketio.emit('signal_update', signal, broadcast=True)
            
            # Esperar antes de la próxima actualización
            time.sleep(5)  # Actualizar cada 5 segundos
            
        except Exception as e:
            print(f"Error en background_updates: {e}")
            time.sleep(10)

# Método auxiliar para señales simuladas
def _generate_simulated_signal():
    """Generar señal simulada (solo para fallback)"""
    symbols = ['BTC', 'ETH', 'SOL']
    signal_types = ['BUY', 'SELL']
    strategies = ['Swarm AI Consensus', 'Trend Following', 'Mean Reversion']
    
    symbol = np.random.choice(symbols)
    signal_type = np.random.choice(signal_types, p=[0.6, 0.4])
    current_price = np.random.uniform(
        {'BTC': 50000, 'ETH': 3000, 'SOL': 100}[symbol],
        {'BTC': 70000, 'ETH': 4000, 'SOL': 150}[symbol]
    )
    
    if signal_type == 'BUY':
        entry = current_price * (1 - np.random.uniform(0.001, 0.005))
        take_profit = entry * (1 + np.random.uniform(0.01, 0.03))
        stop_loss = entry * (1 - np.random.uniform(0.005, 0.015))
    else:
        entry = current_price * (1 + np.random.uniform(0.001, 0.005))
        take_profit = entry * (1 - np.random.uniform(0.01, 0.03))
        stop_loss = entry * (1 + np.random.uniform(0.005, 0.015))
    
    return {
        'id': f"signal_{int(time.time())}_{np.random.randint(1000, 9999)}",
        'symbol': symbol,
        'type': signal_type,
        'price': round(current_price, 2),
        'change': np.random.uniform(-3, 3),
        'entry': round(entry, 2),
        'takeProfit': round(take_profit, 2),
        'stopLoss': round(stop_loss, 2),
        'confidence': np.random.randint(70, 95),
        'strategy': np.random.choice(strategies),
        'timestamp': datetime.now().isoformat(),
        'executed': False
    }

# Añadir método al estado
dashboard_state._generate_simulated_signal = _generate_simulated_signal

# Iniciar tarea en segundo plano
def start_background_thread():
    """Iniciar el hilo de actualizaciones en segundo plano"""
    thread = threading.Thread(target=background_updates, daemon=True)
    thread.start()
    print("✅ Hilo de actualizaciones en segundo plano iniciado")

# Configuración e inicio
if __name__ == '__main__':
    # Iniciar sistema real si está disponible
    if REAL_SYSTEM_AVAILABLE:
        try:
            start_real_system()
            print("✅ Sistema real de trading iniciado")
        except Exception as e:
            print(f"⚠️  Error iniciando sistema real: {e}")
    
    # Iniciar hilo de actualizaciones
    start_background_thread()
    
    print("\n" + "="*60)
    print("🚀 SWARM TRADING AI - DASHBOARD REAL")
    print("="*60)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Modo: {dashboard_state.system_mode}")
    print(f"Agentes: {'REALES' if real_system and real_system.swarm_coordinator else 'SIMULADOS'}")
    print(f"Precios: {'REALES (CoinGecko)' if real_system and real_system.price_fetcher else 'SIMULADOS'}")
    print(f"Dashboard disponible en: http://0.0.0.0:5000")
    print(f"Dashboard moderno: http://0.0.0.0:5000/modern")
    print(f"Dashboard real: http://0.0.0.0:5000/real")
    print("="*60 + "\n")
    
    # Iniciar servidor
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)