#!/usr/bin/env python3
"""
Signal monitoring and automatic Telegram sending system
Monitors market conditions and sends signals when conditions are optimal
"""

import os
import json
import time
import schedule
from datetime import datetime, timedelta
from signal_generator import SignalGenerator
import subprocess
import sys

class SignalMonitor:
    def __init__(self, test_mode=False):
        self.generator = SignalGenerator()
        self.test_mode = test_mode
        self.capital = 10000  # Default capital for position sizing
        self.signals_sent_today = 0
        self.max_signals_per_day = 3
        self.trading_hours = {
            "start": 8,   # 08:00 UTC
            "end": 20     # 20:00 UTC
        }
        
        # Load configuration
        self.load_config()
        
        # Create results directory
        os.makedirs('signal_results', exist_ok=True)
    
    def load_config(self):
        """Load monitoring configuration"""
        config_file = 'signal_monitor_config.json'
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config = json.load(f)
                self.capital = config.get('capital', 10000)
                self.max_signals_per_day = config.get('max_signals_per_day', 3)
                self.trading_hours = config.get('trading_hours', self.trading_hours)
        else:
            # Create default config
            config = {
                "capital": self.capital,
                "max_signals_per_day": self.max_signals_per_day,
                "trading_hours": self.trading_hours,
                "min_confidence": 0.70,
                "min_volume_ratio": 1.0,
                "max_volatility_pct": 4.0,
                "check_interval_minutes": 30
            }
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
    
    def is_trading_hours(self):
        """Check if current time is within trading hours"""
        current_hour = datetime.utcnow().hour
        return self.trading_hours["start"] <= current_hour < self.trading_hours["end"]
    
    def can_send_signal(self):
        """Check if we can send a new signal"""
        if not self.is_trading_hours():
            print(f"⏰ Fuera de horario de trading ({datetime.utcnow().hour}:00 UTC)")
            return False
        
        if self.signals_sent_today >= self.max_signals_per_day:
            print(f"📊 Límite diario alcanzado ({self.signals_sent_today}/{self.max_signals_per_day})")
            return False
        
        # Check last signal time
        history_file = 'signal_history.json'
        if os.path.exists(history_file):
            with open(history_file, 'r') as f:
                history = json.load(f)
            
            if history["signals"]:
                last_signal_time = datetime.fromisoformat(history["signals"][-1]['timestamp'])
                time_since_last = datetime.utcnow() - last_signal_time
                if time_since_last.total_seconds() < 7200:  # 2 hours minimum
                    print(f"⏳ Esperando... última señal hace {time_since_last.total_seconds()/3600:.1f} horas")
                    return False
        
        return True
    
    def generate_and_send_signal(self):
        """Generate a signal and prepare for sending"""
        if not self.can_send_signal():
            return None
        
        print(f"\n{'='*60}")
        print(f"🔍 BUSCANDO SEÑAL - {datetime.utcnow().strftime('%H:%M UTC')}")
        print(f"{'='*60}")
        
        # Try to generate signal (may return None if conditions not optimal)
        signal = self.generator.generate_signal(capital=self.capital)
        
        if signal:
            print(f"✅ SEÑAL GENERADA: {signal['signal_id']}")
            print(f"   Activo: {signal['asset']}")
            print(f"   Dirección: {signal['direction']}")
            print(f"   Confianza: {signal['confidence']*100:.0f}%")
            
            # Format for Telegram
            telegram_message = self.generator.format_signal_for_telegram(signal)
            
            # Save signal
            self.generator.save_signal_history(signal)
            
            # Save to file for sending
            signal_file = f"signal_results/{signal['signal_id']}.txt"
            with open(signal_file, 'w') as f:
                f.write(telegram_message)
            
            # Also save JSON version
            json_file = f"signal_results/{signal['signal_id']}.json"
            with open(json_file, 'w') as f:
                json.dump(signal, f, indent=2)
            
            self.signals_sent_today += 1
            
            print(f"\n💾 Señal guardada en:")
            print(f"   {signal_file}")
            print(f"   {json_file}")
            
            # Display the signal
            print(f"\n{'='*60}")
            print("📋 MENSAJE PARA TELEGRAM:")
            print(f"{'='*60}")
            print(telegram_message)
            print(f"{'='*60}")
            
            return signal
        else:
            print("⏸️  No se generó señal - condiciones no óptimas")
            return None
    
    def reset_daily_counter(self):
        """Reset daily signal counter (call at midnight UTC)"""
        self.signals_sent_today = 0
        print(f"\n🔄 Contador diario reiniciado a las 00:00 UTC")
    
    def run_once(self):
        """Run one check cycle"""
        signal = self.generate_and_send_signal()
        return signal
    
    def run_continuous(self, interval_minutes=30):
        """Run continuous monitoring"""
        print(f"\n{'='*60}")
        print("🚀 MONITOR DE SEÑALES INICIADO")
        print(f"{'='*60}")
        print(f"• Horario de trading: {self.trading_hours['start']}:00-{self.trading_hours['end']}:00 UTC")
        print(f"• Máximo señales/día: {self.max_signals_per_day}")
        print(f"• Intervalo de chequeo: {interval_minutes} minutos")
        print(f"• Capital base: ${self.capital:,}")
        print(f"{'='*60}")
        
        # Schedule daily reset at midnight UTC
        schedule.every().day.at("00:00").do(self.reset_daily_counter)
        
        # Schedule signal checks
        schedule.every(interval_minutes).minutes.do(self.generate_and_send_signal)
        
        print(f"\n⏰ Primer chequeo en 1 minuto...")
        time.sleep(60)
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            print(f"\n\n⏹️  Monitor detenido por usuario")
            self.generate_daily_report()

    def generate_daily_report(self):
        """Generate daily performance report"""
        history_file = 'signal_history.json'
        if not os.path.exists(history_file):
            print("📊 No hay historial de señales para reportar")
            return
        
        with open(history_file, 'r') as f:
            history = json.load(f)
        
        if not history["signals"]:
            print("📊 No hay señales en el historial")
            return
        
        # Filter today's signals
        today = datetime.utcnow().date()
        today_signals = []
        for signal in history["signals"]:
            signal_date = datetime.fromisoformat(signal['timestamp']).date()
            if signal_date == today:
                today_signals.append(signal)
        
        if not today_signals:
            print(f"📊 No hay señales hoy ({today})")
            return
        
        print(f"\n{'='*60}")
        print(f"📊 REPORTE DIARIO - {today}")
        print(f"{'='*60}")
        print(f"Señales generadas hoy: {len(today_signals)}")
        
        # Calculate statistics
        long_count = sum(1 for s in today_signals if s['direction'] == 'LONG')
        short_count = len(today_signals) - long_count
        
        avg_confidence = sum(s['confidence'] for s in today_signals) / len(today_signals)
        avg_rr = sum(s['risk_reward_ratio'] for s in today_signals) / len(today_signals)
        
        print(f"• LONG: {long_count} | SHORT: {short_count}")
        print(f"• Confianza promedio: {avg_confidence*100:.1f}%")
        print(f"• Risk/Reward promedio: 1:{avg_rr:.1f}")
        
        # Save report
        report = {
            "date": today.isoformat(),
            "total_signals": len(today_signals),
            "long_signals": long_count,
            "short_signals": short_count,
            "avg_confidence": round(avg_confidence, 3),
            "avg_risk_reward": round(avg_rr, 2),
            "signals": today_signals
        }
        
        report_file = f"signal_results/daily_report_{today}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n💾 Reporte guardado en: {report_file}")
        print(f"{'='*60}")

