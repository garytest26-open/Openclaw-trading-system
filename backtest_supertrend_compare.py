import pandas as pd
import numpy as np
import yfinance as yf
from backtesting import Backtest, Strategy
import warnings
warnings.filterwarnings('ignore')

def calc_ema(close, period=200):
    return pd.Series(close).ewm(span=period, adjust=False).mean()

# -----------------------
# SuperTrend Logic
# -----------------------
def supertrend(high, low, close, period=10, multiplier=5.0):
    high = pd.Series(high)
    low = pd.Series(low)
    close = pd.Series(close)
    
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(period).mean().bfill()
    
    hl2 = (high + low) / 2
    basic_upper = hl2 + (multiplier * atr)
    basic_lower = hl2 - (multiplier * atr)
    
    c = close.values
    bu = basic_upper.values
    bl = basic_lower.values
    
    fu = np.zeros_like(c)
    fl = np.zeros_like(c)
    trend = np.zeros_like(c)
    
    fu[0] = bu[0]
    fl[0] = bl[0]
    trend[0] = 1
    
    for i in range(1, len(c)):
        if bu[i] < fu[i-1] or c[i-1] > fu[i-1]:
            fu[i] = bu[i]
        else:
            fu[i] = fu[i-1]
            
        if bl[i] > fl[i-1] or c[i-1] < fl[i-1]:
            fl[i] = bl[i]
        else:
            fl[i] = fl[i-1]
            
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
            trend[i] = 1 
            
    return trend, fu, fl

# -----------------------
# Old Strategy (No TP/SL)
# -----------------------
class BitcoinSuperTrendOld(Strategy):
    atr_period = 10
    atr_multiplier = 5.0
    
    def init(self):
        self.st_trend, self.st_upper, self.st_lower = self.I(supertrend, self.data.High, self.data.Low, self.data.Close, self.atr_period, self.atr_multiplier)

    def next(self):
        if len(self.data) < 50: return
        trend = self.st_trend[-1]
        
        if trend == 1:
            if not self.position.is_long:
                if self.position.is_short:
                    self.position.close()
                self.buy(size=0.95)
        elif trend == -1:
             if not self.position.is_short:
                if self.position.is_long:
                    self.position.close()
                self.sell(size=0.95)

# -----------------------
# New Strategy (ATR Trailing Stop)
# -----------------------
class BitcoinSuperTrendNew(Strategy):
    atr_period = 10
    atr_multiplier = 5.0
    ts_atr_mult = 2.0  # Trailing stop multiplier

    def init(self):
        self.st_trend, self.st_upper, self.st_lower = self.I(supertrend, self.data.High, self.data.Low, self.data.Close, self.atr_period, self.atr_multiplier)
        
        # Calculate ATR for the trailing stop
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        close = pd.Series(self.data.Close)
        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        self.atr = self.I(lambda x: x, tr.rolling(10).mean().bfill())
        
        self.trail_stop = 0.0
        self.best_price = 0.0

    def next(self):
        if len(self.data) < 50: return
        trend = self.st_trend[-1]
        current_close = self.data.Close[-1]
        atr_val = self.atr[-1]
        
        # 1. Trailing Stop Execution
        if self.position.is_long:
            if current_close > self.best_price:
                self.best_price = current_close
                self.trail_stop = max(self.trail_stop, current_close - (atr_val * self.ts_atr_mult))
            
            if current_close <= self.trail_stop:
                self.position.close()
                self.trail_stop = 0.0
                self.best_price = 0.0
                
        elif self.position.is_short:
            if current_close < self.best_price or self.best_price == 0:
                self.best_price = current_close
                new_stop = current_close + (atr_val * self.ts_atr_mult)
                if self.trail_stop == 0:
                     self.trail_stop = new_stop
                else:
                     self.trail_stop = min(self.trail_stop, new_stop)
            
            if current_close >= self.trail_stop and self.trail_stop > 0:
                self.position.close()
                self.trail_stop = 0.0
                self.best_price = 0.0

        # 2. Enter and Reverse logic
        if trend == 1:
            if not self.position.is_long:
                if self.position.is_short:
                    self.position.close()
                self.buy(size=0.95)
                self.best_price = current_close
                self.trail_stop = current_close - (atr_val * self.ts_atr_mult)
                
        elif trend == -1:
             if not self.position.is_short:
                if self.position.is_long:
                    self.position.close()
                self.sell(size=0.95)
                self.best_price = current_close
                self.trail_stop = current_close + (atr_val * self.ts_atr_mult)

