import pandas as pd
import numpy as np
import yfinance as yf
from backtesting import Backtest, Strategy

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
# Estrategia: Bitcoin Momentum 4H
# -----------------------

class BitcoinMomentum4H(Strategy):
    # Parámetros (OPTIMIZED for 2 Years)
    rsi_period = 14
    macd_fast = 12
    macd_slow = 26
    macd_signal = 9
    ema_trend = 200   # Long term trend 
    atr_period = 14
    sl_atr_mult = 1.5 # Tighter stop
    tp_atr_mult = 3.0

    def init(self):
        # Data is already 4H
        close = pd.Series(self.data.Close)
        
        # RSI
        self.rsi = self.I(rsi, close, self.rsi_period)
        
        # MACD
        self.macd_line, self.signal_line = self.I(macd, close, self.macd_fast, self.macd_slow, self.macd_signal)
        
        # Trend EMA (Filter)
        self.ema_trend_line = self.I(ema, close, self.ema_trend)
        
        # ATR
        self.atr = self.I(atr_arrays, self.data.High, self.data.Low, self.data.Close, self.atr_period)

    def next(self):
        # Init check
        if np.isnan(self.ema_trend_line[-1]) or np.isnan(self.macd_line[-1]):
            return

        price = self.data.Close[-1]
        
        # Logic
        # 1. Trend Filter: Price above/below EMA
        bull_trend = price > self.ema_trend_line[-1]
        bear_trend = price < self.ema_trend_line[-1]
        
        # 2. Momentum Trigger: MACD Crossover + RSI Value
        # Bullish: RSI > 50 (Strength) AND MACD > Signal
        bull_mom = self.rsi[-1] > 50 and self.macd_line[-1] > self.signal_line[-1]
        
        # Bearish: RSI < 50 (Weakness) AND MACD < Signal
        bear_mom = self.rsi[-1] < 50 and self.macd_line[-1] < self.signal_line[-1]
        
        # Entries
        if not self.position:
            if bull_trend and bull_mom:
                self.entry_long(price)
            elif bear_trend and bear_mom:
                self.entry_short(price)


    def entry_long(self, price):
        atr_val = self.atr[-1]
        sl = price - (atr_val * self.sl_atr_mult)
        tp = price + (atr_val * self.tp_atr_mult)
        size = 0.95 # Use 95% of cash
        self.buy(sl=sl, tp=tp, size=size)

    def entry_short(self, price):
        atr_val = self.atr[-1]
        sl = price + (atr_val * self.sl_atr_mult)
        tp = price - (atr_val * self.tp_atr_mult)
        size = 0.95
        self.sell(sl=sl, tp=tp, size=size)

# -----------------------
# Data Processing
# -----------------------

def get_data_4h(ticker="BTC-USD", period="729d"):
    print(f"Downloading {ticker} 1h data for {period} to resample to 4H...")
    
    # Download 1h data (max resolution for long periods usually)
    try:
        df = yf.download(ticker, period=period, interval="1h", progress=False, auto_adjust=True)
    except Exception as e:
        print(f"Error: {e}")
        return pd.DataFrame()

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)
    
    df = df[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()
    df = df[df['Volume'] > 0]
    
    # Remove duplicates
    df = df[~df.index.duplicated(keep='first')]
    
    print(f"1H Data Loaded: {len(df)} candles.")
    
    # RESAMPLE TO 4H
    agg_dict = {
        'Open': 'first',
        'High': 'max',
        'Low': 'min',
        'Close': 'last',
        'Volume': 'sum'
    }
    
    df_4h = df.resample('4h').agg(agg_dict).dropna()
    print(f"Resampled to 4H: {len(df_4h)} candles.")
    
    return df_4h

# -----------------------
# Main
# -----------------------

def main():
    print("--- Bitcoin Momentum Strategy (4H Swing) - 2 Year Validation ---")
    
    # 1. Get Data (Max 729 days for 1h interval in yfinance)
    df_4h = get_data_4h(period="729d") 
    
    if len(df_4h) < 100:
        print("Not enough data.")
        return

    # 2. Initial Backtest
    # 10M Cash to avoid fractions logic issues
    bt = Backtest(df_4h, BitcoinMomentum4H, cash=10000000, commission=.001, exclusive_orders=True)
    
    print("\nRunning Validation Backtest (Optimized Params)...")
    try:
        stats = bt.run()
        print(stats)
        
        # Save Plot
        bt.plot(filename='btc_momentum_4h_2y_validated.html', open_browser=False)
        print("Results saved to btc_momentum_4h_2y_validated.html")
        
    except Exception as e:
        print(f"Error: {e}")
        return

    # Skip Grid Search for this validation run
    return

if __name__ == "__main__":
    main()
