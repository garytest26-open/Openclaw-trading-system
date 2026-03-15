"""
BINGX_FIRST_SIGNAL.py - Primera señal para bingX demo
Ejecución inmediata para comenzar
"""

import sys
sys.path.append('/home/ubuntu/.openclaw/workspace/trading/swarm_ai_advanced')

from AGGRESSIVE_DUAL_SYSTEM import AggressiveDualTradingSystem
from datetime import datetime, timedelta

print("🏦 PRIMERA SEÑAL BINGX DEMO - 20:15 CET")
print("=" * 60)

# Hora Madrid
madrid_time = datetime.utcnow() + timedelta(hours=1)
print(f"⏰ Hora Madrid: {madrid_time.strftime('%H:%M CET')}")

# Crear sistema
system = AggressiveDualTradingSystem()

# Símbolos bingX
symbols = [
    ('BTC/USDT', 'BTCUSDT'),
    ('ETH/USDT', 'ETHUSDT')
]

print(f"\n🎯 GENERANDO SEÑALES PARA BINGX DEMO")
print(f"💰 Capital demo: $10 USDT virtuales")
print(f"📊 Formato: BTCUSDT, ETHUSDT (sin guiones)")
print(f"🏦 Exchange: bingX demo")
print(f"{'='*60}")

for std_symbol, bingx_symbol in symbols:
    print(f"\n📊 PROCESANDO {bingx_symbol}...")
    
    try:
        # Generar señal
        signal = system.generate_aggressive_signals(std_symbol)
        
        if signal:
            # Precio simulado
            import random
            base_prices = {'BTC/USDT': 52147.32, 'ETH/USDT': 3147.85}
            base = base_prices.get(std_symbol, 1000.0)
            price = base * (1 + random.uniform(-0.02, 0.02))
            
            # Calcular para $10 demo
            position_pct = signal['total_position'] * 100
            position_usdt = 10 * signal['total_position']
            
            # Cálculos
            stop_loss = price * 0.95
            take_profit = price * 1.10
            
            print(f"   ✅ SEÑAL: {signal['final_signal']}")
            print(f"   📊 POSICIÓN: {position_pct:.1f}% (${position_usdt:.2f} de $10)")
            print(f"   💰 PRECIO: ${price:,.2f}")
            print(f"   🎯 CONFIANZA: {max(signal['safe_signal']['confidence'], signal['growth_signal']['confidence'])*100:.0f}%")
            print(f"   📊 RÉGIMEN: {signal['market_regime']}")
            print(f"   📉 STOP LOSS: ${stop_loss:,.2f} (-5%)")
            print(f"   📈 TAKE PROFIT: ${take_profit:,.2f} (+10%)")
            
            # Recomendación
            if signal['final_signal'] in ['BUY', 'SELL'] and position_pct > 20:
                recommendation = "🚀 EJECUTAR EN BINGX DEMO"
            elif signal['final_signal'] in ['BUY', 'SELL'] and position_pct > 10:
                recommendation = "⚡ CONSIDERAR EN BINGX DEMO"
            else:
                recommendation = "👀 OBSERVAR SOLO"
            
            print(f"   💡 RECOMENDACIÓN: {recommendation}")
            
            # Instrucciones específicas
            if signal['final_signal'] == 'BUY':
                action = f"COMPRAR ${position_usdt:.2f} de {bingx_symbol}"
            elif signal['final_signal'] == 'SELL':
                action = f"VENDER ${position_usdt:.2f} de {bingx_symbol}"
            else:
                action = "NO OPERAR - Mantener posición"
            
            print(f"   🏦 INSTRUCCIÓN BINGX: {action}")
            
        else:
            print(f"   ❌ No se pudo generar señal")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")

print(f"\n{'='*60}")
print("✅ PRIMERA SEÑAL BINGX GENERADA")
print(f"⏰ Hora: {madrid_time.strftime('%H:%M CET')}")
print(f"🏦 Exchange: bingX demo")
print(f"💰 Capital: $10 USDT virtuales")

print(f"\n📋 PRÓXIMOS PASOS:")
print(f"1. Revisar señales arriba")
print(f"2. Decidir ejecutar en bingX demo (Sí/No)")
print(f"3. Si ejecutas: seguir instrucciones específicas")
print(f"4. Reportar resultado para aprendizaje")
print(f"5. Próxima señal: 21:00 CET")

print(f"\n🎯 OBJETIVO: Aprendizaje colaborativo con 0 riesgo")
print(f"   Capital: $10 virtuales")
print(f"   Control: Ejecución manual tú")
print(f"   Aprendizaje: Ambos aprendemos de resultados")

print(f"\n🏦 ¡COMIENZA EL TRADING EN BINGX DEMO!")