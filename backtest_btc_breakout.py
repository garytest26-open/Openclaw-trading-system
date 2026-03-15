import pandas as pd
import numpy as np
import yfinance as yf
from backtesting import Backtest, Strategy
from datetime import datetime, timedelta

# -----------------------
# Estrategia Donchian Breakout (Adaptada para BTC)
# -----------------------
class DonchianBreakoutBTC(Strategy):
    # Parámetros "Refined" de QQQ
    lookback = 38           
    exit_lookback = 6      
    atr_period = 14
    atr_stop_mult = 1.5     
    
    def init(self):
        self.high = self.data.High
        self.low = self.data.Low
        self.close = self.data.Close
        
        # Canal Donchian (High/Low de N periodos ATRAS)
        self.upper_channel = self.I(lambda x: pd.Series(x).rolling(self.lookback).max().shift(1), self.high)
        self.lower_channel = self.I(lambda x: pd.Series(x).rolling(self.lookback).min().shift(1), self.low)
        
        # Canal de Salida
        self.exit_upper = self.I(lambda x: pd.Series(x).rolling(self.exit_lookback).max().shift(1), self.high)
        self.exit_lower = self.I(lambda x: pd.Series(x).rolling(self.exit_lookback).min().shift(1), self.low)
        
        # ATR para Stop Loss inicial (Pre-calculado)
        self.atr = self.data.MyATR

    def next(self):
        # Asegurar datos iniciales
        if np.isnan(self.upper_channel[-1]) or np.isnan(self.atr[-1]):
            return

        # Use dynamic access to current data slice
        price = self.data.Close[-1]
        
        # Gestión de Posiciones
        if self.position:
            if self.position.is_long:
                if price < self.exit_lower[-1]:
                    self.position.close()
            elif self.position.is_short:
                if price > self.exit_upper[-1]:
                    self.position.close()
            return

        # Entradas
        # Long
        if price > self.upper_channel[-1]:
            sl_price = price - (self.atr[-1] * self.atr_stop_mult)
            self.buy(sl=sl_price)
            
        # Short
        elif price < self.lower_channel[-1]:
            sl_price = price + (self.atr[-1] * self.atr_stop_mult)
            self.sell(sl=sl_price)   

def descargar_datos_btc():
    ticker = "BTC-USD"
    interval = "1h"
    
    # Calcular fecha de inicio (1 año + buffer)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=370) 
    
    print(f"Descargando datos de {ticker} ({interval}) desde {start_date.strftime('%Y-%m-%d')}...")
    
    # Force auto_adjust=True explicitly to be safe, though default changed
    data = yf.download(ticker, start=start_date, interval=interval, progress=False, auto_adjust=True)

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.droplevel(1)

    data = data[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()
    data.index = pd.to_datetime(data.index)
    data = data[data['Volume'] > 0] 

    return data

def main():
    print("Iniciando Backtest: Breakout Refined en BTC-USD (1 Año)")
    
    try:
        df = descargar_datos_btc()
    except Exception as e:
        print(f"Error descargando datos: {e}")
        return

    if len(df) == 0:
        print("Error: No se descargaron datos.")
        return

    print(f"Datos obtenidos: {len(df)} velas.")

    # Data Inspection
    print("\n--- Data Inspection ---")
    print(df.head())
    print("\nCheck High < Low:")
    invalid_rows = df[df['High'] < df['Low']]
    print(f"Invalid Rows (High < Low): {len(invalid_rows)}")
    if len(invalid_rows) > 0:
        print(invalid_rows.head())
        print("FIXING: Swapping High and Low for invalid rows...")
        df.loc[df['High'] < df['Low'], ['High', 'Low']] = df.loc[df['High'] < df['Low'], ['Low', 'High']].values
        
    print("\nCheck NaNs:")
    print(df.isna().sum())
    
    # Check ATR calculation manually
    df['tr'] = df['High'] - df['Low']  # Simplest TR
    # Use rolling mean for ATR
    df['MyATR'] = df['tr'].rolling(14).mean()
    
    print(f"\nMax True Range: {df['tr'].max()}")
    print(f"Min True Range: {df['tr'].min()}")
    if df['tr'].min() < 0:
         print("FATAL: True Range is negative!")
         
    # Fill NaN ATRs
    df['MyATR'] = df['MyATR'].fillna(method='bfill')

    bt = Backtest(
        df,
        DonchianBreakoutBTC,
        cash=200000,
        commission=.001, # Comision crypto standard (0.1%)
        exclusive_orders=True
    )

    stats = bt.run()
    print("\n--- Resultados (BTC 1h - Config Refined) ---")
    print(stats)

    # Guardar reporte
    filename = 'results/btc_breakout_results.html'
    bt.plot(filename=filename, open_browser=False)
    print(f"\nReporte guardado en: {filename}")

    # Guardar resumen en txt
    with open('results/btc_breakout_stats.txt', 'w') as f:
        f.write(str(stats))

if __name__ == "__main__":
    main()
