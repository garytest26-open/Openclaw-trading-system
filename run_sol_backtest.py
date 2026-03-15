"""Backtest rapido de SOL con el modelo especifico SOL"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.append(os.getcwd())

import backtest_multi as bm

bm.MODEL_PATH = 'models/tamc_sol_best.pth'
bm.TICKERS = {'SOL': 'SOL-USD'}

print("=== BACKTEST SOL 2Y con modelo SOL-especifico ===")
model = bm.load_model()
df = bm.load_data('SOL-USD')
results = bm.run_backtest(model, df, 'SOL')
metrics = bm.calculate_metrics(results)

m = metrics
print(f"\n=== RESULTADOS SOL ===")
print(f"Retorno:       {m['total_return']:+.2f}%")
print(f"Capital Final: ${m['final_equity']:,.0f}")
print(f"Sharpe:        {m['sharpe']:.2f}")
print(f"Max DD:        -{m['max_dd']:.2f}%")
print(f"Win Rate:      {m['win_rate']:.1f}%")
print(f"Profit Factor: {m['profit_factor']:.2f}")
print(f"Trades:        {m['total_trades']:,}")

bm.generate_individual_html('SOL', results, metrics, 'tamc_backtest_2y_sol_v2.html')
print("\nReporte guardado: tamc_backtest_2y_sol_v2.html")
