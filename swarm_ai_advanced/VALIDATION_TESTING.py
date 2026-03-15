"""
VALIDATION_TESTING.py - Validación extendida del cerebro entrenado
Walk-forward + Stress testing + Paper trading setup
"""

import torch
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

print("🔬 VALIDACIÓN EXTENDIDA - CEREBRO REVOLUCIONARIO")
print("=" * 60)

# Load the trained brain
from FAST_TRAINING import FastBrain

def load_trained_brain(model_path="fast_brain_trained.pth"):
    """Load the trained brain"""
    print("🧠 Cargando cerebro entrenado...")
    
    # Create brain with same architecture
    brain = FastBrain(input_dim=8, hidden_dim=128)  # 8 features from training
    
    try:
        brain.load_state_dict(torch.load(model_path))
        brain.eval()
        print(f"✅ Cerebro cargado: {sum(p.numel() for p in brain.parameters()):,} parámetros")
        return brain
    except Exception as e:
        print(f"❌ Error cargando cerebro: {e}")
        return None

def walk_forward_validation(brain, symbol='BTC-USD', total_days=365, window_days=90):
    """
    Walk-forward validation: Train on window, test on next period
    """
    print(f"\n🚶‍♂️ WALK-FORWARD VALIDATION: {symbol}")
    print(f"   Período total: {total_days} días")
    print(f"   Ventana deslizante: {window_days} días")
    print("-" * 40)
    
    # Download full data
    end_date = datetime.now()
    start_date = end_date - timedelta(days=total_days)
    
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start_date, end=end_date, interval='1d')
        
        if df.empty:
            print(f"   ❌ Sin datos para {symbol}")
            return None
        
        # Calculate features (same as training)
        df['returns'] = df['Close'].pct_change()
        df['sma_10'] = df['Close'].rolling(10).mean()
        df['sma_20'] = df['Close'].rolling(20).mean()
        df['volume_sma'] = df['Volume'].rolling(20).mean()
        df['volume_ratio'] = df['Volume'] / df['volume_sma']
        
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
        features = df[feature_cols].values.astype(np.float32)
        
        # Walk-forward windows
        window_size = window_days
        step_size = 30  # Test every 30 days
        
        results = []
        
        for start_idx in range(0, len(features) - window_size - step_size, step_size):
            train_end = start_idx + window_size
            test_start = train_end
            test_end = min(test_start + step_size, len(features))
            
            if test_end - test_start < 10:  # Need minimum test data
                continue
            
            # Train window (simulate retraining)
            train_features = features[start_idx:train_end]
            
            # Test window
            test_features = features[test_start:test_end]
            
            # Simulate predictions on test window
            test_sequences = []
            actual_returns = []
            
            seq_length = 30
            for i in range(seq_length, len(test_features) - 1):
                if i >= len(test_features):
                    break
                seq = test_features[i-seq_length:i]
                test_sequences.append(seq)
                actual_returns.append(test_features[i, 0])
            
            if not test_sequences:
                continue
            
            # Make predictions
            X_test = torch.FloatTensor(test_sequences)
            
            with torch.no_grad():
                decisions, risk_params = brain(X_test)
                _, predictions = torch.max(decisions, 1)
            
            # Calculate test performance
            strategy_returns = []
            for i, pred in enumerate(predictions):
                if i >= len(actual_returns):
                    break
                
                if pred == 0:  # Buy
                    strategy_returns.append(actual_returns[i])
                elif pred == 2:  # Sell
                    strategy_returns.append(-actual_returns[i])
                else:  # Hold
                    strategy_returns.append(0)
            
            if strategy_returns:
                strategy_returns = np.array(strategy_returns)
                market_returns = np.array(actual_returns[:len(strategy_returns)])
                
                # Calculate metrics
                market_cumulative = np.cumprod(1 + market_returns)
                strategy_cumulative = np.cumprod(1 + strategy_returns)
                
                market_return = (market_cumulative[-1] - 1) * 100
                strategy_return = (strategy_cumulative[-1] - 1) * 100
                
                if len(strategy_returns) > 0 and strategy_returns.std() > 0:
                    sharpe = (strategy_returns.mean() / strategy_returns.std()) * np.sqrt(252)
                else:
                    sharpe = 0
                
                # Store results
                window_start = df.index[start_idx]
                window_end = df.index[test_end-1]
                
                results.append({
                    'window': f"{window_start.date()} to {window_end.date()}",
                    'market_return': market_return,
                    'strategy_return': strategy_return,
                    'sharpe': sharpe,
                    'alpha': strategy_return - market_return
                })
                
                print(f"   📅 {window_start.date()}-{window_end.date()}: "
                      f"Mkt={market_return:6.2f}%, Str={strategy_return:6.2f}%, "
                      f"Alpha={strategy_return-market_return:6.2f}%, Sharpe={sharpe:.3f}")
        
        # Summary statistics
        if results:
            print(f"\n📊 RESUMEN WALK-FORWARD ({len(results)} ventanas):")
            
            avg_market = np.mean([r['market_return'] for r in results])
            avg_strategy = np.mean([r['strategy_return'] for r in results])
            avg_sharpe = np.mean([r['sharpe'] for r in results])
            avg_alpha = np.mean([r['alpha'] for r in results])
            
            win_rate = sum(1 for r in results if r['alpha'] > 0) / len(results) * 100
            
            print(f"   Retorno Mercado Promedio: {avg_market:.2f}%")
            print(f"   Retorno Estrategia Promedio: {avg_strategy:.2f}%")
            print(f"   Alpha Promedio: {avg_alpha:.2f}%")
            print(f"   Sharpe Promedio: {avg_sharpe:.3f}")
            print(f"   Win Rate: {win_rate:.1f}%")
            
            return {
                'avg_market_return': avg_market,
                'avg_strategy_return': avg_strategy,
                'avg_sharpe': avg_sharpe,
                'avg_alpha': avg_alpha,
                'win_rate': win_rate,
                'num_windows': len(results)
            }
        
    except Exception as e:
        print(f"❌ Error en walk-forward: {e}")
    
    return None

