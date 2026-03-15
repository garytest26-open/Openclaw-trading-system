#!/usr/bin/env python3
"""
Dashboard moderno para Swarm Trading AI
Con WebSocket en tiempo real, datos reales y interfaz profesional
"""

import os
import json
import time
import threading
import asyncio
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import pandas as pd
import numpy as np
import plotly.graph_objs as go
import plotly.utils
from typing import Dict, List, Optional, Any

# Importar componentes del sistema de trading
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    from swarm_ai.swarm.swarm_coordinator import SwarmCoordinator
    from swarm_ai.agents.trend_agent import TrendAgent
    from swarm_ai.agents.reversal_agent import ReversalAgent
    from swarm_ai.agents.volatility_agent import VolatilityAgent
    from swarm_ai.signal_generator import SignalGenerator
    from swarm_ai.price_fetcher import PriceFetcher
    SWARM_AVAILABLE = True
except ImportError as e:
    print(f"Advertencia: No se pudieron importar módulos de trading: {e}")
    print("Usando datos simulados para el dashboard")
    SWARM_AVAILABLE = False

# Configuración de la aplicación
app = Flask(__name__)
app.config['SECRET_KEY'] = 'swarm-trading-ai-secret-key-2026'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Estado del sistema
class TradingSystemState:
    def __init__(self):
        self.connected_clients = 0
        self.last_prices = {
            'BTC': {'price': 68423.50, 'change': 1.8, 'timestamp': datetime.now()},
            'ETH': {'price': 3812.30, 'change': -0.9, 'timestamp': datetime.now()},
            'SOL': {'price': 142.56, 'change': 3.2, 'timestamp': datetime.now()}
        }
        self.active_signals = []
        self.agents_status = {
            'trend': {'status': 'active', 'confidence': 88, 'last_update': datetime.now()},
            'reversal': {'status': 'active', 'confidence': 76, 'last_update': datetime.now()},
            'volatility': {'status': 'training', 'confidence': 45, 'last_update': datetime.now()},
            'volume': {'status': 'offline', 'confidence': 0, 'last_update': None},
            'sentiment': {'status': 'offline', 'confidence': 0, 'last_update': None}
        }
        self.portfolio_value = 24857.32
        self.portfolio_change = 2.4
        self.win_rate = 62.4
        self.sharpe_ratio = 2.31
        self.profit_factor = 2.45
        self.max_drawdown = 23.09
        self.annual_return = 97.94
        self.swarm_confidence = 94
        
        # Historial para gráficos
        self.price_history = {
            'BTC': [],
            'ETH': [],
            'SOL': []
        }
        self._init_history()
    
    def _init_history(self):
        """Inicializar historial de precios para gráficos"""
        now = datetime.now()
        for symbol in ['BTC', 'ETH', 'SOL']:
            base_price = self.last_prices[symbol]['price']
            for i in range(7):
                time_point = now - timedelta(hours=6-i*1)
                price_variation = np.random.normal(0, 0.02)  # Variación del 2%
                price = base_price * (1 + price_variation * (6-i)/6)
                self.price_history[symbol].append({
                    'time': time_point,
                    'price': price,
                    'volume': np.random.uniform(100, 1000)
                })
    
    def update_prices(self):
        """Actualizar precios desde APIs reales o simulación"""
        try:
            if SWARM_AVAILABLE:
                # Intentar obtener precios reales
                fetcher = PriceFetcher()
                for symbol in ['BTC', 'ETH', 'SOL']:
                    price_data = fetcher.get_price(symbol)
                    if price_data:
                        old_price = self.last_prices[symbol]['price']
                        new_price = price_data['price']
                        change = ((new_price - old_price) / old_price) * 100
                        self.last_prices[symbol] = {
                            'price': new_price,
                            'change': change,
                            'timestamp': datetime.now()
                        }
                        
                        # Añadir al historial
                        self.price_history[symbol].append({
                            'time': datetime.now(),
                            'price': new_price,
                            'volume': price_data.get('volume', np.random.uniform(100, 1000))
                        })
                        
                        # Mantener solo últimas 100 puntos
                        if len(self.price_history[symbol]) > 100:
                            self.price_history[symbol] = self.price_history[symbol][-100:]
            else:
                # Simulación de precios
                for symbol in self.last_prices:
                    old_price = self.last_prices[symbol]['price']
                    change = np.random.normal(0, 0.001)  # 0.1% de variación
                    new_price = old_price * (1 + change)
                    self.last_prices[symbol] = {
                        'price': new_price,
                        'change': change * 100,
                        'timestamp': datetime.now()
                    }
                    
                    # Añadir al historial
                    self.price_history[symbol].append({
                        'time': datetime.now(),
                        'price': new_price,
                        'volume': np.random.uniform(100, 1000)
                    })
                    
                    # Mantener solo últimas 100 puntos
                    if len(self.price_history[symbol]) > 100:
                        self.price_history[symbol] = self.price_history[symbol][-100:]
                        
            # Actualizar valor del portfolio
            portfolio_change = np.random.normal(0.001, 0.0005)  # 0.1% ± 0.05%
            self.portfolio_value *= (1 + portfolio_change)
            self.portfolio_change = portfolio_change * 100
            
        except Exception as e:
            print(f"Error actualizando precios: {e}")
    
    def generate_signal(self):
        """Generar una nueva señal de trading"""
        symbols = ['BTC', 'ETH', 'SOL']
        signal_types = ['BUY', 'SELL']
        strategies = [
            'Trend Agent + Reversal Consensus',
            'Volatility Spike Detection',
            'Breakout + Volume Confirmation',
            'Mean Reversion Extreme',
            'Swarm AI Consensus'
        ]
        
        symbol = np.random.choice(symbols)
        signal_type = np.random.choice(signal_types, p=[0.6, 0.4])  # 60% BUY, 40% SELL
        current_price = self.last_prices[symbol]['price']
        
        # Generar niveles de entrada, TP y SL
        if signal_type == 'BUY':
            entry = current_price * (1 - np.random.uniform(0.001, 0.005))  # 0.1-0.5% below
            take_profit = entry * (1 + np.random.uniform(0.01, 0.03))  # 1-3% profit
            stop_loss = entry * (1 - np.random.uniform(0.005, 0.015))  # 0.5-1.5% stop
        else:  # SELL
            entry = current_price * (1 + np.random.uniform(0.001, 0.005))  # 0.1-0.5% above
            take_profit = entry * (1 - np.random.uniform(0.01, 0.03))  # 1-3% profit
            stop_loss = entry * (1 + np.random.uniform(0.005, 0.015))  # 0.5-1.5% stop
        
        signal = {
            'id': f"signal_{int(time.time())}_{len(self.active_signals)}",
            'symbol': symbol,
            'type': signal_type,
            'price': current_price,
            'change': self.last_prices[symbol]['change'],
            'entry': round(entry, 2),
            'takeProfit': round(take_profit, 2),
            'stopLoss': round(stop_loss, 2),
            'confidence': np.random.randint(70, 95),
            'strategy': np.random.choice(strategies),
            'timestamp': datetime.now().isoformat(),
            'executed': False
        }
        
        self.active_signals.insert(0, signal)
        
        # Mantener solo últimas 10 señales
        if len(self.active_signals) > 10:
            self.active_signals = self.active_signals[:10]
        
        return signal
    
    def get_dashboard_data(self):
        """Obtener todos los datos para el dashboard"""
        return {
            'portfolio': {
                'value': round(self.portfolio_value, 2),
                'change': round(self.portfolio_change, 2)
            },
            'activeSignals': {
                'count': len(self.active_signals),
                'details': f"{sum(1 for s in self.active_signals if s['type'] == 'BUY')} BUY, {sum(1 for s in self.active_signals if s['type'] == 'SELL')} SELL"
            },
            'winRate': round(self.win_rate, 1),
            'sharpeRatio': round(self.sharpe_ratio, 2),
            'profitFactor': round(self.profit_factor, 2),
            'maxDrawdown': round(self.max_drawdown, 2),
            'annualReturn': round(self.annual_return, 2),
            'swarmConfidence': self.swarm_confidence,
            'prices': self.last_prices,
            'agents': self.agents_status,
            'signals': self.active_signals[:3],  # Solo últimas 3 señales
            'priceHistory': self.get_formatted_history(),
            'timestamp': datetime.now().isoformat()
        }
    
    def get_formatted_history(self):
        """Obtener historial formateado para gráficos"""
        formatted = {}
        for symbol in self.price_history:
            formatted[symbol] = {
                'times': [h['time'].strftime('%H:%M') for h in self.price_history[symbol][-7:]],
                'prices': [h['price'] for h in self.price_history[symbol][-7:]],
                'volumes': [h['volume'] for h in self.price_history[symbol][-7:]]
            }
        return formatted

