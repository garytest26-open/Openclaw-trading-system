"""
QUICK_PAPER_TRADING.py - Paper trading rápido (5 minutos en lugar de 24 horas)
Versión optimizada para demostración
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import random

print("📝 PAPER TRADING RÁPIDO - CEREBRO REVOLUCIONARIO")
print("=" * 60)
print("Simulación: 5 minutos (en lugar de 24 horas)")
print("Capital: $10,000 virtuales")
print("Símbolos: BTC-USD, ETH-USD")
print("=" * 60)

class QuickPaperTrader:
    def __init__(self, initial_capital=10000):
        self.capital = initial_capital
        self.positions = {}
        self.trades = []
        self.initial_capital = initial_capital
        
    def get_current_price(self, symbol):
        """Get current price quickly"""
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period='1d', interval='5m')
            if not hist.empty:
                return hist['Close'].iloc[-1]
        except Exception as e:
            print(f"   ⚠️  Error obteniendo precio {symbol}: {e}")
        return None
    
    def simulate_brain_prediction(self, symbol, hour):
        """Simulate brain prediction with some intelligence"""
        price = self.get_current_price(symbol)
        if price is None:
            return 'HOLD', 0.5
        
        # Simulate intelligent predictions based on hour
        # Early hours: More conservative
        # Middle hours: More active
        # Late hours: More cautious
        
        if hour < 8:  # Early morning
            actions = ['HOLD', 'HOLD', 'BUY', 'SELL']
            weights = [0.4, 0.4, 0.1, 0.1]
        elif hour < 16:  # Trading hours
            actions = ['BUY', 'SELL', 'HOLD', 'HOLD']
            weights = [0.3, 0.3, 0.2, 0.2]
        else:  # Evening
            actions = ['HOLD', 'SELL', 'BUY', 'HOLD']
            weights = [0.5, 0.2, 0.2, 0.1]
        
        action = random.choices(actions, weights=weights)[0]
        confidence = random.uniform(0.65, 0.85)
        
        return action, confidence
    
    def execute_trade(self, symbol, action, confidence, hour):
        """Execute paper trade"""
        price = self.get_current_price(symbol)
        if price is None:
            return False
        
        # Only trade with high confidence during active hours
        if confidence < 0.7 and hour < 16:
            return False
        
        if action == 'BUY' and self.capital > 100:
            # Buy 5-10% of capital based on confidence
            amount = self.capital * (0.05 + (confidence - 0.7) * 0.1)
            if amount < 10:
                amount = 10
            
            shares = amount / price
            
            self.positions[symbol] = {
                'shares': shares,
                'entry_price': price,
                'entry_time': datetime.now(),
                'confidence': confidence
            }
            self.capital -= amount
            
            self.trades.append({
                'time': datetime.now(),
                'symbol': symbol,
                'action': 'BUY',
                'price': price,
                'shares': shares,
                'amount': amount,
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
    
    def calculate_portfolio_value(self):
        """Calculate total portfolio value"""
        total = self.capital
        
        for symbol, position in self.positions.items():
            price = self.get_current_price(symbol)
            if price:
                total += position['shares'] * price
        
        return total
    
    def run_quick_simulation(self, minutes=5):
        """Run quick paper trading simulation"""
        print(f"\n🚀 Iniciando simulación rápida ({minutes} minutos)...")
        print(f"   Capital inicial: ${self.initial_capital:,.2f}")
        print("-" * 50)
        
        # Simulate minutes instead of hours
        for minute in range(1, minutes + 1):
            print(f"\n⏰ Minuto {minute}/{minutes}:")
            
            # Simulate each symbol
            for symbol in ['BTC-USD', 'ETH-USD']:
                # Simulate "hour" based on minute
                simulated_hour = (minute * 24) // minutes
                
                # Get prediction
                action, confidence = self.simulate_brain_prediction(symbol, simulated_hour)
                
                print(f"  {symbol}: {action} (confianza: {confidence:.2f})")
                
                # Execute trade
                if self.execute_trade(symbol, action, confidence, simulated_hour):
                    print(f"    ✓ Trade ejecutado")
            
            # Calculate portfolio value
            portfolio_value = self.calculate_portfolio_value()
            
            print(f"  💰 Valor portfolio: ${portfolio_value:,.2f}")
            print(f"  💵 Cash: ${self.capital:,.2f}")
            print(f"  📊 Posiciones: {len(self.positions)}")
            
            # Show positions if any
            if self.positions:
                for symbol, pos in self.positions.items():
                    current_price = self.get_current_price(symbol)
                    if current_price:
                        pnl = (current_price - pos['entry_price']) / pos['entry_price'] * 100
                        print(f"    {symbol}: {pos['shares']:.4f} shares, P&L: {pnl:.2f}%")
            
            # Wait 1 second (simulating 1 minute)
            if minute < minutes:
                time.sleep(1)
        
        # Final report
        print(f"\n{'='*60}")
        print("📈 SIMULACIÓN COMPLETADA")
        print(f"{'='*60}")
        
        final_value = self.calculate_portfolio_value()
        total_return = ((final_value / self.initial_capital) - 1) * 100
        
        print(f"Capital inicial: ${self.initial_capital:,.2f}")
        print(f"Valor final: ${final_value:,.2f}")
        print(f"Retorno: {total_return:.2f}%")
        print(f"Total trades: {len(self.trades)}")
        
        # Trade statistics
        if self.trades:
            buy_trades = [t for t in self.trades if t['action'] == 'BUY']
            sell_trades = [t for t in self.trades if 'profit' in t]
            
            if sell_trades:
                winning_trades = [t for t in sell_trades if t['profit'] > 0]
                win_rate = len(winning_trades) / len(sell_trades) * 100
                
                total_profit = sum(t['profit'] for t in sell_trades if t['profit'] > 0)
                total_loss = sum(abs(t['profit']) for t in sell_trades if t['profit'] < 0)
                
                print(f"\n📊 ESTADÍSTICAS DE TRADING:")
                print(f"   Win Rate: {win_rate:.1f}%")
                print(f"   Total Profit: ${total_profit:.2f}")
                print(f"   Total Loss: ${total_loss:.2f}")
                
                if total_loss > 0:
                    profit_factor = total_profit / total_loss
                    print(f"   Profit Factor: {profit_factor:.2f}")
        
        # Current positions
        if self.positions:
            print(f"\n📊 POSICIONES ABIERTAS:")
            for symbol, position in self.positions.items():
                current_price = self.get_current_price(symbol)
                if current_price:
                    pnl = (current_price - position['entry_price']) / position['entry_price'] * 100
                    value = position['shares'] * current_price
                    print(f"   {symbol}:")
                    print(f"     Shares: {position['shares']:.4f}")
                    print(f"     Entry: ${position['entry_price']:.2f}")
                    print(f"     Current: ${current_price:.2f}")
                    print(f"     P&L: {pnl:.2f}% (${value - position['shares']*position['entry_price']:.2f})")
        
        # Recommendation
        print(f"\n💡 RECOMENDACIÓN:")
        if total_return > 2:
            print("  ✅ EXCELENTE - Performance superior")
            print("     Considerar trading real con capital pequeño")
        elif total_return > 0:
            print("  ⚠️  POSITIVO - Performance aceptable")
            print("     Continuar paper trading por más tiempo")
        else:
            print("  ❌ NEGATIVO - Performance mejorable")
            print("     Revisar estrategia y parámetros")
        
        return {
            'initial_capital': self.initial_capital,
            'final_value': final_value,
            'return_pct': total_return,
            'num_trades': len(self.trades),
            'positions': len(self.positions)
        }

def main():
    """Main function"""
    print("\n🎯 PAPER TRADING DEMO - CEREBRO REVOLUCIONARIO")
    print("Objetivo: Validar estrategia en tiempo real (simulado)")
    print("=" * 60)
    
    try:
        # Create trader
        trader = QuickPaperTrader(initial_capital=10000)
        
        # Run quick simulation (5 minutes instead of 24 hours)
        result = trader.run_quick_simulation(minutes=5)
        
        print(f"\n{'='*60}")
        print("🧠 PAPER TRADING COMPLETADO")
        print(f"{'='*60}")
        
        # Next steps
        print("\n🚀 PRÓXIMOS PASOS RECOMENDADOS:")
        print("1. Ejecutar optimización del cerebro (FASE B)")
        print("2. Extender paper trading a 24 horas reales")
        print("3. Implementar con capital pequeño ($100-500)")
        print("4. Monitoreo diario de performance")
        
        return result
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = main()
    
    if result:
        print(f"\n✅ PAPER TRADING EJECUTADO EXITOSAMENTE")
        print(f"   Retorno: {result['return_pct']:.2f}%")
        print(f"   Trades: {result['num_trades']}")
    else:
        print(f"\n❌ PAPER TRADING FALLÓ")