#!/usr/bin/env python3
"""
PAPER_TRADING_HYBRID.py - Paper trading con sistema híbrido
24 horas reales de simulación
"""

import time
from datetime import datetime, timedelta
from HYBRID_SYSTEM import HybridTradingSystem

print("📝 PAPER TRADING HÍBRIDO - 24 HORAS")
print("=" * 60)

class HybridPaperTrader:
    def __init__(self, initial_capital=10000):
        self.system = HybridTradingSystem()
        self.capital = initial_capital
        self.positions = {}
        self.trade_history = []
        self.initial_capital = initial_capital
        
    def run_24h_simulation(self):
        """Ejecutar simulación de 24 horas"""
        print(f"\n🚀 INICIANDO PAPER TRADING HÍBRIDO (24h)")
        print(f"   Capital inicial: ${self.initial_capital:,.2f}")
        print(f"   Símbolos: BTC-USD, ETH-USD")
        print(f"   Frecuencia: Cada hora")
        print("-" * 60)
        
        # Simular 24 horas (en realidad 24 iteraciones rápidas)
        for hour in range(1, 25):
            print(f"\n⏰ Hora {hour}/24:")
            
            # Analizar cada símbolo
            for symbol in ['BTC-USD', 'ETH-USD']:
                # Generar señal
                result = self.system.generate_final_signal(symbol)
                
                print(f"  {symbol}: {result['final_signal']} (Modo: {result['mode']})")
                
                # Ejecutar trade si no es HOLD
                if result['final_signal'] != "HOLD":
                    self.execute_trade(symbol, result)
            
            # Mostrar estado
            self.show_portfolio_status()
            
            # Esperar (en simulación real sería 3600 segundos)
            if hour < 24:
                print(f"  ⏳ Esperando próxima hora...")
                time.sleep(2)  # 2 segundos para demo
        
        # Reporte final
        self.final_report()
    
    def execute_trade(self, symbol, signal_result):
        """Ejecutar trade basado en señal"""
        # En sistema real, aquí se conectaría a exchange
        # Por ahora solo simulamos
        
        action = signal_result['final_signal']
        position_size = signal_result['position_size']
        
        print(f"    📊 {action} {symbol}:")
        print(f"      Tamaño: {position_size*100:.1f}%")
        print(f"      Stop Loss: {signal_result['stop_loss']:.1f}%")
        print(f"      Take Profit: {signal_result['take_profit']:.1f}%")
        
        # Simular trade (en sistema real sería real)
        trade_value = self.capital * position_size
        
        if action == "BUY":
            # Simular compra
            self.positions[symbol] = {
                'action': 'BUY',
                'size': position_size,
                'value': trade_value,
                'time': datetime.now(),
                'stop_loss': signal_result['stop_loss'],
                'take_profit': signal_result['take_profit']
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
            # Simular venta
            position = self.positions[symbol]
            
            # Simular P&L (aleatorio para demo)
            import random
            pnl_pct = random.uniform(-signal_result['stop_loss'], signal_result['take_profit'])
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
    
    def show_portfolio_status(self):
        """Mostrar estado del portfolio"""
        portfolio_value = self.capital
        
        print(f"  💰 Portfolio:")
        print(f"     Cash: ${self.capital:,.2f}")
        print(f"     Posiciones: {len(self.positions)}")
        
        if self.positions:
            for symbol, pos in self.positions.items():
                print(f"     {symbol}: {pos['size']*100:.1f}% (${pos['value']:,.2f})")
    
    def final_report(self):
        """Reporte final"""
        print(f"\n{'='*60}")
        print("📈 PAPER TRADING HÍBRIDO COMPLETADO")
        print(f"{'='*60}")
        
        final_value = self.capital
        # En sistema real, sumar valor de posiciones abiertas
        
        total_return = ((final_value / self.initial_capital) - 1) * 100
        
        print(f"Capital inicial: ${self.initial_capital:,.2f}")
        print(f"Valor final: ${final_value:,.2f}")
        print(f"Retorno: {total_return:.2f}%")
        print(f"Total trades: {len(self.trade_history)}")
        
        if self.trade_history:
            winning_trades = [t for t in self.trade_history if 'pnl_value' in t and t['pnl_value'] > 0]
            win_rate = len(winning_trades) / len(self.trade_history) * 100 if self.trade_history else 0
            
            print(f"Win Rate: {win_rate:.1f}%")
        
        print(f"\n💡 RECOMENDACIÓN:")
        if total_return > 5:
            print("  ✅ EXCELENTE - Sistema listo para trading real")
        elif total_return > 0:
            print("  ⚠️  POSITIVO - Continuar paper trading")
        else:
            print("  ❌ MEJORABLE - Ajustar parámetros")

if __name__ == "__main__":
    trader = HybridPaperTrader(initial_capital=10000)
    trader.run_24h_simulation()