def stress_testing(brain, symbol='BTC-USD'):
    """
    Stress testing with historical crisis scenarios
    """
    print(f"\n🌪️  STRESS TESTING: {symbol}")
    print("   Simulando condiciones extremas...")
    print("-" * 40)
    
    # Define crisis periods (approximate dates)
    crisis_periods = [
        # COVID crash 2020
        ('2020-02-20', '2020-03-23', 'COVID Crash'),
        # Crypto winter 2018
        ('2018-01-07', '2018-12-15', 'Crypto Winter 2018'),
        # FTX collapse 2022
        ('2022-11-05', '2022-11-22', 'FTX Collapse'),
    ]
    
    results = []
    
    for start_date, end_date, crisis_name in crisis_periods:
        try:
            # Download crisis period data
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start_date, end=end_date, interval='1d')
            
            if df.empty:
                # Try with BTC-USD if symbol doesn't have that history
                if symbol != 'BTC-USD':
                    ticker = yf.Ticker('BTC-USD')
                    df = ticker.history(start=start_date, end=end_date, interval='1d')
            
            if df.empty or len(df) < 20:
                print(f"   ⚠️  {crisis_name}: Datos insuficientes")
                continue
            
            # Calculate features
            df['returns'] = df['Close'].pct_change()
            df['sma_10'] = df['Close'].rolling(10).mean()
            df['sma_20'] = df['Close'].rolling(20).mean()
            df['volume_sma'] = df['Volume'].rolling(20).mean()
            df['volume_ratio'] = df['Volume'] / df['volume_sma']
            
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
            features = df[feature_cols].values.astype(np.float32)
            
            # Simulate brain predictions
            seq_length = 30
            test_sequences = []
            actual_returns = []
            
            for i in range(seq_length, len(features) - 1):
                if i >= len(features):
                    break
                seq = features[i-seq_length:i]
                test_sequences.append(seq)
                actual_returns.append(features[i, 0])
            
            if not test_sequences:
                continue
            
            X_test = torch.FloatTensor(test_sequences)
            
            with torch.no_grad():
                decisions, risk_params = brain(X_test)
                _, predictions = torch.max(decisions, 1)
            
            # Calculate performance during crisis
            strategy_returns = []
            for i, pred in enumerate(predictions):
                if i >= len(actual_returns):
                    break
                
                if pred == 0:  # Buy
                    strategy_returns.append(actual_returns[i])
                elif pred == 2:  # Sell
                    strategy_returns.append(-actual_returns[i])
                else:  # Hold
                    strategy_returns.append(0)
            
            if strategy_returns:
                strategy_returns = np.array(strategy_returns)
                market_returns = np.array(actual_returns[:len(strategy_returns)])
                
                market_cumulative = np.cumprod(1 + market_returns)
                strategy_cumulative = np.cumprod(1 + strategy_returns)
                
                market_return = (market_cumulative[-1] - 1) * 100
                strategy_return = (strategy_cumulative[-1] - 1) * 100
                
                # Maximum drawdown during crisis
                cumulative = strategy_cumulative
                running_max = cumulative.expanding().max()
                drawdown = (cumulative - running_max) / running_max
                max_drawdown = drawdown.min() * 100
                
                results.append({
                    'crisis': crisis_name,
                    'period': f"{start_date} to {end_date}",
                    'market_return': market_return,
                    'strategy_return': strategy_return,
                    'max_drawdown': max_drawdown,
                    'protection': strategy_return - market_return
                })
                
                print(f"   {crisis_name}:")
                print(f"     Mercado: {market_return:6.2f}%")
                print(f"     Estrategia: {strategy_return:6.2f}%")
                print(f"     Protección: {strategy_return - market_return:6.2f}%")
                print(f"     Max Drawdown: {max_drawdown:6.2f}%")
        
        except Exception as e:
            print(f"   ❌ Error en {crisis_name}: {e}")
    
    return results

def paper_trading_setup(brain):
    """
    Setup for paper trading simulation
    """
    print(f"\n📝 PAPER TRADING SETUP")
    print("   Configurando simulación de trading real...")
    print("-" * 40)
    
    setup_code = """
# PAPER TRADING SYSTEM - CEREBRO REVOLUCIONARIO
# Simulación de trading con $10,000 virtuales

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time

class PaperTradingBot:
    def __init__(self, brain_model, initial_capital=10000):
        self.brain = brain_model
        self.capital = initial_capital
        self.positions = {}
        self.trade_history = []
        self.current_prices = {}
        
    def update_prices(self, symbols):
        '''Update current prices for symbols'''
        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period='1d', interval='1h')
                if not hist.empty:
                    self.current_prices[symbol] = hist['Close'].iloc[-1]
            except:
                pass
    
    def generate_features(self, symbol):
        '''Generate features for brain prediction'''
        # Download recent data
        ticker = yf.Ticker(symbol)
        df = ticker.history(period='10d', interval='1h')
        
        if df.empty or len(df) < 50:
            return None
        
        # Calculate features (same as training)
        df['returns'] = df['Close'].pct_change()
        df['sma_10'] = df['Close'].rolling(10).mean()
        df['sma_20'] = df['Close'].rolling(20).mean()
        df['volume_sma'] = df['Volume'].rolling(20).mean()
        df['volume_ratio'] = df['Volume'] / df['volume_sma']
        
        delta = df['Close'].diff()
        gain = (delta.where(delta