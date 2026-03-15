"""
real_trading_system.py - Sistema de trading REAL integrando sistema mejorado
Conecta señales del sistema mejorado con ejecución real en exchange
"""

import os
import sys
import time
from datetime import datetime, timedelta
import json
import logging
from typing import Dict, Optional, List
import warnings
warnings.filterwarnings('ignore')

# Añadir ruta para importar sistema mejorado
sys.path.append('/home/ubuntu/.openclaw/workspace/trading/swarm_ai_advanced')

from exchange_connector import ExchangeConnector
from IMPROVED_DUAL_SYSTEM import ImprovedDualTradingSystem

print("🚀 SISTEMA DE TRADING REAL - VALIDACIÓN CON CAPITAL PEQUEÑO")
print("=" * 70)
print("Integración: Sistema Mejorado + Exchange Real")
print("Capital: $100 virtual (sandbox) o real controlado")
print("Objetivo: Validación real del sistema mejorado")
print("=" * 70)

class RealTradingSystem:
    """Sistema de trading real que ejecuta señales del sistema mejorado"""
    
    def __init__(self, initial_capital=100.0, use_sandbox=True):
        # Sistema mejorado
        self.trading_system = ImprovedDualTradingSystem()
        
        # Conector a exchange
        self.exchange = ExchangeConnector(use_sandbox=use_sandbox)
        
        # Configuración de capital
        self.initial_capital = initial_capital
        self.total_capital = initial_capital
        self.safe_capital = initial_capital * 0.60  # 60%
        self.growth_capital = initial_capital * 0.40  # 40%
        
        # Estado actual
        self.positions = {}  # {symbol: {amount, entry_price, mode, timestamp}}
        self.trade_history = []
        self.signal_history = []
        
        # Configuración de riesgo
        self.risk_config = {
            'max_position_size': 0.15,  # 15% máximo por trade
            'stop_loss_pct': 0.05,      # 5% stop loss
            'take_profit_pct': 0.10,    # 10% take profit
            'max_daily_trades': 2,      # Máximo 2 trades por día
            'max_daily_loss_pct': 0.10, # 10% pérdida diaria máxima
        }
        
        # Estadísticas
        self.stats = {
            'total_trades': 0,
            'profitable_trades': 0,
            'total_pnl': 0.0,
            'daily_trades': 0,
            'daily_pnl': 0.0,
            'start_time': datetime.now()
        }
        
        # Setup logging
        self.setup_logging()
        
        print(f"✅ Sistema de trading real inicializado")
        print(f"   Capital total: ${self.total_capital:,.2f}")
        print(f"   🛡️  Modo Seguro: ${self.safe_capital:,.2f} (60%)")
        print(f"   ⚡  Modo Crecimiento: ${self.growth_capital:,.2f} (40%)")
        print(f"   📊 Configuración de riesgo:")
        print(f"      • Stop loss: {self.risk_config['stop_loss_pct']*100}%")
        print(f"      • Take profit: {self.risk_config['take_profit_pct']*100}%")
        print(f"      • Máx trades/día: {self.risk_config['max_daily_trades']}")
    
    def setup_logging(self):
        """Configurar logging para monitoreo"""
        log_dir = '/home/ubuntu/.openclaw/workspace/trading/real_trading/logs'
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, f'trading_{datetime.now().strftime("%Y%m%d")}.log')
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Iniciando sistema de trading real - Capital: ${self.initial_capital}")
    
    def connect_to_exchange(self):
        """Conectar al exchange"""
        print("\n🔗 Conectando al exchange...")
        
        if not self.exchange.connect():
            self.logger.error("No se pudo conectar al exchange")
            return False
        
        # Verificar balance inicial
        balance = self.exchange.update_balance()
        usdt_balance = balance.get('total', {}).get('USDT', 0)
        
        print(f"✅ Conectado exitosamente")
        print(f"   Balance disponible: ${usdt_balance:,.2f} USDT")
        
        if usdt_balance < self.total_capital * 0.5:
            print(f"⚠️  Balance bajo: ${usdt_balance:,.2f} (esperado: ${self.total_capital:,.2f})")
        
        return True
    
    def generate_signal(self, symbol='BTC/USDT'):
        """Generar señal usando sistema mejorado"""
        print(f"\n🎯 GENERANDO SEÑAL PARA {symbol}")
        
        try:
            # Convertir símbolo para sistema mejorado
            system_symbol = symbol.replace('/', '-')
            
            # Generar señal
            signal_result = self.trading_system.generate_improved_signals(system_symbol)
            
            # Registrar señal
            signal_record = {
                'timestamp': datetime.now(),
                'symbol': symbol,
                'signal': signal_result['final_signal'],
                'position_size': signal_result['total_position'],
                'market_regime': signal_result['market_regime'],
                'distribution': signal_result['distribution'],
                'details': signal_result
            }
            
            self.signal_history.append(signal_record)
            
            print(f"✅ Señal generada: {signal_result['final_signal']}")
            print(f"   Posición sugerida: {signal_result['total_position']*100:.1f}%")
            print(f"   Régimen: {signal_result['market_regime']}")
            
            return signal_result
            
        except Exception as e:
            self.logger.error(f"Error generando señal para {symbol}: {e}")
            return None
    
    def calculate_position_size(self, signal_result, available_capital, mode='SAFE'):
        """Calcular tamaño de posición basado en señal y modo"""
        if not signal_result or signal_result['final_signal'] == 'HOLD':
            return 0.0
        
        base_position = signal_result['total_position']
        
        # Ajustar según modo
        if mode == 'SAFE':
            position_multiplier = 0.8  # 80% de la posición sugerida
            max_position = self.risk_config['max_position_size'] * 0.7  # 70% del máximo
        else:  # GROWTH
            position_multiplier = 1.2  # 120% de la posición sugerida
            max_position = self.risk_config['max_position_size']  # 100% del máximo
        
        # Calcular posición final
        position_pct = base_position * position_multiplier
        position_pct = min(position_pct, max_position)
        
        # Calcular monto en USD
        position_amount = available_capital * position_pct
        
        # Asegurar mínimo viable
        min_trade = 10.0  # $10 mínimo
        if position_amount < min_trade:
            return 0.0
        
        return position_amount
    
    def execute_trade(self, symbol, signal_result):
        """Ejecutar trade basado en señal"""
        
        signal = signal_result['final_signal']
        position_pct = signal_result['total_position']
        
        print(f"\n📊 EVALUANDO EJECUCIÓN: {symbol} - {signal}")
        
        # Verificar límites diarios
        if self.stats['daily_trades'] >= self.risk_config['max_daily_trades']:
            print(f"⚠️  Límite diario alcanzado ({self.stats['daily_trades']}/{self.risk_config['max_daily_trades']})")
            return None
        
        # Verificar pérdida diaria máxima
        if self.stats['daily_pnl'] < -self.total_capital * self.risk_config['max_daily_loss_pct']:
            print(f"⚠️  Pérdida diaria máxima alcanzada: ${self.stats['daily_pnl']:,.2f}")
            return None
        
        if signal == 'HOLD' or position_pct <= 0.01:
            print(f"⏸️  Señal HOLD o posición muy pequeña ({position_pct*100:.1f}%)")
            return None
        
        # Determinar modo a usar
        distribution = signal_result['distribution']
        market_regime = signal_result['market_regime']
        
        # Calcular capital disponible por modo
        safe_available = self.safe_capital
        growth_available = self.growth_capital
        
        # Ajustar por régimen
        if market_regime == 'BULL':
            # Más crecimiento en alcista
            safe_weight = 0.4
            growth_weight = 0.6
        elif market_regime == 'BEAR':
            # Más seguro en bajista
            safe_weight = 0.7
            growth_weight = 0.3
        else:  # SIDEWAYS
            safe_weight = 0.5
            growth_weight = 0.5
        
        # Calcular posición por modo
        safe_position = self.calculate_position_size(signal_result, safe_available * safe_weight, 'SAFE')
        growth_position = self.calculate_position_size(signal_result, growth_available * growth_weight, 'GROWTH')
        
        total_position = safe_position + growth_position
        
        if total_position <= 0:
            print(f"⚠️  Posición calculada es 0 o negativa")
            return None
        
        # Obtener precio actual
        ticker = self.exchange.get_ticker(symbol)
        if not ticker:
            print(f"❌ No se pudo obtener precio para {symbol}")
            return None
        
        current_price = ticker['last']
        
        # Calcular cantidad a comprar/vender
        amount = total_position / current_price
        
        # Verificar mínimo del exchange
        if amount * current_price < 10:  # $10 mínimo en Binance
            print(f"⚠️  Monto muy pequeño: ${amount * current_price:,.2f} (mínimo: $10)")
            return None
        
        print(f"\n🎯 EJECUTANDO TRADE:")
        print(f"   Símbolo: {symbol}")
        print(f"   Señal: {signal}")
        print(f"   Precio: ${current_price:,.2f}")
        print(f"   Monto total: ${total_position:,.2f}")
        print(f"   Cantidad: {amount:.6f}")
        print(f"   Distribución: 🛡️ ${safe_position:,.2f} + ⚡ ${growth_position:,.2f}")
        
        # Ejecutar orden
        try:
            if signal == 'BUY':
                order = self.exchange.place_order(
                    symbol=symbol,
                    side='buy',
                    amount=amount,
                    order_type='market'
                )
                
                if order:
                    # Actualizar capital
                    if safe_position > 0:
                        self.safe_capital -= safe_position
                    if growth_position > 0:
                        self.growth_capital -= growth_position
                    
                    # Registrar posición
                    self.positions[symbol] = {
                        'amount': amount,
                        'entry_price': current_price,
                        'entry_time': datetime.now(),
                        'safe_portion': safe_position,
                        'growth_portion': growth_position,
                        'order_id': order['id'],
                        'stop_loss': current_price * (1 - self.risk_config['stop_loss_pct']),
                        'take_profit': current_price * (1 + self.risk_config['take_profit_pct'])
                    }
                    
                    # Actualizar estadísticas
                    self.stats['daily_trades'] += 1
                    self.stats['total_trades'] += 1
                    
                    self.logger.info(f"BUY ejecutado: {symbol} - ${total_position:,.2f} a ${current_price:,.2f}")
                    
                    return order
                
            elif signal == 'SELL':
                # Verificar si tenemos posición para vender
                if symbol not in self.positions:
                    print(f"⚠️  No hay posición abierta para {symbol}")
                    return None
                
                position = self.positions[symbol]
                amount_to_sell = position['amount']
                
                order = self.exchange.place_order(
                    symbol=symbol,
                    side='sell',
                    amount=amount_to_sell,
                    order_type='market'
                )
                
                if order:
                    # Calcular P&L
                    entry_price = position['entry_price']
                    pnl = (current_price - entry_price) * amount_to_sell
                    pnl_pct = (current_price / entry_price - 1) * 100
                    
                    # Actualizar capital
                    total_return = position['safe_portion'] + position['growth_portion'] + pnl
                    safe_return = position['safe_portion'] + (pnl * (position['safe_portion'] / total_position))
                    growth_return = position['growth_portion'] + (pnl * (position['growth_portion'] / total_position))
                    
                    self.safe_capital += safe_return
                    self.growth_capital += growth_return
                    
                    # Registrar trade
                    trade_record = {
                        'symbol': symbol,
                        'action': 'SELL',
                        'entry_price': entry_price,
                        'exit_price': current_price,
                        'amount': amount_to_sell,
                        'pnl': pnl,
                        'pnl_pct': pnl_pct,
                        'timestamp': datetime.now(),
                        'order_id': order['id'],
                        'position_duration': (datetime.now() - position['entry_time']).total_seconds() / 3600  # horas
                    }
                    
                    self.trade_history.append(trade_record)
                    
                    # Actualizar estadísticas
                    self.stats['daily_pnl'] += pnl
                    self.stats['total_pnl'] += pnl
                    if pnl > 0:
                        self.stats['profitable_trades'] += 1
                    
                    # Eliminar posición
                    del self.positions[symbol]
                    
                    self.logger.info(f"SELL ejecutado: {symbol} - P&L: ${pnl:,.2f} ({pnl_pct:.2f}%)")
                    
                    return order
            
        except Exception as e:
            self.logger.error(f"Error ejecutando trade: {e}")
            return None
        
        return None
    
    def check_stop_loss_take_profit(self):
        """Verificar stop loss y take profit para posiciones abiertas"""
        if not self.positions:
            return
        
        print(f"\n🔍 VERIFICANDO STOP LOSS / TAKE PROFIT")
        
        for symbol, position in list(self.positions.items()):
            ticker = self.exchange.get_ticker(symbol)
            if not ticker:
                continue
            
            current_price = ticker['last']
            entry_price = position['entry_price']
            stop_loss = position['stop_loss']
            take_profit = position['take_profit']
            
            pnl_pct = (current_price / entry_price - 1) * 100
            
            # Verificar stop loss
            if current_price <= stop_loss:
                print(f"⚠️  STOP LOSS ACTIVADO: {symbol}")
                print(f"   Precio actual: ${current_price:,.2f}")
                print(f"   Stop loss: ${stop_loss:,.2f}")
                print(f"   P&L: {pnl_pct:.2f}%")
                
                # Ejecutar venta por stop loss
                self.execute_stop_loss(symbol)
                
            # Verificar take profit
            elif current_price >= take_profit:
                print(f"✅ TAKE PROFIT ACTIVADO: {symbol}")
                print(f"   Precio actual: ${current_price:,.2f}")
                print(f"   Take profit: ${take_profit:,.2f}")
                print(f"   P&L: {pnl_pct:.2f}%")
                
                # Ejecutar venta por take profit
                self.execute_take_profit(symbol)
    
    def execute_stop_loss(self, symbol):
        """Ejecutar stop loss para una posición"""
        if symbol not in self.positions:
            return
        
        position = self.positions[symbol]
        
        try:
            order = self.exchange.place_order(
                symbol=symbol,
                side='sell',
                amount=position['amount'],
                order_type='market'
            )
            
            if order:
                self.logger.warning(f"Stop loss ejecutado: {symbol}")
                del self.positions[symbol]
        
        except Exception as e:
            self.logger.error(f"Error ejecutando stop loss: {e}")
    
    def execute_take_profit(self, symbol):
        """Ejecutar take profit para una posición"""
        if symbol not in self.positions:
            return
        
        position = self.positions[symbol]
        
        try:
            order = self.exchange.place_order(
                symbol=symbol,
                side='sell',
                amount=position['amount'],
                order_type='market'
            )
            
            if order:
                self.logger.info(f"Take profit ejecutado: {symbol}")
                del self.positions[symbol]
        
        except Exception as e:
            self.logger.error(f"Error ejecutando take profit: {e}")
    
    def get_portfolio_summary(self):
        """Obtener resumen del portfolio"""
        total_value = self.safe_capital + self.growth_capital
        
        # Sumar valor de posiciones abiertas
        for symbol, position in self.positions.items():
            ticker = self.exchange.get_ticker(symbol)
            if ticker:
                position_value = position['amount'] * ticker['last']
                total_value += position_value
        
        return {
            'total_value': total_value,
            'safe_capital': self.safe_capital,
            'growth_capital': self.growth_capital,
            'open_positions': len(self.positions),
            'total_return_pct': ((total_value / self.initial_capital) - 1) * 100,
            'daily_trades': self.stats['daily_trades'],
            'daily_pnl': self.stats['daily_pnl'],
            'total_pnl': self.stats['total_pnl'],
            'profitable_trades': self.stats['profitable_trades'],
            'total_trades': self.stats['total_trades']
        }
    
    def print_dashboard(self):
        """Mostrar dashboard del sistema"""
        summary = self.get_portfolio_summary()
        
        print(f"\n{'='*70}")
        print("📊 DASHBOARD - SISTEMA DE TRADING REAL")
        print(f"{'='*70}")
        
        print(f"\n💰 CAPITAL:")
        print(f"   Total: ${summary['total_value']:,.2f} ({summary['total_return_pct']:+.2f}%)")
        print(f"   🛡️  Modo Seguro: ${summary['safe_capital']:,.2f}")
        print(f"   ⚡  Modo Crecimiento: ${summary['growth_capital']:,.2f}")
        print(f"   📈 Inicial: ${self.initial_capital:,.2f}")
        
        print(f"\n🎯 ESTADÍSTICAS:")
        print(f"   Trades hoy: {summary['daily_trades']}/{self.risk_config['max_daily_trades']}")
        print(f"   P&L hoy: ${summary['daily_pnl']:,.2f}")
        print(f"   Trades totales: {summary['total_trades']}")
        print(f"   Trades rentables: {summary['profitable_trades']} ({summary['profitable_trades']/max(summary['total_trades'],1)*100:.1f}%)")
        print(f"   P&L total: ${summary['total_pnl']:,.2f}")
        
        print(f"\n📈 POSICIONES ABIERTAS: {summary['open_positions']}")
        for symbol, position in self.positions.items():
            ticker = self.exchange.get_ticker(symbol)
            if ticker:
                current_price = ticker['last']
                entry_price = position['entry_price']
                pnl_pct = (current_price / entry_price - 1) * 100
                pnl_value = (current_price - entry_price) * position['amount']
                
                print(f"   {symbol}:")
                print(f"     Entrada: ${entry_price:,.2f}")
                print(f"     Actual: ${current_price:,.2f}")
                print(f"     P&L: ${pnl_value:,.2f} ({pnl_pct:+.2f}%)")
                print(f"     Stop loss: ${position['stop_loss']:,.2f}")
                print(f"     Take profit: ${position['take_profit']:,.2f}")
        
        print(f"\n⏰ TIEMPO EJECUCIÓN: {(datetime.now() - self.stats['start_time']).total_seconds()/3600:.1f} horas")
    
    def run_single_cycle(self):
        """Ejecutar un ciclo completo de trading"""
        print(f"\n{'='*70}")
        print(f"🔄 CICLO DE TRADING - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*70}")
        
        # 1. Verificar stop loss / take profit
        self.check_stop_loss_take_profit()
        
        # 2. Generar señales para cada símbolo
        symbols = ['BTC/USDT', 'ETH/USDT']
        
        for symbol in symbols:
            # 3. Generar señal
            signal_result = self.generate_signal(symbol)
            
            if not signal_result:
                continue
            
            # 4. Ejecutar trade si señal es activa
            order = self.execute_trade(symbol, signal_result)
            
            if order:
                print(f"✅ Trade ejecutado exitosamente")
        
        # 5. Mostrar dashboard
        self.print_dashboard()
        
        return True
    
    def run_continuous(self, interval_minutes=60, max_cycles=24):
        """Ejecutar sistema continuamente"""
        print(f"\n🚀 INICIANDO SISTEMA CONTINUO")
        print(f"   Intervalo: {interval_minutes} minutos")
        print(f"   Ciclos máximos: {max_cycles}")
        print(f"   Duración total: {interval_minutes * max_cycles / 60:.1f} horas")
        print(f"{'='*70}")
        
        cycles_completed = 0
        
        try:
            while cycles_completed < max_cycles:
                print(f"\n📅 CICLO {cycles_completed + 1}/{max_cycles}")
                
                # Ejecutar ciclo
                success = self.run_single_cycle()
                
                if not success:
                    print("⚠️  Ciclo falló, continuando...")
                
                cycles_completed += 1
                
                # Esperar para próximo ciclo
                if cycles_completed < max_cycles:
                    print(f"\n⏳ Esperando {interval_minutes} minutos para próximo ciclo...")
                    time.sleep(interval_minutes * 60)
            
            print(f"\n{'='*70}")
            print("✅ EJECUCIÓN COMPLETADA")
            print(f"{'='*70}")
            
            # Reporte final
            self.final_report()
            
        except KeyboardInterrupt:
            print(f"\n⏹️  EJECUCIÓN INTERRUMPIDA POR USUARIO")
            self.final_report()
        except Exception as e:
            print(f"\n❌ ERROR DURANTE EJECUCIÓN: {e}")
            import traceback
            traceback.print_exc()
            self.final_report()
    
    def final_report(self):
        """Generar reporte final"""
        print(f"\n{'='*70}")
        print("📈 REPORTE FINAL - SISTEMA DE TRADING REAL")
        print(f"{'='*70}")
        
        summary = self.get_portfolio_summary()
        
        print(f"\n💰 RESULTADOS FINANCIEROS:")
        print(f"   Capital inicial: ${self.initial_capital:,.2f}")
        print(f"   Capital final: ${summary['total_value']:,.2f}")
        print(f"   Retorno total: {summary['total_return_pct']:+.2f}%")
        print(f"   P&L total: ${summary['total_pnl']:,.2f}")
        
        print(f"\n🎯 PERFORMANCE DE TRADING:")
        print(f"   Trades totales: {summary['total_trades']}")
        print(f"   Trades rentables: {summary['profitable_trades']} ({summary['profitable_trades']/max(summary['total_trades'],1)*100:.1f}%)")
        print(f"   Trades por día: {summary['daily_trades']}")
        
        print(f"\n📊 EVALUACIÓN:")
        if summary['total_return_pct'] > 5:
            print("  ✅ EXCELENTE - Sistema funciona perfectamente")
            print("     Listo para escalado de capital")
        elif summary['total_return_pct'] > 2:
            print("  ✅ BUENO - Sistema muestra rentabilidad")
            print("     Considerar deployment con monitoreo")
        elif summary['total_return_pct'] > 0:
            print("  ⚠️  ACEPTABLE - Sistema preserva capital")
            print("     Necesita optimización para mejor rentabilidad")
        elif summary['total_return_pct'] > -2:
            print("  🔄 NEUTRAL - Pérdidas mínimas")
            print("     Requiere ajustes significativos")
        else:
            print("  ❌ MEJORABLE - Pérdidas significativas")
            print("     Revisión completa del sistema requerida")
        
        print(f"\n💡 RECOMENDACIONES:")
        if summary['total_trades'] == 0:
            print("  1. 🔍 Investigar por qué no se ejecutaron trades")
            print("  2. 📊 Revisar señales generadas vs condiciones de mercado")
            print("  3. ⚙️  Ajustar parámetros de ejecución")
        elif summary['profitable_trades'] / max(summary['total_trades'], 1) < 0.4:
            print("  1. 🎯 Mejorar calidad de señales")
            print("  2. ⏱️  Optimizar timing de entrada/salida")
            print("  3. 🛡️  Revisar gestión de riesgo")
        else:
            print("  1. 📈 Considerar escalado de capital")
            print("  2. 🔄 Automatizar completamente el sistema")
            print("  3. 📊 Implementar monitoreo avanzado")

