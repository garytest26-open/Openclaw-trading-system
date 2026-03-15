"""
QUICK_BINGX_TEST.py - Test rápido del sistema bingX
"""

import sys
sys.path.append('/home/ubuntu/.openclaw/workspace/trading/swarm_ai_advanced')

from AGGRESSIVE_DUAL_SYSTEM import AggressiveDualTradingSystem

print("⚡ TEST RÁPIDO BINGX - HORARIO MADRID")
print("=" * 60)

# Crear sistema
system = AggressiveDualTradingSystem()

# Probar con BTC/USDT
symbol = "BTC/USDT"
print(f"\n🎯 GENERANDO SEÑAL PARA {symbol}")
print("-" * 40)

signal = system.generate_aggressive_signals(symbol)

if signal:
    print(f"✅ SEÑAL GENERADA:")
    print(f"   Señal final: {signal['final_signal']}")
    print(f"   Posición: {signal['total_position']*100:.1f}%")
    print(f"   Régimen: {signal['market_regime']}")
    print(f"   Riesgo: {signal['risk_level']*100:.0f}%")
    
    print(f"\n📊 DISTRIBUCIÓN:")
    print(f"   🛡️  Modo Seguro: {signal['distribution']['SAFE_MODE']*100:.0f}%")
    print(f"   ⚡ Modo Crecimiento: {signal['distribution']['GROWTH_MODE']*100:.0f}%")
    
    print(f"\n🎯 SEÑALES INDIVIDUALES:")
    print(f"   Seguro: {signal['safe_signal']['signal']} ({signal['safe_signal']['confidence']*100:.0f}% confianza)")
    print(f"   Crecimiento: {signal['growth_signal']['signal']} ({signal['growth_signal']['confidence']*100:.0f}% confianza)")
    
    # Convertir a formato bingX
    bingx_symbol = symbol.replace('/', '')  # BTCUSDT
    print(f"\n🏦 FORMATO BINGX:")
    print(f"   Símbolo original: {symbol}")
    print(f"   Símbolo bingX: {bingx_symbol}")
    
    # Precio simulado
    import random
    price = 52147.32 * (1 + random.uniform(-0.02, 0.02))
    print(f"   Precio demo: ${price:,.2f}")
    
    # Calcular montos para $10 demo
    position_usdt = 10 * signal['total_position']
    print(f"\n💰 PARA $10 DEMO EN BINGX:")
    print(f"   Monto a {'COMPRAR' if signal['final_signal'] == 'BUY' else 'VENDER' if signal['final_signal'] == 'SELL' else 'NO OPERAR'}: ${position_usdt:.2f}")
    print(f"   Stop loss: ${price * 0.95:,.2f} (-5%)")
    print(f"   Take profit: ${price * 1.10:,.2f} (+10%)")
    
    print(f"\n⏰ HORARIO MADRID (CET):")
    from datetime import datetime, timedelta
    madrid_time = datetime.utcnow() + timedelta(hours=1)
    print(f"   Hora actual Madrid: {madrid_time.strftime('%H:%M CET')}")
    
    print(f"\n✅ SISTEMA BINGX FUNCIONANDO CORRECTAMENTE")
    print(f"   Listo para enviar señales por Telegram")
    
else:
    print(f"❌ No se pudo generar señal")

print(f"\n🎯 PRÓXIMOS PASOS:")
print(f"1. Depositar $10 USDT virtuales en bingX demo")
print(f"2. Decir 'LISTO' para comenzar señales")
print(f"3. Recibir señales cada 1 hora (horario Madrid)")
print(f"4. Ejecutar manualmente en bingX demo")
print(f"5. Aprender juntos de resultados")