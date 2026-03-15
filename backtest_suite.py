import pandas as pd
import yfinance as yf
from backtesting import Backtest, Strategy
from backtesting.lib import crossover
import numpy as np

# --- Helper Functions ---
def EMA(values, n):
    """
    Return scalar exponential moving average of `values`, at
    the respective index.
    """
    return pd.Series(values).ewm(span=n, adjust=False).mean().values

def SMA(values, n):
    """
    Return simple moving average of `values`, at
    the respective index.
    """
    return pd.Series(values).rolling(n).mean().values

def RSI(values, n=14):
    delta = pd.Series(values).diff()
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)
    avg_gain = gain.ewm(span=n, adjust=False).mean()
    avg_loss = loss.ewm(span=n, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.finfo(float).eps) 
    return (100 - (100 / (1 + rs))).values

# --- 1. Breakout Strategy (Turtle) ---
def DonchianHigh(series, n):
    return pd.Series(series).rolling(n).max().shift(1).values

def DonchianLow(series, n):
    return pd.Series(series).rolling(n).min().shift(1).values

class BreakoutBacktest(Strategy):
    entry_window = 20
    exit_window = 10
    
    def init(self):
        self.donchian_high = self.I(DonchianHigh, self.data.High, self.entry_window)
        self.donchian_low = self.I(DonchianLow, self.data.Low, self.exit_window)
        
    def next(self):
        price = self.data.Close[-1]
        
        # Check valid indicator values
        if np.isnan(self.donchian_high[-1]) or np.isnan(self.donchian_low[-1]):
            return

        if not self.position:
            if price > self.donchian_high[-1]:
                self.buy()
        else:
            if price < self.donchian_low[-1]:
                self.position.close()

# --- 2. Mean Reversion Backtest ---
class MeanReversionBacktest(Strategy):
    bb_length = 20
    bb_std = 2.0
    rsi_length = 14
    rsi_lower = 30
    rsi_upper = 70
    
    def init(self):
        self.close = self.data.Close
        # Precompute indicators for speed
        self.ma = self.I(SMA, self.close, self.bb_length)
        self.std = self.I(lambda x: pd.Series(x).rolling(self.bb_length).std().values, self.close)
        self.rsi = self.I(RSI, self.close, self.rsi_length)
        
    def next(self):
        upper_band = self.ma[-1] + self.bb_std * self.std[-1]
        lower_band = self.ma[-1] - self.bb_std * self.std[-1]
        current_rsi = self.rsi[-1]
        price = self.close[-1]
        
        if not self.position:
            if price < lower_band and current_rsi < self.rsi_lower:
                self.buy()
        else:
            if price > upper_band and current_rsi > self.rsi_upper:
                self.position.close()

# --- 3. ORB Strategy (Simplified for Hourly/Daily if needed, but best with 5m) ---
# Importing logic from orb_strategy_spy.py would be best, but let's redefine simplified here
# because ORB is tricky with 1h data (Opening range is usually 30m).
# Checking data resolution first.

def download_data(symbol, period='6mo', interval='1h'):
    print(f"Descargando datos para {symbol} ({period}, {interval})...")
    data = yf.download(symbol, period=period, interval=interval)
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.droplevel(1)
    data = data[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()
    return data

def main():
    symbol = "QQQ" # Tech heavy
    
    # 1. Backtest Breakout (Swing - Works well with Daily/Hourly)
    print("\n--- Ejecutando Backtest: Breakout (6 Meses, 1h) ---")
    df_1h = download_data(symbol, period='6mo', interval='1h')
    bt_breakout = Backtest(df_1h, BreakoutBacktest, cash=10000, commission=.0005)
    stats_breakout = bt_breakout.run()
    print(stats_breakout)
    
    # 2. Backtest Mean Reversion (Swing/Intraday)
    print("\n--- Ejecutando Backtest: Mean Reversion (6 Meses, 1h) ---")
    bt_meanrev = Backtest(df_1h, MeanReversionBacktest, cash=10000, commission=.0005)
    stats_meanrev = bt_meanrev.run()
    print(stats_meanrev)
    
    # 3. ORB (Intraday - Needs 5m data)
    print("\n--- Ejecutando Backtest: ORB (60 Días - Max YF Limit para 5m) ---")
    # ORB needs higher resolution. YF only gives 60 days of 5m data.
    # We will accept this limitation or use 1h data with modified logic? 
    # ORB logic fundamentally requires sub-hourly data to define the range (first 30m).
    # We will run 60 days for ORB as proxy for "recent performance".
    df_5m = download_data(symbol, period='59d', interval='5m')
    
    # Import ORB class dynamically to reuse
    from orb_strategy_spy import ORBStrategy
    bt_orb = Backtest(df_5m, ORBStrategy, cash=10000, commission=.0005)
    stats_orb = bt_orb.run()
    print(stats_orb)
    
    # Summary Report
    print("\n" + "="*50)
    print(f"RESUMEN COMPARATIVO ({symbol})")
    print("="*50)
    print(f"1. Breakout (6mo 1h): Return {stats_breakout['Return [%]']:.2f}% | Win Rate {stats_breakout['Win Rate [%]']:.2f}% | MaxDD {stats_breakout['Max. Drawdown [%]']:.2f}%")
    print(f"2. Mean Rev (6mo 1h): Return {stats_meanrev['Return [%]']:.2f}% | Win Rate {stats_meanrev['Win Rate [%]']:.2f}% | MaxDD {stats_meanrev['Max. Drawdown [%]']:.2f}%")
    print(f"3. ORB (60d 5m)     : Return {stats_orb['Return [%]']:.2f}% | Win Rate {stats_orb['Win Rate [%]']:.2f}% | MaxDD {stats_orb['Max. Drawdown [%]']:.2f}%")
    print("="*50)

if __name__ == "__main__":
    main()
