import pandas as pd
from backtesting import Backtest
from orb_strategy_spy import ORBStrategy, descargar_datos

# Configuración ganadora
class BestORBStrategy(ORBStrategy):
    atr_mult = 3.5
    tp_mult = 3.0
    ema_fast = 5
    ema_slow = 60
    vol_mult = 1.0

def main():
    print("Descargando datos y preparando backtest...")
    df = descargar_datos("QQQ")

    bt = Backtest(
        df,
        BestORBStrategy,
        cash=10000,
        commission=.0005,
        exclusive_orders=True,
    )

    print("Ejecutando backtest con configuración ganadora:")
    print(f"ATR: {BestORBStrategy.atr_mult}, TP: {BestORBStrategy.tp_mult}, "
          f"EMA Fast: {BestORBStrategy.ema_fast}, EMA Slow: {BestORBStrategy.ema_slow}, "
          f"Vol Mult: {BestORBStrategy.vol_mult}")

    stats = bt.run()
    
    print("\nResultados Completos:")
    print(stats)
    
    # Guardar reporte visual
    bt.plot(filename='best_orb_results_qqq.html', open_browser=False)
    print("\nGráfico guardado en 'best_orb_results_qqq.html'")

if __name__ == "__main__":
    main()
