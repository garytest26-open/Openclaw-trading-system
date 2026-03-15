import pandas as pd
import numpy as np
import yfinance as yf
from backtesting import Backtest, Strategy

# -----------------------
# Estrategia de Ruptura (Donchian Breakout)
# -----------------------

class DonchianBreakoutQQQ(Strategy):
    # Parámetros optimizables ("Refined" Originales)
    lookback = 38           
    exit_lookback = 6      
    atr_period = 14
    atr_stop_mult = 1.5     
    
    def init(self):
        # NOTA: No asignar self.close = self.data.Close aquí para uso en next()
        # backtesting.py requiere acceso dinámico via self.data.Close[-1]
        
        # Canal Donchian (Máximo y Mínimo de N periodos ATRAS)
        self.upper_channel = self.I(lambda x: pd.Series(x).rolling(self.lookback).max().shift(1), self.data.High)
        self.lower_channel = self.I(lambda x: pd.Series(x).rolling(self.lookback).min().shift(1), self.data.Low)
        
        # Canal de Salida (Trailing Stop "natural" del precio)
        self.exit_upper = self.I(lambda x: pd.Series(x).rolling(self.exit_lookback).max().shift(1), self.data.High)
        self.exit_lower = self.I(lambda x: pd.Series(x).rolling(self.exit_lookback).min().shift(1), self.data.Low)
        
        # ATR para Stop Loss inicial de protección duro
        self.atr = self.I(lambda h, l, c: pd.Series(h-l).rolling(self.atr_period).mean(), self.data.High, self.data.Low, self.data.Close)

    def next(self):
        # Asegurar datos suficientes
        if np.isnan(self.upper_channel[-1]) or np.isnan(self.atr[-1]):
            return

        price = self.data.Close[-1]
        
        # Debug ocasional
        # if len(self.data) % 100 == 0:
        #    print(f"Debug: Price={price}, Upper={self.upper_channel[-1]}, Lower={self.lower_channel[-1]}")

        # Gestión de Posiciones Abiertas
        if self.position:
            # Salida Dinámica (Trailing Stop basado en Price Action)
            if self.position.is_long:
                # Si el precio rompe el mínimo de hace N periodos (exit_lower), salimos
                if price < self.exit_lower[-1]:
                    self.position.close()
            elif self.position.is_short:
                # Si el precio rompe el máximo de hace N periodos (exit_upper), salimos
                if price > self.exit_upper[-1]:
                    self.position.close()
            return

        # Lógica de Entrada (Breakout)
        
        # LONG: El precio rompe el techo del canal (Nuevo máximo de N periodos)
        if price > self.upper_channel[-1]:
            # Entramos a mercado, SL gestionado por lógica o stop dinámico
            self.buy()
            
        # SHORT: El precio rompe el suelo del canal (Nuevo mínimo de N periodos)
        elif price < self.lower_channel[-1]:
            self.sell()

# -----------------------
# Descarga de datos
# -----------------------

