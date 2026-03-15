#!/usr/bin/env python3
"""
OPTIMIZADOR NASDAQ CON CHECKPOINTING
=====================================
Este script busca la mejor combinacion de parametros para la estrategia
Donchian Breakout en QQQ, guardando progreso regularmente.

Caracteristicas:
- Grid search completo
- Checkpoint cada 20 iteraciones
- Resumen automatico si se interrumpe
- Busqueda de configuraciones rentables con multiples trades
"""

import pandas as pd
import numpy as np
from datetime import datetime
import yfinance as yf
from backtesting import Backtest, Strategy
import pickle
import os
from itertools import product
import warnings
warnings.filterwarnings('ignore')

# ==========================================
# CONFIGURACION
# ==========================================
CHECKPOINT_FILE = 'optimization_checkpoint.pkl'
RESULTS_FILE = 'optimization_results.csv'
BEST_PARAMS_FILE = 'best_params.txt'
CHECKPOINT_EVERY = 20  # Guardar cada 20 iteraciones

# Espacio de busqueda
PARAM_GRID = {
    'lookback_entry': [5, 10, 15, 20, 25, 30],
    'lookback_exit': [3, 5, 7, 10, 12, 15],
    'atr_multiplier': [0.5, 1.0, 1.5, 2.0, 2.5],
    'use_trend_filter': [False, True],  # Filtro MA(50)
}

# ==========================================
# ESTRATEGIA PARAMETRIZABLE
# ==========================================
class OptimizableBreakout(Strategy):
    """Estrategia con parametros optimizables"""
    
    lookback_entry = 20
    lookback_exit = 10
    atr_period = 14
    atr_multiplier = 2.0
    use_trend_filter = False
    ma_filter_period = 50
    
    def init(self):
        high = self.data.High
        low = self.data.Low
        close = self.data.Close
        
        # Canales Donchian
        self.entry_high = self.I(
            lambda x: pd.Series(x).rolling(self.lookback_entry).max().shift(1), 
            high
        )
        self.entry_low = self.I(
            lambda x: pd.Series(x).rolling(self.lookback_entry).min().shift(1), 
            low
        )
        self.exit_high = self.I(
            lambda x: pd.Series(x).rolling(self.lookback_exit).max().shift(1), 
            high
        )
        self.exit_low = self.I(
            lambda x: pd.Series(x).rolling(self.lookback_exit).min().shift(1), 
            low
        )
        
        # ATR
        def calculate_atr(high, low, close):
            tr1 = high - low
            tr2 = abs(high - pd.Series(close).shift(1))
            tr3 = abs(low - pd.Series(close).shift(1))
            tr = pd.concat([pd.Series(tr1), tr2, tr3], axis=1).max(axis=1)
            return tr.rolling(self.atr_period).mean()
        
        self.atr = self.I(calculate_atr, high, low, close)
        
        # Filtro de tendencia (opcional)
        if self.use_trend_filter:
            self.ma_filter = self.I(
                lambda x: pd.Series(x).rolling(self.ma_filter_period).mean(),
                close
            )
    
    def next(self):
        price = self.data.Close[-1]
        
        if np.isnan(self.entry_high[-1]) or np.isnan(self.atr[-1]):
            return
        
        # Verificar filtro de tendencia
        if self.use_trend_filter:
            if np.isnan(self.ma_filter[-1]):
                return
            
            # Solo long si precio > MA
            # Solo short si precio < MA
            above_ma = price > self.ma_filter[-1]
        else:
            above_ma = True  # Sin filtro, permitir ambos
        
        # Gestion de posiciones
        if self.position:
            if self.position.is_long:
                if price < self.exit_low[-1]:
                    self.position.close()
            elif self.position.is_short:
                if price > self.exit_high[-1]:
                    self.position.close()
            return
        
        # Entradas
        if price > self.entry_high[-1]:
            if not self.use_trend_filter or above_ma:
                sl_price = price - (self.atr[-1] * self.atr_multiplier)
                self.buy(sl=sl_price)
        
        elif price < self.entry_low[-1]:
            if not self.use_trend_filter or not above_ma:
                sl_price = price + (self.atr[-1] * self.atr_multiplier)
                self.sell(sl=sl_price)


# ==========================================
# FUNCIONES DE CHECKPOINTING
# ==========================================
def save_checkpoint(iteration, results, tested_params):
    """Guarda el estado actual de la optimizacion"""
    checkpoint = {
        'iteration': iteration,
        'results': results,
        'tested_params': tested_params,
        'timestamp': datetime.now()
    }
    with open(CHECKPOINT_FILE, 'wb') as f:
        pickle.dump(checkpoint, f)
    print(f"[CHECKPOINT] Guardado en iteracion {iteration}")


