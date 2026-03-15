import pandas as pd
import os
from backtesting import Backtest
from breakout_strategy_qqq import DonchianBreakoutQQQ, descargar_datos_intradia_qqq

# ----------------------------------------------------
# Configuración de Archivos y Parámetros
# ----------------------------------------------------
CHECKPOINT_FILE = 'breakout_checkpoint.csv'
REPORT_FILE = 'breakout_resumable_best.txt'
HTML_FILE = 'breakout_resumable_results.html'

def optim_func(series):
    """
    Métrica de optimización personalizada.
    Prioriza SQN.
    Aceptamos estrategias con pocos trades (min 2) dada la baja frecuencia.
    """
    trades = series['# Trades']
    if trades < 2: 
        return -1
    
    val = series['SQN']
    if pd.isna(val):
        return -1
    return val

def main():
    print("=== Iniciando Optimización Resumible (Donchian Breakout QQQ) ===")

    # ----------------------------------------------------
    # FIX: Agent Crash / Multiprocessing Error
    # Forzamos el uso de hilos (ThreadPool) en lugar de procesos pesados
    # para evitar que el entorno del agente se quede sin memoria o colapse.
    # ----------------------------------------------------
    from multiprocessing.dummy import Pool as ThreadPool
    import backtesting
    backtesting.Pool = ThreadPool
    print("Multiprocesamiento ajustado a ThreadPool para estabilidad del agente.")
    
    # 1. Obtener Datos
    df = descargar_datos_intradia_qqq()
    if len(df) == 0:
        print("Error: No se pudieron descargar datos.")
        return
    print(f"Datos cargados: {len(df)} registros.")

    bt = Backtest(
        df,
        DonchianBreakoutQQQ,
        cash=10000,
        commission=.0005, 
        exclusive_orders=True
    )

    # 2. Definir Espacio de Búsqueda
    # Iteraremos sobre 'lookback' como el bucle principal ("batch")
    lookback_range = range(10, 80, 5)  # E.g. [10, 15, ..., 75]
    
    # Parámetros secundarios (se optimizan en cada batch)
    exit_lookback_range = range(3, 30, 2)
    atr_stop_mult_range = [1.0, 1.5, 2.0, 2.5, 3.0]

    # 3. Cargar Checkpoint existente
    processed_lookbacks = set()
    if os.path.exists(CHECKPOINT_FILE):
        print(f"Encontrado checkpoint: {CHECKPOINT_FILE}. Cargando progreso previo...")
        try:
            # Asumimos que el CSV guarda una columna con el valor de 'lookback'
            # Backtesting.py heatmap tiene MultiIndex, pero al guardar a CSV se aplana o se gestiona.
            # Vamos a leerlo para ver qué lookbacks ya están.
            existing_results = pd.read_csv(CHECKPOINT_FILE)
            # Limpiar datos corruptos o incompletos
            existing_results.dropna(subset=['score'], inplace=True)
            if 'lookback' in existing_results.columns:
                processed_lookbacks = set(existing_results['lookback'].unique())
            print(f"Se encontraron {len(processed_lookbacks)} valores de lookback ya procesados.")
        except Exception as e:
            print(f"Advertencia: No se pudo leer el checkpoint correctamente ({e}). Se empezará de nuevo.")

    # 4. Bucle de Optimización por Lotes
    full_heatmap = []
    
    for lb in lookback_range:
        if lb in processed_lookbacks:
            print(f"Skipping lookback={lb} (ya procesado).")
            continue
            
        print(f"\nProcesando lote: lookback={lb}...")
        
        try:
            # Ejecutamos optimización solo para ESTE valor de lookback
            # Nota: lookback=[lb] fuerza a que solo use este valor
            stats, heatmap = bt.optimize(
                lookback=[lb], 
                exit_lookback=exit_lookback_range,
                atr_stop_mult=atr_stop_mult_range,
                constraint=lambda p: p.exit_lookback < p.lookback,
                maximize=optim_func,
                return_heatmap=True
            )
            
            # Convertir heatmap a DataFrame plano para guardar
            # El heatmap de backtesting es una Series con MultiIndex. Reset index lo convierte a DF.
            batch_results = heatmap.reset_index()
            batch_results.rename(columns={0: 'score'}, inplace=True) # Rename value column
            
            # Verificar que 'score' no tenga NaNs
            batch_results.dropna(subset=['score'], inplace=True)
            
            if batch_results.empty:
                print(f"Advertencia: Lote lookback={lb} no generó resultados válidos.")
                continue

            # Guardar en CSV (Append mode)
            header = not os.path.exists(CHECKPOINT_FILE)
            batch_results.to_csv(CHECKPOINT_FILE, mode='a', header=header, index=False)
            
            print(f"Lote lookback={lb} completado y guardado.")
            
        except Exception as e:
            print(f"Error procesando lookback={lb}: {e}")
            # Continuamos con el siguiente para no detener todo el proceso
            continue

    print("\n=== Todos los lotes procesados. Generando reporte final... ===")
    
    # 5. Análisis Final y Reporte
    if not os.path.exists(CHECKPOINT_FILE):
        print("No se generaron resultados.")
        return

    # Leer todos los resultados acumulados
    all_results = pd.read_csv(CHECKPOINT_FILE)
    
    if all_results.empty:
        print("El archivo de resultados está vacío.")
        return

    # Encontrar la mejor combinación
    # Asumimos que la columna de score (la métrica optimizada) es la última o tiene nombre 'score' si hicimos rename
    # Si backtesting devuelve series, el nombre es None, por eso hicimos rename arriba.
    # Pero cuidado: si el archivo ya existía de antes sin rename, podría variar. 
    # Aseguramos usar la última columna si 'score' no existe.
    score_col = 'score' if 'score' in all_results.columns else all_results.columns[-1]
    
    best_row_idx = all_results[score_col].idxmax()
    best_row = all_results.iloc[best_row_idx]
    
    print("\nMejor Combinación Encontrada:")
    print(best_row)
    
    # Extraer parámetros de la mejor fila
    best_params = {
        'lookback': int(best_row['lookback']),
        'exit_lookback': int(best_row['exit_lookback']),
        'atr_stop_mult': float(best_row['atr_stop_mult'])
    }
    
    print("Re-ejecutando backtest con mejores parámetros para generar HTML...")
    
    # Ejecutar una vez más con los mejores parámetros para obtener el objeto stats completo y plot
    final_stats = bt.run(**best_params)
    
    print(final_stats)
    
    # Guardar Reportes
    try:
        with open(REPORT_FILE, 'w') as f:
            f.write("Resultados Optimización Resumible:\n")
            f.write(str(final_stats))
            f.write("\n\nMejores Parámetros (desde CSV):\n")
            f.write(str(best_params))
        
        bt.plot(filename=HTML_FILE, open_browser=False)
        print(f"\nReporte guardado en: {HTML_FILE}")
        print(f"Detalles en: {REPORT_FILE}")
        
    except Exception as e:
        print(f"Error guardando reporte final: {e}")

if __name__ == "__main__":
    main()