# -----------------------
# Strategy 3 (EMA 200 Trend Filter + Mismo ATR Trailing Stop 4.5x)
# -----------------------
class BitcoinSuperTrendEMA(Strategy):
    atr_period = 10
    atr_multiplier = 5.0
    ts_atr_mult = 4.5  # Fixed from optimization
    ema_period = 200

    def init(self):
        self.st_trend, self.st_upper, self.st_lower = self.I(supertrend, self.data.High, self.data.Low, self.data.Close, self.atr_period, self.atr_multiplier)
        self.ema = self.I(calc_ema, self.data.Close, self.ema_period)
        
        # Calculate ATR for the trailing stop
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        close = pd.Series(self.data.Close)
        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        self.atr = self.I(lambda x: x, tr.rolling(10).mean().bfill())
        
        self.trail_stop = 0.0
        self.best_price = 0.0

    def next(self):
        if len(self.data) < max(50, self.ema_period): return
        trend = self.st_trend[-1]
        current_close = self.data.Close[-1]
        atr_val = self.atr[-1]
        ema_val = self.ema[-1]
        
        # 1. Trailing Stop Execution
        if self.position.is_long:
            if current_close > self.best_price:
                self.best_price = current_close
                self.trail_stop = max(self.trail_stop, current_close - (atr_val * self.ts_atr_mult))
            
            if current_close <= self.trail_stop:
                self.position.close()
                self.trail_stop = 0.0
                self.best_price = 0.0
                
        elif self.position.is_short:
            if current_close < self.best_price or self.best_price == 0:
                self.best_price = current_close
                new_stop = current_close + (atr_val * self.ts_atr_mult)
                if self.trail_stop == 0:
                     self.trail_stop = new_stop
                else:
                     self.trail_stop = min(self.trail_stop, new_stop)
            
            if current_close >= self.trail_stop and self.trail_stop > 0:
                self.position.close()
                self.trail_stop = 0.0
                self.best_price = 0.0

        # 2. Enter and Reverse logic with EMA FILTER
        is_bull_market = current_close > ema_val
        is_bear_market = current_close < ema_val

        if trend == 1:
            if self.position.is_short:
                self.position.close()
            # ONLY BUY if above EMA 200
            if not self.position.is_long and is_bull_market:
                self.buy(size=0.95)
                self.best_price = current_close
                self.trail_stop = current_close - (atr_val * self.ts_atr_mult)
                
        elif trend == -1:
            if self.position.is_long:
                self.position.close()
            # ONLY SELL if below EMA 200
            if not self.position.is_short and is_bear_market:
                self.sell(size=0.95)
                self.best_price = current_close
                self.trail_stop = current_close + (atr_val * self.ts_atr_mult)


# -----------------------
# Data & Main Comparison
# -----------------------
def get_data_1h(period="730d"):
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
        print(f"Error downloading data: {e}")
        return pd.DataFrame()