def load_checkpoint():
    """Carga checkpoint si existe"""
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, 'rb') as f:
            checkpoint = pickle.load(f)
        print(f"[CHECKPOINT] Cargado desde iteracion {checkpoint['iteration']}")
        print(f"[CHECKPOINT] Timestamp: {checkpoint['timestamp']}")
        return checkpoint
    return None


def save_results_csv(results):
    """Guarda resultados en CSV"""
    df = pd.DataFrame(results)
    df = df.sort_values('return', ascending=False)
    df.to_csv(RESULTS_FILE, index=False)
    print(f"[GUARDADO] Resultados en {RESULTS_FILE}")


def save_best_params(results):
    """Guarda los mejores parametros encontrados"""
    if not results:
        return
    
    df = pd.DataFrame(results)
    
    # Filtrar solo configuraciones rentables con trades suficientes
    df_profitable = df[(df['return'] > 0) & (df['trades'] >= 12)]
    
    with open(BEST_PARAMS_FILE, 'w', encoding='utf-8') as f:
        f.write("="*80 + "\n")
        f.write("MEJORES PARAMETROS ENCONTRADOS\n")
        f.write("="*80 + "\n\n")
        f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total combinaciones probadas: {len(df)}\n")
        f.write(f"Configuraciones rentables: {len(df_profitable)}\n\n")
        
        if len(df_profitable) > 0:
            f.write("="*80 + "\n")
            f.write("TOP 10 CONFIGURACIONES RENTABLES\n")
            f.write("="*80 + "\n\n")
            
            for i, row in df_profitable.head(10).iterrows():
                f.write(f"#{i+1} - Retorno: {row['return']:.2f}%\n")
                f.write(f"   Lookback Entry: {int(row['lookback_entry'])}\n")
                f.write(f"   Lookback Exit: {int(row['lookback_exit'])}\n")
                f.write(f"   ATR Multiplier: {row['atr_multiplier']:.1f}\n")
                f.write(f"   Filtro Tendencia: {'Si' if row['use_trend_filter'] else 'No'}\n")
                f.write(f"   Trades: {int(row['trades'])}\n")
                f.write(f"   Win Rate: {row['win_rate']:.1f}%\n")
                f.write(f"   Sharpe: {row['sharpe']:.2f}\n")
                f.write(f"   Max DD: {row['max_dd']:.2f}%\n")
                f.write("\n")
        else:
            f.write("NO SE ENCONTRARON CONFIGURACIONES RENTABLES\n")
            f.write("\nMejores configuraciones por metrica:\n\n")
            
            f.write(f"Mayor Retorno:\n")
            best_return = df.loc[df['return'].idxmax()]
            f.write(f"  Retorno: {best_return['return']:.2f}%\n")
            f.write(f"  Parametros: Entry={int(best_return['lookback_entry'])}, ")
            f.write(f"Exit={int(best_return['lookback_exit'])}, ")
            f.write(f"ATR={best_return['atr_multiplier']:.1f}\n\n")
            
            f.write(f"Mayor Sharpe:\n")
            best_sharpe = df.loc[df['sharpe'].idxmax()]
            f.write(f"  Sharpe: {best_sharpe['sharpe']:.2f}\n")
            f.write(f"  Parametros: Entry={int(best_sharpe['lookback_entry'])}, ")
            f.write(f"Exit={int(best_sharpe['lookback_exit'])}, ")
            f.write(f"ATR={best_sharpe['atr_multiplier']:.1f}\n\n")
    
    print(f"[GUARDADO] Mejores parametros en {BEST_PARAMS_FILE}")


