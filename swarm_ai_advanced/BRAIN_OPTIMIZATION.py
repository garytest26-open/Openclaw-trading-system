"""
BRAIN_OPTIMIZATION.py - Optimización avanzada del cerebro revolucionario
Mejora Sharpe ratio, accuracy, y gestión de riesgo
"""

import torch
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

print("🔧 OPTIMIZACIÓN AVANZADA - CEREBRO REVOLUCIONARIO")
print("=" * 60)
print("Objetivo: Mejorar Sharpe ratio > 1.5, Accuracy > 50%")
print("=" * 60)

class OptimizedBrain(torch.nn.Module):
    """Cerebro optimizado con mejor arquitectura"""
    
    def __init__(self, input_dim=15, hidden_dim=256):
        super().__init__()
        
        # Enhanced feature extractor
        self.feature_extractor = torch.nn.Sequential(
            torch.nn.Linear(input_dim, hidden_dim),
            torch.nn.BatchNorm1d(hidden_dim),
            torch.nn.ReLU(),
            torch.nn.Dropout(0.3),
            torch.nn.Linear(hidden_dim, hidden_dim // 2),
            torch.nn.BatchNorm1d(hidden_dim // 2),
            torch.nn.ReLU(),
            torch.nn.Dropout(0.2),
            torch.nn.Linear(hidden_dim // 2, hidden_dim // 4),
            torch.nn.ReLU()
        )
        
        # Bidirectional LSTM for temporal patterns
        self.lstm = torch.nn.LSTM(
            input_size=hidden_dim // 4,
            hidden_size=hidden_dim // 2,
            num_layers=2,
            batch_first=True,
            bidirectional=True,
            dropout=0.2
        )
        
        # Attention mechanism
        self.attention = torch.nn.MultiheadAttention(
            embed_dim=hidden_dim // 2 * 2,  # bidirectional
            num_heads=4,
            dropout=0.1,
            batch_first=True
        )
        
        # Decision head with risk awareness
        self.decision_head = torch.nn.Sequential(
            torch.nn.Linear(hidden_dim, 128),
            torch.nn.ReLU(),
            torch.nn.Dropout(0.2),
            torch.nn.Linear(128, 64),
            torch.nn.ReLU(),
            torch.nn.Linear(64, 32),
            torch.nn.ReLU(),
            torch.nn.Linear(32, 3),  # Buy, Hold, Sell
            torch.nn.Softmax(dim=-1)
        )
        
        # Risk management head
        self.risk_head = torch.nn.Sequential(
            torch.nn.Linear(hidden_dim, 64),
            torch.nn.ReLU(),
            torch.nn.Linear(64, 32),
            torch.nn.ReLU(),
            torch.nn.Linear(32, 4),  # Position size, stop loss, take profit, confidence
            torch.nn.Sigmoid()
        )
        
        # Market regime detector
        self.regime_detector = torch.nn.Sequential(
            torch.nn.Linear(hidden_dim, 64),
            torch.nn.ReLU(),
            torch.nn.Linear(64, 3),  # Bull, Bear, Sideways
            torch.nn.Softmax(dim=-1)
        )
        
        print(f"🧠 OptimizedBrain creado: {sum(p.numel() for p in self.parameters()):,} parámetros")
    
    def forward(self, x):
        # x shape: (batch_size, seq_len, input_dim)
        batch_size, seq_len, _ = x.shape
        
        # Extract features
        x_flat = x.reshape(-1, x.shape[-1])
        features = self.feature_extractor(x_flat)
        features = features.view(batch_size, seq_len, -1)
        
        # Temporal patterns with LSTM
        lstm_out, (hidden, cell) = self.lstm(features)
        
        # Attention mechanism
        attn_out, attn_weights = self.attention(lstm_out, lstm_out, lstm_out)
        
        # Context vector (weighted sum)
        context = torch.mean(attn_out, dim=1)
        
        # Decisions with market context
        decisions = self.decision_head(context)
        risk_params = self.risk_head(context)
        market_regime = self.regime_detector(context)
        
        return decisions, risk_params, market_regime

def download_enhanced_data(symbols=['BTC-USD', 'ETH-USD', 'SOL-USD'], days=365):
    """Download data with enhanced features"""
    print(f"\n📥 Descargando datos mejorados ({len(symbols)} símbolos, {days} días)...")
    
    all_data = []
    
    for symbol in symbols:
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start_date, end=end_date, interval='1d')
            
            if df.empty:
                print(f"   ❌ {symbol}: Sin datos")
                continue
            
            # Price features
            df['returns'] = df['Close'].pct_change()
            df['log_returns'] = np.log(df['Close'] / df['Close'].shift(1))
            
            # Moving averages
            for window in [5, 10, 20, 50]:
                df[f'sma_{window}'] = df['Close'].rolling(window).mean()
                df[f'ema_{window}'] = df['Close'].ewm(span=window, adjust=False).mean()
                df[f'price_vs_sma_{window}'] = df['Close'] / df[f'sma_{window}']
                df[f'price_vs_ema_{window}'] = df['Close'] / df[f'ema_{window}']
            
            # Volume features
            df['volume_sma'] = df['Volume'].rolling(20).mean()
            df['volume_ratio'] = df['Volume'] / df['volume_sma']
            df['volume_obv'] = (np.sign(df['Close'].diff()) * df['Volume']).cumsum()
            
            # Volatility features
            df['volatility'] = df['returns'].rolling(20).std() * np.sqrt(252)
            df['atr'] = calculate_atr(df)  # Average True Range
            
            # Momentum indicators
            df['rsi'] = calculate_rsi(df['Close'])
            df['macd'], df['macd_signal'] = calculate_macd(df['Close'])
            df['macd_histogram'] = df['macd'] - df['macd_signal']
            
            # Trend indicators
            df['adx'] = calculate_adx(df)
            
            # Support/Resistance
            df['pivot_point'] = (df['High'].shift(1) + df['Low'].shift(1) + df['Close'].shift(1)) / 3
            df['r1'] = 2 * df['pivot_point'] - df['Low'].shift(1)
            df['s1'] = 2 * df['pivot_point'] - df['High'].shift(1)
            
            # Market regime features
            df['trend_strength'] = df['Close'].rolling(50).apply(lambda x: np.polyfit(range(len(x)), x, 1)[0])
            df['market_regime'] = np.where(df['trend_strength'] > 0.001, 1, 
                                          np.where(df['trend_strength'] < -0.001, -1, 0))
            
            # Fill NaN
            df = df.fillna(0)
            
            # Select enhanced features (15 total)
            feature_cols = [
                'returns', 'log_returns',
                'sma_10', 'sma_20', 'ema_10', 'ema_20',
                'price_vs_sma_20', 'price_vs_ema_20',
                'volume_ratio', 'rsi', 'macd_histogram',
                'volatility', 'atr', 'adx',
                'market_regime'
            ]
            
            # Ensure all columns exist
            available_cols = [col for col in feature_cols if col in df.columns]
            
            if len(available_cols) >= 10:
                feature_data = df[available_cols].values.astype(np.float32)
                all_data.append((symbol, feature_data, available_cols))
                print(f"   ✅ {symbol}: {len(feature_data)} muestras, {len(available_cols)} features")
            else:
                print(f"   ⚠️  {symbol}: Features insuficientes ({len(available_cols)})")
                
        except Exception as e:
            print(f"   ❌ {symbol}: Error - {e}")
    
    return all_data

def calculate_atr(df, period=14):
    """Calculate Average True Range"""
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    return atr

def calculate_rsi(series, period=14):
    """Calculate RSI"""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_macd(series, fast=12, slow=26, signal=9):
    """Calculate MACD"""
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    macd_signal = macd.ewm(span=signal, adjust=False).mean()
    return macd, macd_signal

def calculate_adx(df, period=14):
    """Calculate ADX"""
    high = df['High']
    low = df['Low']
    close = df['Close']
    
    plus_dm = high.diff()
    minus_dm = low.diff()
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm > 0] = 0
    
    tr = pd.concat([high - low, 
                   abs(high - close.shift()), 
                   abs(low - close.shift())], axis=1).max(axis=1)
    
    atr = tr.rolling(period).mean()
    plus_di = 100 * (plus_dm.rolling(period).mean() / atr)
    minus_di = 100 * (abs(minus_dm).rolling(period).mean() / atr)
    
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.rolling(period).mean()
    
    return adx

def create_enhanced_sequences(data, seq_length=30):
    """Create sequences with enhanced targets"""
    sequences = []
    targets = []
    risk_labels = []
    
    for symbol, features, _ in data:
        if len(features) < seq_length + 1:
            continue
        
        for i in range(seq_length, len(features) - 1):
            # Input sequence
            seq = features[i-seq_length:i]
            
            # Enhanced target: consider risk-adjusted returns
            next_return = features[i, 0] if features.shape[1] > 0 else 0
            volatility = features[i, 12] if features.shape[1] > 12 else 0.01  # volatility index
            
            # Risk-adjusted return
            risk_adj_return = next_return / (volatility + 0.01)
            
            # Create target with risk consideration
            if risk_adj_return > 0.5:  # High risk-adjusted return
                target = 0  # Strong Buy
            elif risk_adj_return > 0.1:
                target = 0  # Buy
            elif risk_adj_return < -0.5:
                target = 2  # Strong Sell
            elif risk_adj_return < -0.1:
                target = 2  # Sell
            else:
                target = 1  # Hold
            
            # Risk label (position size suggestion)
            if abs(risk_adj_return) > 1.0:
                risk_label = 2  # Large position
            elif abs(risk_adj_return) > 0.3:
                risk_label = 1  # Medium position
            else:
                risk_label = 0  # Small position
            
            sequences.append(seq)
            targets.append(target)
            risk_labels.append(risk_label)
    
    return np.array(sequences), np.array(targets), np.array(risk_labels)

def train_optimized_brain(sequences, targets, risk_labels, epochs=30, batch_size=64):
    """Train optimized brain with enhanced loss"""
    print(f"\n🔥 ENTRENANDO CEREBRO OPTIMIZADO ({epochs} épocas)...")
    
    # Convert to tensors
    X = torch.FloatTensor(sequences)
    y = torch.LongTensor(targets)
    r = torch.FloatTensor(risk_labels)
    
    # Create brain
    input_dim = sequences.shape[-1]
    brain = OptimizedBrain(input_dim=input_dim, hidden_dim=256)
    
    # Multiple optimizers
    optimizer = torch.optim.AdamW(brain.parameters(), lr=0.001, weight_decay=0.01)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, 'min', patience=5, factor=0.5)
    
    # Multiple loss functions
    criterion_class = torch.nn.CrossEntropyLoss()
    criterion_risk = torch.nn.MSELoss()
    
    # Training loop
    brain.train()
    best_accuracy = 0
    patience_counter = 0
    
    for epoch in range(epochs):
        epoch_loss = 0
        correct = 0
        total = 0
        
        # Shuffle data
        indices = torch.randperm(len(X))
        X_shuffled = X[indices]
        y_shuffled = y[indices]
        r_shuffled = r[indices]
        
        # Mini-batch training
        for i in range(0, len(X_shuffled), batch_size):
            batch_X = X_shuffled[i:i+batch_size]
            batch_y = y_shuffled[i:i+batch_size]
            batch_r = r_shuffled[i:i+batch_size]
            
            # Forward pass
            decisions, risk_params, market_regime = brain(batch_X)
            
            # Calculate losses
            loss_class = criterion_class(decisions, batch_y)
            
            # Risk prediction loss
            risk_pred = risk_params[:, 0]  # Position size
            loss_risk = criterion_risk(risk_pred, batch_r / 2.0)  # Normalize
            
            # Combined loss
            loss = loss_class + 0.5 * loss_risk
            
            # Backward pass
            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(brain.parameters(), 1.0)  # Gradient clipping
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
        
        # Learning rate scheduling
        scheduler.step(avg_loss)
        
        # Early stopping with patience
        if accuracy > best_accuracy:
            best_accuracy = accuracy
            patience_counter = 0
            # Save best model
            torch.save(brain.state_dict(), 'optimized_brain_best.pth')
        else:
            patience_counter += 1
        
        if patience_counter >= 10 and epoch >= 15:
            print(f"   ⏹️  Early stopping (no improvement)")
            break
        
        # Stop if good enough
        if accuracy > 65 and epoch >= 20:
            print(f"   ✅ Accuracy suficiente alcanzada")
            break
    
    print(f"\n🎯 ENTRENAMIENTO OPTIMIZADO COMPLETADO")
    print(f"   Mejor Accuracy: {best_accuracy:.1f}%")
    print(f"   Parámetros entrenados: {sum(p.numel() for p in brain.parameters()):,}")
    
    # Load best model
    brain.load_state_dict(torch.load('optimized_brain_best.pth'))
    
    return brain