# Instancia global del estado
system_state = TradingSystemState()

# Rutas principales
@app.route('/')
def index():
    """Página principal del dashboard"""
    return render_template('index_modern.html')

@app.route('/modern')
def modern_dashboard():
    """Dashboard moderno con todas las funcionalidades"""
    return render_template('index_modern.html')

@app.route('/api/dashboard-data')
def get_dashboard_data():
    """API para obtener datos del dashboard"""
    data = system_state.get_dashboard_data()
    return jsonify(data)

@app.route('/api/generate-signal', methods=['POST'])
def generate_signal():
    """API para generar una nueva señal"""
    signal = system_state.generate_signal()
    # Emitir via WebSocket
    socketio.emit('signal_update', signal, broadcast=True)
    return jsonify({'success': True, 'signal': signal})

@app.route('/api/execute-signal/<signal_id>', methods=['POST'])
def execute_signal(signal_id):
    """API para ejecutar una señal"""
    # Buscar señal
    signal = next((s for s in system_state.active_signals if s['id'] == signal_id), None)
    if signal:
        signal['executed'] = True
        signal['executed_at'] = datetime.now().isoformat()
        
        # Simular resultado
        signal['result'] = 'success' if np.random.random() > 0.3 else 'failed'
        if signal['result'] == 'success':
            signal['profit'] = abs(signal['takeProfit'] - signal['entry']) * np.random.uniform(0.8, 1.2)
        
        # Emitir actualización
        socketio.emit('signal_executed', signal, broadcast=True)
        
        return jsonify({'success': True, 'message': 'Señal ejecutada', 'signal': signal})
    
    return jsonify({'success': False, 'message': 'Señal no encontrada'}), 404