def descargar_datos_intradia_qqq():
    """Descarga datos 1h para Backtest de >1 año (Robustez)"""
    ticker = "QQQ"
    interval = "1h"
    start_date = "2025-01-01"  # Forzamos fecha de inicio para asegurar >1 año
    
    # Nota: yfinance permite 730 días para 1h.
    print(f"Descargando datos de {ticker} ({interval}) desde {start_date}...")
    
    # Usamos start= en lugar de period=
    data = yf.download(ticker, start=start_date, interval=interval, progress=False)

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.droplevel(1)

    data = data[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()
    data.index = pd.to_datetime(data.index)
    data = data[data['Volume'] > 0] 

    return data

def descargar_datos_15m_qqq():
    """Descarga datos 15m para Backtest (Max 60 días por limitación de Yahoo)"""
    ticker = "QQQ"
    interval = "15m"
    period = "60d" 
    
    print(f"Descargando datos de {ticker} ({interval}) últimos {period}...")
    
    data = yf.download(ticker, period=period, interval=interval, progress=False)

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.droplevel(1)

    data = data[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()
    data.index = pd.to_datetime(data.index)
    data = data[data['Volume'] > 0] 

    return data

def main():
    print("Iniciando Verificación de Hipótesis #2: Donchian Breakout (QQQ 1h - >1 Año)")
    df = descargar_datos_intradia_qqq()
    
    if len(df) == 0:
        print("Error: No se pudieron descargar datos.")
        return

    print(f"Datos: {len(df)} velas (Desde {df.index[0]} hasta {df.index[-1]}).")

    bt = Backtest(
        df,
        DonchianBreakoutQQQ,
        cash=10000,
        commission=.0005, 
        exclusive_orders=True
    )

    print("Ejecutando Backtest Base (Params Refined)...")
    stats = bt.run()
    print("\n--- Resultados (Refined 1h - FIXED) ---")
    print(stats)

    # Bloque de Optimización comentado para evitar crashes en combinaciones sin trades
    """
    print("\nEjecutando Optimización Ampliada...")
    # Buscamos configuraciones más rápidas para aumentar el número de trades
    stats_opt, heatmap = bt.optimize(
        lookback=range(5, 60, 5),       # Rango más corto para ser más reactivo (5h a 60h)
        exit_lookback=range(3, 25, 2),  # Salidas más ajustadas
        atr_stop_mult=[1.0, 1.5, 2.0, 2.5, 3.0], 
        constraint=lambda p: p.exit_lookback < p.lookback, 
        maximize='Sharpe Ratio',
        return_heatmap=True
    )

    print("\n--- Resultados Optimizados ---")
    print(stats_opt)
    print("\nMejores Parámetros:")
    print(stats_opt._strategy)

    # Resultados y Heatmap
    try:
        with open('breakout_qqq_1y_best_params.txt', 'w') as f:
            f.write("Resultados Optimización 1 Año (Robustez):\n")
            f.write(str(stats_opt))
            f.write("\n\nStrategy Args:\n")
            f.write(str(stats_opt._strategy))
        
        heatmap.to_csv('breakout_qqq_1y_heatmap.csv')
        bt.plot(filename='breakout_qqq_1y_results.html', open_browser=False)
        print("\nReporte guardado en: breakout_qqq_1y_results.html")
    except Exception as e:
        print(f"Error guardando reporte: {e}")
    """
    
    # Guardar solo el reporte Base Refined
    bt.plot(filename='breakout_qqq_refined_fixed.html', open_browser=False)
    print("\nReporte guardado en: breakout_qqq_refined_fixed.html")

if __name__ == "__main__":
    main()

# -----------------------
# Descarga de datos
# -----------------------

def descargar_datos_intradia_qqq():
    """Descarga datos 1h para Backtest de >1 año (Robustez)"""
    ticker = "QQQ"
    interval = "1h"
    start_date = "2025-01-01"  # Forzamos fecha de inicio para asegurar >1 año
    
    # Nota: yfinance permite 730 días para 1h.
    print(f"Descargando datos de {ticker} ({interval}) desde {start_date}...")
    
    # Usamos start= en lugar de period=
    data = yf.download(ticker, start=start_date, interval=interval, progress=False)

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.droplevel(1)

    data = data[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()
    data.index = pd.to_datetime(data.index)
    data = data[data['Volume'] > 0] 

    return data

def descargar_datos_15m_qqq():
    """Descarga datos 15m para Backtest (Max 60 días por limitación de Yahoo)"""
    ticker = "QQQ"
    interval = "15m"
    period = "60d" 
    
    print(f"Descargando datos de {ticker} ({interval}) últimos {period}...")
    
    data = yf.download(ticker, period=period, interval=interval, progress=False)

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.droplevel(1)

    data = data[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()
    data.index = pd.to_datetime(data.index)
    data = data[data['Volume'] > 0] 

    return data

def main():
    print("Iniciando Optimización Profunda de Hipótesis #2: Donchian Breakout (QQQ 1h - >1 Año)")
    df = descargar_datos_intradia_qqq()
    
    if len(df) == 0:
        print("Error: No se pudieron descargar datos.")
        return

    print(f"Datos: {len(df)} velas (Desde {df.index[0]} hasta {df.index[-1]}).")

    bt = Backtest(
        df,
        DonchianBreakoutQQQ,
        cash=10000,
        commission=.0005, 
        exclusive_orders=True
    )

    print("Ejecutando Backtest Base...")
    stats = bt.run()
    print("\n--- Resultados (Base 1h) ---")
    print(stats)

    print("\nEjecutando Optimización Ampliada...")
    # Buscamos configuraciones más rápidas para aumentar el número de trades
    stats_opt, heatmap = bt.optimize(
        lookback=range(5, 60, 5),       # Rango más corto para ser más reactivo (5h a 60h)
        exit_lookback=range(3, 25, 2),  # Salidas más ajustadas
        atr_stop_mult=[1.0, 1.5, 2.0, 2.5, 3.0], 
        constraint=lambda p: p.exit_lookback < p.lookback, 
        maximize='Sharpe Ratio',
        return_heatmap=True
    )

    print("\n--- Resultados Optimizados ---")
    print(stats_opt)
    print("\nMejores Parámetros:")
    print(stats_opt._strategy)

    # Resultados y Heatmap
    try:
        with open('breakout_qqq_1y_best_params.txt', 'w') as f:
            f.write("Resultados Optimización 1 Año (Robustez):\n")
            f.write(str(stats_opt))
            f.write("\n\nStrategy Args:\n")
            f.write(str(stats_opt._strategy))
        
        heatmap.to_csv('breakout_qqq_1y_heatmap.csv')
        bt.plot(filename='breakout_qqq_1y_results.html', open_browser=False)
        print("\nReporte guardado en: breakout_qqq_1y_results.html")
    except Exception as e:
        print(f"Error guardando reporte: {e}")

if __name__ == "__main__":
    main()
