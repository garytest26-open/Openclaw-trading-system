"""
HISTORICAL_BACKTEST.py - Backtesting histórico del sistema dual ajustado
30 días de datos reales para validación
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

print("📊 BACKTESTING HISTÓRICO - SISTEMA DUAL AJUSTADO")
print("=" * 60)
print("Período: 30 días históricos")
print("Símbolos: BTC-USD, ETH-USD")
print("Frecuencia: Horaria")
print("=" * 60)

class HistoricalBacktester:
    """Backtesting histórico del sistema dual ajustado"""
    
    def __init__(self):
        self.initial_capital = 10000
        self.capital = self.initial_capital
        self.positions = {}
        self.trade_history = []
        self.signals_history = []
        
        # Parámetros del sistema (simplificado para backtesting)
        self.safe_mode_allocation = 0.70
        self.growth_mode_allocation = 0.30
        
    def download_historical_data(self, symbol, days=30):
        """Descargar datos históricos"""
        print(f"📥 Descargando datos históricos para {symbol}...")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start_date, end=end_date, interval='1h')
            
            if df.empty:
                print(f"⚠️  No hay datos para {symbol}")
                return None
            
            print(f"   ✅ {len(df)} registros descargados")
            print(f"   📅 Período: {df.index[0]} a {df.index[-1]}")
            
            return df
            
        except Exception as e:
            print(f"❌ Error descargando {symbol}: {e}")
            return None
    
    def simulate_system_signal(self, df, current_index):
        """Simular señal del sistema dual ajustado en punto histórico"""
        if current_index < 50:  # Necesitamos datos suficientes
            return "HOLD", 0.0
        
        # Tomar datos hasta el punto actual (no futuro)
        current_df = df.iloc[:current_index+1].copy()
        
        # Simular indicadores del sistema ajustado
        signals = self.calculate_historical_signals(current_df)
        
        # Contar señales (simplificado)
        buy_signals = sum(1 for s in signals.values() if s == "BUY")
        sell_signals = sum(1 for s in signals.values() if s == "SELL")
        
        # Determinar señal (lógica simplificada del sistema ajustado)
        if sell_signals >= 2:
            return "SELL", 0.114  # 11.4% posición (como en paper trading)
        elif buy_signals >= 2:
            return "BUY", 0.114
        else:
            return "HOLD", 0.0
    
    def calculate_historical_signals(self, df):
        """Calcular señales históricas (simulación del sistema ajustado)"""
        signals = {}
        
        try:
            # RSI signal (ajustado)
            if len(df) >= 14:
                delta = df['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs))
                current_rsi = rsi.iloc[-1]
                
                if current_rsi < 35:
                    signals['rsi'] = "BUY"
                elif current_rsi > 65:
                    signals['rsi'] = "SELL"
                else:
                    signals['rsi'] = "HOLD"
            else:
                signals['rsi'] = "HOLD"
            
            # Trend signal (ajustado)
            if len(df) >= 30:
                sma_10 = df['Close'].rolling(10).mean()
                sma_30 = df['Close'].rolling(30).mean()
                
                if sma_10.iloc[-1] > sma_30.iloc[-1]:
                    signals['trend'] = "BUY"
                elif sma_10.iloc[-1] < sma_30.iloc[-1]:
                    signals['trend'] = "SELL"
                else:
                    signals['trend'] = "HOLD"
            else:
                signals['trend'] = "HOLD"
            
            # Volume signal (ajustado)
            if len(df) >= 10:
                volume_sma = df['Volume'].rolling(10).mean()
                current_volume = df['Volume'].iloc[-1]
                volume_ratio = current_volume / volume_sma.iloc[-1]
                
                price_change = (df['Close'].iloc[-1] / df['Close'].iloc[-2] - 1) * 100
                
                if volume_ratio > 1.3 and price_change > 0.5:
                    signals['volume'] = "BUY"
                elif volume_ratio > 1.3 and price_change < -0.5:
                    signals['volume'] = "SELL"
                else:
                    signals['volume'] = "HOLD"
            else:
                signals['volume'] = "HOLD"
            
            # Momentum signal
            if len(df) >= 6:
                momentum_5 = (df['Close'].iloc[-1] / df['Close'].iloc[-6] - 1) * 100
                
                if momentum_5 > 2:
                    signals['momentum'] = "BUY"
                elif momentum_5 < -2:
                    signals['momentum'] = "SELL"
                else:
                    signals['momentum'] = "HOLD"
            else:
                signals['momentum'] = "HOLD"
            
            return signals
            
        except Exception as e:
            print(f"⚠️  Error calculando señales: {e}")
            return {'rsi': 'HOLD', 'trend': 'HOLD', 'volume': 'HOLD', 'momentum': 'HOLD'}
    
    def run_backtest(self, symbol):
        """Ejecutar backtesting para un símbolo"""
        print(f"\n🔍 BACKTESTING {symbol}:")
        print("-" * 50)
        
        # Descargar datos
        df = self.download_historical_data(symbol, days=30)
        
        if df is None or len(df) < 100:
            print(f"❌ Datos insuficientes para {symbol}")
            return None
        
        # Inicializar tracking
        capital = self.initial_capital
        positions = 0
        trades = []
        signals_count = {'BUY': 0, 'SELL': 0, 'HOLD': 0}
        
        print(f"📈 Ejecutando backtesting en {len(df)} puntos de datos...")
        
        # Simular cada punto en el tiempo
        for i in range(50, len(df)):  # Empezar después de tener datos suficientes
            current_price = df['Close'].iloc[i]
            current_time = df.index[i]
            
            # Obtener señal del sistema
            signal, position_size = self.simulate_system_signal(df, i)
            
            # Contar señales
            signals_count[signal] += 1
            
            # Simular trade si señal activa
            if signal != "HOLD" and position_size > 0:
                trade_value = capital * position_size
                
                if signal == "BUY" and capital >= trade_value:
                    # Simular compra
                    shares = trade_value / current_price
                    capital -= trade_value
                    positions += shares
                    
                    trades.append({
                        'time': current_time,
                        'action': 'BUY',
                        'price': current_price,
                        'shares': shares,
                        'value': trade_value
                    })
                    
                elif signal == "SELL" and positions > 0:
                    # Simular venta
                    sell_value = positions * current_price
                    capital += sell_value
                    
                    # Calcular P&L
                    if trades and trades[-1]['action'] == 'BUY':
                        buy_trade = trades[-1]
                        pnl = (current_price - buy_trade['price']) * buy_trade['shares']
                        pnl_pct = (current_price / buy_trade['price'] - 1) * 100
                    else:
                        pnl = 0
                        pnl_pct = 0
                    
                    trades.append({
                        'time': current_time,
                        'action': 'SELL',
                        'price': current_price,
                        'shares': positions,
                        'value': sell_value,
                        'pnl': pnl,
                        'pnl_pct': pnl_pct
                    })
                    
                    positions = 0
        
        # Valor final (incluir posiciones abiertas)
        final_value = capital + (positions * df['Close'].iloc[-1] if positions > 0 else 0)
        total_return = ((final_value / self.initial_capital) - 1) * 100
        
        # Calcular métricas
        total_trades = len([t for t in trades if t['action'] in ['BUY', 'SELL']])
        profitable_trades = len([t for t in trades if t.get('pnl', 0) > 0])
        total_pnl = sum(t.get('pnl', 0) for t in trades)
        
        # Reporte
        print(f"\n📊 RESULTADOS BACKTEST {symbol}:")
        print(f"   Capital inicial: ${self.initial_capital:,.2f}")
        print(f"   Valor final: ${final_value:,.2f}")
        print(f"   Retorno total: {total_return:.2f}%")
        print(f"   Señales generadas: {sum(signals_count.values())}")
        print(f"     BUY: {signals_count['BUY']} ({signals_count['BUY']/sum(signals_count.values())*100:.1f}%)")
        print(f"     SELL: {signals_count['SELL']} ({signals_count['SELL']/sum(signals_count.values())*100:.1f}%)")
        print(f"     HOLD: {signals_count['HOLD']} ({signals_count['HOLD']/sum(signals_count.values())*100:.1f}%)")
        print(f"   Trades ejecutados: {total_trades}")
        print(f"   Trades rentables: {profitable_trades} ({profitable_trades/max(total_trades,1)*100:.1f}%)")
        print(f"   P&L total: ${total_pnl:,.2f}")
        
        return {
            'symbol': symbol,
            'initial_capital': self.initial_capital,
            'final_value': final_value,
            'total_return': total_return,
            'signals_count': signals_count,
            'total_trades': total_trades,
            'profitable_trades': profitable_trades,
            'total_pnl': total_pnl,
            'trades': trades
        }
    
    def run_comparative_backtest(self):
        """Ejecutar backtesting comparativo para BTC y ETH"""
        print("\n📈 BACKTESTING COMPARATIVO 30 DÍAS")
        print("=" * 60)
        
        results = {}
        
        for symbol in ['BTC-USD', 'ETH-USD']:
            result = self.run_backtest(symbol)
            if result:
                results[symbol] = result
        
        # Análisis comparativo
        if len(results) == 2:
            print("\n" + "=" * 60)
            print("📊 ANÁLISIS COMPARATIVO")
            print("=" * 60)
            
            for symbol, result in results.items():
                print(f"\n{symbol}:")
                print(f"   Retorno: {result['total_return']:.2f}%")
                print(f"   Señales BUY: {result['signals_count']['BUY']}")
                print(f"   Señales SELL: {result['signals_count']['SELL']}")
                print(f"   Trades rentables: {result['profitable_trades']}/{result['total_trades']}")
            
            # Evaluación general
            avg_return = np.mean([r['total_return'] for r in results.values()])
            total_signals = sum(sum(r['signals_count'].values()) for r in results.values())
            buy_signals = sum(r['signals_count']['BUY'] for r in results.values())
            sell_signals = sum(r['signals_count']['SELL'] for r in results.values())
            
            print(f"\n📈 RESUMEN GENERAL:")
            print(f"   Retorno promedio: {avg_return:.2f}%")
            print(f"   Total señales: {total_signals}")
            print(f"   BUY/SELL ratio: {buy_signals}/{sell_signals} ({buy_signals/max(sell_signals,1):.2f})")
            print(f"   % señales activas: {(buy_signals+sell_signals)/total_signals*100:.1f}%")
            
            # Recomendación basada en backtesting
            print(f"\n💡 RECOMENDACIÓN BASADA EN BACKTESTING:")
            if avg_return > 5:
                print("  ✅ EXCELENTE - Sistema muestra retornos positivos consistentes")
                print("     Listo para deployment inmediato")
            elif avg_return > 0:
                print("  ⚠️  POSITIVO - Sistema preserva/crece capital")
                print("     Considerar deployment con capital controlado")
            elif avg_return > -2:
                print("  🔄 NEUTRAL - Sistema preserva capital con pequeñas pérdidas")
                print("     Necesita ajustes antes de deployment")
            else:
                print("  ❌ MEJORABLE - Sistema muestra pérdidas")
                print("     Requiere ajustes significativos")
        
        return results

def main():
    """Función principal"""
    print("\n🧪 EJECUTANDO BACKTESTING HISTÓRICO COMPLETO")
    print("=" * 60)
    
    try:
        backtester = HistoricalBacktester()
        results = backtester.run_comparative_backtest()
        
        print("\n" + "=" * 60)
        print("🎯 BACKTESTING COMPLETADO")
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
        print(f"\n✅ BACKTESTING HISTÓRICO COMPLETADO EXITOSAMENTE")
    else:
        print(f"\n❌ FALLÓ: {result.get('error', 'Unknown')}")