"""
HYBRID_ACTIVE_TEST.py - Sistema híbrido con ajustes para testing activo
Versión más agresiva para paper trading
"""

from HYBRID_SYSTEM import HybridTradingSystem

class ActiveHybridSystem(HybridTradingSystem):
    """Sistema híbrido ajustado para testing más activo"""
    
    def __init__(self):
        super().__init__()
        
        # Ajustes para testing más activo
        self.position_sizes = {
            'DEFENSIVE': 0.10,    # 10% (antes 5%)
            'AGGRESSIVE': 0.25,   # 25% (antes 15%)
            'HYBRID': 0.15        # 15% (antes 10%)
        }
        
        # Umbrales más bajos para señales
        self.defensive_threshold = 0.6  # 60% confianza (antes 80%)
        self.aggressive_threshold = 1   # 1 de 3 señales (antes 2)
        
        print(f"⚡ Sistema Híbrido ACTIVO inicializado")
        print(f"   Umbral defensivo: {self.defensive_threshold*100}%")
        print(f"   Umbral agresivo: {self.aggressive_threshold}/3 señales")
    
    def decide_trading_mode(self, market_regime, defensive_signal):
        """Versión más activa para testing"""
        
        defensive_action, defensive_confidence = defensive_signal
        
        # Versión MÁS ACTIVA para testing
        # Siempre intentar modo HYBRID o AGGRESSIVE en testing
        
        if market_regime == "BEAR" and defensive_confidence > 0.9:
            # Solo DEFENSIVE si muy seguro
            self.current_mode = "DEFENSIVE"
            reason = "Mercado bajista + cerebro muy seguro"
        
        elif market_regime == "BULL" or self.risk_level > 0.5:
            # Más agresivo en alcista o riesgo medio
            self.current_mode = "AGGRESSIVE"
            reason = "Condiciones favorables para testing activo"
        
        else:
            # Por defecto: HYBRID (balanceado pero activo)
            self.current_mode = "HYBRID"
            reason = "Modo balanceado para testing"
        
        return self.current_mode, reason
    
    def combine_signals(self, mode, defensive_signal, aggressive_signals):
        """Versión más activa para testing"""
        
        defensive_action, defensive_confidence = defensive_signal
        
        # Contar señales agresivas
        aggressive_buy = sum(1 for s in aggressive_signals.values() if s == "BUY")
        aggressive_sell = sum(1 for s in aggressive_signals.values() if s == "SELL")
        
        # Modo DEFENSIVO (más activo que antes)
        if mode == "DEFENSIVE":
            if defensive_action != "HOLD" and defensive_confidence > self.defensive_threshold:
                return defensive_action
            elif aggressive_buy >= 1:  # 1 señal BUY es suficiente
                return "BUY"
            elif aggressive_sell >= 1:
                return "SELL"
            else:
                return "HOLD"
        
        # Modo AGGRESSIVE (muy activo)
        elif mode == "AGGRESSIVE":
            if aggressive_buy >= self.aggressive_threshold:
                return "BUY"
            elif aggressive_sell >= self.aggressive_threshold:
                return "SELL"
            elif defensive_action != "HOLD" and defensive_confidence > 0.5:
                return defensive_action
            else:
                return "HOLD"
        
        # Modo HYBRID (balanceado pero activo)
        else:  # HYBRID
            # Ponderar señales (más peso a agresivas)
            defensive_weight = 0.4  # Menos peso (antes 0.6)
            aggressive_weight = 0.6  # Más peso (antes 0.4)
            
            # Convertir a valores numéricos
            defensive_value = 0
            if defensive_action == "BUY":
                defensive_value = 1 * defensive_confidence
            elif defensive_action == "SELL":
                defensive_value = -1 * defensive_confidence
            
            # Valor agresivo
            aggressive_value = 0
            for signal in aggressive_signals.values():
                if signal == "BUY":
                    aggressive_value += 1
                elif signal == "SELL":
                    aggressive_value -= 1
            
            aggressive_value = aggressive_value / 3  # Normalizar
            
            # Combinar (más peso a agresivas)
            combined = (defensive_value * defensive_weight + 
                       aggressive_value * aggressive_weight)
            
            # Umbrales más bajos para testing
            if combined > 0.2:  # 0.2 (antes 0.3)
                return "BUY"
            elif combined < -0.2:
                return "SELL"
            else:
                return "HOLD"

