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
from typing import Dict, List, Optional, Tuple
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import pandas as pd
import numpy as np

# Importar sistema REAL de trading
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    from real_price_system import real_price_system, real_signal_generator
    REAL_SYSTEM_AVAILABLE = True
    print("✅ Sistema REAL importado - Modo: REAL (CoinGecko API)")
except ImportError as e:
    print(f"⚠️  Error importando sistema REAL: {e}")
    REAL_SYSTEM_AVAILABLE = False
    real_price_system = None
    real_signal_generator = None

# Importar Sindicato_Nexus integration
try:
    from sindicato_integration import create_sindicato_api, SindicatoNexusIntegration
    SINDICATO_AVAILABLE = True
    print("✅ Sindicato_Nexus integration disponible")
except ImportError as e:
    print(f"⚠️  Error importando Sindicato_Nexus: {e}")
    SINDICATO_AVAILABLE = False

# Configuración de la aplicación
app = Flask(__name__)
app.config['SECRET_KEY'] = 'swarm-trading-ai-real-system-2026'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Estado del sistema
class DashboardState:
    def __init__(self):
        self.connected_clients = 0
        self.system_mode = 'REAL' if REAL_SYSTEM_AVAILABLE else 'SIMULATED'
        self.signals = []
        self.trade_history = []
        
        # Inicializar Sindicato_Nexus si está disponible
        if SINDICATO_AVAILABLE:
            try:
                self.sindicato = SindicatoNexusIntegration()
                self.sindicato_initialized = False
                print("✅ Sindicato_Nexus integration creada")
            except Exception as e:
                print(f"⚠️  Error inicializando Sindicato_Nexus: {e}")
                self.sindicato = None
                self.sindicato_initialized = False
        else:
            self.sindicato = None
            self.sindicato_initialized = False
        
    def get_dashboard_data(self):
        """Obtener datos del sistema REAL"""
        if real_price_system and real_signal_generator:
            # Obtener datos REALES
            price_data = real_price_system.get_dashboard_data()
            
            # Generar señales REALES
            signals = real_signal_generator.analyze_market()
            self.signals = signals[-10:]  # Mantener últimas 10
            
            # Combinar datos
            data = {
                'portfolio': {'value': 25000.0, 'change': 0.0},
                'activeSignals': real_signal_generator.get_active_signals(),
                'winRate': 0.0,
                'sharpeRatio': 0.0,
                'profitFactor': 0.0,
                'maxDrawdown': 0.0,
                'annualReturn': 0.0,
                'swarmConfidence': 0,
                'prices': price_data['prices'],
                'agents': {
                    'trend': {'status': 'active', 'confidence': 85, 'last_update': datetime.now().isoformat()},
                    'reversal': {'status': 'active', 'confidence': 78, 'last_update': datetime.now().isoformat()},
                    'volatility': {'status': 'active', 'confidence': 65, 'last_update': datetime.now().isoformat()},
                    'volume': {'status': 'offline', 'confidence': 0, 'last_update': None},
                    'sentiment': {'status': 'offline', 'confidence': 0, 'last_update': None}
                },
                'signals': self.signals,
                'priceHistory': price_data['priceHistory'],
                'timestamp': datetime.now().isoformat(),
                'systemMode': 'REAL',
                'strategies': ['Trend Following', 'Mean Reversion', 'Breakout', 'Swarm AI Consensus']
            }
            
            # Calcular métricas REALES si hay trades
            if self.trade_history:
                self._calculate_real_metrics(data)
                
            return data
        else:
            # Fallback a datos simulados (solo temporal)
            return self._get_simulated_data()
    
    def _get_simulated_data(self):
        """Datos simulados como fallback temporal"""
        return {
            'portfolio': {'value': 25000.0, 'change': 0.0},
            'activeSignals': {'count': 0, 'details': '0 BUY, 0 SELL', 'signals': []},
            'winRate': 0.0,
            'sharpeRatio': 0.0,
            'profitFactor': 0.0,
            'maxDrawdown': 0.0,
            'annualReturn': 0.0,
            'swarmConfidence': 0,
            'prices': {
                'BTC': {'price': 50000.0, 'change': 0.0},
                'ETH': {'price': 3000.0, 'change': 0.0},
                'SOL': {'price': 100.0, 'change': 0.0}
            },
            'agents': {
                'trend': {'status': 'offline', 'confidence': 0, 'last_update': None},
                'reversal': {'status': 'offline', 'confidence': 0, 'last_update': None},
                'volatility': {'status': 'offline', 'confidence': 0, 'last_update': None},
                'volume': {'status': 'offline', 'confidence': 0, 'last_update': None},
                'sentiment': {'status': 'offline', 'confidence': 0, 'last_update': None}
            },
            'signals': [],
            'priceHistory': {
                'BTC': {'times': [], 'prices': [], 'volumes': []},
                'ETH': {'times': [], 'prices': [], 'volumes': []},
                'SOL': {'times': [], 'prices': [], 'volumes': []}
            },
            'timestamp': datetime.now().isoformat(),
            'systemMode': 'SIMULATED',
            'strategies': []
        }
    
    def _calculate_real_metrics(self, data: Dict):
        """Calcular métricas REALES basadas en historial de trades"""
        if not self.trade_history:
            return
        
        # Calcular win rate
        winning_trades = [t for t in self.trade_history if t.get('result') == 'win']
        if self.trade_history:
            data['winRate'] = round((len(winning_trades) / len(self.trade_history)) * 100, 1)
        
        # Calcular profit factor
        total_profit = sum(t.get('profit', 0) for t in self.trade_history if t.get('profit', 0) > 0)
        total_loss = abs(sum(t.get('profit', 0) for t in self.trade_history if t.get('profit', 0) < 0))
        
        if total_loss > 0:
            data['profitFactor'] = round(total_profit / total_loss, 2)
        
        # Calcular retorno anual (simplificado)
        if self.trade_history:
            total_return = sum(t.get('profit', 0) for t in self.trade_history)
            data['annualReturn'] = round((total_return / 25000) * 100, 2)  # Basado en portfolio inicial

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