def test_optimized_brain(brain, test_data):
    """Test optimized brain with enhanced metrics"""
    print(f"\n📊 TESTING CEREBRO OPTIMIZADO...")
    
    results = {}
    
    for symbol, features, feature_names in test_data:
        if len(features) < 50:
            continue
        
        # Prepare test sequences
        seq_length = 30
        test_sequences = []
        actual_returns = []
        actual_volatilities = []
        
        for i in range(seq_length, len(features) - 1):
            seq = features[i-seq_length:i]
            test_sequences.append(seq)
            actual_returns.append(features[i, 0])  # Next return
            if features.shape[1] > 12:
                actual_volatilities.append(features[i, 12])  # Volatility
        
        if not test_sequences:
            continue
        
        # Convert to tensor
        X_test = torch.FloatTensor(test_sequences)
        
        # Make predictions
        brain.eval()
        with torch.no_grad():
            decisions, risk_params, market_regime = brain(X_test)
            _, predictions = torch.max(decisions, 1)
        
        # Calculate enhanced strategy returns with risk management
        strategy_returns = []
        position_sizes = []
        
        for i, pred in enumerate(predictions):
            if i >= len(actual_returns):
                break
            
            # Get risk parameters
            position_size = risk_params[i, 0].item()  # 0-1
            stop_loss = risk_params[i, 1].item() * 0.05  # 0-5%
            take_profit = risk_params[i, 2].item() * 0.10  # 0-10%
            confidence = risk_params[i, 3].item()
            
            # Apply position sizing
            adjusted_return = actual_returns[i] * position_size
            
            # Apply stop loss / take profit
            if adjusted_return < -stop_loss:
                adjusted_return = -stop_loss
            elif adjusted_return > take_profit:
                adjusted_return = take_profit
            
            # Decision logic with risk management
            if pred == 0:  # Buy
                strategy_returns.append(adjusted_return)
            elif pred == 2:  # Sell
                strategy_returns.append(-adjusted_return)
            else:  # Hold
                strategy_returns.append(0)
            
            position_sizes.append(position_size)
        
        # Calculate metrics
        if strategy_returns:
            strategy_returns = np.array(strategy_returns)
            market_returns = np.array(actual_returns[:len(strategy_returns)])
            
            # Basic metrics
            market_cumulative = np.cumprod(1 + market_returns)
            strategy_cumulative = np.cumprod(1 + strategy_returns)
            
            market_return = (market_cumulative[-1] - 1) * 100
            strategy_return = (strategy_cumulative[-1] - 1) * 100
            
            # Risk-adjusted metrics
            if len(strategy_returns) > 0 and strategy_returns.std() > 0:
                sharpe = (strategy_returns.mean() / strategy_returns.std()) * np.sqrt(252)
                sortino = (strategy_returns.mean() / strategy_returns[strategy_returns < 0].std()) * np.sqrt(252) if len(strategy_returns[strategy_returns < 0]) > 0 else 0
            else:
                sharpe = sortino = 0
            
            # Maximum drawdown
            cumulative = strategy_cumulative
            running_max = cumulative.expanding().max()
            drawdown = (cumulative - running_max) / running_max
            max_drawdown = drawdown.min() * 100
            
            # Win rate
            winning_trades = sum(1 for r in strategy_returns if r > 0)
            total_trades = sum(1 for r in strategy_returns if r != 0)
            win_rate = winning_trades / total_trades * 100 if total_trades > 0 else 0
            
            # Profit factor
            gross_profit = sum(r for r in strategy_returns if r > 0)
            gross_loss = abs(sum(r for r in strategy_returns if r < 0))
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
            
            # Signal distribution
            buy_count = (predictions == 0).sum().item()
            hold_count = (predictions == 1).sum().item()
            sell_count = (predictions == 2).sum().item()
            
            # Average position size
            avg_position_size = np.mean(position_sizes) * 100
            
            results[symbol] = {
                'market_return': market_return,
                'strategy_return': strategy_return,
                'alpha': strategy_return - market_return,
                'sharpe': sharpe,
                'sortino': sortino,
                'max_drawdown': max_drawdown,
                'win_rate': win_rate,
                'profit_factor': profit_factor,
                'avg_position_size': avg_position_size,
                'signals': {'BUY': buy_count, 'HOLD': hold_count, 'SELL': sell_count}
            }
            
            print(f"\n📈 {symbol}:")
            print(f"   Retorno Mercado: {market_return:.2f}%")
            print(f"   Retorno Estrategia: {strategy_return:.2f}%")
            print(f"   Alpha: {strategy_return - market_return:.2f}%")
            print(f"   Sharpe: {sharpe:.3f}")
            print(f"   Sortino: {sortino:.3f}")
            print(f"   Max Drawdown: {max_drawdown:.2f}%")
            print(f"   Win Rate: {win_rate:.1f}%")
            print(f"   Profit Factor: {profit_factor:.2f}")
            print(f"   Avg Position: {avg_position_size:.1f}%")
            print(f"   Señales: BUY={buy_count}, HOLD={hold_count}, SELL={sell_count}")
    
    return results

