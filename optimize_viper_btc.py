"""
Optimización profunda de Viper Strike SOLO para BTC
Grid más amplio que el script principal para encontrar los mejores parámetros.
Los parámetros de ETH ya están fijados y no se tocan.
"""
import pandas as pd
import numpy as np
import yfinance as yf
from backtesting import Backtest, Strategy
import itertools
import sys
import io
import warnings
warnings.filterwarnings('ignore')

if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Importar la estrategia desde el archivo principal
from viper_strike_strategy import ViperStrike, get_data


def main():
    print("====================================================")
    print("  VIPER STRIKE - Optimizacion Profunda SOLO BTC")
    print("====================================================")

    # 1. Descargar datos BTC
    df = get_data("BTC-USD", period="729d", interval="1h")
    if df.empty or len(df) < 100:
        print("Error: datos insuficientes")
        return

    bt = Backtest(df, ViperStrike, cash=10_000_000, commission=0.001,
                  exclusive_orders=False, hedging=True)

    # 2. Grid ampliado para BTC
    param_grid = list(itertools.product(
        [15, 20, 25],              # bb_period
        [1.5, 2.0, 2.5],           # bb_std
        [1.0, 1.5, 2.0],          # kc_atr_mult
        [8, 10, 14],              # adx_period
        [10, 15, 20],             # adx_threshold
        [3, 5, 7],                 # pivot_len
        [1.5, 2.0, 2.5, 3.0],     # trail_atr_mult
    ))

    print(f"  Total combinaciones: {len(param_grid)}")
    print(f"  Esto puede tardar bastante. Mostrando progreso cada 500 runs...")
    print()

    best_stats = None
    best_return = -999999
    best_sharpe = -999999
    best_params = {}
    best_by_sharpe_params = {}
    best_by_sharpe_stats = None

    total = len(param_grid)

    for i, (bb_p, bb_s, kc_m, adx_p, adx_t, piv, trail) in enumerate(param_grid):
        ViperStrike.bb_period = bb_p
        ViperStrike.bb_std = bb_s
        ViperStrike.kc_atr_mult = kc_m
        ViperStrike.adx_period = adx_p
        ViperStrike.adx_threshold = adx_t
        ViperStrike.pivot_len = piv
        ViperStrike.trail_atr_mult = trail

        try:
            s = bt.run()
            ret = s['Return [%]']
            n_trades = s['# Trades']
            sharpe = s.get('Sharpe Ratio', 0)
            if pd.isna(sharpe):
                sharpe = 0

            if i % 500 == 0:
                print(f"  [{i}/{total}] Mejor hasta ahora: R={best_return:.2f}%  |  Actual: R={ret:.2f}%, T={n_trades}")

            if n_trades >= 10:
                if ret > best_return:
                    best_return = ret
                    best_stats = s
                    best_params = {
                        'bb_period': bb_p, 'bb_std': bb_s, 'kc_atr_mult': kc_m,
                        'adx_period': adx_p, 'adx_threshold': adx_t,
                        'pivot_len': piv, 'trail_atr_mult': trail
                    }
                if sharpe > best_sharpe:
                    best_sharpe = sharpe
                    best_by_sharpe_stats = s
                    best_by_sharpe_params = {
                        'bb_period': bb_p, 'bb_std': bb_s, 'kc_atr_mult': kc_m,
                        'adx_period': adx_p, 'adx_threshold': adx_t,
                        'pivot_len': piv, 'trail_atr_mult': trail
                    }
        except Exception:
            pass

    # 3. Resultados
    print("\n" + "="*55)
    print("  MEJOR POR RETURN")
    print("="*55)
    if best_stats is not None:
        print(f"  Params: {best_params}")
        for m in ['Return [%]', 'Buy & Hold Return [%]', 'Sharpe Ratio',
                  'Max. Drawdown [%]', '# Trades', 'Win Rate [%]',
                  'Profit Factor', 'Avg. Trade [%]', 'Expectancy [%]']:
            if m in best_stats:
                v = best_stats[m]
                if isinstance(v, float): print(f"  {m:.<35} {v:>10.2f}")
                else: print(f"  {m:.<35} {str(v):>10s}")

        # Guardar HTML
        for k, v in best_params.items():
            setattr(ViperStrike, k, v)
        bt.run()
        bt.plot(filename='viper_strike_btc_optimized.html', open_browser=False)
        print(f"\n  [SAVE] viper_strike_btc_optimized.html")
    else:
        print("  Sin resultados con suficientes trades.")

    print("\n" + "="*55)
    print("  MEJOR POR SHARPE RATIO")
    print("="*55)
    if best_by_sharpe_stats is not None:
        print(f"  Params: {best_by_sharpe_params}")
        for m in ['Return [%]', 'Sharpe Ratio', 'Max. Drawdown [%]',
                  '# Trades', 'Win Rate [%]', 'Profit Factor']:
            if m in best_by_sharpe_stats:
                v = best_by_sharpe_stats[m]
                if isinstance(v, float): print(f"  {m:.<35} {v:>10.2f}")
                else: print(f"  {m:.<35} {str(v):>10s}")

        if best_by_sharpe_params != best_params:
            for k, v in best_by_sharpe_params.items():
                setattr(ViperStrike, k, v)
            bt.run()
            bt.plot(filename='viper_strike_btc_sharpe.html', open_browser=False)
            print(f"\n  [SAVE] viper_strike_btc_sharpe.html")

    # Recordatorio ETH
    print("\n" + "="*55)
    print("  PARAMETROS ETH (sin cambios)")
    print("="*55)
    print("  bb_period=20, bb_std=1.5, kc_atr_mult=2.0")
    print("  adx_period=14, adx_threshold=15, trail_atr_mult=2.0")
    print("  Return: +38.95%, Alpha: +71.47%")
    print("="*55)


if __name__ == "__main__":
    main()
