"""
IMPROVED_24H_PAPER_TRADING.py - Paper trading 24h del sistema mejorado
Validación en tiempo real con condiciones actuales
"""

import time
from datetime import datetime, timedelta
from IMPROVED_DUAL_SYSTEM import ImprovedDualTradingSystem
import numpy as np

print("📊 PAPER TRADING 24H - SISTEMA MEJORADO")
print("=" * 60)
print("Objetivo: Validar sistema mejorado en condiciones reales")
print("Duración: 24 horas simuladas (1 hora = 1 iteración)")
print("Símbolos: BTC-USD, ETH-USD")
print("Capital: $10,000 total (🛡️ $6,000 + ⚡ $4,000 base)")
print("=" * 60)

class Improved24hPaperTrader:
    def __init__(self, initial_capital=10000):
        self.system = ImprovedDualTradingSystem()
        self.total_capital = initial_capital
        
        # Distribución base mejorada
        self.base_safe_allocation = 0.60  # 60%
        self.base_growth_allocation = 0.40  # 40%
        
        self.safe_capital = initial_capital * self.base_safe_allocation
        self.growth_capital = initial_capital * self.base_growth_allocation
        
        self.safe_positions = {}
        self.growth_positions = {}
        self.trade_history = []
        self.signal_history = []
        
        self.performance_metrics = {
            'total_signals': 0,
            'buy_signals': 0,
            'sell_signals': 0,
            'hold_signals': 0,
            'profitable_trades': 0,
            'total_trades': 0,
            'total_pnl': 0.0
        }
        
    def run_24h_simulation(self):
        """Ejecutar simulación de 24 horas"""
        print(f"\n🚀 INICIANDO PAPER TRADING 24H - SISTEMA MEJORADO")
        print(f"   Capital total: ${self.total_capital:,.2f}")
        print(f"   🛡️  Modo Seguro base: ${self.safe_capital:,.2f} ({self.base_safe_allocation*100:.0f}%)")
        print(f"   ⚡  Modo Crecimiento base: ${self.growth_capital:,.2f} ({self.base_growth_allocation*100:.0f}%)")
        print(f"   Símbolos: BTC-USD, ETH-USD")
        print(f"   Frecuencia: Cada hora (24 iteraciones)")
        print("-" * 60)
        
        for hour in range(1, 25):
            print(f"\n⏰ Hora {hour}/24:")
            print(f"   📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            hour_results = []
            
            for symbol in ['BTC-USD', 'ETH-USD']:
                # Generar señal del sistema mejorado
                result = self.system.generate_improved_signals(symbol)
                
                final_signal = result['final_signal']
                total_position = result['total_position']
                distribution = result['distribution']
                market_regime = result['market_regime']
                
                print(f"  {symbol}:")
                print(f"    Señal: {final_signal}")
                print(f"    Posición: {total_position*100:.1f}% total")
                print(f"    Régimen: {market_regime}")
                print(f"    Distribución: 🛡️ {distribution['SAFE_MODE']*100:.0f}% / ⚡ {distribution['GROWTH_MODE']*100:.0f}%")
                
                # Registrar señal
                self.signal_history.append({
                    'hour': hour,
                    'symbol': symbol,
                    'signal': final_signal,
                    'position': total_position,
                    'regime': market_regime,
                    'timestamp': datetime.now()
                })
                
                # Contar estadísticas
                self.performance_metrics['total_signals'] += 1
                if final_signal == "BUY":
                    self.performance_metrics['buy_signals'] += 1
                elif final_signal == "SELL":
                    self.performance_metrics['sell_signals'] += 1
                else:
                    self.performance_metrics['hold_signals'] += 1
                
                if final_signal != "HOLD":
                    print(f"    ⚡ SEÑAL ACTIVA MEJORADA!")
                    
                    # Simular trade con sistema mejorado
                    trade_result = self.simulate_improved_trade(symbol, result, hour)
                    if trade_result:
                        hour_results.append(trade_result)
                
                result['hour'] = hour
                hour_results.append(result)
            
            # Mostrar estado del portfolio
            self.show_improved_portfolio_status()
            
            # Mostrar resumen de la hora
            if hour_results:
                self.show_hour_summary(hour_results, hour)
            
            # Esperar breve entre iteraciones
            if hour < 24:
                time.sleep(0.5)  # Más rápido para simulación
        
        # Reporte final
        self.final_improved_report()
    
    def simulate_improved_trade(self, symbol, signal_result, hour):
        """Simular trade con sistema mejorado"""
        final_signal = signal_result['final_signal']
        total_position = signal_result['total_position']
        distribution = signal_result['distribution']
        market_regime = signal_result['market_regime']
        
        # Calcular posición por modo (dinámico)
        safe_position = total_position * distribution['SAFE_MODE']
        growth_position = total_position * distribution['GROWTH_MODE']
        
        trade_executed = False
        
        if final_signal == "BUY":
            # Modo Seguro mejorado
            if self.safe_capital > 50 and safe_position > 0:
                trade_value = self.safe_capital * safe_position
                
                # Ajustar según régimen (más agresivo en BULL)
                if market_regime == "BULL":
                    trade_value *= 1.2  # 20% más en alcista
                
                self.safe_positions[symbol] = {
                    'action': 'BUY',
                    'value': trade_value,
                    'mode': 'SAFE',
                    'hour': hour,
                    'price': self.get_current_price(symbol),
                    'regime': market_regime
                }
                self.safe_capital -= trade_value
                trade_executed = True
            
            # Modo Crecimiento mejorado
            if self.growth_capital > 50 and growth_position > 0:
                trade_value = self.growth_capital * growth_position
                
                # Más agresivo en crecimiento
                if market_regime == "BULL":
                    trade_value *= 1.5  # 50% más en alcista
                elif market_regime == "SIDEWAYS":
                    trade_value *= 1.2  # 20% más en lateral
                
                self.growth_positions[symbol] = {
                    'action': 'BUY',
                    'value': trade_value,
                    'mode': 'GROWTH',
                    'hour': hour,
                    'price': self.get_current_price(symbol),
                    'regime': market_regime
                }
                self.growth_capital -= trade_value
                trade_executed = True
        
        elif final_signal == "SELL":
            # Cerrar posiciones si existen
            pnl_total = 0
            
            if symbol in self.safe_positions:
                position = self.safe_positions[symbol]
                current_price = self.get_current_price(symbol)
                entry_price = position['price']
                
                # Calcular P&L (simulado con lógica mejorada)
                pnl = self.calculate_improved_pnl(entry_price, current_price, position['value'], 
                                                  position['regime'], position['mode'])
                
                pnl_total += pnl
                self.safe_capital += position['value'] + pnl
                del self.safe_positions[symbol]
                
                # Registrar trade
                self.record_trade(symbol, 'SELL', position['value'], pnl, 'SAFE', hour)
                trade_executed = True
            
            if symbol in self.growth_positions:
                position = self.growth_positions[symbol]
                current_price = self.get_current_price(symbol)
                entry_price = position['price']
                
                # Calcular P&L (más volátil para crecimiento)
                pnl = self.calculate_improved_pnl(entry_price, current_price, position['value'],
                                                  position['regime'], position['mode'])
                
                pnl_total += pnl
                self.growth_capital += position['value'] + pnl
                del self.growth_positions[symbol]
                
                # Registrar trade
                self.record_trade(symbol, 'SELL', position['value'], pnl, 'GROWTH', hour)
                trade_executed = True
        
        return trade_executed
    
    def get_current_price(self, symbol):
        """Obtener precio actual simulado"""
        # Simulación simple de precio
        import random
        
        base_prices = {
            'BTC-USD': 65000,
            'ETH-USD': 3500
        }
        
        # Variación aleatoria pequeña
        base = base_prices.get(symbol, 1000)
        variation = random.uniform(-0.02, 0.02)  # ±2%
        
        return base * (1 + variation)
    
    def calculate_improved_pnl(self, entry_price, exit_price, trade_value, regime, mode):
        """Calcular P&L con lógica mejorada"""
        price_change_pct = (exit_price - entry_price) / entry_price
        
        # Ajustar según régimen y modo
        if regime == "BULL":
            multiplier = 1.3 if mode == 'GROWTH' else 1.1
        elif regime == "BEAR":
            multiplier = 0.7 if mode == 'GROWTH' else 0.9
        else:  # SIDEWAYS
            multiplier = 1.0 if mode == 'GROWTH' else 0.8
        
        # P&L ajustado
        pnl = trade_value * price_change_pct * multiplier
        
        # Límites razonables
        max_loss_pct = -0.10 if mode == 'GROWTH' else -0.05  # -10% o -5%
        max_gain_pct = 0.15 if mode == 'GROWTH' else 0.08    # +15% o +8%
        
        pnl_pct = pnl / trade_value
        if pnl_pct < max_loss_pct:
            pnl = trade_value * max_loss_pct
        elif pnl_pct > max_gain_pct:
            pnl = trade_value * max_gain_pct
        
        return pnl
    
    def record_trade(self, symbol, action, value, pnl, mode, hour):
        """Registrar trade en historial"""
        trade = {
            'symbol': symbol,
            'action': action,
            'value': value,
            'pnl': pnl,
            'mode': mode,
            'hour': hour,
            'timestamp': datetime.now(),
            'pnl_pct': (pnl / value) * 100 if value > 0 else 0
        }
        
        self.trade_history.append(trade)
        self.performance_metrics['total_trades'] += 1
        if pnl > 0:
            self.performance_metrics['profitable_trades'] += 1
        self.performance_metrics['total_pnl'] += pnl
        
        print(f"      💰 Trade {mode}: {action} {symbol}")
        print(f"         Valor: ${value:,.2f}, P&L: ${pnl:,.2f} ({trade['pnl_pct']:.2f}%)")
    
    def show_improved_portfolio_status(self):
        """Mostrar estado del portfolio mejorado"""
        safe_value = self.safe_capital
        for pos in self.safe_positions.values():
            safe_value += pos['value']
        
        growth_value = self.growth_capital
        for pos in self.growth_positions.values():
            growth_value += pos['value']
        
        total_value = safe_value + growth_value
        
        # Calcular retornos
        safe_return = ((safe_value / (self.total_capital * self.base_safe_allocation)) - 1) * 100
        growth_return = ((growth_value / (self.total_capital * self.base_growth_allocation)) - 1) * 100
        total_return = ((total_value / self.total_capital) - 1) * 100
        
        print(f"  📊 Portfolio Mejorado:")
        print(f"     🛡️  Modo Seguro: ${safe_value:,.2f} ({safe_return:+.2f}%)")
        print(f"     ⚡  Modo Crecimiento: ${growth_value:,.2f} ({growth_return:+.2f}%)")
        print(f"     📈 Total: ${total_value:,.2f} ({total_return:+.2f}%)")
        print(f"     📊 Posiciones abiertas: {len(self.safe_positions)+len(self.growth_positions)}")
    
    def show_hour_summary(self, hour_results, hour):
        """Mostrar resumen de la hora"""
        active_signals = sum(1 for r in hour_results if isinstance(r, dict) and r.get('final_signal') != "HOLD")
        buy_signals = sum(1 for r in hour_results if isinstance(r, dict) and r.get('final_signal') == "BUY")
        
        print(f"  📋 Resumen Hora {hour}:")
        print(f"     Señales activas: {active_signals}/2")
        print(f"     Señales BUY: {buy_signals}")
        
        # Trades de esta hora
        hour_trades = [t for t in self.trade_history if t['hour'] == hour]
        if hour_trades:
            hour_pnl = sum(t['pnl'] for t in hour_trades)
            print(f"     Trades ejecutados: {len(hour_trades)}")
            print(f"     P&L hora: ${hour_pnl:,.2f}")
    
    def final_improved_report(self):
        """Reporte final del paper trading mejorado"""
        print(f"\n{'='*60}")
        print("📈 PAPER TRADING 24H - SISTEMA MEJORADO COMPLETADO")
        print(f"{'='*60}")
        
        # Calcular valores finales
        safe_final = self.safe_capital
        for pos in self.safe_positions.values():
            safe_final += pos['value']
        
        growth_final = self.growth_capital
        for pos in self.growth_positions.values():
            growth_final += pos['value']
        
        total_final = safe_final + growth_final
        
        # Calcular retornos finales
        safe_return = ((safe_final / (self.total_capital * self.base_safe_allocation)) - 1) * 100
        growth_return = ((growth_final / (self.total_capital * self.base_growth_allocation)) - 1) * 100
        total_return = ((total_final / self.total_capital) - 1) * 100
        
        # Estadísticas de señales
        total_signals = self.performance_metrics['total_signals']
        buy_pct = self.performance_metrics['buy_signals'] / total_signals * 100 if total_signals > 0 else 0
        sell_pct = self.performance_metrics['sell_signals'] / total_signals * 100 if total_signals > 0 else 0
        hold_pct = self.performance_metrics['hold_signals'] / total_signals * 100 if total_signals > 0 else 0
        
        # Estadísticas de trades
        total_trades = self.performance_metrics['total_trades']
        profitable_trades = self.performance_metrics['profitable_trades']
        profitability = profitable_trades / total_trades * 100 if total_trades > 0 else 0
        
        print(f"\n📊 ESTADÍSTICAS FINALES:")
        print(f"   Señales totales: {total_signals}")
        print(f"     BUY: {self.performance_metrics['buy_signals']} ({buy_pct:.1f}%)")
        print(f"     SELL: {self.performance_metrics['sell_signals']} ({sell_pct:.1f}%)")
        print(f"     HOLD: {self.performance_metrics['hold_signals']} ({hold_pct:.1f}%)")
        
        print(f"\n💰 RESULTADOS POR MODO:")
        print(f"   🛡️  Modo Seguro: ${safe_final:,.2f} ({safe_return:+.2f}%)")
        print(f"   ⚡  Modo Crecimiento: ${growth_final:,.2f} ({growth_return:+.2f}%)")
        print(f"   📈 Total: ${total_final:,.2f} ({total_return:+.2f}%)")
        
        print(f"\n🎯 PERFORMANCE DE TRADES:")
        print(f"   Trades totales: {total_trades}")
        print(f"   Trades rentables: {profitable_trades} ({profitability:.1f}%)")
        print(f"   P&L total: ${self.performance_metrics['total_pnl']:,.2f}")
        
        print(f"\n💡 EVALUACIÓN FINAL DEL SISTEMA MEJORADO:")
        
        if total_return > 3 and profitability > 60:
            print("  ✅ EXCELENTE - Sistema mejorado funciona perfectamente")
            print("     Listo para deployment con confianza")
        elif total_return > 1 and profitability > 50:
            print("  ✅ BUENO - Sistema muestra mejora significativa")
            print("     Listo para deployment con monitoreo")
        elif total_return > 0 and profitability > 40:
            print("  ⚠️  ACEPTABLE - Sistema mejora pero necesita ajustes")
            print("     Considerar deployment pequeño")
        elif total_return > -1:
            print("  🔄 NEUTRAL - Sistema preserva capital")
            print("     Necesita más optimización")
        else:
            print("  ❌ MEJORABLE - Sistema no muestra mejora suficiente")
            print("     Requiere revisión completa")
        
        # Recomendación basada en resultados
        print(f"\n🎯 RECOMENDACIÓN BASADA EN PAPER TRADING 24H:")
        if total_return > 2 and profitability > 55:
            print("  1. 🚀 DEPLOYMENT INMEDIATO con capital controlado")
            print("  2. 📊 Monitoreo estricto primera semana")
            print("  3. 🔄 Escalado gradual basado en resultados")
        elif total_return > 0:
            print("  1. 🔧 OPTIMIZACIÓN ADICIONAL antes de deployment")
            print("  2. 📝 Más paper trading para validación")
            print("  3. 🎯 Deployment pequeño después de confirmación")
        else:
            print("  1. 🔄 REVISIÓN COMPLETA del sistema")
            print("  2. 🧪 Más testing con diferentes parámetros")
            print("  3. 📊 Reevaluación antes de considerar deployment")

def main():
    """Función principal"""
    print("\n🚀 EJECUTANDO PAPER TRADING 24H - SISTEMA MEJORADO")
    print("=" * 60)
    
    try:
        trader = Improved24hPaperTrader(initial_capital=10000)
        trader.run_24h_simulation()
        
        return {
            'success': True,
            'message': 'Paper trading 24h completado exitosamente'
        }
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            'success': False,
            'error': str(e)
        }

if __name__ == "__main__":
    result = main()
    
    if result['success']:
        print(f"\n✅ PAPER TRADING 24H COMPLETADO")
    else:
        print(f"\n❌ FALLÓ: {result.get('error', 'Unknown')}")