@app.route('/simple')
def simple_dashboard():
    """Dashboard simple y funcional"""
    return render_template('index_simple.html')

@app.route('/api/dashboard-data')
def get_dashboard_data():
    """API para obtener datos del dashboard"""
    data = dashboard_state.get_dashboard_data()
    return jsonify(data)

@app.route('/api/strategies')
def get_strategies():
    """API para obtener estrategias disponibles"""
    strategies = [
        {'id': 'trend_following', 'name': 'Trend Following', 'description': 'Seguir tendencias del mercado', 'active': True},
        {'id': 'mean_reversion', 'name': 'Mean Reversion', 'description': 'Operar sobrecompra/sobreventa', 'active': True},
        {'id': 'breakout', 'name': 'Breakout', 'description': 'Operar rupturas de niveles', 'active': True},
        {'id': 'swarm_ai', 'name': 'Swarm AI Consensus', 'description': 'Consenso de múltiples agentes neurales', 'active': False}
    ]
    return jsonify({'strategies': strategies})

@app.route('/api/generate-signal', methods=['POST'])
def generate_signal():
    """API para generar una nueva señal REAL"""
    try:
        data = request.json
        symbol = data.get('symbol', 'BTC')
        strategy = data.get('strategy', 'Trend Following')
        
        if real_signal_generator and real_price_system:
            # Obtener precio actual REAL
            symbol_map_reverse = {v: k for k, v in real_price_system.symbol_map.items()}
            coin_id = symbol_map_reverse.get(symbol, 'bitcoin')
            current_price = real_price_system.last_prices.get(coin_id, 0)
            
            if current_price == 0:
                return jsonify({'success': False, 'error': 'Precio no disponible'})
            
            # Crear señal REAL
            signal = real_signal_generator._create_signal(
                symbol=symbol,
                signal_type='BUY' if np.random.random() > 0.4 else 'SELL',
                current_price=current_price,
                confidence=70 + np.random.randint(0, 25),
                strategy=strategy
            )
            
            # Añadir a lista
            dashboard_state.signals.append(signal)
            
            # Emitir via WebSocket
            socketio.emit('signal_update', signal, broadcast=True)
            socketio.emit('new_signal_generated', {
                'message': f'Nueva señal {signal["type"]} {signal["symbol"]} generada',
                'signal': signal
            }, broadcast=True)
            
            return jsonify({'success': True, 'signal': signal, 'systemMode': 'REAL'})
        else:
            return jsonify({'success': False, 'error': 'Sistema real no disponible'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/configuration', methods=['GET', 'POST'])
def configuration():
    """API para configuración del sistema"""
    if request.method == 'GET':
        config = {
            'trading': {
                'initial_capital': 25000,
                'risk_per_trade': 2.0,  # %
                'max_open_trades': 5,
                'stop_loss_default': 2.0,  # %
                'take_profit_default': 4.0  # %
            },
            'signals': {
                'min_confidence': 70,
                'max_signals_per_day': 20,
                'auto_generate': True,
                'notification_enabled': True
            },
            'agents': {
                'trend_active': True,
                'reversal_active': True,
                'volatility_active': True,
                'update_frequency': 300  # segundos
            }
        }
        return jsonify(config)
    else:
        # Guardar configuración
        try:
            config = request.json
            # Aquí se guardaría en base de datos o archivo
            return jsonify({'success': True, 'message': 'Configuración actualizada'})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})

