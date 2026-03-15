"""
SIMPLE_OPTIMIZATION.py - Optimización simple pero efectiva
"""

import torch
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

print("🔧 OPTIMIZACIÓN SIMPLE - CEREBRO REVOLUCIONARIO")
print("=" * 60)

class SimpleOptimizedBrain(torch.nn.Module):
    """Cerebro simple pero optimizado"""
    
    def __init__(self, input_dim=8, hidden_dim=192):
        super().__init__()
        
        self.feature_extractor = torch.nn.Sequential(
            torch.nn.Linear(input_dim, hidden_dim),
            torch.nn.ReLU(),
            torch.nn.Dropout(0.2),
            torch.nn.Linear(hidden_dim, hidden_dim // 2),
            torch.nn.ReLU()
        )
        
        self.lstm = torch.nn.LSTM(
            input_size=hidden_dim // 2,
            hidden_size=hidden_dim // 2,
            num_layers=1,
            batch_first=True
        )
        
        self.decision_head = torch.nn.Sequential(
            torch.nn.Linear(hidden_dim // 2, 64),
            torch.nn.ReLU(),
            torch.nn.Linear(64, 32),
            torch.nn.ReLU(),
            torch.nn.Linear(32, 3),
            torch.nn.Softmax(dim=-1)
        )
        
        print(f"🧠 SimpleOptimizedBrain: {sum(p.numel() for p in self.parameters()):,} parámetros")
    
    def forward(self, x):
        batch_size, seq_len, _ = x.shape
        x_flat = x.reshape(-1, x.shape[-1])
        features = self.feature_extractor(x_flat)
        features = features.view(batch_size, seq_len, -1)
        
        lstm_out, (hidden, cell) = self.lstm(features)
        context = hidden[-1]
        
        decisions = self.decision_head(context)
        return decisions

def download_simple_data(symbols=['BTC-USD', 'ETH-USD'], days=180):
    """Download simple data"""
    print(f"\n📥 Descargando datos simples ({len(symbols)} símbolos)...")
    
    all_data = []
    
    for symbol in symbols:
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start_date, end=end_date, interval='1d')
            
            if df.empty:
                continue
            
            # Simple features
            df['returns'] = df['Close'].pct_change()
            df['sma_10'] = df['Close'].rolling(10).mean()
            df['sma_20'] = df['Close'].rolling(20).mean()
            df['volume_sma'] = df['Volume'].rolling(20).mean()
            df['volume_ratio'] = df['Volume'] / df['volume_sma']
            
            # RSI
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            df['rsi'] = 100 - (100 / (1 + rs))
            
            df['price_vs_sma_10'] = df['Close'] / df['sma_10']
            df['price_vs_sma_20'] = df['Close'] / df['sma_20']
            df['volatility'] = df['returns'].rolling(20).std() * np.sqrt(252)
            df = df.fillna(0)
            
            feature_cols = ['returns', 'sma_10', 'sma_20', 'volume_ratio', 'rsi', 
                          'price_vs_sma_10', 'price_vs_sma_20', 'volatility']
            
            available_cols = [col for col in feature_cols if col in df.columns]
            
            if len(available_cols) >= 5:
                feature_data = df[available_cols].values.astype(np.float32)
                all_data.append((symbol, feature_data))
                print(f"   ✅ {symbol}: {len(feature_data)} muestras")
                
        except Exception as e:
            print(f"   ❌ {symbol}: {e}")
    
    return all_data

def create_simple_sequences(data, seq_length=20):
    """Create simple sequences"""
    sequences = []
    targets = []
    
    for symbol, features in data:
        if len(features) < seq_length + 1:
            continue
        
        for i in range(seq_length, len(features) - 1):
            seq = features[i-seq_length:i]
            next_return = features[i, 0] if features.shape[1] > 0 else 0
            
            # Better target: consider volatility
            volatility = features[i, 7] if features.shape[1] > 7 else 0.01
            risk_adj_return = next_return / (volatility + 0.01)
            
            if risk_adj_return > 0.2:
                target = 0  # Buy
            elif risk_adj_return < -0.2:
                target = 2  # Sell
            else:
                target = 1  # Hold
            
            sequences.append(seq)
            targets.append(target)
    
    return np.array(sequences), np.array(targets)

def train_simple_brain(sequences, targets, epochs=25):
    """Train simple brain"""
    print(f"\n🔥 ENTRENANDO ({epochs} épocas)...")
    
    X = torch.FloatTensor(sequences)
    y = torch.LongTensor(targets)
    
    input_dim = sequences.shape[-1]
    brain = SimpleOptimizedBrain(input_dim=input_dim, hidden_dim=192)
    
    optimizer = torch.optim.Adam(brain.parameters(), lr=0.001)
    criterion = torch.nn.CrossEntropyLoss()
    
    brain.train()
    
    for epoch in range(epochs):
        # Shuffle
        indices = torch.randperm(len(X))
        X_shuffled = X[indices]
        y_shuffled = y[indices]
        
        # Train
        predictions = []
        actuals = []
        
        for i in range(0, len(X_shuffled), 32):
            batch_X = X_shuffled[i:i+32]
            batch_y = y_shuffled[i:i+32]
            
            decisions = brain(batch_X)
            loss = criterion(decisions, batch_y)
            
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
            # Track predictions
            _, preds = torch.max(decisions, 1)
            predictions.extend(preds.tolist())
            actuals.extend(batch_y.tolist())
        
        # Calculate accuracy
        correct = sum(1 for p, a in zip(predictions, actuals) if p == a)
        accuracy = correct / len(predictions) * 100
        
        print(f"   Epoch {epoch+1}/{epochs}: Acc={accuracy:.1f}%")
        
        if accuracy > 70 and epoch >= 15:
            print(f"   ✅ Suficiente")
            break
    
    print(f"\n🎯 Entrenamiento completado")
    return brain

def test_simple_brain(brain, test_data):
    """Test simple brain"""
    print(f"\n📊 TESTING...")
    
    results = {}
    
    for symbol, features in test_data:
        if len(features) < 40:
            continue
        
        seq_length = 20
        test_sequences = []
        actual_returns = []
        
        for i in range(seq_length, len(features) - 1):
            seq = features[i-seq_length:i]
            test_sequences.append(seq)
            actual_returns.append(features[i, 0])
        
        if not test_sequences:
            continue
        
        X_test = torch.FloatTensor(test_sequences)
        
        brain.eval()
        with torch.no_grad():
            decisions = brain(X_test)
            _, predictions = torch.max(decisions, 1)
        
        # Calculate returns with simple risk management
        strategy_returns = []
        for i, pred in enumerate(predictions):
            if i >= len(actual_returns):
                break
            
            return_val = actual_returns[i]
            
            # Simple position sizing based on confidence
            probs = decisions[i].numpy()
            confidence = np.max(probs)
            position_size = 0.5 + (confidence - 0.5)  # 0.5-1.0
            
            adjusted_return = return_val * position_size
            
            # Simple stop loss
            if adjusted_return < -0.02:  # 2% stop loss
                adjusted_return = -0.02
            
            if pred == 0:  # Buy
                strategy_returns.append(adjusted_return)
            elif pred == 2:  # Sell
                strategy_returns.append(-adjusted_return)
            else:
                strategy_returns.append(0)
        
        if strategy_returns:
            strategy_returns = np.array(strategy_returns)
            market_returns = np.array(actual_returns[:len(strategy_returns)])
            
            # Calculate metrics
            market_cum = np.prod(1 + market_returns)
            strategy_cum = np.prod(1 + strategy_returns)
            
            market_ret = (market_cum - 1) * 100
            strategy_ret = (strategy_cum - 1) * 100
            
            # Simple Sharpe
            if len(strategy_returns) > 0 and strategy_returns.std() > 0:
                sharpe = (strategy_returns.mean() / strategy_returns.std()) * np.sqrt(252)
            else:
                sharpe = 0
            
            # Simple drawdown
            cumulative = np.cumprod(1 + strategy_returns)
            peak = np.maximum.accumulate(cumulative)
            drawdown = (cumulative - peak) / peak
            max_dd = np.min(drawdown) * 100
            
            # Win rate
            trades = [r for r in strategy_returns if r != 0]
            if trades:
                win_rate = sum(1 for r in trades if r > 0) / len(trades) * 100
            else:
                win_rate = 0
            
            results[symbol] = {
                'market': market_ret,
                'strategy': strategy_ret,
                'alpha': strategy_ret - market_ret,
                'sharpe': sharpe,
                'drawdown': max_dd,
                'win_rate': win_rate
            }
            
            print(f"\n📈 {symbol}:")
            print(f"   Mercado: {market_ret:.2f}%")
            print(f"   Estrategia: {strategy_ret:.2f}%")
            print(f"   Alpha: {strategy_ret - market_ret:.2f}%")
            print(f"   Sharpe: {sharpe:.3f}")
            print(f"   Drawdown: {max_dd:.2f}%")
            print(f"   Win Rate: {win_rate:.1f}%")
    
    return results

def main():
    """Main function"""
    print("\n🔧 OPTIMIZACIÓN SIMPLE PERO EFECTIVA")
    print("=" * 60)
    
    try:
        # 1. Download data
        data = download_simple_data(['BTC-USD', 'ETH-USD'], days=180)
        
        if not data:
            print("❌ Sin datos")
            return
        
        # 2. Prepare sequences
        sequences, targets = create_simple_sequences(data, seq_length=20)
        
        print(f"\n📊 Datos preparados:")
        print(f"   Secuencias: {len(sequences)}")
        print(f"   Distribución: Buy={(targets==0).sum()}, Hold={(targets==1).sum()}, Sell={(targets==2).sum()}")
        
        if len(sequences) < 50:
            print("❌ Muy pocos datos")
            return
        
        # 3. Split
        split = int(len(sequences) * 0.8)
        X_train, X_test = sequences[:split], sequences[split:]
        y_train, y_test = targets[:split], targets[split:]
        
        print(f"   Train: {len(X_train)}, Test: {len(X_test)}")
        
        # 4. Train
        brain = train_simple_brain(X_train, y_train, epochs=25)
        
        # 5. Test
        results = test_simple_brain(brain, data)
        
        # 6. Save
        torch.save(brain.state_dict(), 'simple_optimized_brain.pth')
        
        # 7. Summary
        print("\n" + "=" * 60)
        print("🎯 RESUMEN DE OPTIMIZACIÓN")
        print("=" * 60)
        
        if results:
            avg_sharpe = np.mean([r['sharpe'] for r in results.values()])
            avg_alpha = np.mean([r['alpha'] for r in results.values()])
            avg_dd = np.mean([r['drawdown'] for r in results.values()])
            
            print(f"\n📊 PROMEDIOS:")
            print(f"   Sharpe: {avg_sharpe:.3f}")
            print(f"   Alpha: {avg_alpha:.2f}%")
            print(f"   Drawdown: {avg_dd:.2f}%")
            
            print(f"\n🎯 EVALUACIÓN:")
            if avg_sharpe > 1.0:
                print("   ✅ BUENO - Sharpe > 1.0")
            elif avg_sharpe > 0.5:
                print("   ⚠️  ACEPTABLE - Sharpe > 0.5")
            else:
                print("   ❌ MEJORABLE - Sharpe < 0.5")
            
            if avg_alpha > 0:
                print("   ✅ POSITIVO - Alpha positivo")
            else:
                print("   ❌ NEGATIVO - Alpha negativo")
        
        print(f"\n💾 Modelo guardado: simple_optimized_brain.pth")
        
        return {
            'success': True,
            'results': results,
            'avg_sharpe': avg_sharpe if results else 0
        }
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return {'success': False, 'error': str(e)}

if __name__ == "__main__":
    result = main()
    
    if result['success']:
        print(f"\n✅ OPTIMIZACIÓN COMPLETADA")
        if 'avg_sharpe' in result:
            print(f"   Sharpe Promedio: {result['avg_sharpe']:.3f}")
    else:
        print(f"\n❌ FALLÓ: {result.get('error', 'Unknown')}")