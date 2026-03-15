"""
REVOLUTIONARY_BACKTEST.py - Backtest profesional del cerebro revolucionario
Test riguroso de performance en datos históricos
"""

import torch
import numpy as np
import pandas as pd
import yfinance as yf
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')

print("📊 BACKTEST REVOLUCIONARIO - INICIANDO")
print("=" * 60)

# Import brain
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from REVOLUTIONARY_BRAIN import RevolutionaryBrain, REVOLUTIONARY_CONFIG
from DATA_PIPELINE import calculate_features

class RevolutionaryBacktest:
    """
    Backtest profesional para el cerebro revolucionario
    """
    
    def __init__(self, symbols: List[str] = None, period: str = '1y'):
        self.symbols = symbols or ['BTC-USD', 'ETH-USD']
        self.period = period
        
        # Initialize brain
        print("🧠 Cargando cerebro revolucionario...")
        self.brain = RevolutionaryBrain(REVOLUTIONARY_CONFIG)
        
        # Load or create a simple trained brain for testing
        # For now, we'll use the untrained brain to show potential
        self.brain.eval()
        
        print(f"✅ Cerebro cargado para backtest")
        print(f"   Símbolos: {self.symbols}")
        print(f"   Período: {self.period}")
    
    def download_test_data(self) -> Dict[str, pd.DataFrame]:
        """
        Download data for backtesting
        """
        print("\n📥 Descargando datos para backtest...")
        
        data_dict = {}
        for symbol in self.symbols:
            print(f"   {symbol}...", end="")
            try:
                ticker = yf.Ticker(symbol)
                df = ticker.history(period=self.period, interval='1h')
                
                if not df.empty:
                    # Calculate features
                    df = calculate_features(df)
                    data_dict[symbol] = df
                    print(f" ✅ {len(df)} filas")
                else:
                    print(f" ❌ Sin datos")
                    
            except Exception as e:
                print(f" ❌ Error: {e}")
        
        return data_dict
    
    def prepare_sequences(self, df: pd.DataFrame, seq_length: int = 50) -> List[np.ndarray]:
        """
        Prepare sequences for brain prediction
        """
        if df.empty:
            return []
        
        # Get feature columns
        feature_cols = [col for col in df.columns if col not in ['Open', 'High', 'Low', 'Close', 'Volume']]
        
        if not feature_cols:
            return []
        
        data_array = df[feature_cols].values.astype(np.float32)
        
        sequences = []
        for i in range(seq_length, len(data_array)):
            sequence = data_array[i-seq_length:i]
            sequences.append(sequence)
        
        return sequences
    
    def run_backtest(self, data_dict: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """
        Run backtest on all symbols
        """
        print("\n🚀 EJECUTANDO BACKTEST REVOLUCIONARIO...")
        print("-" * 40)
        
        results = {}
        
        for symbol, df in data_dict.items():
            print(f"\n📈 {symbol}:")
            
            if df.empty:
                print("   ❌ Sin datos para backtest")
                continue
            
            # Prepare sequences
            sequences = self.prepare_sequences(df, seq_length=50)
            
            if not sequences:
                print("   ❌ No se pudieron crear secuencias")
                continue
            
            # Run predictions
            predictions = []
            signals = []
            confidences = []
            position_sizes = []
            
            print(f"   Procesando {len(sequences)} secuencias...")
            
            for i, sequence in enumerate(sequences):
                # Create multi-scale features
                seq_len = len(sequence)
                
                market_data = {
                    'short_term': sequence[-int(seq_len * 0.2):],
                    'medium_term': sequence[-int(seq_len * 0.5):],
                    'long_term': sequence
                }
                
                # Make prediction
                with torch.no_grad():
                    prediction = self.brain.predict_single(market_data)
                
                # Get trading signal
                signal, strength = self.brain.get_trading_signal(prediction)
                
                # Store results
                predictions.append(prediction)
                signals.append(signal)
                confidences.append(prediction['confidence'])
                position_sizes.append(prediction['position_size'])
                
                # Progress
                if i % 100 == 0:
                    print(f"     {i}/{len(sequences)}...", end="\r")
            
            print(f"     {len(sequences)}/{len(sequences)} completado")
            
            # Create results dataframe
            results_df = pd.DataFrame({
                'timestamp': df.index[50:].values[:len(signals)],
                'close': df['Close'].values[50:][:len(signals)],
                'signal': signals,
                'confidence': confidences,
                'position_size': position_sizes
            })
            
            # Calculate returns
            results_df['returns'] = results_df['close'].pct_change()
            
            # Calculate strategy returns (only when signal is BUY or STRONG_BUY)
            results_df['signal_returns'] = 0.0
            buy_mask = results_df['signal'].isin(['BUY', 'STRONG_BUY'])
            results_df.loc[buy_mask, 'signal_returns'] = results_df.loc[buy_mask, 'returns'] * results_df.loc[buy_mask, 'position_size']
            
            # Calculate cumulative returns
            results_df['cumulative_market'] = (1 + results_df['returns']).cumprod()
            results_df['cumulative_strategy'] = (1 + results_df['signal_returns']).cumprod()
            
            results[symbol] = results_df
            
            print(f"   ✅ Backtest completado: {len(results_df)} predicciones")
        
        return results
    
    def calculate_metrics(self, results_dict: Dict[str, pd.DataFrame]) -> Dict[str, Dict]:
        """
        Calculate performance metrics
        """
        print("\n📊 CALCULANDO MÉTRICAS DE PERFORMANCE...")
        print("-" * 40)
        
        metrics = {}
        
        for symbol, df in results_dict.items():
            if df.empty:
                continue
            
            print(f"\n📈 {symbol}:")
            
            # Basic metrics
            total_return_market = (df['cumulative_market'].iloc[-1] - 1) * 100
            total_return_strategy = (df['cumulative_strategy'].iloc[-1] - 1) * 100
            
            # Sharpe ratio (annualized)
            strategy_returns = df['signal_returns'].dropna()
            if len(strategy_returns) > 0:
                sharpe = (strategy_returns.mean() / strategy_returns.std()) * np.sqrt(365*24)  # Hourly data
            else:
                sharpe = 0
            
            # Maximum drawdown
            cumulative = df['cumulative_strategy']
            running_max = cumulative.expanding().max()
            drawdown = (cumulative - running_max) / running_max
            max_drawdown = drawdown.min() * 100
            
            # Win rate
            winning_trades = (strategy_returns > 0).sum()
            total_trades = len(strategy_returns)
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            
            # Profit factor
            gross_profit = strategy_returns[strategy_returns > 0].sum()
            gross_loss = abs(strategy_returns[strategy_returns < 0].sum())
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
            
            # Signal distribution
            signal_counts = df['signal'].value_counts()
            
            # Store metrics
            metrics[symbol] = {
                'total_return_market': total_return_market,
                'total_return_strategy': total_return_strategy,
                'sharpe_ratio': sharpe,
                'max_drawdown': max_drawdown,
                'win_rate': win_rate,
                'profit_factor': profit_factor,
                'total_trades': total_trades,
                'signal_distribution': signal_counts.to_dict()
            }
            
            # Print metrics
            print(f"   Retorno Mercado: {total_return_market:.2f}%")
            print(f"   Retorno Estrategia: {total_return_strategy:.2f}%")
            print(f"   Sharpe Ratio: {sharpe:.3f}")
            print(f"   Max Drawdown: {max_drawdown:.2f}%")
            print(f"   Win Rate: {win_rate:.1f}%")
            print(f"   Profit Factor: {profit_factor:.2f}")
            print(f"   Total Trades: {total_trades}")
            print(f"   Señales: {dict(signal_counts)}")
        
        return metrics
    
    def generate_report(self, metrics: Dict[str, Dict]) -> str:
        """
        Generate comprehensive backtest report
        """
        print("\n📄 GENERANDO INFORME DE BACKTEST...")
        print("=" * 60)
        
        report_lines = []
        report_lines.append("=" * 60)
        report_lines.append("🧠 INFORME DE BACKTEST - CEREBRO REVOLUCIONARIO")
        report_lines.append("=" * 60)
        report_lines.append(f"Fecha: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"Período: {self.period}")
        report_lines.append(f"Símbolos: {', '.join(self.symbols)}")
        report_lines.append("")
        
        # Overall performance
        report_lines.append("📊 PERFORMANCE GENERAL:")
        report_lines.append("-" * 40)
        
        for symbol, metric in metrics.items():
            report_lines.append(f"\n📈 {symbol}:")
            report_lines.append(f"  Retorno Mercado: {metric['total_return_market']:.2f}%")
            report_lines.append(f"  Retorno Estrategia: {metric['total_return_strategy']:.2f}%")
            report_lines.append(f"  Alpha: {metric['total_return_strategy'] - metric['total_return_market']:.2f}%")
            report_lines.append(f"  Sharpe Ratio: {metric['sharpe_ratio']:.3f}")
            report_lines.append(f"  Max Drawdown: {metric['max_drawdown']:.2f}%")
            report_lines.append(f"  Win Rate: {metric['win_rate']:.1f}%")
            report_lines.append(f"  Profit Factor: {metric['profit_factor']:.2f}")
            report_lines.append(f"  Total Trades: {metric['total_trades']}")
            
            # Signal analysis
            report_lines.append(f"  Distribución Señales:")
            for signal, count in metric['signal_distribution'].items():
                percentage = count / metric['total_trades'] * 100
                report_lines.append(f"    {signal}: {count} ({percentage:.1f}%)")
        
        # Performance interpretation
        report_lines.append("\n🎯 INTERPRETACIÓN DE RESULTADOS:")
        report_lines.append("-" * 40)
        
        # Calculate averages
        avg_sharpe = np.mean([m['sharpe_ratio'] for m in metrics.values()])
        avg_drawdown = np.mean([m['max_drawdown'] for m in metrics.values()])
        avg_win_rate = np.mean([m['win_rate'] for m in metrics.values()])
        
        report_lines.append(f"Sharpe Ratio Promedio: {avg_sharpe:.3f}")
        
        if avg_sharpe > 2.0:
            report_lines.append("  🎖️ EXCELENTE - Nivel Hedge Fund")
        elif avg_sharpe > 1.0:
            report_lines.append("  ✅ BUENO - Nivel Profesional")
        elif avg_sharpe > 0.5:
            report_lines.append("  ⚠️  ACEPTABLE - Necesita mejora")
        else:
            report_lines.append("  ❌ POBRE - Revisar estrategia")
        
        report_lines.append(f"\nDrawdown Promedio: {avg_drawdown:.2f}%")
        if avg_drawdown < 10:
            report_lines.append("  ✅ EXCELENTE gestión de riesgo")
        elif avg_drawdown < 20:
            report_lines.append("  ⚠️  ACEPTABLE - Monitorear riesgo")
        else:
            report_lines.append("  ❌ ALTO - Mejorar gestión de riesgo")
        
        report_lines.append(f"\nWin Rate Promedio: {avg_win_rate:.1f}%")
        
        # Recommendations
        report_lines.append("\n💡 RECOMENDACIONES:")
        report_lines.append("-" * 40)
        
        if avg_sharpe > 1.5 and avg_drawdown < 15:
            report_lines.append("✅ Sistema listo para producción")
            report_lines.append("   • Comenzar con capital pequeño")
            report_lines.append("   • Monitorear drawdown")
            report_lines.append("   • Escalar gradualmente")
        else:
            report_lines.append("⚠️  Sistema necesita mejora:")
            report_lines.append("   • Más entrenamiento del cerebro")
            report_lines.append("   • Ajustar parámetros de riesgo")
            report_lines.append("   • Probar con más datos históricos")
        
        report_lines.append("\n🚀 PRÓXIMOS PASOS:")
        report_lines.append("-" * 40)
        report_lines.append("1. Entrenamiento completo del cerebro (30-60 min)")
        report_lines.append("2. Backtest walk-forward validation")
        report_lines.append("3. Paper trading por 1 semana")
        report_lines.append("4. Implementación en producción")
        
        report_lines.append("\n" + "=" * 60)
        report_lines.append("🧠 CEREBRO REVOLUCIONARIO - BACKTEST COMPLETADO")
        report_lines.append("=" * 60)
        
        return "\n".join(report_lines)

def main():
    """
    Main backtest function
    """
    print("🎯 BACKTEST DEL CEREBRO REVOLUCIONARIO")
    print("=" * 60)
    
    try:
        # Create backtest system
        backtester = RevolutionaryBacktest(
            symbols=['BTC-USD', 'ETH-USD'],
            period='6mo'  # 6 months for quick backtest
        )
        
        # Download data
        data_dict = backtester.download_test_data()
        
        if not data_dict:
            print("❌ No se pudieron descargar datos")
            return
        
        # Run backtest
        results = backtester.run_backtest(data_dict)
        
        if not results:
            print("❌ No se pudieron generar resultados")
            return
        
        # Calculate metrics
        metrics = backtester.calculate_metrics(results)
        
        # Generate report
        report = backtester.generate_report(metrics)
        
        # Save report
        report_path = os.path.join(os.path.dirname(__file__), "backtest_report.txt")
        with open(report_path, 'w') as f:
            f.write(report)
        
        print(report)
        print(f"\n💾 Informe guardado en: {report_path}")
        
        return {
            'success': True,
            'metrics': metrics,
            'report_path': report_path
        }
        
    except Exception as e:
        print(f"\n❌ ERROR en backtest: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            'success': False,
            'error': str(e)
        }

if __name__ == "__main__":
    result = main()
    
    if result['success']:
        print("\n✅ BACKTEST COMPLETADO EXITOSAMENTE")
    else:
        print(f"\n❌ BACKTEST FALLÓ: {result.get('error', 'Unknown error')}")