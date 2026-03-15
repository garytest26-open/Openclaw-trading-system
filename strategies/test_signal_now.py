#!/usr/bin/env python3
"""
Quick test - generate one signal right now
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from signal_generator import SignalGenerator
from datetime import datetime

print("=" * 70)
print("⚡ GENERADOR RÁPIDO DE SEÑAL")
print("=" * 70)
print(f"⏰ Hora actual: {datetime.utcnow().strftime('%H:%M UTC')}")
print()

# Create generator
generator = SignalGenerator()

# Generate signal
signal = generator.generate_signal(capital=10000)

if signal:
    # Format for Telegram
    telegram_message = generator.format_signal_for_telegram(signal)
    
    # Save to history
    generator.save_signal_history(signal)
    
    # Display
    print(telegram_message)
    
    # Also show raw data
    print("\n" + "=" * 70)
    print("📊 DATOS CRUDOS DE LA SEÑAL:")
    print("=" * 70)
    print(f"ID: {signal['signal_id']}")
    print(f"Activo: {signal['asset']}")
    print(f"Dirección: {signal['direction']}")
    print(f"Entrada: ${signal['entry_price']:,}")
    print(f"Stop Loss: ${signal['stop_loss']:,}")
    print(f"Take Profits: ${signal['take_profits'][0]:,} | ${signal['take_profits'][1]:,} | ${signal['take_profits'][2]:,}")
    print(f"Tamaño posición: ${signal['position_size_usd']:,} ({signal['position_size_pct']}%)")
    print(f"Confianza: {signal['confidence']*100:.0f}%")
    print(f"Risk/Reward: 1:{signal['risk_reward_ratio']:.1f}")
    
    # Save to file
    signal_file = f"signal_{signal['signal_id']}.txt"
    with open(signal_file, 'w') as f:
        f.write(telegram_message)
    
    print("\n" + "=" * 70)
    print(f"💾 Señal guardada en: {signal_file}")
    print("📋 Copia el mensaje de arriba y envíalo por Telegram a FRAN")
    print("=" * 70)
    
else:
    print("⏸️  No se pudo generar señal en este momento")
    print("   Razones posibles:")
    print("   • Volatilidad muy alta (>4%)")
    print("   • Volumen muy bajo")
    print("   • Tendencia muy débil para trend following")
    print("   • Señal muy reciente (mínimo 2 horas entre señales)")
    print()
    print("💡 Intenta de nuevo en 30-60 minutos")