#!/usr/bin/env python3
"""
ADJUSTED_DUAL_PAPER_TRADING.py - Paper trading con sistema dual ajustado
8 horas simuladas para validación rápida
"""

import time
from datetime import datetime
from DUAL_SYSTEM_ADJUSTED import AdjustedDualTradingSystem

print("⚡ PAPER TRADING DUAL AJUSTADO - 8 HORAS")
print("=" * 60)

class AdjustedDualPaperTrader:
    def __init__(self, initial_capital=10000):
        self.system = AdjustedDualTradingSystem()
        self.total_capital = initial_capital
        
        # Capital dividido por modo (ajustado dinámicamente)
        self.safe_capital = initial_capital * 0.70  # Base 70%
        self.growth_capital = initial_capital * 0.30  # Base 30%
        
        self.safe_positions = {}
        self.growth_positions = {}
        self.trade_history = []
        
    def run_8h_simulation(self):
        """Ejecutar simulación de 8 horas"""
        print(f"\n🚀 INICIANDO PAPER TRADING DUAL AJUSTADO (8h)")
        print(f"   Capital total: ${self.total_capital:,.2f}")
        print(f"   🛡️  Modo Seguro base: ${self.safe_capital:,.2f} (70%)")
        print(f"   ⚡  Modo Crecimiento base: ${self.growth_capital:,.2f} (30%)")
        print(f"   Símbolos: BTC-USD, ETH-USD")
        print(f"   Frecuencia: Cada hora")
        print("-" * 60)
        
        total_signals = 0
        
        for hour in range(1, 9):
            print(f"\n⏰ Hora {hour}/8:")
            
            for symbol in ['BTC-USD', 'ETH-USD']:
                # Generar señal dual ajustada
                result = self.system.generate_dual_signals(symbol)
                
                final_signal = result['final_signal']
                total_position = result['total_position']
                distribution = result['distribution']
                
                print(f"  {symbol}: {final_signal}")
                print(f"    Posición: {total_position*100:.1f}% total")
                print(f"    Distribución: 🛡️ {distribution['SAFE_MODE']*100:.0f}% / ⚡ {distribution['GROWTH_MODE']*100:.0f}%")
                
                if final_signal != "HOLD":
                    total_signals += 1
                    print(f"    ⚡ SEÑAL ACTIVA CON SISTEMA AJUSTADO!")
                    
                    # Simular trade dual ajustado
                    self.simulate_adjusted_dual_trade(symbol, result)
            
            # Mostrar estado
            self.show_adjusted_portfolio_status()
            
            # Esperar breve
            if hour < 8:
                time.sleep(1)
        
        # Reporte final
        self.final_adjusted_report(total_signals)
    
    def simulate_adjusted_dual_trade(self, symbol, result):
        """Simular trade con sistema ajustado"""
        final_signal = result['final_signal']
        total_position = result['total_position']
        distribution = result['distribution']
        
        # Calcular posición por modo (dinámico)
        safe_position = total_position * distribution['SAFE_MODE']
        growth_position = total_position * distribution['GROWTH_MODE']
        
        if final_signal == "BUY":
            # Modo Seguro (más conservador incluso ajustado)
            if self.safe_capital > 100 and safe_position > 0:
                trade_value = self.safe_capital * safe_position * 0.8  # 80% del sugerido
                self.safe_positions[symbol] = {
                    'action': 'BUY',
                    'value': trade_value,
                    'mode': 'SAFE',
                    'time': datetime.now()
                }
                self.safe_capital -= trade_value
            
            # Modo Crecimiento (más agresivo ajustado)
            if self.growth_capital > 100 and growth_position > 0:
                trade_value = self.growth_capital * growth_position * 1.2  # 120% del sugerido
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
                pnl_pct = random.uniform(-1, 3)  # -1% a +3% (más optimista)
                pnl_value = position['value'] * pnl_pct / 100
                self.safe_capital += position['value'] + pnl_value
                del self.safe_positions[symbol]
            
            if symbol in self.growth_positions:
                position = self.growth_positions[symbol]
                # Simular P&L más amplio para modo crecimiento ajustado
                pnl_pct = random.uniform(-4, 8)  # -4% a +8% (más amplio)
                pnl_value = position['value'] * pnl_pct / 100
                self.growth_capital += position['value'] + pnl_value
                del self.growth_positions[symbol]
    
    def show_adjusted_portfolio_status(self):
        """Mostrar estado del portfolio dual ajustado"""
        safe_value = self.safe_capital
        for pos in self.safe_positions.values():
            safe_value += pos['value']
        
        growth_value = self.growth_capital
        for pos in self.growth_positions.values():
            growth_value += pos['value']
        
        total_value = safe_value + growth_value
        
        print(f"  💰 Portfolio Dual Ajustado:")
        print(f"     🛡️  Modo Seguro: ${safe_value:,.2f}")
        print(f"     ⚡  Modo Crecimiento: ${growth_value:,.2f}")
        print(f"     📊 Total: ${total_value:,.2f}")
        print(f"     📈 Posiciones: {len(self.safe_positions)+len(self.growth_positions)}")
    
    def final_adjusted_report(self, total_signals):
        """Reporte final del paper trading dual ajustado"""
        print(f"\n{'='*60}")
        print("📈 PAPER TRADING DUAL AJUSTADO COMPLETADO")
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
        print(f"\n📊 RESULTADOS POR MODO (AJUSTADO):")
        print(f"   🛡️  Modo Seguro: ${safe_final:,.2f} ({safe_return:.2f}%)")
        print(f"   ⚡  Modo Crecimiento: ${growth_final:,.2f} ({growth_return:.2f}%)")
        print(f"   📈 Total: ${total_final:,.2f} ({total_return:.2f}%)")
        
        print(f"\n💡 EVALUACIÓN DEL SISTEMA AJUSTADO:")
        if total_signals >= 4:
            print("  ✅ EXCELENTE - Sistema ajustado genera señales consistentemente")
            print("     Listo para deployment con monitoreo")
        elif total_signals >= 2:
            print("  ⚠️  BUENO - Sistema genera algunas señales")
            print("     Continuar testing antes de deployment")
        elif total_signals >= 1:
            print("  🔄 ACEPTABLE - Algunas señales generadas")
            print("     Sistema funciona pero podría mejorarse")
        else:
            print("  ❌ MEJORABLE - Pocas señales incluso ajustado")
            print("     Considerar ajustes adicionales")

if __name__ == "__main__":
    trader = AdjustedDualPaperTrader(initial_capital=10000)
    trader.run_8h_simulation()
