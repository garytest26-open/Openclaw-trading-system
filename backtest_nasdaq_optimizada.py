#!/usr/bin/env python3
"""
BACKTEST - ESTRATEGIA NASDAQ OPTIMIZADA
=========================================
Estrategia de Breakout Donchian optimizada para QQQ
Basada en el archivo original del usuario
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from backtesting import Backtest, Strategy
from backtesting.lib import crossover
import yfinance as yf

# ==========================================
# ESTRATEGIA OPTIMIZADA
# ==========================================
class OptimizedBreakoutQQQ(Strategy):
    """
    Estrategia de Donchian Breakout Optimizada para QQQ
    
    Parámetros optimizados:
    - lookback_entry: 20 períodos (canal de entrada)
    - lookback_exit: 10 períodos (canal de salida)  
    - atr_period: 14 (cálculo de volatilidad)
    - atr_multiplier: 2.0 (stop loss dinámico)
    """
    
    # Parámetros optimizados (basados en optimizer_nasdaq_checkpoint.py)
    # Mejor configuración encontrada: Return 6.22%, Win Rate 53.3%, 15 trades/año
    lookback_entry = 10  # Optimizado: era 20
    lookback_exit = 3    # Optimizado: era 10
    atr_period = 14
    atr_multiplier = 2.0
    
    def init(self):
        # Preparar datos
        high = self.data.High
        low = self.data.Low
        close = self.data.Close
        
        # Canal de Donchian para entrada (20 períodos)
        self.entry_high = self.I(
            lambda x: pd.Series(x).rolling(self.lookback_entry).max().shift(1), 
            high
        )
        self.entry_low = self.I(
            lambda x: pd.Series(x).rolling(self.lookback_entry).min().shift(1), 
            low
        )
        
        # Canal de Donchian para salida (10 períodos)
        self.exit_high = self.I(
            lambda x: pd.Series(x).rolling(self.lookback_exit).max().shift(1), 
            high
        )
        self.exit_low = self.I(
            lambda x: pd.Series(x).rolling(self.lookback_exit).min().shift(1), 
            low
        )
        
        # ATR para stop loss dinámico
        def calculate_atr(high, low, close):
            tr1 = high - low
            tr2 = abs(high - pd.Series(close).shift(1))
            tr3 = abs(low - pd.Series(close).shift(1))
            tr = pd.concat([pd.Series(tr1), tr2, tr3], axis=1).max(axis=1)
            return tr.rolling(self.atr_period).mean()
        
        self.atr = self.I(calculate_atr, high, low, close)
    
    def next(self):
        price = self.data.Close[-1]
        
        # Validar que los indicadores están calculados
        if np.isnan(self.entry_high[-1]) or np.isnan(self.atr[-1]):
            return
        
        # GESTIÓN DE POSICIONES ABIERTAS
        if self.position:
            if self.position.is_long:
                # Salida Long: precio cae por debajo del canal de salida
                if price < self.exit_low[-1]:
                    self.position.close()
            
            elif self.position.is_short:
                # Salida Short: precio sube por encima del canal de salida
                if price > self.exit_high[-1]:
                    self.position.close()
            
            return
        
        # SEÑALES DE ENTRADA
        # Entrada Long: ruptura del canal superior
        if price > self.entry_high[-1]:
            sl_price = price - (self.atr[-1] * self.atr_multiplier)
            self.buy(sl=sl_price)
        
        # Entrada Short: ruptura del canal inferior  
        elif price < self.entry_low[-1]:
            sl_price = price + (self.atr[-1] * self.atr_multiplier)
            self.sell(sl=sl_price)


def run_backtest(data, cash=10000, commission=0.001, plot=False):
    """
    Ejecuta el backtest con los datos proporcionados
    """
    bt = Backtest(
        data,
        OptimizedBreakoutQQQ,
        cash=cash,
        commission=commission,
        exclusive_orders=True
    )
    
    stats = bt.run()
    
    if plot:
        bt.plot()
    
    return bt, stats


# ==========================================
# EJECUCIÓN PRINCIPAL
# ==========================================
if __name__ == "__main__":
    print("\n" + "="*80)
    print("BACKTEST - ESTRATEGIA NASDAQ OPTIMIZADA (QQQ)")
    print("="*80)
    
    # DESCARGAR DATOS REALES
    print("\n[*] Descargando datos de QQQ...")
    
    try:
        data = yf.download(
            "QQQ",
            period="1y",
            interval="1d",
            progress=False
        )
        
        if len(data) == 0:
            raise Exception("No se descargaron datos")
        
        # Preparar formato
        data.columns = [col.capitalize() if isinstance(col, str) else col[0].capitalize() for col in data.columns]
        data = data[['Open', 'High', 'Low', 'Close', 'Volume']]
        
        print(f"[OK] Datos descargados: {len(data)} velas")
        print(f"   Período: {data.index[0]} a {data.index[-1]}")
        print(f"   Precio inicial: ${data['Close'].iloc[0]:.2f}")
        print(f"   Precio final: ${data['Close'].iloc[-1]:.2f}")
        
    except Exception as e:
        print(f"[ERROR] Error descargando datos: {e}")
        print("Generando datos sintéticos...")
        
        # Datos sintéticos de respaldo
        np.random.seed(42)
        n_bars = 60 * 24
        dates = pd.date_range(end=datetime.now(), periods=n_bars, freq='1h')
        
        initial_price = 500.0
        returns = np.random.normal(0.0004, 0.008, n_bars)
        prices = initial_price * np.exp(np.cumsum(returns))
        
        data = pd.DataFrame(index=dates)
        data['Close'] = prices
        data['Open'] = data['Close'].shift(1).fillna(initial_price)
        data['High'] = data[['Open', 'Close']].max(axis=1) * (1 + np.abs(np.random.normal(0, 0.003, n_bars)))
        data['Low'] = data[['Open', 'Close']].min(axis=1) * (1 - np.abs(np.random.normal(0, 0.003, n_bars)))
        data['Volume'] = np.random.randint(1000000, 5000000, n_bars)
        
        print(f"[OK] Datos sintéticos generados: {len(data)} velas")
    
    # EJECUTAR BACKTEST
    print("\n" + "="*80)
    print(" EJECUTANDO BACKTEST")
    print("="*80)
    print("\nParámetros:")
    print(f"   Capital Inicial: $10,000")
    print(f"   Comisión: 0.1%")
    print(f"   Lookback Entrada: 10 (optimizado)")
    print(f"   Lookback Salida: 3 (optimizado)")
    print(f"   ATR Multiplier: 2.0x")
    
    try:
        bt, stats = run_backtest(data, cash=10000, commission=0.001, plot=False)
        
        # MOSTRAR RESULTADOS
        print("\n" + "="*80)
        print(" RESULTADOS DEL BACKTEST")
        print("="*80)
        
        print(f"\n RENDIMIENTO:")
        print(f"   Retorno Total:        {stats['Return [%]']:.2f}%")
        print(f"   Buy & Hold Return:    {stats['Buy & Hold Return [%]']:.2f}%")
        print(f"   Capital Final:        ${stats['Equity Final [$]']:,.2f}")
        print(f"   Ganancia/Pérdida:     ${stats['Equity Final [$]'] - 10000:,.2f}")
        
        print(f"\n TRADING:")
        print(f"   Número de Trades:     {stats['# Trades']}")
        print(f"   Win Rate:             {stats['Win Rate [%]']:.1f}%")
        print(f"   Mejor Trade:          {stats['Best Trade [%]']:.2f}%")
        print(f"   Peor Trade:           {stats['Worst Trade [%]']:.2f}%")
        print(f"   Promedio Trade:       {stats['Avg. Trade [%]']:.2f}%")
        
        try:
            print(f"   Profit Factor:        {stats['Profit Factor']:.2f}")
        except:
            print(f"   Profit Factor:        N/A")
        
        print(f"\n[!]  RIESGO:")
        print(f"   Max Drawdown:         {stats['Max. Drawdown [%]']:.2f}%")
        print(f"   Avg Drawdown:         {stats['Avg. Drawdown [%]']:.2f}%")
        print(f"   Max DD Duration:      {stats['Max. Drawdown Duration']}")
        
        print(f"\n SHARPE/SORTINO:")
        print(f"   Sharpe Ratio:         {stats['Sharpe Ratio']:.2f}")
        print(f"   Sortino Ratio:        {stats['Sortino Ratio']:.2f}")
        print(f"   Calmar Ratio:         {stats['Calmar Ratio']:.2f}")
        
        print(f"\n  EXPOSICIÓN:")
        print(f"   Tiempo en Mercado:    {stats['Exposure Time [%]']:.1f}%")
        print(f"   Duración Promedio:    {stats['Avg. Trade Duration']}")
        
        # GUARDAR RESULTADOS
        print("\n" + "="*80)
        print(" GUARDANDO RESULTADOS")
        print("="*80)
        
        # Guardar gráfico HTML
        try:
            bt.plot(filename='nasdaq_optimizada_backtest.html', open_browser=False)
            print("[OK] Gráfico guardado: nasdaq_optimizada_backtest.html")
        except Exception as e:
            print(f"[!]  No se pudo guardar el gráfico: {e}")
        
        # Guardar trades
        if hasattr(stats, '_trades') and len(stats._trades) > 0:
            stats._trades.to_csv('nasdaq_optimizada_trades.csv', index=False)
            print("[OK] Trades guardados: nasdaq_optimizada_trades.csv")
        
        # Guardar estadísticas
        with open('nasdaq_optimizada_stats.txt', 'w', encoding='utf-8') as f:
            f.write("BACKTEST - ESTRATEGIA NASDAQ OPTIMIZADA\n")
            f.write("="*80 + "\n\n")
            f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(str(stats))
        print("[OK] Estadísticas guardadas: nasdaq_optimizada_stats.txt")
        
        print("\n" + "="*80)
        print("[OK] BACKTEST COMPLETADO EXITOSAMENTE")
        print("="*80)
        
    except Exception as e:
        print(f"\n[ERROR] Error ejecutando backtest: {e}")
        import traceback
        traceback.print_exc()