# ==========================================
# OPTIMIZACION PRINCIPAL
# ==========================================
def run_optimization():
    """Ejecuta la optimizacion completa con checkpoint"""
    
    print("="*80)
    print("OPTIMIZADOR NASDAQ - CON CHECKPOINTING")
    print("="*80)
    
    # Descargar datos
    print("\n[1/4] Descargando datos de QQQ (1 año)...")
    data = yf.download("QQQ", period="1y", interval="1d", progress=False)
    
    if len(data) == 0:
        print("[ERROR] No se pudieron descargar datos")
        return
    
    data.columns = [col.capitalize() if isinstance(col, str) else col[0].capitalize() 
                    for col in data.columns]
    data = data[['Open', 'High', 'Low', 'Close', 'Volume']]
    
    print(f"[OK] Datos: {len(data)} velas")
    print(f"     Periodo: {data.index[0].date()} a {data.index[-1].date()}")
    
    # Cargar checkpoint si existe
    checkpoint = load_checkpoint()
    if checkpoint:
        results = checkpoint['results']
        tested_params = checkpoint['tested_params']
        start_iteration = checkpoint['iteration'] + 1
    else:
        results = []
        tested_params = set()
        start_iteration = 0
    
    # Generar todas las combinaciones
    param_combinations = list(product(
        PARAM_GRID['lookback_entry'],
        PARAM_GRID['lookback_exit'],
        PARAM_GRID['atr_multiplier'],
        PARAM_GRID['use_trend_filter']
    ))
    
    total_combinations = len(param_combinations)
    
    print(f"\n[2/4] Iniciando optimizacion...")
    print(f"      Total combinaciones: {total_combinations}")
    print(f"      Ya probadas: {len(tested_params)}")
    print(f"      Restantes: {total_combinations - len(tested_params)}")
    print(f"      Checkpoint cada: {CHECKPOINT_EVERY} iteraciones")
    
    # Ejecutar optimizacion
    iteration = start_iteration
    
    try:
        for i, (entry, exit, atr_mult, use_filter) in enumerate(param_combinations):
            
            # Saltar si ya se probo
            param_key = (entry, exit, atr_mult, use_filter)
            if param_key in tested_params:
                continue
            
            iteration += 1
            
            # Configurar estrategia
            class CurrentStrategy(OptimizableBreakout):
                lookback_entry = entry
                lookback_exit = exit
                atr_multiplier = atr_mult
                use_trend_filter = use_filter
            
            try:
                # Ejecutar backtest
                bt = Backtest(data, CurrentStrategy, cash=10000, commission=0.001)
                stats = bt.run()
                
                # Guardar resultado
                result = {
                    'lookback_entry': entry,
                    'lookback_exit': exit,
                    'atr_multiplier': atr_mult,
                    'use_trend_filter': use_filter,
                    'return': stats['Return [%]'],
                    'trades': stats['# Trades'],
                    'win_rate': stats['Win Rate [%]'],
                    'sharpe': stats['Sharpe Ratio'],
                    'max_dd': stats['Max. Drawdown [%]'],
                    'profit_factor': stats.get('Profit Factor', 0)
                }
                
                results.append(result)
                tested_params.add(param_key)
                
                # Mostrar progreso
                if iteration % 10 == 0 or result['return'] > 0:
                    status = "[RENTABLE]" if result['return'] > 0 else ""
                    print(f"[{iteration}/{total_combinations}] {status} "
                          f"Entry={entry}, Exit={exit}, ATR={atr_mult:.1f}, "
                          f"Filter={'Si' if use_filter else 'No'} -> "
                          f"Return={result['return']:.2f}%, Trades={result['trades']}")
                
                # Checkpoint
                if iteration % CHECKPOINT_EVERY == 0:
                    save_checkpoint(iteration, results, tested_params)
                    save_results_csv(results)
                    save_best_params(results)
            
            except Exception as e:
                print(f"[ERROR] Combinacion {param_key}: {e}")
                continue
    
    except KeyboardInterrupt:
        print("\n[INTERRUPCION] Guardando progreso...")
        save_checkpoint(iteration, results, tested_params)
        save_results_csv(results)
        save_best_params(results)
        print("[OK] Progreso guardado. Puedes reanudar ejecutando de nuevo el script.")
        return
    
    # Guardar resultados finales
    print(f"\n[3/4] Optimizacion completada!")
    print(f"      Total probadas: {len(results)}")
    
    save_checkpoint(iteration, results, tested_params)
    save_results_csv(results)
    save_best_params(results)
    
    # Mostrar resumen
    print(f"\n[4/4] RESUMEN DE RESULTADOS")
    print("="*80)
    
    df = pd.DataFrame(results)
    
    print(f"\nConfiguraciones probadas: {len(df)}")
    print(f"Configuraciones rentables: {len(df[df['return'] > 0])}")
    print(f"Con >12 trades/año: {len(df[df['trades'] >= 12])}")
    print(f"Rentables + >12 trades: {len(df[(df['return'] > 0) & (df['trades'] >= 12)])}")
    
    if len(df[df['return'] > 0]) > 0:
        best = df.loc[df['return'].idxmax()]
        print(f"\n[MEJOR CONFIGURACION]")
        print(f"  Retorno: {best['return']:.2f}%")
        print(f"  Lookback Entry: {int(best['lookback_entry'])}")
        print(f"  Lookback Exit: {int(best['lookback_exit'])}")
        print(f"  ATR Multiplier: {best['atr_multiplier']:.1f}")
        print(f"  Filtro Tendencia: {'Si' if best['use_trend_filter'] else 'No'}")
        print(f"  Trades: {int(best['trades'])}")
        print(f"  Win Rate: {best['win_rate']:.1f}%")
        print(f"  Sharpe: {best['sharpe']:.2f}")
    
    print("\n" + "="*80)
    print(f"[OK] Resultados guardados en:")
    print(f"     - {RESULTS_FILE}")
    print(f"     - {BEST_PARAMS_FILE}")
    print(f"     - {CHECKPOINT_FILE}")
    print("="*80)


if __name__ == "__main__":
    run_optimization()
