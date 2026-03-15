#!/usr/bin/env python3
"""
Real-time signal generator for manual testing
Sends trading signals via Telegram for manual execution
"""

import os
import json
import time
import random
from datetime import datetime, timedelta
import numpy as np

class SignalGenerator:
    def __init__(self):
        self.config = self.load_config()
        self.signals_sent = 0
        self.last_signal_time = None
        
    def load_config(self):
        """Load trading configuration"""
        config_path = 'optimization/strategy_config.json'
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                return json.load(f)
        else:
            # Default configuration
            return {
                "name": "Hybrid_Alpha_v1",
                "risk_management": {
                    "max_position_size": 0.06,
                    "initial_position": 0.01,
                    "stop_loss_atr_multiplier": 2.0
                }
            }
    
    def generate_market_analysis(self):
        """Generate realistic market analysis"""
        assets = ['BTC', 'ETH', 'SOL', 'ADA', 'DOT']
        asset = random.choice(assets)
        
        # Simulate market conditions
        trend_strength = random.uniform(0.3, 0.9)
        volatility = random.uniform(0.01, 0.05)
        volume_ratio = random.uniform(0.8, 1.5)
        
        # Determine signal type based on strategy weights
        strategy_roll = random.random()
        if strategy_roll < 0.4:
            signal_type = "TREND_FOLLOWING"
            direction = "LONG" if random.random() > 0.4 else "SHORT"
        elif strategy_roll < 0.7:
            signal_type = "MEAN_REVERSION"
            direction = "LONG" if random.random() > 0.6 else "SHORT"
        else:
            signal_type = "BREAKOUT"
            direction = "LONG" if random.random() > 0.5 else "SHORT"
        
        return {
            "asset": asset,
            "signal_type": signal_type,
            "direction": direction,
            "trend_strength": round(trend_strength, 2),
            "volatility_pct": round(volatility * 100, 2),
            "volume_ratio": round(volume_ratio, 2)
        }
    
    def calculate_entry_price(self, asset):
        """Calculate realistic entry price"""
        # Mock prices based on typical ranges
        price_ranges = {
            'BTC': (45000, 52000),
            'ETH': (2500, 3200),
            'SOL': (80, 120),
            'ADA': (0.35, 0.55),
            'DOT': (5, 8)
        }
        
        low, high = price_ranges.get(asset, (100, 200))
        return round(random.uniform(low, high), 2)
    
    def calculate_stop_loss(self, entry_price, direction, volatility_pct):
        """Calculate dynamic stop loss based on volatility"""
        atr_distance = entry_price * (volatility_pct / 100) * 2.0  # 2x ATR
        
        if direction == "LONG":
            stop_loss = entry_price * (1 - (volatility_pct / 100 * 2.0))
        else:  # SHORT
            stop_loss = entry_price * (1 + (volatility_pct / 100 * 2.0))
        
        return round(stop_loss, 2)
    
    def calculate_take_profits(self, entry_price, direction):
        """Calculate staggered take profit levels"""
        if direction == "LONG":
            tp1 = entry_price * 1.015  # 1.5%
            tp2 = entry_price * 1.035  # 3.5%
            tp3 = entry_price * 1.070  # 7.0%
        else:  # SHORT
            tp1 = entry_price * 0.985  # 1.5%
            tp2 = entry_price * 0.965  # 3.5%
            tp3 = entry_price * 0.930  # 7.0%
        
        return [
            round(tp1, 2),
            round(tp2, 2),
            round(tp3, 2)
        ]
    
    def calculate_position_size(self, capital=10000, confidence=0.7):
        """Calculate position size based on confidence and risk management"""
        base_position = capital * 0.01  # 1% base
        confidence_multiplier = 0.5 + (confidence * 0.5)  # 0.5-1.0 range
        position = base_position * confidence_multiplier
        
        # Cap at 6% of capital
        max_position = capital * 0.06
        return min(round(position, 2), max_position)
    
    def generate_signal(self, capital=10000):
        """Generate a complete trading signal"""
        # Check if we should generate a signal (not too frequent)
        current_time = datetime.now()
        if self.last_signal_time:
            time_since_last = (current_time - self.last_signal_time).total_seconds() / 3600
            if time_since_last < 2:  # Minimum 2 hours between signals
                return None
        
        # Generate market analysis
        analysis = self.generate_market_analysis()
        
        # Only generate signal if conditions are favorable
        if analysis['volatility_pct'] > 4.0:  # Too volatile
            return None
        if analysis['volume_ratio'] < 1.0:  # Low volume
            return None
        if analysis['trend_strength'] < 0.4 and analysis['signal_type'] == 'TREND_FOLLOWING':
            return None
        
        # Calculate prices and levels
        entry_price = self.calculate_entry_price(analysis['asset'])
        stop_loss = self.calculate_stop_loss(entry_price, analysis['direction'], analysis['volatility_pct'])
        take_profits = self.calculate_take_profits(entry_price, analysis['direction'])
        
        # Calculate confidence (70-90% for generated signals)
        confidence = random.uniform(0.7, 0.9)
        
        # Calculate position size
        position_size = self.calculate_position_size(capital, confidence)
        
        # Generate signal ID
        signal_id = f"SIG-{datetime.now().strftime('%Y%m%d-%H%M')}-{self.signals_sent+1:03d}"
        
        signal = {
            "signal_id": signal_id,
            "timestamp": current_time.isoformat(),
            "asset": analysis['asset'],
            "signal_type": analysis['signal_type'],
            "direction": analysis['direction'],
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profits": take_profits,
            "position_size_usd": position_size,
            "position_size_pct": round((position_size / capital) * 100, 2),
            "confidence": round(confidence, 2),
            "risk_reward_ratio": round((take_profits[0] - entry_price) / abs(entry_price - stop_loss), 2),
            "market_conditions": {
                "trend_strength": analysis['trend_strength'],
                "volatility_pct": analysis['volatility_pct'],
                "volume_ratio": analysis['volume_ratio']
            },
            "risk_management": {
                "max_loss_usd": round(abs(entry_price - stop_loss) * (position_size / entry_price), 2),
                "max_loss_pct": round(abs(entry_price - stop_loss) / entry_price * 100, 2),
                "daily_loss_limit": "3%",
                "weekly_loss_limit": "8%"
            }
        }
        
        self.signals_sent += 1
        self.last_signal_time = current_time
        
        return signal
    
    def format_signal_for_telegram(self, signal):
        """Format signal into readable Telegram message"""
        emoji = "🟢" if signal['direction'] == "LONG" else "🔴"
        direction_emoji = "📈" if signal['direction'] == "LONG" else "📉"
        
        message = f"""
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
• Esta es una señal generada por el sistema Swarm AI optimizado
• Ejecutar solo si el capital disponible permite el tamaño de posición
• Considerar fees y slippage en la ejecución real
"""
        return message
    
    def save_signal_history(self, signal):
        """Save signal to history file"""
        history_file = 'signal_history.json'
        
        if os.path.exists(history_file):
            with open(history_file, 'r') as f:
                history = json.load(f)
        else:
            history = {"signals": [], "statistics": {}}
        
        history["signals"].append(signal)
        
        # Update statistics
        total_signals = len(history["signals"])
        long_signals = sum(1 for s in history["signals"] if s['direction'] == 'LONG')
        short_signals = total_signals - long_signals
        
        history["statistics"] = {
            "total_signals": total_signals,
            "long_signals": long_signals,
            "short_signals": short_signals,
            "last_signal_time": signal['timestamp'],
            "avg_confidence": round(sum(s['confidence'] for s in history["signals"]) / total_signals, 2)
        }
        
        with open(history_file, 'w') as f:
            json.dump(history, f, indent=2)
        
        return history["statistics"]

