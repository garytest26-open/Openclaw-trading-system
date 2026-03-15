import pandas as pd
import numpy as np
import yfinance as yf
from backtesting import Backtest, Strategy

# -----------------------
# SuperTrend Logic (Robust)
# -----------------------
def supertrend(high, low, close, period=10, multiplier=3):
    # ATR
    high = pd.Series(high)
    low = pd.Series(low)
    close = pd.Series(close)
    
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(period).mean().bfill() # Ensure no NaNs at start
    
    # Basic Bands
    hl2 = (high + low) / 2
    basic_upper = hl2 + (multiplier * atr)
    basic_lower = hl2 - (multiplier * atr)
    
    # Arrays for loop
    c = close.values
    bu = basic_upper.values
    bl = basic_lower.values
    
    fu = np.zeros_like(c)
    fl = np.zeros_like(c)
    trend = np.zeros_like(c) # 1 = Up, -1 = Down
    
    # Init
    fu[0] = bu[0]
    fl[0] = bl[0]
    trend[0] = 1
    
    for i in range(1, len(c)):
        # Final Upper Band
        if bu[i] < fu[i-1] or c[i-1] > fu[i-1]:
            fu[i] = bu[i]
        else:
            fu[i] = fu[i-1]
            
        # Final Lower Band
        if bl[i] > fl[i-1] or c[i-1] < fl[i-1]:
            fl[i] = bl[i]
        else:
            fl[i] = fl[i-1]
            
        # Trend Direction
        prev_trend = trend[i-1]
        
        if prev_trend == -1:
            if c[i] > fu[i-1]:
                trend[i] = 1
            else:
                trend[i] = -1
        elif prev_trend == 1:
            if c[i] < fl[i-1]:
                trend[i] = -1
            else:
                trend[i] = 1
        else:
            trend[i] = 1 # Default
            
    return trend, fu, fl

# -----------------------
# Strategy
# -----------------------
class BitcoinSuperTrend(Strategy):
    atr_period = 10
    atr_multiplier = 5.0
    
    def init(self):
        self.st_trend, self.st_upper, self.st_lower = self.I(supertrend, self.data.High, self.data.Low, self.data.Close, self.atr_period, self.atr_multiplier)

    def next(self):
        if len(self.data) < 50: return
        
        # Trend: 1 = Bull, -1 = Bear
        trend = self.st_trend[-1]
        
        # Always In Logic
        if trend == 1:
            if not self.position.is_long:
                if self.position.is_short:
                    self.position.close()
                self.buy(size=0.99)
                
        elif trend == -1:
             if not self.position.is_short:
                if self.position.is_long:
                    self.position.close()
                self.sell(size=0.99)

# -----------------------
# Data & Main
# -----------------------
def get_data_1h(period="729d"):
    print(f"Downloading BTC-USD 1h data for {period}...")
    try:
        df = yf.download("BTC-USD", period=period, interval="1h", progress=False, auto_adjust=True)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()
        df = df[df['Volume'] > 0]
        df = df[~df.index.duplicated(keep='first')]
        return df
    except Exception as e:
        print(e)
        return pd.DataFrame()

def main():
    print("--- Bitcoin SuperTrend 1H (Aggressive 10/5.0) ---")
    df = get_data_1h()
    if len(df) < 100: return

    bt = Backtest(df, BitcoinSuperTrend, cash=10000000, commission=.001, exclusive_orders=True)
    
    print("Running Validation Backtest...")
    stats = bt.run()
    print(stats)
    
    print("\nOptimizing (Real Grid Search)...")
    import itertools
    # Ranges: Period (10-30), Multiplier (2-6)
    grid = list(itertools.product([10, 14, 20, 30], [2.0, 3.0, 4.0, 5.0, 6.0]))
    
    best_ret = -99999
    best_p = {}
    
    for p, m in grid:
        BitcoinSuperTrend.atr_period = p
        BitcoinSuperTrend.atr_multiplier = m
        try:
            s = bt.run()
            r = s['Return [%]']
            t = s['# Trades']
            if r > best_ret:
                best_ret = r
                best_p = {'p': p, 'm': m}
            # Only print promising ones or every N
            if r > 0:
                print(f"P={p}, M={m} -> R={r:.2f}% | T={t}")
        except: pass
        
    print(f"\nBest Real: {best_ret:.2f}% with {best_p}")
    
    # Save Best
    if best_p:
        BitcoinSuperTrend.atr_period = best_p['p']
        BitcoinSuperTrend.atr_multiplier = best_p['m']
        bt.run()
        bt.plot(filename='btc_supertrend_1h_optimized_real.html', open_browser=False)

if __name__ == "__main__":
    main()
