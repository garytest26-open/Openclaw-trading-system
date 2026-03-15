import pandas as pd
import numpy as np
from datetime import datetime, time, timedelta
import yfinance as yf
from backtesting import Backtest, Strategy

# -----------------------
# Funciones auxiliares
# -----------------------

def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def atr(df, period=14):
    high = df['High']
    low = df['Low']
    close = df['Close']
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(period).mean()

# -----------------------
# Estrategia ORB (Adaptada para BTC 1h)
# -----------------------

class ORBStrategyBTC(Strategy):
    # Parámetros Ganadores de SPY (orb_best_params.txt)
    # Scaled/Checked for 1h? 5/60 EMAs on 1h are reasonable trend filters (short-term)
    ema_fast = 5
    ema_slow = 60
    risk_per_trade = 0.05      # 5% riesgo (Crypto permite más, ajustado para ver impacto)
    atr_mult = 3.5
    tp_mult = 3.0
    vol_mult = 1.0
    max_trades_per_day = 100   # Sin limite estricto salvo lógica, crypto es 24h

    def init(self):
        # NOTA: No asignar self.close = self.data.Close aquí para evitar errores de referencia estática
        
        # Indicators
        self.ema_fast_series = self.I(ema, pd.Series(self.data.Close), self.ema_fast)
        self.ema_slow_series = self.I(ema, pd.Series(self.data.Close), self.ema_slow)
        
        # ATR Calculation
        self.atr_series = self.I(atr, self.data.df, 14)

        self.vol_ma = self.I(lambda v: pd.Series(v).rolling(20).mean(), self.data.Volume)

        self.current_day = None
        self.or_high = None
        self.or_low = None
        self.or_done = False

    def next(self):
        # Time management
        dt = self.data.index[-1] # Current candle timestamp
        
        day = dt.date()
        t = dt.time()
        
        # Daily Reset
        if self.current_day != day:
            self.current_day = day
            self.or_high = None
            self.or_low = None
            self.or_done = False
        
        session_start = time(14, 0)
        or_end = time(15, 0) 

        # 1. Update/Define Range during the Session Start candle
        if t == session_start:
            # CORRECTED: Use self.data.High[-1] dynamically
            self.or_high = self.data.High[-1]
            self.or_low = self.data.Low[-1]
            self.or_done = True 
            return
        
        # 2. Trade after Range is Done
        if not self.or_done:
            return

        # Only trade if we are properly initialized (indicators not NaN)
        if np.isnan(self.ema_fast_series[-1]) or np.isnan(self.ema_slow_series[-1]) or np.isnan(self.atr_series[-1]):
            return

        # Entry Logic
        price = self.data.Close[-1]
        vol = self.data.Volume[-1]
        vol_mean = self.vol_ma[-1]
        
        # Check volume filter
        if vol < (self.vol_mult * vol_mean):
            return

        # Long
        if price > self.or_high and self.ema_fast_series[-1] > self.ema_slow_series[-1]:
            if not self.position.is_long:
                self.entry_long(price)

        # Short
        elif price < self.or_low and self.ema_fast_series[-1] < self.ema_slow_series[-1]:
            if not self.position.is_short:
                self.entry_short(price)

    def entry_long(self, price):
        atr_val = self.atr_series[-1]
        sl = price - (atr_val * self.atr_mult)
        tp = price + (atr_val * self.atr_mult * self.tp_mult)
        
        if sl < 0: return

        if self.position:
            self.position.close()
            
        print(f"BUY at {price} SL={sl} TP={tp}")
        self.buy(sl=sl, tp=tp)

    def entry_short(self, price):
        atr_val = self.atr_series[-1]
        sl = price + (atr_val * self.atr_mult)
        tp = price - (atr_val * self.atr_mult * self.tp_mult)
        
        if tp < 0: return 

        if self.position:
            self.position.close()

        print(f"SELL at {price} SL={sl} TP={tp}")
        self.sell(sl=sl, tp=tp)

# -----------------------
# Data Fetcher
# -----------------------
def descargar_datos_btc_1y():
    print("Descargando datos BTC-USD (1h) últimos 365 días...")
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    
    data = yf.download("BTC-USD", start=start_date, interval="1h", progress=False, auto_adjust=True)
    
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.droplevel(1)
        
    data = data[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()
    data = data[data['Volume'] > 0]
    return data

def main():
    try:
        df = descargar_datos_btc_1y()
    except Exception as e:
        print(f"Error descargando: {e}")
        return

    print(f"Datos obtenidos: {len(df)} velas.")

    bt = Backtest(
        df,
        ORBStrategyBTC,
        cash=10000000, # 10M Cash
        commission=.001,
        exclusive_orders=True
    )

    print("Ejecutando Backtest ORB BTC...")
    stats = bt.run()
    print(stats)
    
    bt.plot(filename='btc_orb_1y_results.html', open_browser=False)
    print("Reporte guardado en btc_orb_1y_results.html")

if __name__ == "__main__":
    main()