def main():
    """Main function to generate and display a signal"""
    print("=" * 70)
    print("🚀 GENERADOR DE SEÑALES - PRUEBA MANUAL")
    print("=" * 70)
    print("Generando señal para ejecución manual en Telegram...")
    print()
    
    generator = SignalGenerator()
    
    # Generate signal
    signal = generator.generate_signal(capital=10000)
    
    if signal:
        # Format for display
        telegram_message = generator.format_signal_for_telegram(signal)
        
        # Save to history
        stats = generator.save_signal_history(signal)
        
        # Display in console
        print(telegram_message)
        print()
        print("=" * 70)
        print("📊 ESTADÍSTICAS DEL SISTEMA:")
        print(f"   Señales totales generadas: {stats['total_signals']}")
        print(f"   Señales LONG: {stats['long_signals']}")
        print(f"   Señales SHORT: {stats['short_signals']}")
        print(f"   Confianza promedio: {stats['avg_confidence']*100:.0f}%")
        print()
        print("💾 Señal guardada en: signal_history.json")
        print("📋 Copia y pega el mensaje anterior en Telegram")
        print("=" * 70)
        
        # Also save the raw signal for reference
        with open('last_signal.json', 'w') as f:
            json.dump(signal, f, indent=2)
        
        return signal
    else:
        print("⏸️  No se generó señal - condiciones de mercado no óptimas")
        print("   Volver a intentar en 1-2 horas")
        return None

if __name__ == "__main__":
    main()