def main():
    """Main optimization function"""
    print("\n🔧 OPTIMIZACIÓN AVANZADA DEL CEREBRO")
    print("=" * 60)
    print("Objetivo: Sharpe > 1.5, Accuracy > 50%, Drawdown < 20%")
    print("=" * 60)
    
    try:
        # Step 1: Download enhanced data
        print("\n1. 📥 DESCARGANDO DATOS MEJORADOS...")
        training_data = download_enhanced_data(
            symbols=['BTC-USD', 'ETH-USD', 'SOL-USD'],
            days=365
        )
        
        if not training_data:
            print("❌ No se pudieron descargar datos")
            return
        
        # Step 2: Prepare enhanced sequences
        print(f"\n2. 📊 PREPARANDO SECUENCIAS MEJORADAS...")
        sequences, targets, risk_labels = create_enhanced_sequences(training_data, seq_length=30)
        
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
        r_train, r_test = risk_labels[:split_idx], risk_labels[split_idx:]
        
        print(f"   Train: {len(X_train)} secuencias")
        print(f"   Test: {len(X_test)} secuencias")
        
        # Step 4: Train optimized brain
        brain = train_optimized_brain(X_train, y_train, r_train, epochs=30, batch_size=64)
        
        # Step 5: Test optimized brain
        test_results = test_optimized_brain(brain, training_data)
        
        # Step 6: Save final model
        model_path = "optimized_brain_final.pth"
        torch.save(brain.state_dict(), model_path)
        
        print(f"\n💾 Cerebro optimizado guardado en: {model_path}")
        
        # Step 7: Summary
        print("\n" + "=" * 60)
        print("🎯 RESUMEN DE OPTIMIZACIÓN")
        print("=" * 60)
        
        if test_results:
            # Calculate averages
            symbols = list(test_results.keys())
            
            avg_sharpe = np.mean([r['sharpe'] for r in test_results.values()])
            avg_alpha = np.mean([r['alpha'] for r in test_results.values()])
            avg_drawdown = np.mean([r['max_drawdown'] for r in test_results.values()])
            avg_win_rate = np.mean([r['win_rate'] for r in test_results.values()])
            
            print(f"\n📊 PERFORMANCE PROMEDIO ({len(symbols)} símbolos):")
            print(f"   Sharpe Ratio: {avg_sharpe:.3f}")
            print(f"   Alpha: {avg_alpha:.2f}%")
            print(f"   Max Drawdown: {avg_drawdown:.2f}%")
            print(f"   Win Rate: {avg_win_rate:.1f}%")
            
            # Evaluation
            print(f"\n🎯 EVALUACIÓN:")
            
            if avg_sharpe > 1.5:
                print("   ✅ EXCELENTE - Sharpe > 1.5 (Nivel Hedge Fund)")
            elif avg_sharpe > 1.0:
                print("   ⚠️  BUENO - Sharpe > 1.0 (Nivel Profesional)")
            else:
                print("   ❌ MEJORABLE - Sharpe < 1.0 (Necesita mejora)")
            
            if avg_drawdown < 20:
                print("   ✅ EXCELENTE - Drawdown < 20% (Gestión de riesgo buena)")
            elif avg_drawdown < 30:
                print("   ⚠️  ACEPTABLE - Drawdown < 30%")
            else:
                print("   ❌ ALTO - Drawdown > 30% (Riesgo elevado)")
            
            if avg_win_rate > 60:
                print("   ✅ EXCELENTE - Win Rate > 60%")
            elif avg_win_rate > 50:
                print("   ⚠️  BUENO - Win Rate > 50%")
            else:
                print("   ❌ BAJO - Win Rate < 50%")
        
        print("\n🚀 PRÓXIMOS PASOS:")
        print("   1. Paper trading extendido (72 horas)")
        print("   2. Backtest walk-forward con nuevo cerebro")
        print("   3. Implementación con capital controlado")
        print("   4. Monitoreo continuo y ajustes")
        
        print("\n" + "=" * 60)
        print("🧠 CEREBRO OPTIMIZADO CON ÉXITO")
        print("=" * 60)
        
        return {
            'success': True,
            'model_path': model_path,
            'test_results': test_results,
            'avg_sharpe': avg_sharpe if test_results else 0,
            'avg_alpha': avg_alpha if test_results else 0,
            'avg_drawdown': avg_drawdown if test_results else 0
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
        print(f"\n✅ OPTIMIZACIÓN COMPLETADA EXITOSAMENTE")
        print(f"   Modelo: {result['model_path']}")
        if 'avg_sharpe' in result:
            print(f"   Sharpe Promedio: {result['avg_sharpe']:.3f}")
            print(f"   Alpha Promedio: {result['avg_alpha']:.2f}%")
    else:
        print(f"\n❌ OPTIMIZACIÓN FALLÓ: {result.get('error', 'Unknown error')}")
