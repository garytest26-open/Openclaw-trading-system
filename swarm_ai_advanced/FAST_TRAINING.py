"""
FAST_TRAINING.py - Entrenamiento rápido del cerebro revolucionario
Versión optimizada para demostración en 15-20 minutos
"""

import torch
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

print("🚀 ENTRENAMIENTO RÁPIDO - CEREBRO REVOLUCIONARIO")
print("=" * 60)

class FastBrain(torch.nn.Module):
    """Cerebro optimizado para entrenamiento rápido"""
    
    def __init__(self, input_dim=20, hidden_dim=128):
        super().__init__()
        
        # Feature extractor
        self.feature_extractor = torch.nn.Sequential(
            torch.nn.Linear(input_dim, hidden_dim),
            torch.nn.ReLU(),
            torch.nn.Dropout(0.2),
            torch.nn.Linear(hidden_dim, hidden_dim // 2),
            torch.nn.ReLU()
        )
        
        # LSTM for temporal patterns
        self.lstm = torch.nn.LSTM(
            input_size=hidden_dim // 2,
            hidden_size=hidden_dim,
            num_layers=1,
            batch_first=True
        )
        
        # Decision head
        self.decision_head = torch.nn.Sequential(
            torch.nn.Linear(hidden_dim, 64),
            torch.nn.ReLU(),
            torch.nn.Linear(64, 32),
            torch.nn.ReLU(),
            torch.nn.Linear(32, 3),  # Buy, Hold, Sell
            torch.nn.Softmax(dim=-1)
        )
        
        # Risk head
        self.risk_head = torch.nn.Sequential(
            torch.nn.Linear(hidden_dim, 32),
            torch.nn.ReLU(),
            torch.nn.Linear(32, 3),  # Position size, stop loss, take profit
            torch.nn.Sigmoid()
        )
        
        print(f"🧠 FastBrain creado: {sum(p.numel() for p in self.parameters()):,} parámetros")
    
    def forward(self, x):
        # x shape: (batch_size, seq_len, input_dim)
        
        # Extract features
        batch_size, seq_len, _ = x.shape
        x_flat = x.view(-1, x.shape[-1])
        features = self.feature_extractor(x_flat)
        features = features.view(batch_size, seq_len, -1)
        
        # Temporal patterns
        lstm_out, (hidden, cell) = self.lstm(features)
        
        # Use last hidden state
        context = hidden[-1]
        
        # Decisions
        decisions = self.decision_head(context)
        risk_params = self.risk_head(context)
        
        return decisions, risk_params

def download_training_data(symbols=['BTC-USD', 'ETH-USD'], days=365):
    """Download and prepare training data quickly"""
    print(f"\n📥 Descargando {len(symbols)} símbolos ({days} días)...")
    
    all_data = []
    
    for symbol in symbols:
        try:
            # Download data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start_date, end=end_date, interval='1d')
            
            if df.empty:
                print(f"   ❌ {symbol}: Sin datos")
                continue
            
            # Calculate simple features
            df['returns'] = df['Close'].pct_change()
            df['sma_10'] = df['Close'].rolling(10).mean()
            df['sma_20'] = df['Close'].rolling(20).mean()
            df['volume_sma'] = df['Volume'].rolling(20).mean()
            df['volume_ratio'] = df['Volume'] / df['volume_sma']
            
            # RSI simplified
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            df['rsi'] = 100 - (100 / (1 + rs))
            
            # Price position
            df['price_vs_sma_10'] = df['Close'] / df['sma_10']
            df['price_vs_sma_20'] = df['Close'] / df['sma_20']
            
            # Volatility
            df['volatility'] = df['returns'].rolling(20).std() * np.sqrt(252)
            
            # Fill NaN
            df = df.fillna(0)
            
            # Select features
            feature_cols = ['returns', 'sma_10', 'sma_20', 'volume_ratio', 'rsi', 
                          'price_vs_sma_10', 'price_vs_sma_20', 'volatility']
            
            # Add more features if available
            available_cols = [col for col in feature_cols if col in df.columns]
            
            if len(available_cols) >= 5:  # Need minimum features
                feature_data = df[available_cols].values.astype(np.float32)
                all_data.append((symbol, feature_data))
                print(f"   ✅ {symbol}: {len(feature_data)} muestras, {len(available_cols)} features")
            else:
                print(f"   ⚠️  {symbol}: Features insuficientes")
                
        except Exception as e:
            print(f"   ❌ {symbol}: Error - {e}")
    
    return all_data

def create_sequences(data, seq_length=30):
    """Create training sequences"""
    sequences = []
    targets = []
    
    for symbol, features in data:
        if len(features) < seq_length + 1:
            continue
        
        for i in range(seq_length, len(features) - 1):
            # Input sequence
            seq = features[i-seq_length:i]
            
            # Target: next period return
            next_return = features[i, 0] if features.shape[1] > 0 else 0
            
            # Create target class
            if next_return > 0.01:  # > 1%
                target = 0  # Buy
            elif next_return < -0.01:  # < -1%
                target = 2  # Sell
            else:
                target = 1  # Hold
            
            sequences.append(seq)
            targets.append(target)
    
    return np.array(sequences), np.array(targets)

def train_fast_brain(sequences, targets, epochs=20, batch_size=32):
    """Train the brain quickly"""
    print(f"\n🔥 ENTRENANDO CEREBRO ({epochs} épocas)...")
    
    # Convert to tensors
    X = torch.FloatTensor(sequences)
    y = torch.LongTensor(targets)
    
    # Create brain
    input_dim = sequences.shape[-1]
    brain = FastBrain(input_dim=input_dim, hidden_dim=128)
    
    # Optimizer and loss
    optimizer = torch.optim.Adam(brain.parameters(), lr=0.001)
    criterion = torch.nn.CrossEntropyLoss()
    
    # Training loop
    brain.train()
    
    for epoch in range(epochs):
        epoch_loss = 0
        correct = 0
        total = 0
        
        # Mini-batch training
        for i in range(0, len(X), batch_size):
            batch_X = X[i:i+batch_size]
            batch_y = y[i:i+batch_size]
            
            # Forward pass
            decisions, risk_params = brain(batch_X)
            
            # Calculate loss
            loss = criterion(decisions, batch_y)
            
            # Backward pass
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
            # Statistics
            epoch_loss += loss.item()
            _, predicted = torch.max(decisions, 1)
            correct += (predicted == batch_y).sum().item()
            total += batch_y.size(0)
        
        # Epoch statistics
        accuracy = correct / total * 100
        avg_loss = epoch_loss / (len(X) / batch_size)
        
        print(f"   Epoch {epoch+1}/{epochs}: Loss={avg_loss:.4f}, Acc={accuracy:.1f}%")
        
        # Early stopping if good enough
        if accuracy > 65 and epoch >= 10:
            print(f"   ✅ Accuracy suficiente alcanzada")
            break
    
    print(f"\n🎯 ENTRENAMIENTO COMPLETADO")
    print(f"   Accuracy final: {accuracy:.1f}%")
    print(f"   Parámetros entrenados: {sum(p.numel() for p in brain.parameters()):,}")
    
    return brain

def quick_backtest(brain, test_data):
    """Quick backtest of trained brain"""
    print(f"\n📊 BACKTEST RÁPIDO DEL CEREBRITO ENTRENADO...")
    
    results = {}
    
    for symbol, features in test_data:
        if len(features) < 50:
            continue
        
        # Prepare test sequences
        seq_length = 30
        test_sequences = []
        actual_returns = []
        
        for i in range(seq_length, len(features) - 1):
            seq = features[i-seq_length:i]
            test_sequences.append(seq)
            actual_returns.append(features[i, 0])  # Next return
        
        if not test_sequences:
            continue
        
        # Convert to tensor
        X_test = torch.FloatTensor(test_sequences)
        
        # Make predictions
        brain.eval()
        with torch.no_grad():
            decisions, risk_params = brain(X_test)
            _, predictions = torch.max(decisions, 1)
        
        # Calculate strategy returns
        strategy_returns = []
        for i, pred in enumerate(predictions):
            if i >= len(actual_returns):
                break
            
            if pred == 0:  # Buy
                strategy_returns.append(actual_returns[i])
            elif pred == 2:  # Sell
                strategy_returns.append(-actual_returns[i])  # Short
            else:  # Hold
                strategy_returns.append(0)
        
        # Calculate metrics
        if strategy_returns:
            strategy_returns = np.array(strategy_returns)
            market_returns = np.array(actual_returns[:len(strategy_returns)])
            
            # Cumulative returns
            market_cumulative = np.cumprod(1 + market_returns)
            strategy_cumulative = np.cumprod(1 + strategy_returns)
            
            market_return = (market_cumulative[-1] - 1) * 100
            strategy_return = (strategy_cumulative[-1] - 1) * 100
            
            # Sharpe ratio
            if len(strategy_returns) > 0 and strategy_returns.std() > 0:
                sharpe = (strategy_returns.mean() / strategy_returns.std()) * np.sqrt(252)
            else:
                sharpe = 0
            
            # Signal distribution
            buy_count = (predictions == 0).sum().item()
            hold_count = (predictions == 1).sum().item()
            sell_count = (predictions == 2).sum().item()
            
            results[symbol] = {
                'market_return': market_return,
                'strategy_return': strategy_return,
                'sharpe': sharpe,
                'alpha': strategy_return - market_return,
                'signals': {'BUY': buy_count, 'HOLD': hold_count, 'SELL': sell_count}
            }
            
            print(f"\n📈 {symbol}:")
            print(f"   Retorno Mercado: {market_return:.2f}%")
            print(f"   Retorno Estrategia: {strategy_return:.2f}%")
            print(f"   Alpha: {strategy_return - market_return:.2f}%")
            print(f"   Sharpe: {sharpe:.3f}")
            print(f"   Señales: BUY={buy_count}, HOLD={hold_count}, SELL={sell_count}")
    
    return results

def main():
    """Main training function"""
    print("\n🎯 ENTRENAMIENTO RÁPIDO DEL CEREBRO REVOLUCIONARIO")
    print("=" * 60)
    print("Objetivo: Cerebro funcional en 15-20 minutos")
    print("=" * 60)
    
    try:
        # Step 1: Download data
        training_data = download_training_data(
            symbols=['BTC-USD', 'ETH-USD', 'SOL-USD'],
            days=180  # 6 months for faster training
        )
        
        if not training_data:
            print("❌ No se pudieron descargar datos")
            return
        
        # Step 2: Prepare sequences
        print(f"\n📊 Preparando secuencias...")
        sequences, targets = create_sequences(training_data, seq_length=30)
        
        print(f"   Secuencias: {len(sequences)}")
        print(f"   Targets: {len(targets)}")
        print(f"   Distribución: Buy={(targets==0).sum()}, Hold={(targets==1).sum()}, Sell={(targets==2).sum()}")
        
        if len(sequences) < 100:
            print("❌ Datos insuficientes para entrenamiento")
            return
        
        # Step 3: Split train/test
        split_idx = int(len(sequences) * 0.8)
        X_train, X_test = sequences[:split_idx], sequences[split_idx:]
        y_train, y_test = targets[:split_idx], targets[split_idx:]
        
        print(f"   Train: {len(X_train)} secuencias")
        print(f"   Test: {len(X_test)} secuencias")
        
        # Step 4: Train brain
        brain = train_fast_brain(X_train, y_train, epochs=15, batch_size=32)
        
        # Step 5: Quick backtest
        test_results = quick_backtest(brain, training_data)
        
        # Step 6: Save brain
        model_path = "fast_brain_trained.pth"
        torch.save(brain.state_dict(), model_path)
        
        print(f"\n💾 Cerebro guardado en: {model_path}")
        print(f"   Tamaño: {os.path.getsize(model_path) / 1024:.1f} KB")
        
        # Step 7: Summary
        print("\n" + "=" * 60)
        print("🎯 RESUMEN DEL ENTRENAMIENTO RÁPIDO")
        print("=" * 60)
        
        if test_results:
            avg_sharpe = np.mean([r['sharpe'] for r in test_results.values()])
            avg_alpha = np.mean([r['alpha'] for r in test_results.values()])
            
            print(f"\n📊 PERFORMANCE PROMEDIO:")
            print(f"   Sharpe Ratio: {avg_sharpe:.3f}")
            print(f"   Alpha: {avg_alpha:.2f}%")
            
            if avg_sharpe > 1.0:
                print("   ✅ EXCELENTE - Cerebro listo para siguiente fase")
            elif avg_sharpe > 0.5:
                print("   ⚠️  ACEPTABLE - Necesita más entrenamiento")
            else:
                print("   ❌ POBRE - Revisar estrategia")
        
        print("\n🚀 PRÓXIMOS PASOS:")
        print("   1. Entrenamiento completo (30-60 min)")
        print("   2. Backtest walk-forward validation")
        print("   3. Paper trading por 1 semana")
        print("   4. Implementación en producción")
        
        print("\n" + "=" * 60)
        print("🧠 CEREBRO RÁPIDO ENTRENADO CON ÉXITO")
        print("=" * 60)
        
        return {
            'success': True,
            'model_path': model_path,
            'test_results': test_results
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
    import os
    result = main()
    
    if result['success']:
        print(f"\n✅ ENTRENAMIENTO COMPLETADO EXITOSAMENTE")
        print(f"   Modelo: {result['model_path']}")
    else:
        print(f"\n❌ ENTRENAMIENTO FALLÓ: {result.get('error', 'Unknown error')}")