def main():
    """Función principal"""
    print("\n🚀 INICIANDO SISTEMA DE TRADING REAL")
    print("=" * 70)
    
    try:
        # Crear sistema
        trading_system = RealTradingSystem(
            initial_capital=100.0,  # $100 para validación
            use_sandbox=True        # Usar sandbox para testing seguro
        )
        
        # Conectar a exchange
        if not trading_system.connect_to_exchange():
            print("❌ No se pudo conectar al exchange")
            return
        
        print("\n✅ SISTEMA LISTO PARA EJECUCIÓN")
        print("\n📋 CONFIGURACIÓN ACTUAL:")
        print(f"   Capital: ${trading_system.initial_capital:,.2f}")
        print(f"   Exchange: {'Binance Testnet (sandbox)' if trading_system.exchange.use_sandbox else 'Binance Production'}")
        print(f"   Símbolos: BTC/USDT, ETH/USDT")
        print(f"   Intervalo: 60 minutos")
        print(f"   Ciclos máximos: 24 (24 horas)")
        
        print(f"\n⚡ EJECUTANDO SISTEMA...")
        
        # Ejecutar sistema continuo (24 horas, cada 60 minutos)
        trading_system.run_continuous(interval_minutes=60, max_cycles=24)
        
        return trading_system
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    system = main()
    
    if system:
        print(f"\n✅ Sistema de trading real completado exitosamente")
    else:
        print(f"\n❌ Sistema falló durante ejecución")