def main():
    """Main function with command line interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Monitor de señales de trading')
    parser.add_argument('--mode', choices=['once', 'continuous'], default='once',
                       help='Modo de operación: una vez o continuo')
    parser.add_argument('--interval', type=int, default=30,
                       help='Intervalo en minutos para modo continuo')
    parser.add_argument('--capital', type=float, default=10000,
                       help='Capital base para cálculo de posición')
    parser.add_argument('--test', action='store_true',
                       help='Modo prueba (no envía realmente)')
    
    args = parser.parse_args()
    
    # Create monitor
    monitor = SignalMonitor(test_mode=args.test)
    monitor.capital = args.capital
    
    if args.mode == 'once':
        print(f"\n🎯 GENERANDO UNA SEÑAL")
        print(f"   Capital: ${args.capital:,}")
        print(f"   Hora: {datetime.utcnow().strftime('%H:%M UTC')}")
        print()
        
        signal = monitor.run_once()
        
        if signal:
            print(f"\n✅ Señal {signal['signal_id']} generada exitosamente")
            print(f"   Copia el mensaje de arriba y envíalo por Telegram a FRAN")
        else:
            print(f"\n⏸️  No se generó señal en este momento")
    
    elif args.mode == 'continuous':
        print(f"\n🔄 INICIANDO MONITOR CONTINUO")
        print(f"   Intervalo: cada {args.interval} minutos")
        print(f"   Capital: ${args.capital:,}")
        print(f"   Modo prueba: {'SI' if args.test else 'NO'}")
        print()
        
        monitor.run_continuous(interval_minutes=args.interval)

if __name__ == "__main__":
    main()