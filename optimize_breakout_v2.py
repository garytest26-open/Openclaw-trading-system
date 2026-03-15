
import pandas as pd
from backtesting import Backtest
from breakout_strategy_qqq import DonchianBreakoutQQQ, descargar_datos_intradia_qqq

def optim_func(series):
    """
    Custom optimization metric.
    Prioritizes SQN but penalizes strategies with too few trades (<20).
    """
    if series['# Trades'] < 20: 
        return -1
    return series['SQN']

def main():
    print("Iniciando Optimización Refinada de Donchian Breakout (QQQ 1h - >1 Año)")
    
    # Download data
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

    print("\nEjecutando Optimización Granular...")
    
    # Refined ranges based on previous analysis
    stats_opt, heatmap = bt.optimize(
        lookback=range(10, 60, 2),        # Step 2 for granularity
        exit_lookback=range(3, 20, 1),    # Step 1 for fine tuning exits
        atr_stop_mult=[1.0, 1.25, 1.5, 1.75, 2.0, 2.5],
        constraint=lambda p: p.exit_lookback < p.lookback,
        maximize=optim_func,              # Use custom metric
        return_heatmap=True
    )

    print("\n--- Resultados Optimizados (v2) ---")
    print(stats_opt)
    print("\nMejores Parámetros:")
    print(stats_opt._strategy)

    # Save results
    try:
        report_file = 'breakout_qqq_v2_best.txt'
        heatmap_file = 'breakout_qqq_v2_heatmap.csv'
        html_file = 'breakout_qqq_v2_results.html'
        
        with open(report_file, 'w') as f:
            f.write("Resultados Optimización Refinada (v2):\n")
            f.write(str(stats_opt))
            f.write("\n\nStrategy Args:\n")
            f.write(str(stats_opt._strategy))
        
        heatmap.to_csv(heatmap_file)
        bt.plot(filename=html_file, open_browser=False)
        print(f"\nReporte guardado en: {html_file}")
        print(f"Parámetros guardados en: {report_file}")
        
    except Exception as e:
        print(f"Error guardando reporte: {e}")

if __name__ == "__main__":
    main()
