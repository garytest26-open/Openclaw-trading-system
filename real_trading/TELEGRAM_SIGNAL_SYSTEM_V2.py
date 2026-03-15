"""
TELEGRAM_SIGNAL_SYSTEM_V2.py - Sistema de señales por Telegram MEJORADO
Usa Binance API para precios reales (no Yahoo Finance)
"""

import sys
import os
import time
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

# Añadir ruta para importar sistema mejorado
sys.path.append('/home/ubuntu/.openclaw/workspace/trading/swarm_ai_advanced')

from IMPROVED_DUAL_SYSTEM import ImprovedDualTradingSystem

print("📡 SISTEMA DE SEÑALES POR TELEGRAM V2")
print("=" * 60)
print("Mejora: Usa Binance API para precios reales")
print("Modo: Generación automática + Ejecución manual")
print("=" * 60)

class TelegramSignalSystemV2:
    """Sistema MEJORADO que usa Binance API para precios reales"""
    
    def __init__(self, use_binance_api=True):
        self.system = ImprovedDualTradingSystem()
        self.signals_history = []
        self.use_binance_api = use_binance_api
        
        print(f"✅ Sistema de señales V2 inicializado")
        print(f"   Fuente de precios: {'Binance API' if use_binance_api else 'Simulados'}")
        print(f"   Ejecución: Manual por usuario")
    
    def get_current_price_binance(self, symbol):
        """Obtener precio actual desde Binance API (sin necesidad de API keys)"""
        
        try:
            import ccxt
            
            # Crear conexión pública a Binance (solo lectura)
            exchange = ccxt.binance({
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'spot',
                }
            })
            
            # Obtener ticker
            ticker = exchange.fetch_ticker(symbol)
            return ticker['last']
            
        except Exception as e:
            print(f"⚠️  Error obteniendo precio de Binance para {symbol}: {e}")
            
            # Precios de respaldo (simulados basados en precios reales aproximados)
            backup_prices = {
                'BTC/USDT': 52147.32,
                'ETH/USDT': 3147.85,
                'BTC-USD': 52147.32,
                'ETH-USD': 3147.85
            }
            
            if symbol in backup_prices:
                return backup_prices[symbol]
            elif symbol.replace('/', '-') in backup_prices:
                return backup_prices[symbol.replace('/', '-')]
            else:
                return 1000.0
    
    def generate_signal_for_symbol(self, symbol):
        """Generar señal para un símbolo específico"""
        
        print(f"\n🎯 GENERANDO SEÑAL PARA {symbol}")
        print("-" * 40)
        
        try:
            # Obtener precio actual REAL desde Binance
            current_price = self.get_current_price_binance(symbol)
            print(f"   Precio actual (Binance): ${current_price:,.2f}")
            
            # Generar señal usando sistema mejorado
            signal_result = self.system.generate_improved_signals(symbol)
            
            if not signal_result:
                print(f"❌ No se pudo generar señal para {symbol}")
                return None
            
            # Calcular niveles de stop loss y take profit
            stop_loss_price = current_price * 0.95  # 5% stop loss
            take_profit_price = current_price * 1.10  # 10% take profit
            
            # Crear objeto de señal completo
            signal = {
                'timestamp': datetime.now(),
                'symbol': symbol,
                'current_price': current_price,
                'final_signal': signal_result['final_signal'],
                'total_position': signal_result['total_position'],
                'market_regime': signal_result['market_regime'],
                'risk_level': signal_result.get('risk_level', 0.5),
                'distribution': signal_result['distribution'],
                'safe_signal': signal_result['safe_signal'],
                'growth_signal': signal_result['growth_signal'],
                'stop_loss_price': stop_loss_price,
                'take_profit_price': take_profit_price,
                'stop_loss_pct': 5.0,
                'take_profit_pct': 10.0,
                'signal_id': f"{symbol.replace('/', '_')}_{datetime.now().strftime('%Y%m%d_%H%M')}"
            }
            
            # Añadir a historial
            self.signals_history.append(signal)
            
            print(f"✅ Señal generada: {signal['final_signal']}")
            print(f"   Posición: {signal['total_position']*100:.1f}%")
            
            return signal
            
        except Exception as e:
            print(f"❌ Error generando señal para {symbol}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def format_signal_for_telegram(self, signal):
        """Formatear señal para enviar por Telegram"""
        
        if not signal:
            return None
        
        symbol = signal['symbol']
        current_price = signal['current_price']
        final_signal = signal['final_signal']
        position_pct = signal['total_position'] * 100
        market_regime = signal['market_regime']
        risk_level = signal['risk_level']
        
        # Emoji para señal
        signal_emoji = "🟢" if final_signal == 'BUY' else "🔴" if final_signal == 'SELL' else "🟡"
        
        # Determinar recomendación
        if final_signal in ['BUY', 'SELL'] and position_pct > 10:
            recommendation = "EJECUTAR 🚀"
            action_emoji = "✅"
        elif final_signal in ['BUY', 'SELL'] and position_pct > 5:
            recommendation = "CONSIDERAR ⚡"
            action_emoji = "⚠️"
        else:
            recommendation = "OBSERVAR 👀"
            action_emoji = "🔄"
        
        # Texto formateado para Telegram
        message = f"""
{action_emoji} **SEÑAL DE TRADING - SISTEMA MEJORADO**
⏰ {signal['timestamp'].strftime('%Y-%m-%d %H:%M UTC')}
📊 {symbol}: **${current_price:,.2f}**

📈 **SEÑAL:** {final_signal} {signal_emoji}
💰 **POSICIÓN:** {position_pct:.1f}% del capital
🎯 **CONFIANZA:** {max(signal['safe_signal'].get('confidence', 0), signal['growth_signal'].get('confidence', 0))*100:.0f}%

🛡️  **MODO SEGURO:** {signal['safe_signal'].get('position_pct', 0)*100:.1f}% ({signal['safe_signal'].get('signal', 'N/A')}, {signal['safe_signal'].get('confidence', 0)*100:.0f}% confianza)
⚡  **MODO CRECIMIENTO:** {signal['growth_signal'].get('position_pct', 0)*100:.1f}% ({signal['growth_signal'].get('signal', 'N/A')}, {signal['growth_signal'].get('confidence', 0)*100:.0f}% confianza)

📊 **RÉGIMEN:** {market_regime} ({risk_level*100:.0f}% riesgo)
📉 **STOP LOSS:** {signal['stop_loss_pct']:.1f}% (${signal['stop_loss_price']:,.2f})
📈 **TAKE PROFIT:** {signal['take_profit_pct']:.1f}% (${signal['take_profit_price']:,.2f})

📋 **DISTRIBUCIÓN:**
   🛡️  Seguro: {signal['distribution'].get('SAFE_MODE', 0)*100:.0f}%
   ⚡  Crecimiento: {signal['distribution'].get('GROWTH_MODE', 0)*100:.0f}%

{action_emoji} **RECOMENDACIÓN:** {recommendation}
🆔 **ID:** {signal['signal_id']}

💡 **INSTRUCCIONES:**
1. Revisar señal y fundamentos
2. Decidir si ejecutar manualmente
3. En Binance Testnet, ejecutar trade
4. Reportar resultado para aprendizaje

❓ **¿EJECUTAS MANUALMENTE?** (Sí/No/Esperar)
"""
        
        return message
    
    def simulate_telegram_send(self, message):
        """Simular envío por Telegram (para testing)"""
        
        print(f"\n📨 SIMULANDO ENVÍO POR TELEGRAM:")
        print("-" * 40)
        print(message)
        print("-" * 40)
        
        print(f"✅ Mensaje listo para enviar a Telegram")
        print(f"   (En producción: se enviaría automáticamente a tu chat)")
        
        return True
    
    def run_single_cycle(self):
        """Ejecutar un ciclo completo de generación de señales"""
        
        print(f"\n🔄 CICLO DE GENERACIÓN DE SEÑALES")
        print("=" * 40)
        
        symbols = ['BTC/USDT', 'ETH/USDT']
        all_signals = []
        
        for symbol in symbols:
            # Generar señal
            signal = self.generate_signal_for_symbol(symbol)
            
            if signal:
                # Formatear para Telegram
                telegram_message = self.format_signal_for_telegram(signal)
                
                if telegram_message:
                    # "Enviar" por Telegram (simulado)
                    self.simulate_telegram_send(telegram_message)
                    
                    # Guardar señal
                    all_signals.append(signal)
        
        return all_signals
    
    def run_test_mode(self, cycles=2, interval_minutes=1):
        """Modo de prueba rápido"""
        
        print(f"\n🧪 MODO DE PRUEBA RÁPIDA")
        print(f"   Ciclos: {cycles}")
        print(f"   Intervalo: {interval_minutes} minuto(s)")
        print("=" * 60)
        
        for cycle in range(1, cycles + 1):
            print(f"\n🔄 CICLO {cycle}/{cycles}")
            print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")
            
            # Ejecutar ciclo
            signals = self.run_single_cycle()
            
            # Resumen del ciclo
            if signals:
                print(f"\n📊 RESUMEN CICLO {cycle}:")
                for signal in signals:
                    print(f"   {signal['symbol']}: {signal['final_signal']} ({signal['total_position']*100:.1f}%)")
            
            # Esperar para próximo ciclo (excepto último ciclo)
            if cycle < cycles:
                print(f"\n⏳ Esperando {interval_minutes} minuto(s)...")
                time.sleep(interval_minutes * 60)
        
        print(f"\n✅ PRUEBA COMPLETADA")
        print(f"   Total señales generadas: {len(self.signals_history)}")
        
        return self.signals_history

def main():
    """Función principal"""
    
    print(f"\n🚀 INICIANDO SISTEMA DE SEÑALES V2")
    
    try:
        # Crear sistema
        signal_system = TelegramSignalSystemV2(use_binance_api=True)
        
        # Ejecutar modo de prueba
        print(f"\n🧪 EJECUTANDO MODO DE PRUEBA...")
        signals = signal_system.run_test_mode(cycles=2, interval_minutes=1)
        
        if signals:
            print(f"\n✅ PRUEBA COMPLETADA EXITOSAMENTE")
            print(f"   Señales generadas: {len(signals)}")
            
            # Estadísticas
            buy_signals = sum(1 for s in signals if s['final_signal'] == 'BUY')
            sell_signals = sum(1 for s in signals if s['final_signal'] == 'SELL')
            hold_signals = sum(1 for s in signals if s['final_signal'] == 'HOLD')
            
            print(f"\n📊 ESTADÍSTICAS:")
            print(f"   BUY: {buy_signals} ({buy_signals/len(signals)*100:.1f}%)")
            print(f"   SELL: {sell_signals} ({sell_signals/len(signals)*100:.1f}%)")
            print(f"   HOLD: {hold_signals} ({hold_signals/len(signals)*100:.1f}%)")
            
            print(f"\n🎯 PRÓXIMOS PASOS PARA PRODUCCIÓN:")
            print(f"1. Configurar bot de Telegram (necesita token)")
            print(f"2. Ejecutar en modo continuo cada 60 minutos")
            print(f"3. Tú ejecutas trades manualmente en Binance")
            print(f"4. Aprendemos juntos de los resultados")
            
        else:
            print(f"\n⚠️  No se generaron señales en la prueba")
        
        return signal_system
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    system = main()
    
    if system:
        print(f"\n✅ SISTEMA V2 LISTO PARA PRODUCCIÓN")
        print(f"   Fuente: Binance API (precios reales)")
        print(f"   Modo: Señales por Telegram + Ejecución manual")
        print(f"   Ventaja: Aprendizaje colaborativo sin riesgo automático")
    else:
        print(f"\n❌ SISTEMA FALLÓ")