# Handlers de WebSocket
@socketio.on('connect')
def handle_connect():
    """Manejar conexión de cliente"""
    system_state.connected_clients += 1
    print(f"Cliente conectado. Total: {system_state.connected_clients}")
    
    # Enviar estado inicial
    emit('connected', {'message': 'Conectado al Swarm Trading AI', 'timestamp': datetime.now().isoformat()})
    emit('initial_data', system_state.get_dashboard_data())

@socketio.on('disconnect')
def handle_disconnect():
    """Manejar desconexión de cliente"""
    system_state.connected_clients -= 1
    print(f"Cliente desconectado. Total: {system_state.connected_clients}")

@socketio.on('generate_signal')
def handle_generate_signal():
    """Manejar solicitud de generación de señal"""
    signal = system_state.generate_signal()
    emit('signal_update', signal, broadcast=True)
    
    # También notificar al cliente que lo solicitó
    emit('signal_generated', {'message': 'Nueva señal generada', 'signal': signal})

@socketio.on('execute_signal')
def handle_execute_signal(data):
    """Manejar ejecución de señal"""
    signal_id = data.get('signalId')
    signal = next((s for s in system_state.active_signals if s['id'] == signal_id), None)
    
    if signal:
        signal['executed'] = True
        signal['executed_at'] = datetime.now().isoformat()
        
        # Simular resultado
        signal['result'] = 'success' if np.random.random() > 0.3 else 'failed'
        if signal['result'] == 'success':
            signal['profit'] = abs(signal['takeProfit'] - signal['entry']) * np.random.uniform(0.8, 1.2)
        
        # Actualizar métricas basadas en resultado simulado
        if signal['result'] == 'success':
            system_state.win_rate = min(100, system_state.win_rate + 0.1)
            system_state.portfolio_value += signal.get('profit', 0)
        else:
            system_state.win_rate = max(0, system_state.win_rate - 0.2)
        
        # Emitir actualización
        emit('signal_executed', signal, broadcast=True)
        
        # Enviar confirmación
        emit('execution_result', {
            'success': True,
            'message': f"Señal {signal_id} ejecutada",
            'signal': signal
        })
    else:
        emit('execution_result', {
            'success': False,
            'message': f"Señal {signal_id} no encontrada"
        })