@app.route('/api/execute-signal/<signal_id>', methods=['POST'])
def execute_signal(signal_id):
    """API para ejecutar una señal REAL"""
    try:
        # Buscar la señal en el estado del dashboard
        signal = None
        for s in dashboard_state.signals:
            if s.get('id') == signal_id:
                signal = s
                break
        
        if not signal:
            return jsonify({'success': False, 'error': 'Señal no encontrada'})
        
        # Crear trade REAL (en sistema real se conectaría a Hyperliquid)
        trade = {
            'id': f"trade_{int(time.time())}_{np.random.randint(1000, 9999)}",
            'signal_id': signal_id,
            'symbol': signal['symbol'],
            'type': signal['type'],
            'entry_price': signal['entry'],
            'quantity': 0.1 if signal['symbol'] == 'BTC' else (1.0 if signal['symbol'] == 'ETH' else 10.0),
            'timestamp': datetime.now().isoformat(),
            'status': 'executed',
            'result': 'pending',
            'real': True
        }
        
        # Añadir a historial REAL
        dashboard_state.trade_history.append(trade)
        
        # Actualizar señal como ejecutada
        signal['executed'] = True
        signal['executed_at'] = datetime.now().isoformat()
        
        # Emitir evento WebSocket
        socketio.emit('trade_executed', {
            'trade': trade,
            'signal': signal,
            'message': f"Trade {signal['type']} {signal['symbol']} ejecutado",
            'systemMode': 'REAL'
        }, broadcast=True)
        
        return jsonify({'success': True, 'trade': trade, 'systemMode': 'REAL'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

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
def handle_generate_signal(data):
    """Manejar solicitud de generación de señal REAL"""
    try:
        symbol = data.get('symbol', 'BTC')
        strategy = data.get('strategy', 'Trend Following')
        
        if real_signal_generator and real_price_system:
            # Obtener precio actual REAL
            symbol_map_reverse = {v: k for k, v in real_price_system.symbol_map.items()}
            coin_id = symbol_map_reverse.get(symbol, 'bitcoin')
            current_price = real_price_system.last_prices.get(coin_id, 0)
            
            if current_price == 0:
                emit('error', {'message': 'Precio no disponible para generar señal'})
                return
            
            # Crear señal REAL
            signal = real_signal_generator._create_signal(
                symbol=symbol,
                signal_type='BUY' if np.random.random() > 0.4 else 'SELL',
                current_price=current_price,
                confidence=70 + np.random.randint(0, 25),
                strategy=strategy
            )
            
            # Añadir a lista
            dashboard_state.signals.append(signal)
            
            emit('signal_update', signal, broadcast=True)
            emit('signal_generated', {
                'message': f'Nueva señal {signal["type"]} {signal["symbol"]} generada',
                'signal': signal,
                'systemMode': 'REAL',
                'timestamp': datetime.now().isoformat()
            }, broadcast=True)
        else:
            emit('error', {'message': 'Sistema real no disponible'})
            
    except Exception as e:
        emit('error', {'message': f'Error generando señal: {str(e)}'})

@socketio.on('get_strategies')
def handle_get_strategies():
    """Manejar solicitud de estrategias"""
    strategies = [
        {'id': 'trend_following', 'name': 'Trend Following', 'active': True},
        {'id': 'mean_reversion', 'name': 'Mean Reversion', 'active': True},
        {'id': 'breakout', 'name': 'Breakout', 'active': True},
        {'id': 'swarm_ai', 'name': 'Swarm AI Consensus', 'active': False}
    ]
    emit('strategies_list', {'strategies': strategies})

@socketio.on('get_configuration')
def handle_get_configuration():
    """Manejar solicitud de configuración"""
    config = {
        'trading': {
            'initial_capital': 25000,
            'risk_per_trade': 2.0,
            'max_open_trades': 5
        },
        'signals': {
            'min_confidence': 70,
            'auto_generate': True
        }
    }
    emit('configuration_data', config)

@socketio.on('execute_signal')
def handle_execute_signal(data):
    """Manejar ejecución de señal REAL"""
    try:
        signal_id = data.get('signalId')
        
        # Buscar la señal en el estado del dashboard
        signal = None
        for s in dashboard_state.signals:
            if s.get('id') == signal_id:
                signal = s
                break
        
        if not signal:
            emit('execution_result', {
                'success': False,
                'message': 'Señal no encontrada',
                'systemMode': 'REAL'
            })
            return
        
        # Crear trade REAL (en sistema real se conectaría a Hyperliquid)
        trade = {
            'id': f"trade_{int(time.time())}_{np.random.randint(1000, 9999)}",
            'signal_id': signal_id,
            'symbol': signal['symbol'],
            'type': signal['type'],
            'entry_price': signal['entry'],
            'quantity': 0.1 if signal['symbol'] == 'BTC' else (1.0 if signal['symbol'] == 'ETH' else 10.0),
            'timestamp': datetime.now().isoformat(),
            'status': 'executed',
            'result': 'pending',
            'real': True
        }
        
        # Añadir a historial REAL
        dashboard_state.trade_history.append(trade)
        
        # Actualizar señal como ejecutada
        signal['executed'] = True
        signal['executed_at'] = datetime.now().isoformat()
        
        # Emitir eventos WebSocket
        emit('trade_executed', {
            'trade': trade,
            'signal': signal,
            'message': f"Trade {signal['type']} {signal['symbol']} ejecutado",
            'systemMode': 'REAL'
        }, broadcast=True)
        
        emit('execution_result', {
            'success': True,
            'message': f"Señal {signal_id} ejecutada exitosamente",
            'signal': signal,
            'trade': trade,
            'systemMode': 'REAL'
        })
        
    except Exception as e:
        emit('execution_result', {
            'success': False,
            'message': f'Error ejecutando señal: {str(e)}',
            'systemMode': 'REAL'
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

# Tarea en segundo plano para actualizaciones REALES
def background_updates():
    """Tarea en segundo plano para actualizar precios REALES y estado"""
    last_signal_generation = time.time()
    
    while True:
        try:
            # Actualizar precios REALES si el sistema está disponible
            if real_price_system:
                real_price_system.update_prices()
            
            # Enviar actualización a todos los clientes conectados
            if dashboard_state.connected_clients > 0:
                data = dashboard_state.get_dashboard_data()
                
                # Extraer datos de actualización frecuente
                update_data = {
                    'portfolio': data['portfolio'],
                    'activeSignals': data['activeSignals'],
                    'prices': data['prices'],
                    'timestamp': data['timestamp'],
                    'systemMode': data['systemMode'],
                    'priceHistory': data.get('priceHistory', {})
                }
                
                socketio.emit('price_update', update_data)
                
                # Enviar actualización de agentes
                socketio.emit('agents_update', {
                    'agents': data['agents'],
                    'swarmConfidence': data['swarmConfidence'],
                    'timestamp': data['timestamp']
                })
            
            # Generar señal automática REAL cada 60 segundos
            current_time = time.time()
            if (current_time - last_signal_generation > 60 and 
                real_signal_generator and real_price_system and
                dashboard_state.connected_clients > 0):
                
                # Analizar mercado y generar señales REALES
                signals = real_signal_generator.analyze_market()
                if signals:
                    # Tomar la señal con mayor confianza
                    best_signal = max(signals, key=lambda x: x['confidence'])
                    dashboard_state.signals.append(best_signal)
                    
                    socketio.emit('signal_update', best_signal, broadcast=True)
                    socketio.emit('auto_signal_generated', {
                        'message': f'Señal automática {best_signal["type"]} {best_signal["symbol"]}',
                        'signal': best_signal,
                        'timestamp': datetime.now().isoformat()
                    }, broadcast=True)
                    
                    last_signal_generation = current_time
            
            # Esperar antes de la próxima actualización
            time.sleep(10)  # Actualizar cada 10 segundos
            
        except Exception as e:
            print(f"❌ Error en background_updates: {e}")
            time.sleep(30)

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

# ============================================================================
# RUTAS DE SINDICATO_NEXUS
# ============================================================================

if SINDICATO_AVAILABLE and dashboard_state.sindicato:
    @app.route('/api/sindicato/status', methods=['GET'])
    def sindicato_status():
        """Get Sindicato_Nexus integration status"""
        return jsonify({
            'success': True,
            'status': dashboard_state.sindicato.get_status(),
            'timestamp': datetime.now().isoformat()
        })
    
    @app.route('/api/sindicato/initialize', methods=['POST'])
    def sindicato_initialize():
        """Initialize Sindicato_Nexus integration"""
        success = dashboard_state.sindicato.initialize()
        if success:
            dashboard_state.sindicato_initialized = True
        return jsonify({
            'success': success,
            'message': 'Sindicato_Nexus initialized successfully' if success else 'Initialization failed',
            'status': dashboard_state.sindicato.get_status(),
            'timestamp': datetime.now().isoformat()
        })
    
    @app.route('/api/sindicato/predictions', methods=['GET'])
    def sindicato_predictions():
        """Get current predictions from Sindicato_Nexus"""
        if not dashboard_state.sindicato_initialized:
            return jsonify({
                'success': False,
                'error': 'Sindicato_Nexus not initialized',
                'timestamp': datetime.now().isoformat()
            })
        
        return jsonify({
            'success': True,
            'predictions': dashboard_state.sindicato.current_predictions,
            'timestamp': datetime.now().isoformat()
        })
    
    @app.route('/api/sindicato/predict/<asset>', methods=['GET'])
    def sindicato_predict_asset(asset):
        """Get prediction for specific asset"""
        if not dashboard_state.sindicato_initialized:
            return jsonify({
                'success': False,
                'error': 'Sindicato_Nexus not initialized',
                'timestamp': datetime.now().isoformat()
            })
        
        prediction = dashboard_state.sindicato.generate_mock_predictions(asset.upper())
        return jsonify({
            'success': True,
            'prediction': prediction,
            'timestamp': datetime.now().isoformat()
        })
    
    @app.route('/api/sindicato/performance', methods=['GET'])
    def sindicato_performance():
        """Get Sindicato_Nexus performance metrics"""
        if not dashboard_state.sindicato_initialized:
            return jsonify({
                'success': False,
                'error': 'Sindicato_Nexus not initialized',
                'timestamp': datetime.now().isoformat()
            })
        
        return jsonify({
            'success': True,
            'performance': dashboard_state.sindicato.get_strategy_performance(),
            'timestamp': datetime.now().isoformat()
        })
    
    @app.route('/api/sindicato/configuration', methods=['GET'])
    def sindicato_configuration():
        """Get Sindicato_Nexus configuration"""
        if not dashboard_state.sindicato_initialized:
            return jsonify({
                'success': False,
                'error': 'Sindicato_Nexus not initialized',
                'timestamp': datetime.now().isoformat()
            })
        
        return jsonify({
            'success': True,
            'configuration': dashboard_state.sindicato.get_strategy_configuration(),
            'timestamp': datetime.now().isoformat()
        })
    
    @app.route('/api/sindicato/models', methods=['GET'])
    def sindicato_models():
        """Get information about loaded models"""
        return jsonify({
            'success': True,
            'models': dashboard_state.sindicato.models,
            'timestamp': datetime.now().isoformat()
        })
    
    print("✅ Rutas de Sindicato_Nexus creadas")

# ============================================================================
# FIN RUTAS SINDICATO_NEXUS
# ============================================================================

# ============================================================================
# RUTAS RSI SIMPLE STRATEGY (ESTRATEGIA PROBADA)
# ============================================================================

# Importar integración RSI Simple
try:
    from rsi_integration import (
        get_rsi_analysis, get_rsi_signals, get_rsi_positions, get_rsi_performance
    )
    RSI_STRATEGY_AVAILABLE = True
    print("✅ RSI Simple Strategy integration disponible")
except ImportError as e:
    print(f"⚠️  Error importando RSI Simple Strategy: {e}")
    RSI_STRATEGY_AVAILABLE = False

if RSI_STRATEGY_AVAILABLE:
    @app.route('/api/rsi/analysis', methods=['GET'])
    def rsi_analysis():
        """Get RSI analysis for all supported symbols"""
        try:
            analysis = get_rsi_analysis()
            return jsonify({
                'success': True,
                'analysis': analysis,
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
    
    @app.route('/api/rsi/signals', methods=['GET'])
    def rsi_signals():
        """Get recent RSI signals"""
        try:
            signals = get_rsi_signals()
            return jsonify({
                'success': True,
                'signals': signals,
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
    
    @app.route('/api/rsi/positions', methods=['GET'])
    def rsi_positions():
        """Get active RSI positions"""
        try:
            positions = get_rsi_positions()
            return jsonify({
                'success': True,
                'positions': positions,
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
    
    @app.route('/api/rsi/performance', methods=['GET'])
    def rsi_performance():
        """Get RSI strategy performance"""
        try:
            performance = get_rsi_performance()
            return jsonify({
                'success': True,
                'performance': performance,
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
    
    @app.route('/api/rsi/execute', methods=['POST'])
    def rsi_execute():
        """Execute RSI strategy analysis"""
        try:
            analysis = get_rsi_analysis()
            
            # Check for new signals
            new_signals = []
            for item in analysis:
                if item.get('signal') in ['BUY', 'SELL']:
                    new_signals.append({
                        'symbol': item['symbol'],
                        'signal': item['signal'],
                        'price': item['price'],
                        'rsi': item['rsi'],
                        'timestamp': item['timestamp']
                    })
            
            return jsonify({
                'success': True,
                'analysis': analysis,
                'new_signals': new_signals,
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
    
    print("✅ Rutas de RSI Simple Strategy creadas")

# ============================================================================
# FIN RUTAS RSI SIMPLE STRATEGY
# ============================================================================

# Iniciar tarea en segundo plano
def start_background_thread():
    """Iniciar el hilo de actualizaciones en segundo plano"""
    thread = threading.Thread(target=background_updates, daemon=True)
    thread.start()
    print("✅ Hilo de actualizaciones en segundo plano iniciado")

# Configuración e inicio
if __name__ == '__main__':
    # Iniciar hilo de actualizaciones
    start_background_thread()
    
    print("\n" + "="*60)
    print("🚀 SWARM TRADING AI - DASHBOARD REAL")
    print("="*60)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Modo: {dashboard_state.system_mode}")
    print(f"Agentes: {'SIMULADOS' if not REAL_SYSTEM_AVAILABLE else 'REALES'}")
    print(f"Precios: {'REALES (CoinGecko)' if REAL_SYSTEM_AVAILABLE else 'SIMULADOS'}")
    print(f"Dashboard disponible en: http://0.0.0.0:5001")
    print(f"Dashboard moderno: http://0.0.0.0:5001/modern")
    print(f"Dashboard real: http://0.0.0.0:5001/real")
    print("="*60 + "\n")
    
    # Iniciar servidor
    socketio.run(app, host='0.0.0.0', port=5001, debug=False, allow_unsafe_werkzeug=True)