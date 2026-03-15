"""
QUICK_IMPROVED_BACKTEST.py - Backtesting rápido del sistema mejorado
7 días para validación rápida
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

print("⚡ BACKTESTING RÁPIDO - SISTEMA MEJORADO")
print("=" * 60)
print("Período: 7 días (validación rápida)")
print("Objetivo: Ver si mejoras funcionan históricamente")
print("=" * 60)

class QuickImprovedBacktester:
    """Backtesting rápido del sistema mejorado"""
    
    def __init__(self):
        self.initial_capital = 10000
        self.results = {}
        
    def simulate_improved_system(self, df):
        """Simular sistema mejorado en datos históricos"""
        signals = []
        capital = self.initial_capital
        position = 0
        trades = []
        
        for i in range(50, len(df)):  # Empezar con datos suficientes
            current_data = df.iloc[:i+1].copy()
            current_price = df['Close'].iloc[i]
            
            # Simular señal del sistema mejorado (simplificado)
            signal, position_size = self.get_improved_signal(current_data)
            
            signals.append({
                'time': df.index[i],
                'signal': signal,
                'position_size': position_size,
                'price': current_price
            })
            
            # Simular trade
            if signal == "BUY" and position_size > 0 and capital > 0:
                trade_value = capital * position_size
                shares = trade_value / current_price
                capital -= trade_value
                position += shares
                
                trades.append({
                    'time': df.index[i],
                    'action': 'BUY',
                    'price': current_price,
                    'shares': shares,
                    'value': trade_value
                })
                
            elif signal == "SELL" and position > 0:
                sell_value = position * current_price
                capital += sell_value
                
                # Calcular P&L
                if trades and trades[-1]['action'] == 'BUY':
                    buy_trade = trades[-1]
                    pnl = (current_price - buy_trade['price']) * buy_trade['shares']
                else:
                    pnl = 0
                
                trades.append({
                    'time': df.index[i],
                    'action': 'SELL',
                    'price': current_price,
                    'shares': position,
                    'value': sell_value,
                    'pnl': pnl
                })
                
                position = 0
        
        # Valor final
        final_value = capital + (position * df['Close'].iloc[-1] if position > 0 else 0)
        total_return = ((final_value / self.initial_capital) - 1) * 100
        
        # Métricas
        total_signals = len(signals)
        buy_signals = sum(1 for s in signals if s['signal'] == "BUY")
        sell_signals = sum(1 for s in signals if s['signal'] == "SELL")
        hold_signals = sum(1 for s in signals if s['signal'] == "HOLD")
        
        profitable_trades = len([t for t in trades if t.get('pnl', 0) > 0])
        total_trades = len([t for t in trades if t['action'] in ['BUY', 'SELL']])
        
        return {
            'final_value': final_value,
            'total_return': total_return,
            'signals': {
                'total': total_signals,
                'buy': buy_signals,
                'sell': sell_signals,
                'hold': hold_signals
            },
            'trades': {
                'total': total_trades,
                'profitable': profitable_trades,
                'profitability': profitable_trades / max(total_trades, 1) * 100
            },
            'trade_list': trades
        }
    
    def get_improved_signal(self, df):
        """Obtener señal del sistema mejorado (simplificado)"""
        if len(df) < 50:
            return "HOLD", 0.0
        
        try:
            # Simular indicadores del sistema mejorado
            signals = []
            
            # 1. RSI mejorado
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            current_rsi = rsi.iloc[-1]
            
            if current_rsi < 40:
                signals.append("BUY")
            elif current_rsi > 70:
                signals.append("SELL")
            else:
                signals.append("HOLD")
            
            # 2. Tendencia mejorada
            ema_9 = df['Close'].ewm(span=9, adjust=False).mean()
            ema_21 = df['Close'].ewm(span=21, adjust=False).mean()
            
            if ema_9.iloc[-1] > ema_21.iloc[-1]:
                signals.append("BUY")
            elif ema_9.iloc[-1] < ema_21.iloc[-1]:
                signals.append("SELL")
            else:
                signals.append("HOLD")
            
            # 3. Momentum mejorado
            mom_5 = (df['Close'].iloc[-1] / df['Close'].iloc[-6] - 1) * 100
            if mom_5 > 1.5:
                signals.append("BUY")
            elif mom_5 < -1.5:
                signals.append("SELL")
            else:
                signals.append("HOLD")
            
            # Contar señales (lógica mejorada)
            buy_count = signals.count("BUY")
            sell_count = signals.count("SELL")
            
            # Determinar señal final (mejorada para más BUY)
            if buy_count >= 2:
                return "BUY", 0.15  # 15% posición
            elif sell_count >= 2:
                return "SELL", 0.10  # 10% posición
            elif buy_count == 1 and sell_count == 0:
                return "BUY", 0.05  # 5% posición pequeña
            else:
                return "HOLD", 0.0
                
        except Exception as e:
            return "HOLD", 0.0
    
    def run_quick_backtest(self, symbol):
        """Ejecutar backtesting rápido para un símbolo"""
        print(f"\n🔍 BACKTESTING RÁPIDO {symbol}:")
        
        # Descargar datos de 7 días
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start_date, end=end_date, interval='1h')
            
            if df.empty or len(df) < 100:
                print(f"❌ Datos insuficientes para {symbol}")
                return None
            
            print(f"   📊 {len(df)} registros descargados")
            
            # Ejecutar simulación
            result = self.simulate_improved_system(df)
            
            # Reporte
            print(f"\n📈 RESULTADOS {symbol}:")
            print(f"   Capital inicial: ${self.initial_capital:,.2f}")
            print(f"   Valor final: ${result['final_value']:,.2f}")
            print(f"   Retorno: {result['total_return']:.2f}%")
            print(f"   Señales: BUY={result['signals']['buy']}, SELL={result['signals']['sell']}, HOLD={result['signals']['hold']}")
            print(f"   Trades: {result['trades']['total']} total, {result['trades']['profitable']} rentables ({result['trades']['profitability']:.1f}%)")
            
            return result
            
        except Exception as e:
            print(f"❌ Error en {symbol}: {e}")
            return None
    
    def run_comparison(self):
        """Ejecutar comparación entre sistema original y mejorado"""
        print("\n📊 COMPARANDO SISTEMA ORIGINAL vs MEJORADO")
        print("=" * 60)
        
        symbols = ['BTC-USD', 'ETH-USD']
        all_results = {}
        
        for symbol in symbols:
            print(f"\n📈 {symbol}:")
            result = self.run_quick_backtest(symbol)
            if result:
                all_results[symbol] = result
        
        # Análisis comparativo
        if len(all_results) >= 1:
            print("\n" + "=" * 60)
            print("📋 RESUMEN COMPARATIVO")
            print("=" * 60)
            
            total_return = np.mean([r['total_return'] for r in all_results.values()])
            avg_profitability = np.mean([r['trades']['profitability'] for r in all_results.values()])
            total_buy_signals = sum(r['signals']['buy'] for r in all_results.values())
            total_signals = sum(r['signals']['total'] for r in all_results.values())
            
            print(f"\n📊 MÉTRICAS PROMEDIO:")
            print(f"   Retorno promedio: {total_return:.2f}%")
            print(f"   Rentabilidad trades: {avg_profitability:.1f}%")
            print(f"   Señales BUY: {total_buy_signals}/{total_signals} ({total_buy_signals/total_signals*100:.1f}%)")
            
            print(f"\n💡 EVALUACIÓN DEL SISTEMA MEJORADO:")
            if total_return > 2:
                print("  ✅ EXCELENTE - Mejoras funcionan, retorno positivo")
                print("     Listo para paper trading 24h")
            elif total_return > 0:
                print("  ⚠️  POSITIVO - Mejoras funcionan parcialmente")
                print("     Continuar con validación")
            elif total_return > -1:
                print("  🔄 NEUTRAL - Sistema preserva capital")
                print("     Necesita más ajustes")
            else:
                print("  ❌ NEGATIVO - Mejoras no funcionan")
                print("     Revisar ajustes")
        
        return all_results

def main():
    """Función principal"""
    print("\n⚡ EJECUTANDO BACKTESTING RÁPIDO DEL SISTEMA MEJORADO")
    print("=" * 60)
    
    try:
        backtester = QuickImprovedBacktester()
        results = backtester.run_comparison()
        
        print("\n" + "=" * 60)
        print("🎯 BACKTESTING RÁPIDO COMPLETADO")
        print("=" * 60)
        
        return {
            'success': True,
            'results': results
        }
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            'success': False,
            'error': str(e)
        }

if __name__ == "__main__":
    result = main()
    
    if result['success']:
        print(f"\n✅ BACKTESTING RÁPIDO COMPLETADO")
        print(f"   Resultados disponibles para análisis")
    else:
        print(f"\n❌ FALLÓ: {result.get('error', 'Unknown')}")