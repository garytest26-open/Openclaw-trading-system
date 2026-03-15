"""
BINGX_TELEGRAM_SYSTEM.py - Sistema específico para bingX demo
Ajustado a horario Madrid (CET) y formato bingX
"""

import sys
import os
import time
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

# Añadir ruta para importar sistema agresivo
sys.path.append('/home/ubuntu/.openclaw/workspace/trading/swarm_ai_advanced')

from AGGRESSIVE_DUAL_SYSTEM import AggressiveDualTradingSystem

print("🎯 SISTEMA TELEGRAM PARA BINGX DEMO")
print("=" * 60)
print("Configuración: Horario Madrid (CET), Formato bingX")
print("Exchange: bingX (demo/sandbox)")
print("Capital: $10 virtuales para aprendizaje")
print("=" * 60)

class BingXTelegramSystem:
    """Sistema específico para bingX demo"""
    
    def __init__(self, symbol_format='BTCUSDT'):
        self.system = AggressiveDualTradingSystem()
        self.signals_history = []
        self.cycle_count = 0
        self.symbol_format = symbol_format  # 'BTCUSDT', 'BTC-USDT', 'BTC/USDT'
        
        # Configurar horario Madrid (CET = UTC+1, CEST = UTC+2)
        self.timezone_offset = 1  # CET (UTC+1) - ajustar según estación
        self.local_tz = "CET (Madrid)"
        
        print(f"✅ Sistema bingX inicializado")
        print(f"   Horario: {self.local_tz} (UTC+{self.timezone_offset})")
        print(f"   Formato símbolos: {symbol_format}")
        print(f"   Exchange: bingX demo")
        print(f"   Capital demo: $10 USDT virtuales")
    
    def get_madrid_time(self):
        """Obtener hora actual en Madrid"""
        utc_now = datetime.utcnow()
        madrid_time = utc_now + timedelta(hours=self.timezone_offset)
        return madrid_time
    
    def convert_to_bingx_symbol(self, symbol):
        """Convertir símbolo estándar a formato bingX"""
        
        # Mapeo de símbolos según formato
        if self.symbol_format == 'BTCUSDT':
            return symbol.replace('/', '').replace('-', '')
        elif self.symbol_format == 'BTC-USDT':
            return symbol.replace('/', '-')
        elif self.symbol_format == 'BTC/USDT':
            return symbol
        else:
            return symbol  # Por defecto
    
    def get_current_price_simulated(self, symbol):
        """Obtener precio simulado (para demo)"""
        
        # Precios base realistas (marzo 2026)
        base_prices = {
            'BTCUSDT': 52147.32,
            'ETHUSDT': 3147.85,
            'BTC-USDT': 52147.32,
            'ETH-USDT': 3147.85,
            'BTC/USDT': 52147.32,
            'ETH/USDT': 3147.85
        }
        
        # Variación realista (±1-3%)
        import random
        bingx_symbol = self.convert_to_bingx_symbol(symbol)
        base = base_prices.get(bingx_symbol, 1000.0)
        variation = random.uniform(-0.03, 0.03)
        
        return base * (1 + variation)
    
    def generate_hourly_signals_bingx(self):
        """Generar señales para bingX cada hora"""
        
        self.cycle_count += 1
        madrid_time = self.get_madrid_time()
        
        print(f"\n{'='*60}")
        print(f"🔄 CICLO {self.cycle_count} - bingX DEMO")
        print(f"⏰ Hora Madrid: {madrid_time.strftime('%Y-%m-%d %H:%M %Z')}")
        print(f"{'='*60}")
        
        # Símbolos estándar (los convertiremos a formato bingX)
        standard_symbols = ['BTC/USDT', 'ETH/USDT']
        cycle_signals = []
        
        for std_symbol in standard_symbols:
            # Convertir a formato bingX
            bingx_symbol = self.convert_to_bingx_symbol(std_symbol)
            
            print(f"\n🎯 PROCESANDO {bingx_symbol} (bingX)...")
            
            try:
                # Obtener precio simulado
                current_price = self.get_current_price_simulated(std_symbol)
                print(f"   💰 Precio demo: ${current_price:,.2f}")
                
                # Generar señal AGRESIVA (usamos símbolo estándar internamente)
                signal_result = self.system.generate_aggressive_signals(std_symbol)
                
                if signal_result:
                    # Añadir información específica bingX
                    signal_result['exchange'] = 'bingX'
                    signal_result['account_type'] = 'demo'
                    signal_result['symbol'] = bingx_symbol
                    signal_result['standard_symbol'] = std_symbol
                    signal_result['current_price'] = current_price
                    signal_result['timestamp'] = self.get_madrid_time()
                    signal_result['signal_id'] = f"bingx_{bingx_symbol}_{madrid_time.strftime('%Y%m%d_%H%M')}"
                    
                    # Calcular stop loss y take profit
                    signal_result['stop_loss_price'] = current_price * 0.95
                    signal_result['take_profit_price'] = current_price * 1.10
                    signal_result['stop_loss_pct'] = 5.0
                    signal_result['take_profit_pct'] = 10.0
                    
                    # Guardar
                    self.signals_history.append(signal_result)
                    cycle_signals.append(signal_result)
                    
                    print(f"   ✅ Señal: {signal_result['final_signal']}")
                    print(f"   📊 Posición: {signal_result['total_position']*100:.1f}%")
                    print(f"   🎯 Confianza: {max(signal_result['safe_signal']['confidence'], signal_result['growth_signal']['confidence'])*100:.0f}%")
                    
                    # Formatear para Telegram específico bingX
                    telegram_msg = self.format_for_bingx_telegram(signal_result)
                    print(f"\n   📨 MENSAJE TELEGRAM BINGX:")
                    print(f"   {'-'*40}")
                    print(telegram_msg[:200] + "..." if len(telegram_msg) > 200 else telegram_msg)
                    print(f"   {'-'*40}")
                    
                else:
                    print(f"   ❌ No se pudo generar señal")
                    
            except Exception as e:
                print(f"   ❌ Error: {e}")
                import traceback
                traceback.print_exc()
        
        # Resumen del ciclo
        if cycle_signals:
            print(f"\n📊 RESUMEN CICLO {self.cycle_count} (bingX):")
            for sig in cycle_signals:
                emoji = "🟢" if sig['final_signal'] == 'BUY' else "🔴" if sig['final_signal'] == 'SELL' else "🟡"
                print(f"   {emoji} {sig['symbol']}: {sig['final_signal']} ({sig['total_position']*100:.1f}%)")
        
        # Próximo ciclo en horario Madrid
        next_cycle_madrid = madrid_time + timedelta(hours=1)
        print(f"\n⏳ Próximo ciclo bingX: {next_cycle_madrid.strftime('%H:%M %Z')}")
        
        return cycle_signals
    
    def format_for_bingx_telegram(self, signal):
        """Formatear señal específicamente para bingX demo"""
        
        symbol = signal['symbol']
        price = signal['current_price']
        final_signal = signal['final_signal']
        position = signal['total_position'] * 100
        market_regime = signal['market_regime']
        
        # Emojis
        signal_emoji = "🟢" if final_signal == 'BUY' else "🔴" if final_signal == 'SELL' else "🟡"
        
        # Recomendación para demo
        if final_signal in ['BUY', 'SELL'] and position > 20:
            recommendation = "🚀 EJECUTAR EN DEMO"
            action_emoji = "✅"
        elif final_signal in ['BUY', 'SELL'] and position > 10:
            recommendation = "⚡ CONSIDERAR EN DEMO"
            action_emoji = "⚠️"
        else:
            recommendation = "👀 OBSERVAR SOLO"
            action_emoji = "🔄"
        
        # Mensaje formateado específico para bingX
        message = f"""
{action_emoji} **SEÑAL BINGX DEMO - CICLO {self.cycle_count}**
🏦 **Exchange:** bingX (cuenta demo)
⏰ **Hora Madrid:** {signal['timestamp'].strftime('%Y-%m-%d %H:%M %Z')}
📊 **Símbolo:** {symbol}
💰 **Precio demo:** **${price:,.2f}**

📈 **SEÑAL:** {final_signal} {signal_emoji}
🎯 **POSICIÓN DEMO:** {position:.1f}% del capital ($10)
🔐 **CONFIANZA:** {max(signal['safe_signal']['confidence'], signal['growth_signal']['confidence'])*100:.0f}%

🛡️  **MODO SEGURO:** {signal['safe_signal']['position_pct']*100:.1f}% ({signal['safe_signal']['signal']})
⚡  **MODO CRECIMIENTO:** {signal['growth_signal']['position_pct']*100:.1f}% ({signal['growth_signal']['signal']})

📊 **RÉGIMEN:** {market_regime} ({signal['risk_level']*100:.0f}% riesgo)
📉 **STOP LOSS:** 5% (${signal['stop_loss_price']:,.2f})
📈 **TAKE PROFIT:** 10% (${signal['take_profit_price']:,.2f})

{action_emoji} **RECOMENDACIÓN DEMO:** {recommendation}
🆔 **ID:** {signal['signal_id']}

💡 **INSTRUCCIONES PARA BINGX DEMO:**
1. Abrir bingX en modo demo/sandbox
2. Buscar símbolo: {symbol}
3. {f'COMPRAR {position/100*10:.2f} USDT de {symbol}' if final_signal == 'BUY' else f'VENDER {position/100*10:.2f} USDT de {symbol}' if final_signal == 'SELL' else 'NO OPERAR'}
4. Configurar stop loss: 5% (${signal['stop_loss_price']:,.2f})
5. Configurar take profit: 10% (${signal['take_profit_price']:,.2f})
6. Reportar resultado para aprendizaje

❓ **¿EJECUTA EN BINGX DEMO?** (Sí/No/Solo observar)
"""
        
        return message
    
    def run_demo_test(self, cycles=2):
        """Ejecutar prueba demo rápida"""
        
        print(f"\n🧪 PRUEBA BINGX DEMO ({cycles} ciclos)")
        print(f"   Intervalo simulado: 30 segundos")
        print(f"{'='*60}")
        
        for i in range(cycles):
            print(f"\n🔄 CICLO {i+1}/{cycles}")
            signals = self.generate_hourly_signals_bingx()
            
            if i < cycles - 1:
                print(f"\n⏳ Esperando 30 segundos...")
                time.sleep(30)
        
        # Estadísticas finales
        print(f"\n{'='*60}")
        print("📊 ESTADÍSTICAS BINGX DEMO")
        print(f"{'='*60}")
        
        if self.signals_history:
            total = len(self.signals_history)
            buy_count = sum(1 for s in self.signals_history if s['final_signal'] == 'BUY')
            sell_count = sum(1 for s in self.signals_history if s['final_signal'] == 'SELL')
            hold_count = sum(1 for s in self.signals_history if s['final_signal'] == 'HOLD')
            
            active_percentage = ((buy_count + sell_count) / total) * 100
            
            print(f"   Total señales: {total}")
            print(f"   BUY: {buy_count} ({buy_count/total*100:.1f}%)")
            print(f"   SELL: {sell_count} ({sell_count/total*100:.1f}%)")
            print(f"   HOLD: {hold_count} ({hold_count/total*100:.1f}%)")
            print(f"   🔥 Señales activas: {active_percentage:.1f}%")
            
            print(f"\n✅ SISTEMA BINGX LISTO PARA PRODUCCIÓN")
            print(f"   Horario: {self.local_tz}")
            print(f"   Formato: {self.symbol_format}")
            print(f"   Capital demo: $10 USDT")
            print(f"   Objetivo: Aprendizaje con 0 riesgo")

