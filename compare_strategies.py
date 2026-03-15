#!/usr/bin/env python3
"""
COMPARADOR DE ESTRATEGIAS QQQ
==============================
Compara múltiples configuraciones de parámetros encontradas en las optimizaciones
y muestra una tabla comparativa de métricas clave.
"""

import pandas as pd
import numpy as np
from datetime import datetime
from backtesting import Backtest, Strategy
import yfinance as yf

# ==========================================
# ESTRATEGIA PARAMETRIZABLE
# ==========================================
class OptimizableBreakout(Strategy):
    """Estrategia con parámetros optimizables"""
    
    lookback_entry = 20
    lookback_exit = 10
    atr_period = 14
    atr_multiplier = 2.0
    
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
    
    def next(self):
        price = self.data.Close[-1]
        
        if np.isnan(self.entry_high[-1]) or np.isnan(self.atr[-1]):
            return
        
        # Gestión de posiciones
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
            sl_price = price - (self.atr[-1] * self.atr_multiplier)
            self.buy(sl=sl_price)
        elif price < self.entry_low[-1]:
            sl_price = price + (self.atr[-1] * self.atr_multiplier)
            self.sell(sl=sl_price)


# ==========================================
# CONFIGURACIONES A COMPARAR
# ==========================================
CONFIGURATIONS = [
    {
        'name': 'Original (No Optimizado)',
        'params': {'lookback_entry': 20, 'lookback_exit': 10, 'atr_multiplier': 2.0}
    },
    {
        'name': 'Mejor Sharpe (#67)',
        'params': {'lookback_entry': 10, 'lookback_exit': 3, 'atr_multiplier': 2.0}
    },
    {
        'name': 'Mejor Return (#51)',
        'params': {'lookback_entry': 5, 'lookback_exit': 15, 'atr_multiplier': 0.5}
    },
    {
        'name': 'Alta Win Rate (#69)',
        'params': {'lookback_entry': 10, 'lookback_exit': 3, 'atr_multiplier': 2.5}
    },
]


def run_comparison():
    """Ejecuta comparación de todas las configuraciones"""
    
    print("=" * 100)
    print("COMPARADOR DE ESTRATEGIAS QQQ")
    print("=" * 100)
    
    # Descargar datos
    print("\n[1/3] Descargando datos de QQQ (1 año)...")
    data = yf.download("QQQ", period="1y", interval="1d", progress=False)
    
    if len(data) == 0:
        print("[ERROR] No se pudieron descargar datos")
        return
    
    data.columns = [col.capitalize() if isinstance(col, str) else col[0].capitalize() 
                    for col in data.columns]
    data = data[['Open', 'High', 'Low', 'Close', 'Volume']]
    
    print(f"[OK] Datos: {len(data)} velas ({data.index[0].date()} a {data.index[-1].date()})")
    
    # Ejecutar backtests
    print(f"\n[2/3] Ejecutando backtests ({len(CONFIGURATIONS)} configuraciones)...")
    
    results = []
    
    for i, config in enumerate(CONFIGURATIONS, 1):
        print(f"   [{i}/{len(CONFIGURATIONS)}] Probando: {config['name']}...", end=' ')
        
        # Crear estrategia con parámetros específicos
        class CurrentStrategy(OptimizableBreakout):
            lookback_entry = config['params']['lookback_entry']
            lookback_exit = config['params']['lookback_exit']
            atr_multiplier = config['params']['atr_multiplier']
        
        try:
            bt = Backtest(data, CurrentStrategy, cash=10000, commission=0.001)
            stats = bt.run()
            
            results.append({
                'Configuración': config['name'],
                'Entry': config['params']['lookback_entry'],
                'Exit': config['params']['lookback_exit'],
                'ATR': config['params']['atr_multiplier'],
                'Retorno %': f"{stats['Return [%]']:.2f}",
                'Trades': int(stats['# Trades']),
                'Win Rate %': f"{stats['Win Rate [%]']:.1f}",
                'Sharpe': f"{stats['Sharpe Ratio']:.2f}",
                'Max DD %': f"{stats['Max. Drawdown [%]']:.2f}",
                'Profit Factor': f"{stats.get('Profit Factor', 0):.2f}",
                'Capital Final': f"${stats['Equity Final [$]']:,.0f}"
            })
            
            print("OK")
            
        except Exception as e:
            print(f"ERROR: {e}")
            continue
    
    # Mostrar resultados
    print(f"\n[3/3] RESULTADOS DE LA COMPARACIÓN")
    print("=" * 100)
    
    df = pd.DataFrame(results)
    
    # Tabla detallada
    print("\n[*] COMPARACION COMPLETA:\n")
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 120)
    print(df.to_string(index=False))
    
    # Resumen
    print("\n" + "=" * 100)
    print("[*] RESUMEN:")
    print("=" * 100)
    
    # Encontrar mejor en cada métrica
    df_numeric = df.copy()
    for col in ['Retorno %', 'Win Rate %', 'Sharpe', 'Max DD %', 'Profit Factor']:
        df_numeric[col] = df_numeric[col].astype(float)
    
    best_return_idx = df_numeric['Retorno %'].idxmax()
    best_sharpe_idx = df_numeric['Sharpe'].idxmax()
    best_wr_idx = df_numeric['Win Rate %'].idxmax()
    
    print(f"\n[MEJOR RETORNO]    {df.iloc[best_return_idx]['Configuración']}")
    print(f"   -> {df.iloc[best_return_idx]['Retorno %']}% | {df.iloc[best_return_idx]['Trades']} trades")
    
    print(f"\n[MEJOR SHARPE]     {df.iloc[best_sharpe_idx]['Configuración']}")
    print(f"   -> Sharpe {df.iloc[best_sharpe_idx]['Sharpe']} | DD {df.iloc[best_sharpe_idx]['Max DD %']}%")
    
    print(f"\n[MEJOR WIN RATE]   {df.iloc[best_wr_idx]['Configuración']}")
    print(f"   -> {df.iloc[best_wr_idx]['Win Rate %']}% | PF {df.iloc[best_wr_idx]['Profit Factor']}")
    
    # Recomendación
    print("\n" + "=" * 100)
    print("[!] RECOMENDACION:")
    print("=" * 100)
    
    # La mejor configuración equilibrada es la que tiene mejor Sharpe
    best_config = df.iloc[best_sharpe_idx]
    print(f"\nConfiguración recomendada: {best_config['Configuración']}")
    print(f"   Parámetros: Entry={best_config['Entry']}, Exit={best_config['Exit']}, ATR={best_config['ATR']}")
    print(f"   Métricas: Return {best_config['Retorno %']}%, Sharpe {best_config['Sharpe']}, WR {best_config['Win Rate %']}%")
    print(f"   Resultado: {best_config['Capital Final']} (de $10,000)")
    
    # Guardar resultados
    df.to_csv('comparison_results.csv', index=False)
    print(f"\n[OK] Resultados guardados en: comparison_results.csv")
    print("=" * 100)


if __name__ == "__main__":
    run_comparison()
