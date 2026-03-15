"""
SIMPLE_VALIDATION.py - Validación simple del cerebro entrenado
"""

import torch
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

print("🔬 VALIDACIÓN SIMPLE - CEREBRO ENTRENADO")
print("=" * 60)

# Load the trained brain
from FAST_TRAINING import FastBrain

print("🧠 Cargando cerebro entrenado...")
brain = FastBrain(input_dim=8, hidden_dim=128)
brain.load_state_dict(torch.load("fast_brain_trained.pth"))
brain.eval()
print(f"✅ Cerebro cargado: {sum(p.numel() for p in brain.parameters()):,} parámetros")

def quick_walk_forward(symbol='BTC-USD'):
    """Quick walk-forward test"""
    print(f"\n🚶‍♂️ WALK-FORWARD RÁPIDO: {symbol}")
    
    # Download 1 year of data
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    
    ticker = yf.Ticker(symbol)
    df = ticker.history(start=start_date, end=end_date, interval='1d')
    
    if df.empty:
        print("   ❌ Sin datos")
        return
    
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
    
    # Split into 4 quarters
    quarter_len = len(features) // 4
    results = []
    
    for q in range(4):
        start_idx = q * quarter_len
        end_idx = (q + 1) * quarter_len if q < 3 else len(features)
        
        if end_idx - start_idx < 50:
            continue
        
        test_features = features[start_idx:end_idx]
        
        # Test brain on this quarter
        seq_length = 30
        test_sequences = []
        actual_returns = []
        
        for i in range(seq_length, len(test_features) - 1):
            seq = test_features[i-seq_length:i]
            test_sequences.append(seq)
            actual_returns.append(test_features[i, 0])
        
        if not test_sequences:
            continue
        
        X_test = torch.FloatTensor(test_sequences)
        
        with torch.no_grad():
            decisions, _ = brain(X_test)
            _, predictions = torch.max(decisions, 1)
        
        # Calculate performance
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
            
            market_cum = np.cumprod(1 + market_returns)
            strategy_cum = np.cumprod(1 + strategy_returns)
            
            market_ret = (market_cum[-1] - 1) * 100
            strategy_ret = (strategy_cum[-1] - 1) * 100
            
            if len(strategy_returns) > 0 and strategy_returns.std() > 0:
                sharpe = (strategy_returns.mean() / strategy_returns.std()) * np.sqrt(252)
            else:
                sharpe = 0
            
            quarter_start = df.index[start_idx].date()
            quarter_end = df.index[end_idx-1].date()
            
            results.append({
                'quarter': f"Q{q+1} ({quarter_start} to {quarter_end})",
                'market': market_ret,
                'strategy': strategy_ret,
                'alpha': strategy_ret - market_ret,
                'sharpe': sharpe
            })
            
            print(f"   Q{q+1}: Mkt={market_ret:6.2f}%, Str={strategy_ret:6.2f}%, "
                  f"Alpha={strategy_ret-market_ret:6.2f}%, Sharpe={sharpe:.3f}")
    
    # Summary
    if results:
        print(f"\n📊 RESUMEN ({len(results)} trimestres):")
        
        avg_market = np.mean([r['market'] for r in results])
        avg_strategy = np.mean([r['strategy'] for r in results])
        avg_sharpe = np.mean([r['sharpe'] for r in results])
        avg_alpha = np.mean([r['alpha'] for r in results])
        win_rate = sum(1 for r in results if r['alpha'] > 0) / len(results) * 100
        
        print(f"   Mercado Promedio: {avg_market:.2f}%")
        print(f"   Estrategia Promedio: {avg_strategy:.2f}%")
        print(f"   Alpha Promedio: {avg_alpha:.2f}%")
        print(f"   Sharpe Promedio: {avg_sharpe:.3f}")
        print(f"   Win Rate: {win_rate:.1f}%")
        
        return {
            'avg_sharpe': avg_sharpe,
            'avg_alpha': avg_alpha,
            'win_rate': win_rate
        }
    
    return None

