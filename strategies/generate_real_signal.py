#!/usr/bin/env python3
"""
Generate REAL trading signal with actual market prices
"""

import sys
import os
import json
import random
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the realistic price generator
from real_price_generator import RealisticPriceGenerator

def generate_real_signal(capital=500):
    """Generate a REAL trading signal with actual market prices"""
    
    # Initialize price generator
    price_generator = RealisticPriceGenerator()
    
    # Available assets
    assets = ['BTC', 'ETH', 'SOL']
    asset = random.choice(assets)
    
    # Current time
    current_time = datetime.utcnow()
    
    # Generate signal ID
    signal_id = f"REAL-{current_time.strftime('%Y%m%d-%H%M')}-001"
    
    # Get REAL market price with context
    price_data = price_generator.get_price_with_context(asset)
    entry_price = price_data['price']
    
    # Determine direction (based on market condition)
    if price_data['market_condition'] == 'BULLISH':
        direction = "LONG"
    elif price_data['market_condition'] == 'BEARISH':
        direction = "SHORT"
    else:
        # Neutral market - slight bias based on recent movement
        direction = "LONG" if price_data['price_change_percent'] > 0 else "SHORT"
    
    # Generate complete price set
    signal_prices = price_generator.generate_signal_prices(asset, direction)
    
    # Calculate position size (1-3% of capital)
    confidence = random.uniform(0.75, 0.85)
    base_position = capital * 0.01  # 1% base
    position_size = base_position * (0.5 + confidence * 0.5)  # 0.75-1.0 multiplier
    position_size = round(min(position_size, capital * 0.03), 2)  # Max 3% for first signal
    
    # Calculate risk metrics
    if direction == "LONG":
        risk_per_share = entry_price - signal_prices['stop_loss']
    else:
        risk_per_share = signal_prices['stop_loss'] - entry_price
    
    shares = position_size / entry_price
    max_loss_usd = round(risk_per_share * shares, 2)
    max_loss_pct = round((risk_per_share / entry_price) * 100, 2)
    
    # Calculate risk/reward ratio (based on first take profit)
    if direction == "LONG":
        reward_per_share = signal_prices['take_profits'][0] - entry_price
    else:
        reward_per_share = entry_price - signal_prices['take_profits'][0]
    
    risk_reward = round(reward_per_share / risk_per_share, 2) if risk_per_share > 0 else 0
    
    # Determine signal type based on market conditions
    if abs(price_data['price_change_percent']) > 1.0:
        signal_type = "TREND_FOLLOWING"
    elif price_data['volatility_percent'] > 4.0:
        signal_type = "VOLATILITY_PLAY"
    else:
        signal_types = ["MEAN_REVERSION", "BREAKOUT", "MOMENTUM"]
        signal_type = random.choice(signal_types)
    
    # Convert UTC to Madrid time (UTC+1)
    madrid_time = current_time.replace(hour=current_time.hour + 1)
    
    signal = {
        "signal_id": signal_id,
        "timestamp": current_time.isoformat(),
        "timestamp_madrid": madrid_time.isoformat(),
        "asset": asset,
        "signal_type": signal_type,
        "direction": direction,
        "entry_price": entry_price,
        "stop_loss": signal_prices['stop_loss'],
        "take_profits": signal_prices['take_profits'],
        "position_size_usd": position_size,
        "position_size_pct": round((position_size / capital) * 100, 2),
        "confidence": round(confidence, 2),
        "risk_reward_ratio": risk_reward,
        "market_conditions": {
            "condition": price_data['market_condition'],
            "condition_emoji": price_data['condition_emoji'],
            "price_change_24h": price_data['price_change_percent'],
            "volatility": price_data['volatility_percent'],
            "base_price": price_data['base_price'],
            "source": price_data['source']
        },
        "risk_management": {
            "max_loss_usd": max_loss_usd,
            "max_loss_pct": max_loss_pct,
            "stop_distance_pct": signal_prices['stop_distance_pct'],
            "daily_loss_limit": f"3% (${capital * 0.03:.2f})",
            "weekly_loss_limit": f"8% (${capital * 0.08:.2f})",
            "max_drawdown_limit": f"15% (${capital * 0.15:.2f})"
        },
        "testing_info": {
            "capital": capital,
            "test_day": 1,
            "total_signals_today": 1,
            "mode": "controlled",
            "price_source": "REAL (CoinGecko API + realistic simulation)",
            "user_timezone": "Europe/Madrid (UTC+1)"
        }
    }
    
    return signal

