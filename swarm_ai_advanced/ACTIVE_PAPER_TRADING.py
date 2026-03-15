#!/usr/bin/env python3
"""
ACTIVE_PAPER_TRADING.py - Paper trading con sistema híbrido activo
Versión más agresiva para testing
"""

import time
from datetime import datetime
from HYBRID_ACTIVE_TEST import ActiveHybridSystem

print("⚡ PAPER TRADING ACTIVO - 24 HORAS")
print("=" * 60)

class ActivePaperTrader:
    def __init__(self, initial_capital=5000):  # Capital más pequeño para testing
        self.system = ActiveHybridSystem()
        self.capital = initial_capital
        self.positions = {}
        self.trade_history = []
        self.initial_capital = initial_capital
        
    def run_quick_test(self, iterations=12):
        """Ejecutar test rápido (12 iteraciones = 12 horas simuladas)"""
        print(f"\n🚀 TEST RÁPIDO ({iterations} iteraciones)")
        print(f"   Capital: ${self.initial_capital:,.2f}")
        print(f"   Símbolos: BTC-USD, ETH-USD")
        print("-" * 60)
        
        signals_generated = 0
        
        for i in range(1, iterations + 1):
            print(f"\n⏰ Iteración {i}/{iterations}:")
            
            for symbol in ['BTC-USD', 'ETH-USD']:
                # Generar señal
                result = self.system.generate_final_signal(symbol)
                
                signal = result['final_signal']
                mode = result['mode']
                
                print(f"  {symbol}: {signal} (Modo: {mode})")
                
                if signal != "HOLD":
                    signals_generated += 1
                    print(f"    ⚡ SEÑAL ACTIVA!")
                    print(f"    Posición: {result['position_size']*100:.1f}%")
                    print(f"    SL: {result['stop_loss']:.1f}%, TP: {result['take_profit']:.1f}%")
                    
                    # Simular trade
                    self.simulate_trade(symbol, result)
            
            # Mostrar estado
            portfolio_value = self.capital
            for symbol, pos in self.positions.items():
                portfolio_value += pos['value']
            
            print(f"  💰 Portfolio: ${portfolio_value:,.2f}")
            print(f"  💵 Cash: ${self.capital:,.2f}")
            print(f"  📊 Posiciones: {len(self.positions)}")
            
            # Esperar breve
            if i < iterations:
                time.sleep(1)
        
        # Reporte
        print(f"\n{'='*60}")
        print("📈 TEST COMPLETADO")
        print(f"{'='*60}")
        
        final_value = self.capital
        for symbol, pos in self.positions.items():
            final_value += pos['value']
        
        total_return = ((final_value / self.initial_capital) - 1) * 100
        
        print(f"Señales activas generadas: {signals_generated}")
        print(f"Capital inicial: ${self.initial_capital:,.2f}")
        print(f"Valor final: ${final_value:,.2f}")
        print(f"Retorno: {total_return:.2f}%")
        print(f"Trades: {len(self.trade_history)}")
        
        if self.trade_history:
            print(f"\n📊 ESTADÍSTICAS:")
            buy_trades = [t for t in self.trade_history if t['action'] == 'BUY']
            sell_trades = [t for t in self.trade_history if t['action'] == 'SELL']
            
            print(f"   Compras: {len(buy_trades)}")
            print(f"   Ventas: {len(sell_trades)}")
        
        print(f"\n💡 EVALUACIÓN:")
        if signals_generated >= 3:
            print("  ✅ BUENO - Sistema genera señales activas")
            print("     Listo para testing extendido")
        elif signals_generated >= 1:
            print("  ⚠️  ACEPTABLE - Algunas señales")
            print("     Considerar ajustar parámetros")
        else:
            print("  ❌ MEJORABLE - Pocas señales")
            print("     Revisar configuración")
    
    def simulate_trade(self, symbol, result):
        """Simular trade para testing"""
        action = result['final_signal']
        position_size = result['position_size']
        
        if action == "BUY" and self.capital > 100:
            trade_value = self.capital * position_size
            
            self.positions[symbol] = {
                'action': 'BUY',
                'size': position_size,
                'value': trade_value,
                'time': datetime.now()
            }
            self.capital -= trade_value
            
            self.trade_history.append({
                'time': datetime.now(),
                'symbol': symbol,
                'action': 'BUY',
                'size': position_size,
                'value': trade_value
            })
            
        elif action == "SELL" and symbol in self.positions:
            position = self.positions[symbol]
            
            # Simular P&L aleatorio para testing
            import random
            max_loss = result['stop_loss']
            max_gain = result['take_profit']
            
            # P&L entre -stop_loss y +take_profit
            pnl_pct = random.uniform(-max_loss/2, max_gain/2)  # Más conservador para testing
            pnl_value = position['value'] * pnl_pct / 100
            
            self.capital += position['value'] + pnl_value
            del self.positions[symbol]
            
            self.trade_history.append({
                'time': datetime.now(),
                'symbol': symbol,
                'action': 'SELL',
                'size': position_size,
                'value': position['value'],
                'pnl_pct': pnl_pct,
                'pnl_value': pnl_value
            })

if __name__ == "__main__":
    print("\n🎯 SISTEMA HÍBRIDO ACTIVO - PAPER TRADING")
    print("Objetivo: Generar señales activas para testing")
    print("=" * 60)
    
    trader = ActivePaperTrader(initial_capital=5000)
    trader.run_quick_test(iterations=12)  # 12 iteraciones = 12 horas simuladas
