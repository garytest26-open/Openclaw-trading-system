#!/usr/bin/env python3
"""
QUICK_HYBRID_TEST.py - Test rápido del sistema híbrido
5 iteraciones para ver señales
"""

import time
from datetime import datetime
from HYBRID_SYSTEM import HybridTradingSystem

print("⚡ TEST RÁPIDO SISTEMA HÍBRIDO")
print("=" * 60)

def quick_test():
    """Test rápido de 5 iteraciones"""
    
    # Crear sistema
    try:
        system = HybridTradingSystem()
        print("✅ Sistema híbrido cargado")
    except Exception as e:
        print(f"❌ Error cargando sistema: {e}")
        return
    
    capital = 10000
    positions = {}
    trade_history = []
    
    print(f"\n💰 Capital inicial: ${capital:,.2f}")
    print(f"📊 Símbolos: BTC-USD, ETH-USD")
    print(f"⏱️  Iteraciones: 5 (horas simuladas)")
    print("-" * 60)
    
    signals_generated = 0
    
    for i in range(1, 6):
        print(f"\n⏰ Hora {i}/5:")
        
        for symbol in ['BTC-USD', 'ETH-USD']:
            try:
                # Generar señal
                result = system.generate_final_signal(symbol)
                
                signal = result['final_signal']
                mode = result['mode']
                position_size = result['position_size']
                
                print(f"  {symbol}: {signal} (Modo: {mode}, Posición: {position_size*100:.1f}%)")
                
                if signal != "HOLD":
                    signals_generated += 1
                    print(f"    ⚡ SEÑAL ACTIVA!")
                    
                    # Simular trade simple
                    if signal == "BUY" and capital > 100:
                        trade_value = capital * position_size
                        positions[symbol] = {
                            'action': 'BUY',
                            'value': trade_value,
                            'time': datetime.now()
                        }
                        capital -= trade_value
                        print(f"    💰 Compra simulada: ${trade_value:,.2f}")
                    
                    elif signal == "SELL" and symbol in positions:
                        position = positions[symbol]
                        # Simular P&L pequeño
                        import random
                        pnl_pct = random.uniform(-2, 4)  # -2% a +4%
                        pnl_value = position['value'] * pnl_pct / 100
                        capital += position['value'] + pnl_value
                        del positions[symbol]
                        print(f"    📈 Venta simulada: P&L {pnl_pct:.1f}% (${pnl_value:,.2f})")
                        
            except Exception as e:
                print(f"  ❌ Error con {symbol}: {e}")
        
        # Mostrar estado
        portfolio_value = capital
        for symbol, pos in positions.items():
            portfolio_value += pos['value']
        
        print(f"  💰 Portfolio total: ${portfolio_value:,.2f}")
        print(f"  💵 Cash disponible: ${capital:,.2f}")
        print(f"  📊 Posiciones abiertas: {len(positions)}")
        
        # Esperar 1 segundo entre iteraciones
        if i < 5:
            time.sleep(1)
    
    # Reporte final
    print(f"\n{'='*60}")
    print("📈 TEST RÁPIDO COMPLETADO")
    print(f"{'='*60}")
    
    final_value = capital
    for symbol, pos in positions.items():
        final_value += pos['value']
    
    total_return = ((final_value / 10000) - 1) * 100
    
    print(f"Señales activas generadas: {signals_generated}/10 posibles")
    print(f"Capital inicial: $10,000")
    print(f"Valor final: ${final_value:,.2f}")
    print(f"Retorno: {total_return:.2f}%")
    print(f"Trades ejecutados: {len(trade_history)}")
    
    print(f"\n💡 EVALUACIÓN:")
    if signals_generated >= 3:
        print("  ✅ EXCELENTE - Sistema genera señales consistentemente")
        print("     Listo para paper trading extendido")
    elif signals_generated >= 1:
        print("  ⚠️  ACEPTABLE - Algunas señales generadas")
        print("     Sistema funciona pero podría ser más activo")
    else:
        print("  ❌ MEJORABLE - Pocas o ninguna señal")
        print("     Revisar configuración o condiciones de mercado")
    
    print(f"\n🚀 RECOMENDACIÓN:")
    if total_return > 0.5:
        print("  Proceder con paper trading 24h completo")
    elif signals_generated >= 2:
        print("  Ajustar parámetros y luego paper trading 24h")
    else:
        print("  Revisar sistema antes de paper trading extendido")

if __name__ == "__main__":
    quick_test()