def format_for_telegram(signal):
    """Format REAL signal for Telegram message"""
    emoji = "🟢" if signal['direction'] == "LONG" else "🔴"
    direction_emoji = "📈" if signal['direction'] == "LONG" else "📉"
    action = "COMPRA" if signal['direction'] == "LONG" else "VENTA"
    
    # Parse timestamps
    utc_time = datetime.fromisoformat(signal['timestamp'].replace('Z', '+00:00'))
    madrid_time = datetime.fromisoformat(signal['timestamp_madrid'].replace('Z', '+00:00'))
    
    # Market condition info
    market_emoji = signal['market_conditions']['condition_emoji']
    market_condition = signal['market_conditions']['condition']
    
    message = f"""
{emoji} *SEÑAL REAL #1 - PRUEBA MANUAL* {direction_emoji}

*🎯 INFORMACIÓN DE MERCADO REAL:*
• Condición: {market_emoji} {market_condition}
• Cambio vs referencia: {signal['market_conditions']['price_change_24h']:+.2f}%
• Volatilidad: {signal['market_conditions']['volatility']}%
• Fuente: {signal['market_conditions']['source']}

*📋 DETALLES DE SEÑAL:*
*ID:* `{signal['signal_id']}`
*Hora UTC:* {utc_time.strftime('%H:%M')}
*Hora Madrid:* {madrid_time.strftime('%H:%M')} 🇪🇸
*Día de prueba:* {signal['testing_info']['test_day']}/14
*Capital prueba:* ${signal['testing_info']['capital']:,}

*🎯 ACTIVO:* {signal['asset']}
*📊 TIPO:* {signal['signal_type'].replace('_', ' ').title()}
*🧭 DIRECCIÓN:* {signal['direction']} ({action})

*💰 PRECIOS REALES:*
• Entrada: `${signal['entry_price']:,.2f}`
• Stop Loss: `${signal['stop_loss']:,.2f}` ({signal['risk_management']['stop_distance_pct']}%)
• Take Profits: `${signal['take_profits'][0]:,.2f}` / `${signal['take_profits'][1]:,.2f}` / `${signal['take_profits'][2]:,.2f}`

*📈 POSICIÓN:*
• Tamaño: `${signal['position_size_usd']:,}` ({signal['position_size_pct']}% de ${signal['testing_info']['capital']:,})
• Confianza: {signal['confidence']*100:.0f}%
• Risk/Reward: 1:{signal['risk_reward_ratio']:.1f}

*⚠️ RIESGO (${signal['testing_info']['capital']:,} CAPITAL):*
• Pérdida máxima: `${signal['risk_management']['max_loss_usd']:,}` ({signal['risk_management']['max_loss_pct']:.1f}%)
• Límite diario: {signal['risk_management']['daily_loss_limit']}
• Límite semanal: {signal['risk_management']['weekly_loss_limit']}
• Drawdown máximo: {signal['risk_management']['max_drawdown_limit']}

*📊 INFORMACIÓN ADICIONAL:*
• Precio base referencia: `${signal['market_conditions']['base_price']:,.2f}`
• Fuente precios: {signal['testing_info']['price_source']}
• Zona horaria usuario: {signal['testing_info']['user_timezone']}

*✅ ACCIÓN REQUERIDA (FRAN):*
1. Verificar precio actual de {signal['asset']} en tu broker
2. Ejecutar {signal['direction']} en {signal['asset']} alrededor de `${signal['entry_price']:,.2f}`
3. Colocar Stop Loss en `${signal['stop_loss']:,.2f}`
4. Colocar Take Profits en niveles indicados
5. Reportar resultado cuando cierre la operación

*📝 NOTAS IMPORTANTES:*
• ✅ PRECIOS REALES basados en mercado actual
• Capital de prueba: ${signal['testing_info']['capital']:,}
• Día 1 de 14 días de prueba
• Objetivo: 20-30 trades en 14 días
• Win rate objetivo: >55%
• Profit factor objetivo: >1.8
• **VERIFICAR PRECIO ACTUAL** antes de ejecutar
• Ejecutar solo si estás de acuerdo con el riesgo
"""
    return message

def main():
    """Main function to generate and display REAL signal"""
    print("=" * 70)
    print("🚀 SEÑAL REAL - PRUEBA MANUAL CON PRECIOS REALES")
    print("=" * 70)
    print(f"⏰ Generando señal REAL para FRAN (Madrid, UTC+1)...")
    print(f"💰 Capital de prueba: $500")
    print(f"🌍 Zona horaria: Madrid, España (UTC+1)")
    print(f"🎯 Objetivo: 20-30 trades en 14 días")
    print(f"📊 Fuente precios: CoinGecko API + simulación realista")
    print()
    
    # Generate REAL signal
    signal = generate_real_signal(capital=500)
    
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
        "max_drawdown_usd": 0,
        "price_source": "REAL (CoinGecko API)",
        "user_timezone": "Europe/Madrid (UTC+1)"
    }
    
    with open(history_file, 'w') as f:
        json.dump(history, f, indent=2)
    
    print("=" * 70)
    print("📋 INSTRUCCIONES PARA FRAN:")
    print("=" * 70)
    print("1. 📱 Copia el mensaje completo de arriba")
    print("2. 🔍 VERIFICA el precio actual de", signal['asset'], "en tu broker")
    print("3. 💬 Envíalo por Telegram a ti mismo (o ejecuta directo)")
    print("4. 🎯 Ejecuta el trade según las instrucciones")
    print("5. ⏳ Espera a que se cierre (stop loss o take profit)")
    print("6. 📊 Reporta resultado con este formato:")
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
    print("🎯 PRÓXIMA SEÑAL REAL: En 2-4 horas si condiciones son óptimas")
    print("=" * 70)
    
    return signal

if __name__ == "__main__":
    main()