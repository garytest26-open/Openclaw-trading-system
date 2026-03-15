#!/usr/bin/env python3
"""
Generate a test signal with relaxed filters for demonstration
"""

import sys
import os
import json
from datetime import datetime

# Create a test signal directly
signal_id = f"TEST-{datetime.utcnow().strftime('%Y%m%d-%H%M')}"
current_time = datetime.utcnow().isoformat()

# Test signal data
signal = {
    "signal_id": signal_id,
    "timestamp": current_time,
    "asset": "BTC",
    "signal_type": "TREND_FOLLOWING",
    "direction": "LONG",
    "entry_price": 51250.75,
    "stop_loss": 49850.25,
    "take_profits": [52015.01, 53044.53, 54838.30],
    "position_size_usd": 615.00,
    "position_size_pct": 6.15,
    "confidence": 0.82,
    "risk_reward_ratio": 1.8,
    "market_conditions": {
        "trend_strength": 0.75,
        "volatility_pct": 2.8,
        "volume_ratio": 1.35
    },
    "risk_management": {
        "max_loss_usd": 184.50,
        "max_loss_pct": 1.85,
        "daily_loss_limit": "3%",
        "weekly_loss_limit": "8%"
    }
}

# Format for Telegram
emoji = "🟢"
direction_emoji = "📈"

telegram_message = f"""
{emoji} *SEÑAL DE TRADING* {direction_emoji}

*ID:* `{signal['signal_id']}`
*Hora:* {datetime.fromisoformat(signal['timestamp']).strftime('%H:%M UTC')}

*🎯 ACTIVO:* {signal['asset']}
*📊 TIPO:* {signal['signal_type'].replace('_', ' ').title()}
*🧭 DIRECCIÓN:* {signal['direction']} ({'COMPRA' if signal['direction'] == 'LONG' else 'VENTA'})

*💰 PRECIOS:*
• Entrada: `${signal['entry_price']:,}`
• Stop Loss: `${signal['stop_loss']:,}`
• Take Profits: `${signal['take_profits'][0]:,}` / `${signal['take_profits'][1]:,}` / `${signal['take_profits'][2]:,}`

*📈 POSICIÓN:*
• Tamaño: `${signal['position_size_usd']:,}` ({signal['position_size_pct']}% del capital)
• Confianza: {signal['confidence']*100:.0f}%
• Risk/Reward: 1:{signal['risk_reward_ratio']:.1f}

*⚠️ RIESGO:*
• Pérdida máxima: `${signal['risk_management']['max_loss_usd']:,}` ({signal['risk_management']['max_loss_pct']:.1f}%)
• Límite diario: {signal['risk_management']['daily_loss_limit']}
• Límite semanal: {signal['risk_management']['weekly_loss_limit']}

*📊 CONDICIONES DE MERCADO:*
• Fuerza de tendencia: {signal['market_conditions']['trend_strength']:.2f}/1.0
• Volatilidad: {signal['market_conditions']['volatility_pct']:.1f}%
• Volumen: {signal['market_conditions']['volume_ratio']:.2f}x promedio

*✅ ACCIÓN REQUERIDA:*
1. Ejecutar {signal['direction']} en {signal['asset']} a `${signal['entry_price']:,}`
2. Colocar Stop Loss en `${signal['stop_loss']:,}`
3. Colocar Take Profits en niveles indicados
4. Reportar resultado cuando cierre la operación

*📝 NOTAS:*
• Esta es una señal de PRUEBA generada por el sistema Swarm AI optimizado
• Ejecutar solo si el capital disponible permite el tamaño de posición
• Considerar fees y slippage en la ejecución real
• Señal de demostración - no usar con capital real
"""

print("=" * 70)
print("🧪 SEÑAL DE PRUEBA - DEMOSTRACIÓN")
print("=" * 70)
print(f"⏰ Generada: {datetime.fromisoformat(signal['timestamp']).strftime('%H:%M UTC')}")
print(f"🎯 Propósito: Mostrar formato para prueba manual con FRAN")
print()

print(telegram_message)

print("=" * 70)
print("📋 INSTRUCCIONES:")
print("=" * 70)
print("1. Copia el mensaje completo de arriba")
print("2. Envíalo por Telegram a FRAN")
print("3. FRAN ejecuta la operación manualmente")
print("4. Reporta resultado (ganancia/pérdida)")
print("5. Repetimos con señales reales del sistema")
print()

# Save files
os.makedirs('signal_results', exist_ok=True)
signal_file = f"signal_results/{signal_id}.txt"
json_file = f"signal_results/{signal_id}.json"

with open(signal_file, 'w') as f:
    f.write(telegram_message)

with open(json_file, 'w') as f:
    json.dump(signal, f, indent=2)

print(f"💾 Archivos guardados:")
print(f"   {signal_file}")
print(f"   {json_file}")
print()
print("✅ Listo para probar el sistema de señales")
print("=" * 70)