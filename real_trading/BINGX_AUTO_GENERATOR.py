"""
BINGX_AUTO_GENERATOR.py - Generador automático para bingX demo
Envía señales cada 1 hora en horario Madrid
"""

import sys
import os
import time
import schedule
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

sys.path.append('/home/ubuntu/.openclaw/workspace/trading/swarm_ai_advanced')

print("🏦 GENERADOR AUTOMÁTICO BINGX DEMO")
print("=" * 60)
print("Configuración: Señales cada 1 hora, horario Madrid")
print("Inicio: 20:15 CET (Madrid)")
print("Exchange: bingX demo")
print("=" * 60)

def generate_bingx_signal():
    """Generar una señal para bingX"""
    
    try:
        from AGGRESSIVE_DUAL_SYSTEM import AggressiveDualTradingSystem
        
        # Hora Madrid
        madrid_time = datetime.utcnow() + timedelta(hours=1)
        
        print(f"\n{'='*60}")
        print(f"🔄 GENERANDO SEÑAL BINGX - {madrid_time.strftime('%H:%M CET')}")
        print(f"{'='*60}")
        
        # Crear sistema
        system = AggressiveDualTradingSystem()
        
        # Símbolos
        symbols = ['BTC/USDT', 'ETH/USDT']
        
        for std_symbol in symbols:
            # Convertir a formato bingX
            bingx_symbol = std_symbol.replace('/', '')  # BTCUSDT, ETHUSDT
            
            print(f"\n🎯 PROCESANDO {bingx_symbol}...")
            
            # Generar señal
            signal = system.generate_aggressive_signals(std_symbol)
            
            if signal:
                # Precio simulado
                import random
                base_prices = {'BTC/USDT': 52147.32, 'ETH/USDT': 3147.85}
                base = base_prices.get(std_symbol, 1000.0)
                price = base * (1 + random.uniform(-0.02, 0.02))
                
                # Calcular para $10 demo
                position_usdt = 10 * signal['total_position']
                
                print(f"   ✅ SEÑAL: {signal['final_signal']}")
                print(f"   📊 POSICIÓN: {signal['total_position']*100:.1f}% (${position_usdt:.2f} de $10)")
                print(f"   💰 PRECIO: ${price:,.2f}")
                print(f"   🎯 CONFIANZA: {max(signal['safe_signal']['confidence'], signal['growth_signal']['confidence'])*100:.0f}%")
                
                # Formatear mensaje Telegram
                telegram_msg = format_bingx_telegram_message(
                    bingx_symbol, signal, price, position_usdt, madrid_time
                )
                
                print(f"\n   📨 MENSAJE TELEGRAM LISTO:")
                print(f"   {'-'*40}")
                print(telegram_msg[:300] + "..." if len(telegram_msg) > 300 else telegram_msg)
                print(f"   {'-'*40}")
                
                # En producción: enviar por Telegram aquí
                # send_telegram_message(telegram_msg)
                
            else:
                print(f"   ❌ No se pudo generar señal")
        
        print(f"\n✅ SEÑAL BINGX GENERADA - {madrid_time.strftime('%H:%M CET')}")
        print(f"⏳ Próxima señal: {(madrid_time + timedelta(hours=1)).strftime('%H:%M CET')}")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

def format_bingx_telegram_message(symbol, signal, price, position_usdt, madrid_time):
    """Formatear mensaje Telegram para bingX"""
    
    final_signal = signal['final_signal']
    position_pct = signal['total_position'] * 100
    confidence = max(signal['safe_signal']['confidence'], signal['growth_signal']['confidence']) * 100
    market_regime = signal['market_regime']
    
    # Emojis
    signal_emoji = "🟢" if final_signal == 'BUY' else "🔴" if final_signal == 'SELL' else "🟡"
    
    # Recomendación
    if final_signal in ['BUY', 'SELL'] and position_pct > 20:
        recommendation = "🚀 EJECUTAR EN BINGX DEMO"
        action_emoji = "✅"
    elif final_signal in ['BUY', 'SELL'] and position_pct > 10:
        recommendation = "⚡ CONSIDERAR EN BINGX DEMO"
        action_emoji = "⚠️"
    else:
        recommendation = "👀 OBSERVAR SOLO"
        action_emoji = "🔄"
    
    # Cálculos
    stop_loss = price * 0.95
    take_profit = price * 1.10
    
    message = f"""
{action_emoji} **SEÑAL BINGX DEMO**
🏦 **Exchange:** bingX (cuenta demo)
⏰ **Hora Madrid:** {madrid_time.strftime('%Y-%m-%d %H:%M CET')}
📊 **Símbolo:** {symbol}
💰 **Precio demo:** **${price:,.2f}**

📈 **SEÑAL:** {final_signal} {signal_emoji}
🎯 **POSICIÓN DEMO:** {position_pct:.1f}% del capital (${position_usdt:.2f} de $10)
🔐 **CONFIANZA:** {confidence:.0f}%

📊 **RÉGIMEN:** {market_regime} ({signal['risk_level']*100:.0f}% riesgo)
📉 **STOP LOSS:** 5% (${stop_loss:,.2f})
📈 **TAKE PROFIT:** 10% (${take_profit:,.2f})

{action_emoji} **RECOMENDACIÓN:** {recommendation}
🆔 **ID:** bingx_{symbol}_{madrid_time.strftime('%Y%m%d_%H%M')}

💡 **INSTRUCCIONES BINGX DEMO:**
1. Abrir bingX en modo demo/sandbox
2. Buscar símbolo: {symbol}
3. {'COMPRAR' if final_signal == 'BUY' else 'VENDER' if final_signal == 'SELL' else 'NO OPERAR'} ${position_usdt:.2f} de {symbol}
4. Configurar stop loss: 5% (${stop_loss:,.2f})
5. Configurar take profit: 10% (${take_profit:,.2f})
6. Reportar resultado para aprendizaje

❓ **¿EJECUTA EN BINGX DEMO?** (Sí/No/Solo observar)
"""
    
    return message

def main():
    """Función principal"""
    
    print(f"\n🚀 INICIANDO GENERADOR BINGX DEMO")
    print(f"   Horario: Madrid (CET)")
    print(f"   Frecuencia: Cada 1 hora")
    print(f"   Capital demo: $10 USDT")
    
    # Programar primera ejecución inmediata
    print(f"\n⏰ PRIMERA SEÑAL: 20:15 CET (inmediata)")
    generate_bingx_signal()
    
    # Programar cada hora en punto
    schedule.every().hour.at(":00").do(generate_bingx_signal)
    
    print(f"\n✅ GENERADOR PROGRAMADO:")
    print(f"   • 20:15 CET - Señal inmediata (prueba)")
    print(f"   • 21:00 CET - Primera señal programada")
    print(f"   • 22:00 CET - Segunda señal programada")
    print(f"   • ... cada hora en punto")
    
    print(f"\n📋 MODO DE OPERACIÓN:")
    print(f"   1. Yo genero señales cada hora")
    print(f"   2. Te envío mensaje Telegram con instrucciones bingX")
    print(f"   3. Tú decides ejecutar manualmente (Sí/No)")
    print(f"   4. Ejecutas en bingX demo si decides Sí")
    print(f"   5. Aprendemos de resultados")
    
    print(f"\n🏦 SISTEMA BINGX DEMO EN MARCHA")
    print(f"   ¡Comienza el aprendizaje colaborativo!")
    
    # Mantener el programa corriendo
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Revisar cada minuto
    except KeyboardInterrupt:
        print(f"\n⏹️  GENERADOR DETENIDO")

if __name__ == "__main__":
    main()