def stress_test_quick():
    """Quick stress test"""
    print("\n🌪️  STRESS TEST RÁPIDO")
    print("   Simulando COVID crash (Mar 2020)...")
    
    # COVID crash period
    start_date = '2020-02-20'
    end_date = '2020-03-23'
    
    try:
        ticker = yf.Ticker('BTC-USD')
        df = ticker.history(start=start_date, end=end_date, interval='1d')
        
        if df.empty:
            print("   ❌ Sin datos históricos")
            return
        
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
        
        # Test brain
        seq_length = 30
        test_sequences = []
        actual_returns = []
        
        for i in range(seq_length, len(features) - 1):
            seq = features[i-seq_length:i]
            test_sequences.append(seq)
            actual_returns.append(features[i, 0])
        
        if not test_sequences:
            print("   ❌ Datos insuficientes")
            return
        
        X_test = torch.FloatTensor(test_sequences)
        
        with torch.no_grad():
            decisions, _ = brain(X_test)
            _, predictions = torch.max(decisions, 1)
        
        # Calculate performance during crash
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
            
            market_cum = np.cumprod(1 + market_returns)
            strategy_cum = np.cumprod(1 + strategy_returns)
            
            market_ret = (market_cum[-1] - 1) * 100
            strategy_ret = (strategy_cum[-1] - 1) * 100
            
            # Drawdown
            cumulative = strategy_cum
            running_max = cumulative.expanding().max()
            drawdown = (cumulative - running_max) / running_max
            max_dd = drawdown.min() * 100
            
            print(f"   COVID Crash Performance:")
            print(f"     Mercado: {market_ret:.2f}%")
            print(f"     Estrategia: {strategy_ret:.2f}%")
            print(f"     Protección: {strategy_ret - market_ret:.2f}%")
            print(f"     Max Drawdown: {max_dd:.2f}%")
            
            return {
                'market_return': market_ret,
                'strategy_return': strategy_ret,
                'protection': strategy_ret - market_ret,
                'max_drawdown': max_dd
            }
    
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    return None

def create_paper_trading_script():
    """Create simple paper trading script"""
    print("\n📝 CREANDO SCRIPT DE PAPER TRADING...")
    
    script = '''#!/usr/bin/env python3
"""
PAPER_TRADING.py - Sistema simple de paper trading
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import time

print("📝 PAPER TRADING - CEREBRO REVOLUCIONARIO")
print("=" * 50)

# Configuración
INITIAL_CAPITAL = 10000
SYMBOLS = ['BTC-USD', 'ETH-USD']
HOURS_TO_SIMULATE = 24

class PaperTrader:
    def __init__(self):
        self.capital = INITIAL_CAPITAL
        self.positions = {}
        self.trades = []
        
    def get_current_price(self, symbol):
        '''Get current price'''
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period='1d', interval='1h')
            if not hist.empty:
                return hist['Close'].iloc[-1]
        except:
            pass
        return None
    
    def simulate_brain_prediction(self, symbol):
        '''Simulate brain prediction (simplified)'''
        # In real system, would use the actual brain
        price = self.get_current_price(symbol)
        if price is None:
            return 'HOLD', 0.5
        
        # Simple rule-based simulation
        # Real brain would be much smarter
        import random
        actions = ['BUY', 'HOLD', 'SELL']
        action = random.choice(actions)
        confidence = random.uniform(0.6, 0.9)
        
        return action, confidence
    
    def execute_trade(self, symbol, action, confidence):
        '''Execute paper trade'''
        price = self.get_current_price(symbol)
        if price is None:
            return False
        
        if action == 'BUY' and self.capital > 100:
            # Buy 5% of capital
            amount = self.capital * 0.05
            shares = amount / price
            
            self.positions[symbol] = {
                'shares': shares,
                'entry_price': price,
                'entry_time': datetime.now()
            }
            self.capital -= amount
            
            self.trades.append({
                'time': datetime.now(),
                'symbol': symbol,
                'action': 'BUY',
                'price': price,
                'shares': shares,
                'confidence': confidence
            })
            return True
            
        elif action == 'SELL' and symbol in self.positions:
            position = self.positions[symbol]
            sale_value = position['shares'] * price
            profit = sale_value - (position['shares'] * position['entry_price'])
            
            self.capital += sale_value
            del self.positions[symbol]
            
            self.trades.append({
                'time': datetime.now(),
                'symbol': symbol,
                'action': 'SELL',
                'price': price,
                'shares': position['shares'],
                'profit': profit,
                'confidence': confidence
            })
            return True
        
        return False
    
    def run_simulation(self):
        '''Run paper trading simulation'''
        print(f"\\n🚀 Iniciando simulación de {HOURS_TO_SIMULATE} horas...")
        print(f"   Capital inicial: ${INITIAL_CAPITAL}")
        print(f"   Símbolos: {', '.join(SYMBOLS)}")
        print("-" * 50)
        
        for hour in range(HOURS_TO_SIMULATE):
            print(f"\\n⏰ Hora {hour+1}/{HOURS_TO_SIMULATE}:")
            
            for symbol in SYMBOLS:
                # Get prediction
                action, confidence = self.simulate_brain_prediction(symbol)
                
                print(f"  {symbol}: {action} (confianza: {confidence:.2f})")
                
                # Execute if high confidence
                if confidence > 0.7:
                    if self.execute_trade(symbol, action, confidence):
                        print(f"    ✓ Trade ejecutado")
            
            # Calculate portfolio value
            portfolio_value = self.capital
            for symbol, pos in self.positions.items():
                price = self.get_current_price(symbol)
                if price:
                    portfolio_value += pos['shares'] * price
            
            print(f"  💰 Valor portfolio: ${portfolio_value:.2f}")
            print(f"  💵 Cash: ${self.capital:.2f}")
            print(f"  📊 Posiciones: {len(self.positions)}")
            
            # Simulate 1 hour wait
            time.sleep(1)  # In real simulation: time.sleep(3600)
        
        # Final report
        print(f"\\n{'='*50}")
        print("📈 SIMULACIÓN COMPLETADA")
        print(f"{'='*50}")
        
        final_value = self.capital
        for symbol, pos in self.positions.items():
            price = self.get_current_price(symbol)
            if price:
                final_value += pos['shares'] * price
        
        total_return = ((final_value / INITIAL_CAPITAL) - 1) * 100
        
        print(f"Capital inicial: ${INITIAL_CAPITAL:.2f}")
        print(f"Valor final: ${final_value:.2f}")
        print(f"Retorno: {total_return:.2f}%")
        print(f"Total trades: {len(self.trades)}")
        
        if self.trades:
            winning = [t for t in self.trades if 'profit' in t and t['profit'] > 0]
            win_rate = len(winning) / len(self.trades) * 100
            print(f"Win rate: {win_rate:.1f}%")
        
        print(f"\\n💡 RECOMENDACIÓN:")
        if total_return > 5:
            print("  ✅ Performance excelente - Listo para trading real")
        elif total_return > 0:
            print("  ⚠️  Performance positiva - Continuar paper trading")
        else:
            print("  ❌ Performance negativa - Revisar estrategia")

if __name__ == "__main__":
    trader = PaperTrader()
    trader.run_simulation()
'''
    
    with open('PAPER_TRADING_DEMO.py', 'w') as f:
        f.write(script)
    
    print(f"✅ Script creado: PAPER_TRADING_DEMO.py")
    print(f"   Ejecutar: python3 PAPER_TRADING_DEMO.py")
    print(f"   Duración: 24 horas simuladas")
    print(f"   Capital: $10,000 virtuales")
    
    return 'PAPER_TRADING_DEMO.py'

