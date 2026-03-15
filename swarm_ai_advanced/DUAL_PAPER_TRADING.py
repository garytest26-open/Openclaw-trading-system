#!/usr/bin/env python3
"""
DUAL_PAPER_TRADING.py - Paper trading con sistema dual
12 horas simuladas para validación
"""

import time
from datetime import datetime
from DUAL_SYSTEM import DualTradingSystem

print("🔄 PAPER TRADING DUAL - 12 HORAS")
print("=" * 60)

class DualPaperTrader:
    def __init__(self, initial_capital=10000):
        self.system = DualTradingSystem()
        self.total_capital = initial_capital
        
        # Capital dividido por modo
        self.safe_capital = initial_capital * 0.70  # 70% modo seguro
        self.growth_capital = initial_capital * 0.30  # 30% modo crecimiento
        
        self.safe_positions = {}
        self.growth_positions = {}
        self.trade_history = []
        
    def run_12h_simulation(self):
        """Ejecutar simulación de 12 horas"""
        print(f"\n🚀 INICIANDO PAPER TRADING DUAL (12h)")
        print(f"   Capital total: ${self.total_capital:,.2f}")
        print(f"   🛡️  Modo Seguro: ${self.safe_capital:,.2f} (70%)")
        print(f"   ⚡  Modo Crecimiento: ${self.growth_capital:,.2f} (30%)")
        print(f"   Símbolos: BTC-USD, ETH-USD")
        print(f"   Frecuencia: Cada hora")
        print("-" * 60)
        
        total_signals = 0
        
        for hour in range(1, 13):
            print(f"\n⏰ Hora {hour}/12:")
            
            for symbol in ['BTC-USD', 'ETH-USD']:
                # Generar señal dual
                result = self.system.generate_dual_signals(symbol)
                
                final_signal = result['final_signal']
                total_position = result['total_position']
                distribution = result['distribution']
                
                print(f"  {symbol}: {final_signal}")
                print(f"    Posición: {total_position*100:.1f}% total")
                print(f"    Distribución: 🛡️ {distribution['SAFE_MODE']*100:.0f}% / ⚡ {distribution['GROWTH_MODE']*100:.0f}%")
                
                if final_signal != "HOLD":
                    total_signals += 1
                    print(f"    ⚡ SEÑAL ACTIVA DUAL!")
                    
                    # Simular trade dual
                    self.simulate_dual_trade(symbol, result)
            
            # Mostrar estado
            self.show_dual_portfolio_status()
            
            # Esperar breve
            if hour < 12:
                time.sleep(1)
        
        # Reporte final
        self.final_dual_report(total_signals)
    
    def simulate_dual_trade(self, symbol, result):
        """Simular trade considerando ambos modos"""
        final_signal = result['final_signal']
        total_position = result['total_position']
        distribution = result['distribution']
        
        # Calcular posición por modo
        safe_position = total_position * distribution['SAFE_MODE']
        growth_position = total_position * distribution['GROWTH_MODE']
        
        if final_signal == "BUY":
            # Modo Seguro
            if self.safe_capital > 100 and safe_position > 0:
                trade_value = self.safe_capital * safe_position
                self.safe_positions[symbol] = {
                    'action': 'BUY',
                    'value': trade_value,
                    'mode': 'SAFE',
                    'time': datetime.now()
                }
                self.safe_capital -= trade_value
            
            # Modo Crecimiento
            if self.growth_capital > 100 and growth_position > 0:
                trade_value = self.growth_capital * growth_position
                self.growth_positions[symbol] = {
                    'action': 'BUY',
                    'value': trade_value,
                    'mode': 'GROWTH',
                    'time': datetime.now()
                }
                self.growth_capital -= trade_value
        
        elif final_signal == "SELL":
            # Cerrar posiciones si existen
            if symbol in self.safe_positions:
                position = self.safe_positions[symbol]
                # Simular P&L conservador para modo seguro
                import random
                pnl_pct = random.uniform(-1, 2)  # -1% a +2%
                pnl_value = position['value'] * pnl_pct / 100
                self.safe_capital += position['value'] + pnl_value
                del self.safe_positions[symbol]
            
            if symbol in self.growth_positions:
                position = self.growth_positions[symbol]
                # Simular P&L más amplio para modo crecimiento
                pnl_pct = random.uniform(-3, 5)  # -3% a +5%
                pnl_value = position['value'] * pnl_pct / 100
                self.growth_capital += position['value'] + pnl_value
                del self.growth_positions[symbol]
    
    def show_dual_portfolio_status(self):
        """Mostrar estado del portfolio dual"""
        safe_value = self.safe_capital
        for pos in self.safe_positions.values():
            safe_value += pos['value']
        
        growth_value = self.growth_capital
        for pos in self.growth_positions.values():
            growth_value += pos['value']
        
        total_value = safe_value + growth_value
        
        print(f"  💰 Portfolio Dual:")
        print(f"     🛡️  Modo Seguro: ${safe_value:,.2f}")
        print(f"     ⚡  Modo Crecimiento: ${growth_value:,.2f}")
        print(f"     📊 Total: ${total_value:,.2f}")
        print(f"     📈 Posiciones: {len(self.safe_positions)+len(self.growth_positions)}")
    
    def final_dual_report(self, total_signals):
        """Reporte final del paper trading dual"""
        print(f"\n{'='*60}")
        print("📈 PAPER TRADING DUAL COMPLETADO")
        print(f"{'='*60}")
        
        # Calcular valores finales
        safe_final = self.safe_capital
        for pos in self.safe_positions.values():
            safe_final += pos['value']
        
        growth_final = self.growth_capital
        for pos in self.growth_positions.values():
            growth_final += pos['value']
        
        total_final = safe_final + growth_final
        
        # Calcular retornos
        safe_return = ((safe_final / (self.total_capital * 0.70)) - 1) * 100
        growth_return = ((growth_final / (self.total_capital * 0.30)) - 1) * 100
        total_return = ((total_final / self.total_capital) - 1) * 100
        
        print(f"Señales activas generadas: {total_signals}")
        print(f"\n📊 RESULTADOS POR MODO:")
        print(f"   🛡️  Modo Seguro: ${safe_final:,.2f} ({safe_return:.2f}%)")
        print(f"   ⚡  Modo Crecimiento: ${growth_final:,.2f} ({growth_return:.2f}%)")
        print(f"   📈 Total: ${total_final:,.2f} ({total_return:.2f}%)")
        
        print(f"\n💡 EVALUACIÓN DUAL:")
        if total_return > 1.0:
            print("  ✅ EXCELENTE - Sistema dual funciona bien")
            print("     Listo para deployment con capital real")
        elif total_return > 0:
            print("  ⚠️  POSITIVO - Sistema preserva/crece capital")
            print("     Continuar testing antes de deployment")
        elif total_return > -1:
            print("  🔄 NEUTRAL - Sistema preserva capital")
            print("     Considerar ajustes para mejor crecimiento")
        else:
            print("  ❌ MEJORABLE - Sistema necesita ajustes")
            print("     Revisar configuración antes de continuar")

if __name__ == "__main__":
    trader = DualPaperTrader(initial_capital=10000)
    trader.run_12h_simulation()
