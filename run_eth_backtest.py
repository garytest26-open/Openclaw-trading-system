"""Backtest ETH 2Y con el modelo especifico ETH"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.append(os.getcwd())

import backtest_multi as bm

bm.MODEL_PATH = 'models/tamc_eth_best.pth'
bm.TICKERS = {'ETH': 'ETH-USD'}

print("=== BACKTEST ETH 2Y con modelo ETH-especifico ===")
model = bm.load_model()
df = bm.load_data('ETH-USD')
results = bm.run_backtest(model, df, 'ETH')
metrics = bm.calculate_metrics(results)

m = metrics
print(f"\n=== RESULTADOS ETH ===")
print(f"Retorno:       {m['total_return']:+.2f}%")
print(f"Capital Final: ${m['final_equity']:,.0f}")
print(f"Sharpe:        {m['sharpe']:.2f}")
print(f"Max DD:        -{m['max_dd']:.2f}%")
print(f"Win Rate:      {m['win_rate']:.1f}%")
print(f"Profit Factor: {m['profit_factor']:.2f}")
print(f"Trades:        {m['total_trades']:,}")

bm.generate_individual_html('ETH', results, metrics, 'tamc_backtest_2y_eth_v2.html')
print("\nReporte guardado: tamc_backtest_2y_eth_v2.html")