def main():
    """Función principal"""
    
    print(f"\n🚀 INICIANDO SISTEMA BINGX TELEGRAM")
    
    try:
        # Preguntar formato de símbolos (en producción sería parámetro)
        symbol_format = 'BTCUSDT'  # Por defecto, ajustar según bingX
        
        # Crear sistema bingX
        system = BingXTelegramSystem(symbol_format=symbol_format)
        
        # Ejecutar prueba demo
        print(f"\n🧪 EJECUTANDO PRUEBA DEMO (2 ciclos)...")
        system.run_demo_test(cycles=2)
        
        print(f"\n🎯 SISTEMA BINGX COMPLETAMENTE LISTO")
        print(f"1. ✅ Horario Madrid configurado")
        print(f"2. ✅ Formato bingX: {symbol_format}")
        print(f"3. ✅ Sistema agresivo integrado")
        print(f"4. ✅ Mensajes Telegram específicos")
        print(f"5. ⏳ Esperando confirmación usuario")
        
        print(f"\n📋 INSTRUCCIONES FINALES:")
        print(f"1. Usuario: Depositar $10 USDT virtuales en bingX demo")
        print(f"2. Usuario: Decir 'LISTO BINGX' para comenzar")
        print(f"3. Asistente: Iniciar señales cada 1 hora (horario Madrid)")
        print(f"4. Usuario: Ejecutar manualmente en bingX demo")
        print(f"5. Ambos: Aprender de resultados demo")
        
        return system
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    system = main()
    
    if system:
        print(f"\n🏦 SISTEMA BINGX DEMO LISTO")
        print(f"   Exchange: bingX (demo)")
        print(f"   Horario: Madrid (CET)")
        print(f"   Capital: $10 virtuales")
        print(f"   Objetivo: Aprendizaje con 0 riesgo")
    else:
        print(f"\n❌ SISTEMA BINGX FALLÓ")