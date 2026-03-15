import pandas as pd
from backtesting import Backtest
from orb_strategy_qqq import ORBStrategy, descargar_datos_qqq

# Configuración ganadora para QQQ
class BestORBStrategyQQQ(ORBStrategy):
    atr_mult = 3.5
    tp_mult = 5.0
    ema_fast = 10
    ema_slow = 50
    vol_mult = 1.5

def main():
    print("Descargando datos y preparando backtest para QQQ...")
    df = descargar_datos_qqq()

    if len(df) == 0:
        print("Error: No se pudieron descargar datos.")
        return

    bt = Backtest(
        df,
        BestORBStrategyQQQ,
        cash=10000,
        commission=.0005,
        exclusive_orders=True,
    )

    print("Ejecutando backtest con configuración ganadora para QQQ:")
    print(f"ATR: {BestORBStrategyQQQ.atr_mult}, TP: {BestORBStrategyQQQ.tp_mult}, "
          f"EMA Fast: {BestORBStrategyQQQ.ema_fast}, EMA Slow: {BestORBStrategyQQQ.ema_slow}, "
          f"Vol Mult: {BestORBStrategyQQQ.vol_mult}")

    stats = bt.run()
    
    print("\nResultados Completos QQQ:")
    print(stats)
    
    # Guardar reporte visual
    bt.plot(filename='best_orb_qqq_results.html', open_browser=False)
    print("\nGráfico guardado en 'best_orb_qqq_results.html'")

if __name__ == "__main__":
    main()