def quick_active_test():
    """Probar sistema activo rápidamente"""
    print("\n⚡ TESTING SISTEMA HÍBRIDO ACTIVO")
    print("=" * 60)
    
    try:
        system = ActiveHybridSystem()
        
        symbols = ['BTC-USD', 'ETH-USD']
        
        for symbol in symbols:
            print(f"\n🔍 {symbol}:")
            print("-" * 40)
            
            result = system.generate_final_signal(symbol)
            
            print(f"   Régimen: {result['market_regime']}")
            print(f"   Riesgo: {result['risk_level']:.2f}")
            print(f"   Modo: {result['mode']}")
            print(f"   Señal Final: {result['final_signal']}")
            print(f"   Posición: {result['position_size']*100:.1f}%")
            
            if result['final_signal'] != "HOLD":
                print(f"   ⚡ SEÑAL ACTIVA GENERADA!")
                print(f"   Stop Loss: {result['stop_loss']:.1f}%")
                print(f"   Take Profit: {result['take_profit']:.1f}%")
        
        print("\n" + "=" * 60)
        print("🎯 SISTEMA ACTIVO LISTO PARA PAPER TRADING")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return False

def create_active_paper_trading():
    """Crear paper trading con sistema activo"""
    print("\n📝 CREANDO PAPER TRADING ACTIVO...")
    
    script = '''#!/usr/bin/env python3
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
        print(f"\\n🚀 TEST RÁPIDO ({iterations} iteraciones)")
        print(f"   Capital: ${self.initial_capital:,.2f}")
        print(f"   Símbolos: BTC-USD, ETH-USD")
        print("-" * 60)
        
        signals_generated = 0
        
        for i in range(1, iterations + 1):
            print(f"\\n⏰ Iteración {i}/{iterations}:")
            
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
        print(f"\\n{'='*60}")
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
            print(f"\\n📊 ESTADÍSTICAS:")
            buy_trades = [t for t in self.trade_history if t['action'] == 'BUY']
            sell_trades = [t for t in self.trade_history if t['action'] == 'SELL']
            
            print(f"   Compras: {len(buy_trades)}")
            print(f"   Ventas: {len(sell_trades)}")
        
        print(f"\\n💡 EVALUACIÓN:")
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
    print("\\n🎯 SISTEMA HÍBRIDO ACTIVO - PAPER TRADING")
    print("Objetivo: Generar señales activas para testing")
    print("=" * 60)
    
    trader = ActivePaperTrader(initial_capital=5000)
    trader.run_quick_test(iterations=12)  # 12 iteraciones = 12 horas simuladas
'''
    
    with open('ACTIVE_PAPER_TRADING.py', 'w') as f:
        f.write(script)
    
    print(f"✅ Script creado: ACTIVE_PAPER_TRADING.py")
    print(f"   Ejecutar: python3 ACTIVE_PAPER_TRADING.py")
    print(f"   Capital: $5,000 virtuales (más pequeño para testing)")
    print(f"   Iteraciones: 12 (horas simuladas)")
    
    return 'ACTIVE_PAPER_TRADING.py'

def main():
    """Función principal"""
    print("\n⚡ IMPLEMENTANDO SISTEMA HÍBRIDO ACTIVO")
    print("=" * 60)
    
    try:
        # 1. Probar sistema activo
        print("\n1. 🧪 TESTING SISTEMA ACTIVO...")
        success = quick_active_test()
        
        if not success:
            print("❌ Testing falló")
            return
        
        # 2. Crear paper trading activo
        print("\n2. 📝 CREANDO PAPER TRADING ACTIVO...")
        active_script = create_active_paper_trading()
        
        # 3. Instrucciones
        print("\n" + "=" * 60)
        print("🎯 SISTEMA HÍBRIDO ACTIVO LISTO")
        print("=" * 60)
        
        print(f"\n🚀 EJECUTAR TEST ACTIVO:")
        print(f"   cd /home/ubuntu/.openclaw/workspace/trading/swarm_ai_advanced")
        print(f"   source /home/ubuntu/.openclaw/workspace/trading/dashboard/venv/bin/activate")
        print(f"   python3 {active_script}")
        
        print(f"\n📋 CARACTERÍSTICAS DEL SISTEMA ACTIVO:")
        print(f"   • Umbral defensivo reducido (60% vs 80%)")
        print(f"   • Umbral agresivo reducido (1/3 vs 2/3 señales)")
        print(f"   • Posiciones más grandes (10-25% vs 5-15%)")
        print(f"   • Más peso a señales agresivas (60% vs 40%)")
        
        print(f"\n🎯 OBJETIVO DEL TEST:")
        print(f"   1. Verificar que sistema genera señales activas")
        print(f"   2. Evaluar calidad de señales (no solo HOLD)")
        print(f"   3. Preparar para paper trading extendido")
        
        return {
            'success': True,
            'active_script': active_script
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
        print(f"\n✅ SISTEMA ACTIVO CREADO EXITOSAMENTE")
        print(f"   Script: {result['active_script']}")
    else:
        print(f"\n❌ FALLÓ: {result.get('error', 'Unknown')}")