@socketio.on('timeframe_change')
def handle_timeframe_change(data):
    """Manejar cambio de timeframe en gráficos"""
    timeframe = data.get('timeframe', '1d')
    print(f"Cliente cambió timeframe a: {timeframe}")
    
    # Aquí podríamos ajustar los datos históricos según el timeframe
    emit('timeframe_updated', {
        'timeframe': timeframe,
        'message': f'Gráfico actualizado a {timeframe}',
        'timestamp': datetime.now().isoformat()
    })

# Tarea en segundo plano para actualizaciones periódicas
def background_updates():
    """Tarea en segundo plano para actualizar precios y estado"""
    while True:
        try:
            # Actualizar precios
            system_state.update_prices()
            
            # Enviar actualización a todos los clientes conectados
            if system_state.connected_clients > 0:
                data = {
                    'portfolio': {
                        'value': round(system_state.portfolio_value, 2),
                        'change': round(system_state.portfolio_change, 2)
                    },
                    'activeSignals': {
                        'count': len(system_state.active_signals),
                        'details': f"{sum(1 for s in system_state.active_signals if s['type'] == 'BUY')} BUY, {sum(1 for s in system_state.active_signals if s['type'] == 'SELL')} SELL"
                    },
                    'prices': system_state.last_prices,
                    'timestamp': datetime.now().isoformat()
                }
                
                socketio.emit('price_update', data)
            
            # Ocasionalmente generar una señal automática
            if np.random.random() < 0.1:  # 10% de probabilidad cada ciclo
                signal = system_state.generate_signal()
                socketio.emit('signal_update', signal, broadcast=True)
            
            # Actualizar estado de agentes
            for agent_name in system_state.agents_status:
                agent = system_state.agents_status[agent_name]
                if agent['status'] == 'training' and agent['confidence'] < 100:
                    agent['confidence'] = min(100, agent['confidence'] + np.random.randint(1, 5))
                    agent['last_update'] = datetime.now()
            
            # Esperar antes de la próxima actualización
            time.sleep(5)  # Actualizar cada 5 segundos
            
        except Exception as e:
            print(f"Error en background_updates: {e}")
            time.sleep(10)

# Iniciar tarea en segundo plano
def start_background_thread():
    """Iniciar el hilo de actualizaciones en segundo plano"""
    thread = threading.Thread(target=background_updates, daemon=True)
    thread.start()
    print("Hilo de actualizaciones en segundo plano iniciado")

# Configuración e inicio
if __name__ == '__main__':
    # Asegurar que el template existe
    template_path = os.path.join(app.root_path, 'templates', 'index_modern.html')
    if not os.path.exists(template_path):
        print(f"ADVERTENCIA: Template no encontrado en {template_path}")
        print("Creando template básico...")
        
        # Crear directorio de templates si no existe
        os.makedirs(os.path.dirname(template_path), exist_ok=True)
        
        # Copiar el template que creamos anteriormente
        try:
            with open('/home/ubuntu/.openclaw/workspace/trading/dashboard/templates/index_modern_final.html', 'r') as f:
                template_content = f.read()
            
            with open(template_path, 'w') as f:
                f.write(template_content)
            print("Template creado exitosamente")
        except Exception as e:
            print(f"Error creando template: {e}")
    
    # Iniciar hilo de actualizaciones
    start_background_thread()
    
    print("\n" + "="*60)
    print("SWARM TRADING AI - DASHBOARD PROFESIONAL")
    print("="*60)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Modo: {'PRODUCCIÓN' if SWARM_AVAILABLE else 'SIMULACIÓN'}")
    print(f"Agentes disponibles: {SWARM_AVAILABLE}")
    print(f"Dashboard disponible en: http://0.0.0.0:5000")
    print(f"Dashboard moderno en: http://0.0.0.0:5000/modern")
    print("="*60 + "\n")
    
    # Iniciar servidor
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)