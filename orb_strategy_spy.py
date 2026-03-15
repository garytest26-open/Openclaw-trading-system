import pandas as pd
import numpy as np
from datetime import datetime, time

import yfinance as yf  # para descargar datos intradía SPY/ES

from backtesting import Backtest, Strategy  # motor de backtest


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
# Estrategia ORB
# -----------------------

class ORBStrategy(Strategy):
    # Parámetros configurables
    or_minutes = 30            # minutos del rango de apertura
    ema_fast = 20              # EMA rápida
    ema_slow = 50              # EMA lenta
    risk_per_trade = 0.01      # 1% del capital por trade
    atr_mult = 0.75            # stop = 0.75 ATR
    tp_mult = 2.0              # nuevo: take profit = TP_MULT * stop_distance
    vol_mult = 1.5             # volumen de ruptura > vol_mult * volumen medio
    max_trades_per_day = 2     # máximo de trades por día

    def init(self):
        self.close = self.data.Close
        self.high = self.data.High
        self.low = self.data.Low
        self.volume = self.data.Volume

        df = self.data.df

        self.ema_fast_series = self.I(ema, df['Close'], self.ema_fast)
        self.ema_slow_series = self.I(ema, df['Close'], self.ema_slow)
        self.atr_series = self.I(atr, df, 14)

        self.vol_ma = self.I(lambda v: v.rolling(20).mean(), df['Volume'])

        self.current_day = None
        self.or_high = None
        self.or_low = None
        self.or_done = False
        self.trades_today = 0

    def next(self):
        i = len(self.data) - 1
        dt = self.data.index[i]

        day = dt.date()
        if self.current_day != day:
            self.current_day = day
            self.or_high = None
            self.or_low = None
            self.or_done = False
            self.trades_today = 0

        t = dt.time()

        # >>> Ajusta aquí si quieres otra ventana de rango de apertura <<<
        # Data comes in UTC. 14:30 UTC is 9:30 EST.
        session_start = time(14, 30)  # apertura cash USA (UTC)
        or_end = time(15, 0)          # fin rango (30 min después)

        if session_start <= t < or_end:
            self.or_high = (
                self.data.High[-1] if self.or_high is None else max(self.or_high, self.data.High[-1])
            )
            self.or_low = (
                self.data.Low[-1] if self.or_low is None else min(self.or_low, self.data.Low[-1])
            )
            # print(f"Update {t}: H={self.data.High[-1]} L={self.data.Low[-1]}")
            return

        if not self.or_done and t >= or_end and self.or_high is not None and self.or_low is not None:
            self.or_done = True
            # print(f"OR Set: {self.or_high} - {self.or_low} for {day}")

        if not self.or_done:
            return

        if self.trades_today >= self.max_trades_per_day:
            return

        if self.position:
            return

        ema_fast = self.ema_fast_series[-1]
        ema_slow = self.ema_slow_series[-1]

        if np.isnan(ema_fast) or np.isnan(ema_slow):
            return

        current_atr = self.atr_series[-1]
        if np.isnan(current_atr) or current_atr == 0:
            return

        or_range = self.or_high - self.or_low
        if or_range < 0.3 * current_atr:
            return

        vol = self.data.Volume[-1]
        vol_mean = self.vol_ma[-1]
        if np.isnan(vol_mean) or vol_mean == 0:
            return

        price = self.data.Close[-1]

        long_cond = (
            price > self.or_high and
            ema_fast > ema_slow and
            vol > self.vol_mult * vol_mean
        )

        short_cond = (
            price < self.or_low and
            ema_fast < ema_slow and
            vol > self.vol_mult * vol_mean
        )

        cash = self.equity
        risk_amount = cash * self.risk_per_trade

        if current_atr <= 0:
            return

        stop_distance = self.atr_mult * current_atr
        if stop_distance <= 0:
            return

        # Calculate shares based on risk
        shares = risk_amount / stop_distance
        
        # Calculate max shares based on equity (approximate, leaving margin for comms)
        max_shares = (self.equity * 0.99) / price
        
        # Limit shares to available equity
        shares = min(shares, max_shares)
        
        # Ensure integer number of shares (Backtesting.py treats floats < 1 as percentages)
        size = int(shares)

        if size < 1:
            return

        if long_cond:
            sl = price - stop_distance
            tp = price + self.tp_mult * stop_distance
            self.buy(size=size, sl=sl, tp=tp)
            self.trades_today += 1

        elif short_cond:
            sl = price + stop_distance
            tp = price - self.tp_mult * stop_distance
            self.sell(size=size, sl=sl, tp=tp)
            self.trades_today += 1


# -----------------------
# Descarga de datos y backtest
# -----------------------

def descargar_datos(ticker="SPY"):
    """
    Descarga datos intradía del ticker especificado de los últimos ~5 años.
    Yahoo Finance permite 1m/5m con límites de histórico; '5y' + '5m' suele dar
    varios años de datos intradía.
    """
    interval = "5m"
    period = "59d"

    print(f"Descargando datos de {ticker} ({interval}, {period}) ...")
    data = yf.download(ticker, period=period, interval=interval)

    # Flatten MultiIndex columns if present (new yfinance behavior)
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.droplevel(1)

    data = data[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()
    data.index = pd.to_datetime(data.index)

    return data


def main():
    df = descargar_datos("SPY")

    bt = Backtest(
        df,
        ORBStrategy,
        cash=10000,
        commission=.0005,
        exclusive_orders=True,
    )

    print("Ejecutando optimización...")

    # Optimización
    # Nota: Backtesting.py optimize prefiere listas de valores para floats
    
    stats, heatmap = bt.optimize(
        atr_mult=[2.0, 2.5, 3.0, 3.5, 4.0],
        tp_mult=[2.0, 3.0, 4.0, 5.0, 6.0],
        ema_fast=[5, 10, 15],
        ema_slow=[40, 50, 60],
        vol_mult=[1.0, 1.5, 2.0],
        constraint=lambda p: p.ema_fast < p.ema_slow,
        maximize='Return [%]',
        return_heatmap=True
    )

    print("\nResultados Optimización:")
    print(stats)
    print("\nMejores Parámetros:")
    print(stats._strategy)
    
    # Mostrar top 10 combinaciones del heatmap
    print("\nTop 10 combinaciones (Heatmap):")
    print(heatmap.sort_values(ascending=False).head(10))

    # Guardar resultados en archivos
    try:
        heatmap.to_csv('orb_optimization_heatmap.csv')
        print("Heatmap guardado en orb_optimization_heatmap.csv")
        
        with open('orb_best_params.txt', 'w') as f:
            f.write("Estadisticas Completas:\n")
            f.write(str(stats))
            f.write("\n\nMejores Parametros:\n")
            f.write(str(stats._strategy))
        print("Mejores parámetros guardados en orb_best_params.txt")
    except Exception as e:
        print(f"Error guardando archivos de resultados: {e}")

    try:
        bt.plot(filename='orb_optimized.html', open_browser=False)
        print("Gráfico optimizado guardado en orb_optimized.html")
    except Exception as e:
        print(f"No se pudo guardar el gráfico: {e}")


if __name__ == "__main__":
    main()
