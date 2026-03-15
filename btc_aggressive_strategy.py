import pandas as pd
import numpy as np
import yfinance as yf
from backtesting import Backtest, Strategy
from backtesting.lib import crossover

# -----------------------
# Indicadores
# -----------------------

def rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def macd(series, fast=12, slow=26, signal=9):
    ema_fast = ema(series, fast)
    ema_slow = ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal)
    return macd_line, signal_line

def atr_arrays(high, low, close, period=14):
    high = pd.Series(high)
    low = pd.Series(low)
    close = pd.Series(close)
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(period).mean()

# -----------------------
# Estrategia: Bitcoin Aggressive Momentum
# -----------------------

class BitcoinMomentum(Strategy):
    # Parámetros optimizables
    rsi_period = 14
    macd_fast = 12
    macd_slow = 26
    macd_signal = 9
    ema_trend = 200
    atr_period = 14
    sl_atr_mult = 1.5
    tp_atr_mult = 3.0

    def init(self):
        # RSI
        self.rsi = self.I(rsi, pd.Series(self.data.Close), self.rsi_period)
        
        # MACD
        self.macd_line, self.signal_line = self.I(macd, pd.Series(self.data.Close), self.macd_fast, self.macd_slow, self.macd_signal)
        
        # Trend EMA
        self.ema200 = self.I(ema, pd.Series(self.data.Close), self.ema_trend)
        
        # ATR
        self.atr = self.I(atr_arrays, self.data.High, self.data.Low, self.data.Close, self.atr_period)

    def next(self):
        if np.isnan(self.ema200[-1]) or np.isnan(self.macd_line[-1]):
            return

        price = self.data.Close[-1]
        
        # Logic
        strong_bull = self.rsi[-1] > 55 and self.macd_line[-1] > self.signal_line[-1]
        strong_bear = self.rsi[-1] < 45 and self.macd_line[-1] < self.signal_line[-1]
        
        trend_bull = price > self.ema200[-1]
        trend_bear = price < self.ema200[-1]
        
        # Entries
        if not self.position:
            # Long
            if strong_bull and trend_bull:
                self.entry_long(price)
            # Short
            elif strong_bear and trend_bear:
                self.entry_short(price)

    def entry_long(self, price):
        atr_val = self.atr[-1]
        sl = price - (atr_val * self.sl_atr_mult)
        tp = price + (atr_val * self.tp_atr_mult)
        self.buy(sl=sl, tp=tp, size=0.5)

    def entry_short(self, price):
        atr_val = self.atr[-1]
        sl = price + (atr_val * self.sl_atr_mult)
        tp = price - (atr_val * self.tp_atr_mult)
        self.sell(sl=sl, tp=tp, size=0.5)

# -----------------------
# Data & Main
# -----------------------

def get_data(ticker="BTC-USD", period="60d", interval="15m"):
    print(f"Downloading {ticker} data ({period}, {interval})...")
    try:
        df = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=True)
    except Exception as e:
        print(f"YF Download Error: {e}")
        return pd.DataFrame()
        
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)
    
    df = df[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()
    df = df[df['Volume'] > 0]
    df = df[~df.index.duplicated(keep='first')]
    return df

def main():
    print("--- Bitcoin Aggressive Momentum ---")
    
    df_15m = get_data(period="59d", interval="15m")
    if len(df_15m) == 0: return
    print(f"Data loaded: {len(df_15m)} bars.")

    bt = Backtest(df_15m, BitcoinMomentum, cash=10000000, commission=.001, exclusive_orders=True)
    
    print("\nRunning Initial Backtest (15m)...")
    try:
        stats = bt.run()
        print(stats)
    except Exception as e:
        print(e)
        return
    
    # 2. Optimization (Manual Grid Search)
    print("\nOptimizing Momentum Strategy (Grid Search)...")
    
    import itertools
    
    # Define ranges
    rsi_periods = [14]
    sl_mults = [1.5, 2.0, 2.5]
    tp_mults = [2.0, 3.0, 4.0]
    ema_trends = [200]
    
    param_grid = list(itertools.product(rsi_periods, sl_mults, tp_mults, ema_trends))
    print(f"Testing {len(param_grid)} combinations...")
    
    best_stats = None
    best_return = -99999
    best_params = {}
    
    for i, (rsi_p, sl_m, tp_m, ema_t) in enumerate(param_grid):
        BitcoinMomentum.rsi_period = rsi_p
        BitcoinMomentum.sl_atr_mult = sl_m
        BitcoinMomentum.tp_atr_mult = tp_m
        BitcoinMomentum.ema_trend = ema_t
        
        try:
            stats = bt.run()
            ret = stats['Return [%]']
            n_trades = stats['# Trades']
            
            if i % 10 == 0: print(f"Run {i}: R={ret:.2f}%, T={n_trades}")
            
            if n_trades > 5 and ret > best_return:
                best_return = ret
                best_stats = stats
                best_params = {'rsi': rsi_p, 'sl': sl_m, 'tp': tp_m, 'ema': ema_t}
        except: pass

    print("\n--- Optimized Results (15m Momentum) ---")
    if best_stats is not None:
        print(f"Best Return: {best_return:.2f}%")
        print("Best Parameters:", best_params)
        print(best_stats)
        
        BitcoinMomentum.rsi_period = best_params['rsi']
        BitcoinMomentum.sl_atr_mult = best_params['sl']
        BitcoinMomentum.tp_atr_mult = best_params['tp']
        BitcoinMomentum.ema_trend = best_params['ema']
        
        bt.run()
        bt.plot(filename='btc_momentum_15m.html', open_browser=False)
        print("Saved to btc_momentum_15m.html")
    else:
        print("No profitable combination found.")

if __name__ == "__main__":
    main()
