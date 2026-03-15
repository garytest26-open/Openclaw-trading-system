#!/usr/bin/env python3
"""
Backtesting script for Swarm Trading AI
2-year backtest on BTC, ETH, SOL
"""

import os
import sys
import json
import time
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

print("=" * 60)
print("SWARM TRADING AI - BACKTESTING 2 AÑOS")
print("=" * 60)
print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"Período: 2 años")
print(f"Activos: BTC, ETH, SOL")
print(f"Agentes: Trend, Reversal, Volatility")
print("=" * 60)

# Load trained models
class TrendAgent(nn.Module):
    def __init__(self):
        super().__init__()
        self.lstm = nn.LSTM(10, 32, batch_first=True)
        self.fc = nn.Linear(32, 3)
    
    def forward(self, x):
        lstm_out, _ = self.lstm(x)
        return self.fc(lstm_out[:, -1, :])

class ReversalAgent(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc1 = nn.Linear(10 * 10, 64)
        self.fc2 = nn.Linear(64, 32)
        self.fc3 = nn.Linear(32, 3)
        self.dropout = nn.Dropout(0.2)
    
    def forward(self, x):
        x = x.view(x.size(0), -1)
        x = torch.relu(self.fc1(x))
        x = self.dropout(x)
        x = torch.relu(self.fc2(x))
        x = self.fc3(x)
        return x

class VolatilityAgent(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc1 = nn.Linear(10 * 10, 64)
        self.fc2 = nn.Linear(64, 32)
        self.fc3 = nn.Linear(32, 3)
        self.dropout = nn.Dropout(0.2)
    
    def forward(self, x):
        x = x.view(x.size(0), -1)
        x = torch.relu(self.fc1(x))
        x = self.dropout(x)
        x = torch.relu(self.fc2(x))
        x = self.fc3(x)
        return x

def load_models():
    """Load trained models"""
    print("\n📂 Cargando modelos entrenados...")
    
    try:
        # Initialize models
        trend_model = TrendAgent()
        reversal_model = ReversalAgent()
        volatility_model = VolatilityAgent()
        
        # Load weights
        trend_model.load_state_dict(torch.load('models/trend_agent_trained.pth'))
        reversal_model.load_state_dict(torch.load('models/reversal_agent_trained.pth'))
        volatility_model.load_state_dict(torch.load('models/volatility_agent_trained.pth'))
        
        # Set to evaluation mode
        trend_model.eval()
        reversal_model.eval()
        volatility_model.eval()
        
        print("✅ Modelos cargados exitosamente")
        return trend_model, reversal_model, volatility_model
        
    except Exception as e:
        print(f"❌ Error cargando modelos: {e}")
        return None, None, None

def generate_backtest_data():
    """Generate synthetic backtest data"""
    print("\n📊 Generando datos de backtesting (2 años)...")
    
    # Generate 2 years of daily data (approx 730 days)
    n_days = 730
    symbols = ['BTC', 'ETH', 'SOL']
    
    backtest_data = {}
    
    for symbol in symbols:
        # Generate price series with trends and volatility
        np.random.seed(42 + ord(symbol[0]))
        
        # Base price
        if symbol == 'BTC':
            base_price = 50000
            volatility = 0.02
        elif symbol == 'ETH':
            base_price = 3000
            volatility = 0.025
        else:  # SOL
            base_price = 100
            volatility = 0.03
        
        # Generate returns with some autocorrelation
        returns = np.zeros(n_days)
        for i in range(n_days):
            if i == 0:
                returns[i] = np.random.normal(0, volatility)
            else:
                returns[i] = 0.3 * returns[i-1] + np.random.normal(0, volatility * 0.7)
        
        # Calculate prices
        prices = base_price * np.exp(np.cumsum(returns))
        
        # Create DataFrame with OHLCV data
        dates = pd.date_range(end=datetime.now(), periods=n_days, freq='D')
        
        df = pd.DataFrame({
            'Open': prices * 0.995,
            'High': prices * 1.01,
            'Low': prices * 0.99,
            'Close': prices,
            'Volume': np.random.lognormal(12, 1, n_days)
        }, index=dates)
        
        # Add technical indicators
        df['Returns'] = df['Close'].pct_change()
        df['MA_5'] = df['Close'].rolling(window=5).mean()
        df['MA_20'] = df['Close'].rolling(window=20).mean()
        df['MA_50'] = df['Close'].rolling(window=50).mean()
        df['Volatility_20'] = df['Returns'].rolling(window=20).std()
        
        # Drop NaN values
        df = df.dropna()
        
        backtest_data[symbol] = df
        print(f"  ✅ {symbol}: {len(df)} días de datos")
    
    print(f"✅ Total: {sum(len(df) for df in backtest_data.values())} puntos de datos")
    return backtest_data

def create_features_from_data(df):
    """Create features from DataFrame"""
    features = []
    dates = []
    
    # Feature columns - need 10 features for the model
    feature_cols = ['Returns', 'MA_5', 'MA_20', 'MA_50', 'Volatility_20',
                   'Open', 'High', 'Low', 'Close', 'Volume']
    
    # Ensure all columns exist
    for col in feature_cols:
        if col not in df.columns:
            df[col] = 0
    
    # Normalize features
    from sklearn.preprocessing import StandardScaler
    scaler = StandardScaler()
    
    # Create sequences of length 10
    seq_length = 10
    for i in range(len(df) - seq_length):
        seq_data = df.iloc[i:i+seq_length][feature_cols].values
        
        # Check for NaN
        if np.isnan(seq_data).any():
            continue
        
        # Normalize
        seq_normalized = scaler.fit_transform(seq_data)
        
        features.append(seq_normalized)
        dates.append(df.index[i+seq_length])
    
    return np.array(features), dates

def run_backtest(trend_model, reversal_model, volatility_model, backtest_data):
    """Run backtest on all symbols"""
    print("\n🎯 Ejecutando backtest...")
    
    results = {}
    
    for symbol, df in backtest_data.items():
        print(f"\n📈 Analizando {symbol}...")
        
        # Create features
        features, dates = create_features_from_data(df)
        
        if len(features) == 0:
            print(f"  ⚠️  No hay suficientes datos para {symbol}")
            continue
        
        # Convert to tensor
        features_tensor = torch.FloatTensor(features)
        
        # Get predictions
        with torch.no_grad():
            trend_preds = trend_model(features_tensor)
            reversal_preds = reversal_model(features_tensor)
            volatility_preds = volatility_model(features_tensor)
        
        # Convert to numpy
        trend_classes = torch.argmax(trend_preds, dim=1).numpy()
        reversal_classes = torch.argmax(reversal_preds, dim=1).numpy()
        volatility_classes = torch.argmax(volatility_preds, dim=1).numpy()
        
        # Map predictions to signals
        signal_map = {
            0: 'BUY',
            1: 'SELL', 
            2: 'HOLD'
        }
        
        trend_signals = [signal_map[c] for c in trend_classes]
        reversal_signals = [signal_map[c] for c in reversal_classes]
        
        # Volatility regimes
        volatility_map = {
            0: 'LOW',
            1: 'MEDIUM',
            2: 'HIGH'
        }
        volatility_regimes = [volatility_map[c] for c in volatility_classes]
        
        # Calculate swarm consensus
        consensus_signals = []
        for t, r in zip(trend_signals, reversal_signals):
            if t == r:
                consensus = t
            elif t == 'HOLD':
                consensus = r
            elif r == 'HOLD':
                consensus = t
            else:
                # Conflicting signals, default to HOLD
                consensus = 'HOLD'
            consensus_signals.append(consensus)
        
        # Simulate trading
        initial_capital = 10000
        capital = initial_capital
        position = 0
        trades = []
        
        for i in range(len(consensus_signals)):
            price = df['Close'].iloc[i+10]  # Offset for sequence
            
            if consensus_signals[i] == 'BUY' and position == 0:
                # Buy
                position = capital / price
                capital = 0
                trades.append({
                    'date': dates[i],
                    'action': 'BUY',
                    'price': price,
                    'position': position
                })
                
            elif consensus_signals[i] == 'SELL' and position > 0:
                # Sell
                capital = position * price
                pnl = capital - initial_capital
                trades.append({
                    'date': dates[i],
                    'action': 'SELL',
                    'price': price,
                    'position': 0,
                    'pnl': pnl
                })
                position = 0
        
        # Final valuation
        if position > 0:
            final_price = df['Close'].iloc[-1]
            capital = position * final_price
        
        total_return = (capital - initial_capital) / initial_capital * 100
        
        # Calculate metrics
        if len(trades) >= 2:
            winning_trades = sum(1 for t in trades if 'pnl' in t and t['pnl'] > 0)
            total_trades = len(trades) // 2  # Each trade pair
            win_rate = winning_trades / total_trades * 100 if total_trades > 0 else 0
        else:
            win_rate = 0
        
        # Convert dates to strings for JSON serialization
        trades_serializable = []
        for trade in trades[-10:] if trades else []:
            trade_copy = trade.copy()
            if 'date' in trade_copy:
                trade_copy['date'] = str(trade_copy['date'])
            trades_serializable.append(trade_copy)
        
        # Store results
        results[symbol] = {
            'initial_capital': initial_capital,
            'final_capital': capital,
            'total_return_percent': total_return,
            'total_trades': len(trades) // 2,
            'win_rate': win_rate,
            'trend_signals': trend_signals[:20],  # First 20 for display
            'reversal_signals': reversal_signals[:20],
            'consensus_signals': consensus_signals[:20],
            'volatility_regimes': volatility_regimes[:20],
            'trades': trades_serializable
        }
        
        print(f"  📊 Resultados {symbol}:")
        print(f"    • Capital inicial: ${initial_capital:,.2f}")
        print(f"    • Capital final: ${capital:,.2f}")
        print(f"    • Retorno total: {total_return:.2f}%")
        print(f"    • Operaciones: {len(trades) // 2}")
        print(f"    • Tasa de acierto: {win_rate:.1f}%")
    
    return results

def generate_report(results):
    """Generate backtest report"""
    print("\n" + "=" * 60)
    print("📊 INFORME DE BACKTESTING - 2 AÑOS")
    print("=" * 60)
    
    total_initial = 0
    total_final = 0
    all_returns = []
    
    for symbol, res in results.items():
        print(f"\n{symbol}:")
        print(f"  Retorno: {res['total_return_percent']:.2f}%")
        print(f"  Operaciones: {res['total_trades']}")
        print(f"  Tasa de acierto: {res['win_rate']:.1f}%")
        
        total_initial += res['initial_capital']
        total_final += res['final_capital']
        all_returns.append(res['total_return_percent'])
    
    # Portfolio summary
    print("\n" + "-" * 40)
    print("📈 RESUMEN DEL PORTAFOLIO:")
    print("-" * 40)
    
    portfolio_return = (total_final - total_initial) / total_initial * 100
    avg_return = np.mean(all_returns) if all_returns else 0
    
    print(f"Capital total inicial: ${total_initial:,.2f}")
    print(f"Capital total final: ${total_final:,.2f}")
    print(f"Retorno del portafolio: {portfolio_return:.2f}%")
    print(f"Retorno promedio por activo: {avg_return:.2f}%")
    
    # Save results
    report = {
        'backtest_date': datetime.now().isoformat(),
        'backtest_period_years': 2,
        'symbols_tested': list(results.keys()),
        'portfolio_summary': {
            'total_initial_capital': total_initial,
            'total_final_capital': total_final,
            'portfolio_return_percent': portfolio_return,
            'average_return_percent': avg_return
        },
        'detailed_results': results
    }
    
    # Save to file
    with open('backtest_results_2years.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n💾 Reporte guardado en: backtest_results_2years.json")
    
    return report

def main():
    """Main function"""
    start_time = time.time()
    
    try:
        # Load models
        trend_model, reversal_model, volatility_model = load_models()
        
        if trend_model is None:
            print("❌ No se pudieron cargar los modelos")
            return
        
        # Generate backtest data
        backtest_data = generate_backtest_data()
        
        # Run backtest
        results = run_backtest(trend_model, reversal_model, volatility_model, backtest_data)
        
        # Generate report
        report = generate_report(results)
        
        print("\n" + "=" * 60)
        print("✅ BACKTEST COMPLETADO")
        print("=" * 60)
        print(f"⏱️  Tiempo total: {time.time() - start_time:.1f} segundos")
        print(f"📊 Resultados: backtest_results_2years.json")
        print("\n🎯 Próximos pasos:")
        print("1. Revisar resultados del backtest")
        print("2. Ajustar parámetros si es necesario")
        print("3. Conectar dashboard a datos reales")
        print("4. Probar en Hyperliquid testnet")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error durante el backtest: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()