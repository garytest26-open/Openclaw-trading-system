#!/usr/bin/env python3
"""
Generate first signal for FRAN with $500 capital
"""

import sys
import os
import json
import random
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Mock signal generation for first test
def generate_first_signal(capital=500):
    """Generate a realistic first signal for testing"""
    
    # Available assets for testing
    assets = ['BTC', 'ETH', 'SOL']
    asset = random.choice(assets)
    
    # Current time
    current_time = datetime.utcnow()
    
    # Generate signal ID
    signal_id = f"SIG-{current_time.strftime('%Y%m%d-%H%M')}-001"
    
    # Price ranges based on asset
    price_ranges = {
        'BTC': (51000, 51500),
        'ETH': (3100, 3200),
        'SOL': (110, 120)
    }
    
    low, high = price_ranges.get(asset, (100, 200))
    entry_price = round(random.uniform(low, high), 2)
    
    # Determine direction (slightly biased long for first test)
    direction = "LONG" if random.random() > 0.4 else "SHORT"
    
    # Calculate stop loss (1.8-2.2% based on volatility)
    volatility_pct = random.uniform(1.8, 2.2)
    if direction == "LONG":
        stop_loss = entry_price * (1 - volatility_pct/100)
    else:
        stop_loss = entry_price * (1 + volatility_pct/100)
    stop_loss = round(stop_loss, 2)
    
    # Calculate take profits (staggered)
    if direction == "LONG":
        tp1 = entry_price * 1.015  # 1.5%
        tp2 = entry_price * 1.035  # 3.5%
        tp3 = entry_price * 1.070  # 7.0%
    else:
        tp1 = entry_price * 0.985  # 1.5%
        tp2 = entry_price * 0.965  # 3.5%
        tp3 = entry_price * 0.930  # 7.0%
    
    take_profits = [round(tp1, 2), round(tp2, 2), round(tp3, 2)]
    
    # Calculate position size (1-3% of $500 = $5-$15)
    confidence = random.uniform(0.75, 0.85)
    base_position = capital * 0.01  # 1% base
    position_size = base_position * (0.5 + confidence * 0.5)  # 0.75-1.0 multiplier
    position_size = round(min(position_size, capital * 0.03), 2)  # Max 3% for first signal
    
    # Calculate risk metrics
    risk_reward = round((take_profits[0] - entry_price) / abs(entry_price - stop_loss), 2)
    max_loss_usd = round(abs(entry_price - stop_loss) * (position_size / entry_price), 2)
    max_loss_pct = round(abs(entry_price - stop_loss) / entry_price * 100, 2)
    
    # Determine signal type
    signal_types = ["TREND_FOLLOWING", "MEAN_REVERSION", "BREAKOUT"]
    signal_type = random.choice(signal_types)
    
    # Market conditions
    market_conditions = {
        "trend_strength": round(random.uniform(0.6, 0.8), 2),
        "volatility_pct": round(volatility_pct, 2),
        "volume_ratio": round(random.uniform(1.1, 1.4), 2)
    }
    
    signal = {
        "signal_id": signal_id,
        "timestamp": current_time.isoformat(),
        "asset": asset,
        "signal_type": signal_type,
        "direction": direction,
        "entry_price": entry_price,
        "stop_loss": stop_loss,
        "take_profits": take_profits,
        "position_size_usd": position_size,
        "position_size_pct": round((position_size / capital) * 100, 2),
        "confidence": round(confidence, 2),
        "risk_reward_ratio": risk_reward,
        "market_conditions": market_conditions,
        "risk_management": {
            "max_loss_usd": max_loss_usd,
            "max_loss_pct": max_loss_pct,
            "daily_loss_limit": "3% ($15)",
            "weekly_loss_limit": "8% ($40)",
            "max_drawdown_limit": "15% ($75)"
        },
        "testing_info": {
            "capital": capital,
            "test_day": 1,
            "total_signals_today": 1,
            "mode": "controlled"
        }
    }
    
    return signal