def main():
    print("=== BACKTEST COMPARISON: BTC SUPERTREND 2 YEARS ===")
    df = get_data_1h()
    if df.empty or len(df) < 100: 
        print("Dataset is too small.")
        return

    # Backtest 1 - OLD
    print("\n--- Running ORIGINAL Version (No TP/SL) ---")
    bt_old = Backtest(df, BitcoinSuperTrendOld, cash=10000000, commission=.001, margin=1.0, trade_on_close=True, exclusive_orders=True)
    stats_old = bt_old.run()
    print(f"Final Equity: ${stats_old['Equity Final [$]']:.2f}")
    print(f"Return:       {stats_old['Return [%]']:.2f}%")
    print(f"Win Rate:     {stats_old['Win Rate [%]']:.2f}%")
    print(f"Max Drawdown: {stats_old['Max. Drawdown [%]']:.2f}%")
    print(f"Total Trades: {stats_old['# Trades']}")
    bt_old.plot(filename='compare_old_supertrend.html', open_browser=False)
    
    # Backtest 3 - EMA FILTER (Nivel 1)
    print("\n--- Running NIVEL 1 Version (EMA 200 Filter + ATR TS 4.5x) ---")
    bt_ema = Backtest(df, BitcoinSuperTrendEMA, cash=10000000, commission=.001, margin=1.0, trade_on_close=True, exclusive_orders=True)
    stats_ema = bt_ema.run()
    print(f"Final Equity: ${stats_ema['Equity Final [$]']:.2f}")
    print(f"Return:       {stats_ema['Return [%]']:.2f}%")
    print(f"Win Rate:     {stats_ema['Win Rate [%]']:.2f}%")
    print(f"Max Drawdown: {stats_ema['Max. Drawdown [%]']:.2f}%")
    print(f"Total Trades: {stats_ema['# Trades']}")

    # Optimize New Version
    print("\n--- Optimizing ATR Multiplier ---")
    best_ret = -99999
    best_mult = 0
    results = []
    
    for mult in [2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]:
        BitcoinSuperTrendNew.ts_atr_mult = mult
        bt_temp = Backtest(df, BitcoinSuperTrendNew, cash=10000000, commission=.001, margin=1.0, trade_on_close=True, exclusive_orders=True)
        try:
            st = bt_temp.run()
            r = st['Return [%]']
            print(f"Multiplier {mult}x -> Return: {r:.2f}% | Max DD: {st['Max. Drawdown [%]']:.2f}% | Trades: {st['# Trades']}")
            if r > best_ret:
                best_ret = r
                best_mult = mult
                stats_new = st
                bt_new = bt_temp
        except: pass
        
    print(f"\nBest Settings Found: {best_mult}x ATR Multiplier")
    
    bt_old.plot(filename='compare_old_supertrend.html', open_browser=False)
    bt_new.plot(filename='compare_new_supertrend.html', open_browser=False)
    bt_ema.plot(filename='compare_ema_supertrend.html', open_browser=False)

    print("\n=== SUMMARY COMPARISON ===")
    print(f"{'Metric':<18} | {'OLD (No TP/SL)':<18} | {f'NEW (ATR TS {best_mult}x)':<18} | {'LEVEL 1 (+EMA 200)':<18}")
    print("-" * 80)
    print(f"{'Return [%]':<18} | {stats_old['Return [%]']:<18.2f} | {stats_new['Return [%]']:<18.2f} | {stats_ema['Return [%]']:<18.2f}")
    print(f"{'Win Rate [%]':<18} | {stats_old['Win Rate [%]']:<18.2f} | {stats_new['Win Rate [%]']:<18.2f} | {stats_ema['Win Rate [%]']:<18.2f}")
    print(f"{'Max Drawdown [%]':<18} | {stats_old['Max. Drawdown [%]']:<18.2f} | {stats_new['Max. Drawdown [%]']:<18.2f} | {stats_ema['Max. Drawdown [%]']:<18.2f}")
    print(f"{'# Trades':<18} | {stats_old['# Trades']:<18} | {stats_new['# Trades']:<18} | {stats_ema['# Trades']:<18}")
    
    # Escribir resumen en txt para facilitar lectura si es necesario
    with open("compare_results.txt", "w") as f:
        f.write("=== SUMMARY COMPARISON ===\n")
        f.write(f"{'Metric':<18} | {'OLD (No TP/SL)':<18} | {'NEW (ATR TS 6.0x)':<18} | {'LEVEL 1 (+EMA 200)':<18}\n")
        f.write("-" * 80 + "\n")
        f.write(f"{'Return [%]':<18} | {stats_old['Return [%]']:<18.2f} | {stats_new['Return [%]']:<18.2f} | {stats_ema['Return [%]']:<18.2f}\n")
        f.write(f"{'Win Rate [%]':<18} | {stats_old['Win Rate [%]']:<18.2f} | {stats_new['Win Rate [%]']:<18.2f} | {stats_ema['Win Rate [%]']:<18.2f}\n")
        f.write(f"{'Max Drawdown [%]':<18} | {stats_old['Max. Drawdown [%]']:<18.2f} | {stats_new['Max. Drawdown [%]']:<18.2f} | {stats_ema['Max. Drawdown [%]']:<18.2f}\n")
        f.write(f"{'# Trades':<18} | {stats_old['# Trades']:<18} | {stats_new['# Trades']:<18} | {stats_ema['# Trades']:<18}\n")

if __name__ == '__main__':
    main()