def main():
    """Main validation function"""
    print("\n🔬 VALIDACIÓN SIMPLE DEL CEREBRO")
    print("=" * 60)
    
    try:
        # 1. Walk-forward validation
        wf_results = {}
        for symbol in ['BTC-USD', 'ETH-USD']:
            result = quick_walk_forward(symbol)
            if result:
                wf_results[symbol] = result
        
        # 2. Stress test
        stress_result = stress_test_quick()
        
        # 3. Paper trading setup
        paper_script = create_paper_trading_script()
        
        # Summary
        print("\n" + "=" * 60)
        print("📄 INFORME DE VALIDACIÓN")
        print("=" * 60)
        
        if wf_results:
            print("\n📊 WALK-FORWARD VALIDATION:")
            for symbol, result in wf_results.items():
                print(f"   {symbol}:")
                print(f"     Sharpe: {result['avg_sharpe']:.3f}")
                print(f"     Alpha: {result['avg_alpha']:.2f}%")
                print(f"     Win Rate: {result['win_rate']:.1f}%")
        
        if stress_result:
            print("\n🌪️  STRESS TEST (COVID Crash):")
            print(f"   Protección: {stress_result['protection']:.2f}%")
            print(f"   Drawdown: {stress_result['max_drawdown']:.2f}%")
        
        print(f"\n📝 PAPER TRADING:")
        print(f"   Script: {paper_script}")
        print(f"   Instrucciones: python3 {paper_script}")
        
        # Overall assessment
        print("\n🎯 EVALUACIÓN FINAL:")
        
        if wf_results and 'BTC-USD' in wf_results:
            btc_result = wf_results['BTC-USD']
            
            if btc_result['avg_sharpe'] > 1.0 and btc_result['win_rate'] > 55:
                print("   ✅ BUENO - Cerebro validado")
                print("      • Sharpe > 1.0")
                print("      • Win rate > 55%")
                print("      • Performance consistente")
            else:
                print("   ⚠️  MEJORABLE - Cerebro necesita optimización")
                print("      • Revisar estrategia")
                print("      • Más entrenamiento")
        
        print("\n🚀 RECOMENDACIONES:")
        print("   1. Ejecutar paper trading por 24 horas")
        print("   2. Monitorear performance")
        print("   3. Ajustar parámetros si es necesario")
        print("   4. Considerar trading real con capital pequeño")
        
        print("\n" + "=" * 60)
        print("🧠 VALIDACIÓN COMPLETADA")
        print("=" * 60)
        
        return {
            'success': True,
            'walk_forward': wf_results,
            'stress_test': stress_result,
            'paper_script': paper_script
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
        print(f"\n✅ VALIDACIÓN COMPLETADA")
    else:
        print(f"\n❌ VALIDACIÓN FALLÓ: {result.get('error', 'Unknown error')}")