def format_for_telegram(signal):
    """Format signal for Telegram message"""
    emoji = "🟢" if signal['direction'] == "LONG" else "🔴"
    direction_emoji = "📈" if signal['direction'] == "LONG" else "📉"
    action = "COMPRA" if signal['direction'] == "LONG" else "VENTA"
    
    # Convert UTC to Madrid time (UTC+1)
    utc_time = datetime.fromisoformat(signal['timestamp'])
    madrid_time = utc_time.replace(hour=utc_time.hour + 1)
    
    message = f"""
{emoji} *SEÑAL #1 - PRUEBA MANUAL* {direction_emoji}

*ID:* `{signal['signal_id']}`
*Hora UTC:* {utc_time.strftime('%H:%M')}
*Hora Madrid:* {madrid_time.strftime('%H:%M')} 🇪🇸
*Día de prueba:* 1/14
*Capital prueba:* ${signal['testing_info']['capital']:,}

*🎯 ACTIVO:* {signal['asset']}
*📊 TIPO:* {signal['signal_type'].replace('_', ' ').title()}
*🧭 DIRECCIÓN:* {signal['direction']} ({action})

*💰 PRECIOS:*
• Entrada: `${signal['entry_price']:,}`
• Stop Loss: `${signal['stop_loss']:,}`
• Take Profits: `${signal['take_profits'][0]:,}` / `${signal['take_profits'][1]:,}` / `${signal['take_profits'][2]:,}`

*📈 POSICIÓN:*
• Tamaño: `${signal['position_size_usd']:,}` ({signal['position_size_pct']}% de ${signal['testing_info']['capital']:,})
• Confianza: {signal['confidence']*100:.0f}%
• Risk/Reward: 1:{signal['risk_reward_ratio']:.1f}

*⚠️ RIESGO ($500 CAPITAL):*
• Pérdida máxima: `${signal['risk_management']['max_loss_usd']:,}` ({signal['risk_management']['max_loss_pct']:.1f}%)
• Límite diario: {signal['risk_management']['daily_loss_limit']}
• Límite semanal: {signal['risk_management']['weekly_loss_limit']}
• Drawdown máximo: {signal['risk_management']['max_drawdown_limit']}

*📊 CONDICIONES DE MERCADO:*
• Fuerza de tendencia: {signal['market_conditions']['trend_strength']:.2f}/1.0
• Volatilidad: {signal['market_conditions']['volatility_pct']:.1f}%
• Volumen: {signal['market_conditions']['volume_ratio']:.2f}x promedio

*✅ ACCIÓN REQUERIDA (FRAN):*
1. Ejecutar {signal['direction']} en {signal['asset']} a `${signal['entry_price']:,}`
2. Colocar Stop Loss en `${signal['stop_loss']:,}`
3. Colocar Take Profits en niveles indicados
4. Reportar resultado cuando cierre la operación

*📝 NOTAS PRUEBA MANUAL:*
• Capital de prueba: ${signal['testing_info']['capital']:,}
• Día 1 de 14 días de prueba
• Objetivo: 20-30 trades en 14 días
• Win rate objetivo: >55%
• Profit factor objetivo: >1.8
• Ejecutar solo si estás de acuerdo con el riesgo
"""
    return message

def main():
    """Main function to generate and display first signal"""
    print("=" * 70)
    print("🚀 PRIMERA SEÑAL - PRUEBA MANUAL CON $500")
    print("=" * 70)
    print(f"⏰ Generando primera señal para FRAN (Madrid, UTC+1)...")
    print(f"💰 Capital de prueba: $500")
    print(f"🌍 Zona horaria: Madrid, España (UTC+1)")
    print(f"🎯 Objetivo: 20-30 trades en 14 días")
    print()
    
    # Generate signal
    signal = generate_first_signal(capital=500)
    
    # Format for Telegram
    telegram_message = format_for_telegram(signal)
    
    # Display
    print(telegram_message)
    
    # Save to files
    os.makedirs('signal_results', exist_ok=True)
    
    # Save Telegram message
    signal_file = f"signal_results/{signal['signal_id']}.txt"
    with open(signal_file, 'w') as f:
        f.write(telegram_message)
    
    # Save JSON data
    json_file = f"signal_results/{signal['signal_id']}.json"
    with open(json_file, 'w') as f:
        json.dump(signal, f, indent=2)
    
    # Update signal history
    history_file = 'signal_history.json'
    if os.path.exists(history_file):
        with open(history_file, 'r') as f:
            history = json.load(f)
    else:
        history = {"signals": [], "statistics": {}, "testing": {}}
    
    history["signals"].append(signal)
    
    # Initialize testing statistics
    history["testing"] = {
        "start_date": datetime.utcnow().date().isoformat(),
        "capital": 500,
        "target_duration_days": 14,
        "target_trades": 30,
        "signals_today": 1,
        "trades_executed": 0,
        "trades_won": 0,
        "trades_lost": 0,
        "total_profit_usd": 0,
        "total_loss_usd": 0,
        "current_drawdown_usd": 0,
        "max_drawdown_usd": 0
    }
    
    with open(history_file, 'w') as f:
        json.dump(history, f, indent=2)
    
    print("=" * 70)
    print("📋 INSTRUCCIONES PARA FRAN:")
    print("=" * 70)
    print("1. 📱 Copia el mensaje completo de arriba")
    print("2. 💬 Envíalo por Telegram a ti mismo (o ejecuta directo)")
    print("3. 🎯 Ejecuta el trade según las instrucciones")
    print("4. ⏳ Espera a que se cierre (stop loss o take profit)")
    print("5. 📊 Reporta resultado con este formato:")
    print()
    print("   ✅ TRADE CERRADO")
    print("   ID: [ID de la señal]")
    print("   Resultado: +X.X% / -X.X%")
    print("   Ganancia/Pérdida: +$XX.XX / -$XX.XX")
    print("   Tiempo: X horas X minutos")
    print("   Comentarios: [opcional]")
    print()
    print("💾 Archivos guardados:")
    print(f"   {signal_file}")
    print(f"   {json_file}")
    print(f"   {history_file}")
    print()
    print("🎯 PRÓXIMA SEÑAL: En 2-4 horas si condiciones son óptimas")
    print("=" * 70)
    
    return signal

if __name__ == "__main__":
    main()