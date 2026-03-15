import pandas as pd
import os
from backtesting import Backtest
from breakout_strategy_qqq import DonchianBreakoutQQQ, descargar_datos_15m_qqq

# ----------------------------------------------------
# Configuración de Archivos y Parámetros
# ----------------------------------------------------
CHECKPOINT_FILE = 'breakout_15m_checkpoint.csv'
REPORT_FILE = 'breakout_15m_best.txt'
HTML_FILE = 'breakout_15m_results.html'

def optim_func(series):
    """
    Métrica de optimización personalizada.
    Prioriza SQN.
    En 15m esperamos más trades, pero si es muy selectiva bajamos la valla.
    """
    trades = series['# Trades']
    if trades < 2: 
        return -1
    
    val = series['SQN']
    if pd.isna(val):
        return -1
    return val

def main():
    print("=== Iniciando Optimización High Frequency (Breakout QQQ 15m) ===")

    # ----------------------------------------------------
    # FIX: Agent Crash / Multiprocessing Error
    # Forzamos el uso de hilos (ThreadPool) en lugar de procesos pesados
    # ----------------------------------------------------
    from multiprocessing.dummy import Pool as ThreadPool
    import backtesting
    backtesting.Pool = ThreadPool
    print("Multiprocesamiento ajustado a ThreadPool.")
    
    # 1. Obtener Datos 15m
    df = descargar_datos_15m_qqq()
    if len(df) == 0:
        print("Error: No se pudieron descargar datos.")
        return
    print(f"Datos cargados: {len(df)} velas 15m.")

    bt = Backtest(
        df,
        DonchianBreakoutQQQ,
        cash=10000,
        commission=.0005, 
        exclusive_orders=True
    )

    # 2. Definir Espacio de Búsqueda (Más corto para HFT/DayTrading)
    # Lookback: 10 velas (2.5h) a 100 velas (25h)
    lookback_range = range(10, 100, 5) 
    
    # Parámetros secundarios
    # Exit: 3 velas (45m) a 20 velas (5h)
    exit_lookback_range = range(3, 20, 1)
    atr_stop_mult_range = [1.0, 1.5, 2.0, 2.5]

    # 3. Cargar Checkpoint existente
    processed_lookbacks = set()
    if os.path.exists(CHECKPOINT_FILE):
        print(f"Encontrado checkpoint: {CHECKPOINT_FILE}. Cargando progreso previo...")
        try:
            existing_results = pd.read_csv(CHECKPOINT_FILE)
            existing_results.dropna(subset=['score'], inplace=True)
            if 'lookback' in existing_results.columns:
                processed_lookbacks = set(existing_results['lookback'].unique())
            print(f"Se encontraron {len(processed_lookbacks)} valores de lookback ya procesados.")
        except Exception as e:
            print(f"Advertencia: No se pudo leer el checkpoint ({e}).")

    # 4. Bucle de Optimización por Lotes
    for lb in lookback_range:
        if lb in processed_lookbacks:
            print(f"Skipping lookback={lb} (ya procesado).")
            continue
            
        print(f"\nProcesando lote: lookback={lb}...")
        
        try:
            stats, heatmap = bt.optimize(
                lookback=[lb], 
                exit_lookback=exit_lookback_range,
                atr_stop_mult=atr_stop_mult_range,
                constraint=lambda p: p.exit_lookback < p.lookback,
                maximize=optim_func,
                return_heatmap=True
            )
            
            # Guardar resultados parciales
            batch_results = heatmap.reset_index()
            batch_results.rename(columns={0: 'score'}, inplace=True)
            batch_results.dropna(subset=['score'], inplace=True)
            
            if not batch_results.empty:
                header = not os.path.exists(CHECKPOINT_FILE)
                batch_results.to_csv(CHECKPOINT_FILE, mode='a', header=header, index=False)
            
            print(f"Lote lookback={lb} completado.")
            
        except Exception as e:
            print(f"Error procesando lookback={lb}: {e}")
            continue

    print("\n=== Todos los lotes procesados. Generando reporte final... ===")
    
    # 5. Análisis Final
    if not os.path.exists(CHECKPOINT_FILE):
        print("No se generaron resultados.")
        return

    all_results = pd.read_csv(CHECKPOINT_FILE)
    if all_results.empty:
        print("Archivo vacío.")
        return

    score_col = 'score' if 'score' in all_results.columns else all_results.columns[-1]
    best_row_idx = all_results[score_col].idxmax()
    best_row = all_results.iloc[best_row_idx]
    
    print("\nMejor Combinación Encontrada:")
    print(best_row)
    
    best_params = {
        'lookback': int(best_row['lookback']),
        'exit_lookback': int(best_row['exit_lookback']),
        'atr_stop_mult': float(best_row['atr_stop_mult'])
    }
    
    print("Generando HTML final...")
    final_stats = bt.run(**best_params)
    print(final_stats)

    try:
        with open(REPORT_FILE, 'w') as f:
            f.write("Resultados Optimización 15m (60 Días):\n")
            f.write(str(final_stats))
            f.write("\n\nMejores Parámetros:\n")
            f.write(str(best_params))
        
        bt.plot(filename=HTML_FILE, open_browser=False)
        print(f"\nReporte guardado en: {HTML_FILE}")
        
    except Exception as e:
        print(f"Error guardando reporte final: {e}")

if __name__ == "__main__":
    main()
