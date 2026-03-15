import pandas as pd
import numpy as np
import yfinance as yf
from backtesting import Backtest, Strategy
from backtesting.lib import crossover

def SMA(values, n):
    """
    Return simple moving average of `values`, at
    each step taking into account `n` previous values.
    """
    return pd.Series(values).rolling(n).mean()

def RSI(array, n):
    """Relative Strength Index"""
    # Approximate; good enough
    gain = pd.Series(array).diff()
    loss = gain.copy()
    gain[gain < 0] = 0
    loss[loss > 0] = 0
    rs = gain.ewm(span=n).mean() / loss.abs().ewm(span=n).mean()
    return 100 - 100 / (1 + rs)

def BBANDS(data, n_lookback, n_std):
    """Bollinger Bands"""
    hlc3 = (data.High + data.Low + data.Close) / 3
    mean = hlc3.rolling(n_lookback).mean()
    std = hlc3.rolling(n_lookback).std()
    upper = mean + n_std * std
    lower = mean - n_std * std
    return upper, lower

# -----------------------
# Estrategia Mean Reversion
# -----------------------

class MeanReversionQQQ(Strategy):
    # Parámetros por default (optimizables)
    rsi_period = 14
    rsi_lower = 30       # Sobreventa
    rsi_upper = 70       # Sobrecompra
    bb_period = 20
    bb_std = 2.0
    
    # Gestión de riesgo
    stop_loss_pct = 0.01 # 1% de caída desde entrada
    take_profit_pct = 0.02

    def init(self):
        self.close = self.data.Close
        
        # Indicadores
        self.sma = self.I(SMA, self.close, self.bb_period)
        self.rsi = self.I(RSI, self.close, self.rsi_period)
        
        # BBands (Calculadas manualmente para tener upper/lower)
        # Nota: self.I requiere una función que devuelva array(s)
        # Usamos un wrapper simple si BBANDS retorna tupla
        self.upper_band, self.lower_band = self.I(BBANDS, self.data.df, self.bb_period, self.bb_std)

    def next(self):
        # Gestión de salida manualmente para evitar errores por gaps
        if self.position:
            # Check Stop Loss / Take Profit manual
            # Nota: pl_pct es flotante (ej 0.01 es 1%)
            if self.position.pl_pct < -self.stop_loss_pct:
                self.position.close()
                return
            if self.position.pl_pct > self.take_profit_pct:
                self.position.close()
                return

            # Salida por Indicadores (Mean Reversion completada)
            if self.position.is_long and self.rsi[-1] > self.rsi_upper:
                self.position.close()
            elif self.position.is_short and self.rsi[-1] < self.rsi_lower:
                self.position.close()
            return

        # Lógica de Entrada
        
        # LONG: Precio debajo de banda inferior Y RSI < 30
        if self.close[-1] < self.lower_band[-1] and self.rsi[-1] < self.rsi_lower:
            self.buy() # Market order, sin SL/TP fijo para evitar error de gap

        # SHORT: Precio encima de banda superior Y RSI > 70
        elif self.close[-1] > self.upper_band[-1] and self.rsi[-1] > self.rsi_upper:
            self.sell()

# -----------------------
# Descarga de datos
# -----------------------

def descargar_datos_intradia_qqq():
    """
    Descarga 59 días de datos 15m para tener un backtest intradía válido.
    """
    ticker = "QQQ"
    interval = "15m" 
    period = "59d" # Max permitido por yfinance para <1h

    print(f"Descargando datos de {ticker} ({interval}, {period}) ...")
    data = yf.download(ticker, period=period, interval=interval, progress=False)

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.droplevel(1)

    data = data[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()
    # Asegurar índice datetime
    data.index = pd.to_datetime(data.index)
    
    # Limpieza básica
    data = data[data['Volume'] > 0]

    return data

def main():
    print("Iniciando análisis de Hipótesis: Reversión a la Media (QQQ 15m)")
    df = descargar_datos_intradia_qqq()
    
    if len(df) == 0:
        print("Error: No se pudieron descargar datos intradía.")
        return

    print(f"Datos descargados: {len(df)} velas intradía.")

    bt = Backtest(
        df,
        MeanReversionQQQ,
        cash=10000,
        commission=.0005, # Interactive Brokers approx tier
        exclusive_orders=True
    )

    print("Ejecutando Backtest inicial...")
    stats = bt.run()
    print("\n--- Resultados Iniciales ---")
    print(stats)

    # Optimización
    print("\nOptimizando parámetros...")
    stats_opt, heatmap = bt.optimize(
        rsi_lower=[20, 25, 30],
        rsi_upper=[70, 75, 80],
        bb_period=[15, 20, 25],
        constraint=lambda p: p.rsi_lower < 50 and p.rsi_upper > 50,
        maximize='Sharpe Ratio',
        return_heatmap=True
    )

    print("\n--- Resultados Optimizados ---")
    print(stats_opt)
    
    # Guardar resultados
    try:
        with open('pullback_qqq_best_params.txt', 'w') as f:
            f.write(str(stats_opt))
            f.write("\n\nStrategy Args:\n")
            f.write(str(stats_opt._strategy))
        
        bt.plot(filename='pullback_qqq_results.html', open_browser=False)
        print("\nReporte guardado en: pullback_qqq_results.html")
    except Exception as e:
        print(f"Error guardando reporte: {e}")

if __name__ == "__main__":
    main()
