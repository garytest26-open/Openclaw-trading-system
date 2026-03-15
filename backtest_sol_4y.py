"""
Backtest SOL-USD 4 Anos — Intervalo Diario (1d)
Usa el modelo tamc_sol_best.pth entrenado en datos horarios.
Nota: yfinance limita 1h a ~730 dias, por lo que se usa 1d para 4 anos.
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.append(os.getcwd())

import numpy as np
import pandas as pd
import yfinance as yf
import torch
import warnings
from datetime import datetime, timedelta

warnings.filterwarnings('ignore')

from tamc_strategy import (
    StrategyConfig, DuelingDQN, TradingEnvironment,
    calculate_indicators, device
)

# ============================================================
# CONFIG
# ============================================================
TICKER      = "SOL-USD"
INTERVAL    = "1d"
YEARS       = 4
MODEL_PATH  = "models/tamc_sol_best.pth"
INITIAL_CAP = 10_000.0
OUTPUT_HTML = "tamc_backtest_4y_sol.html"

# ============================================================
# CARGAR DATOS
# ============================================================
end_date   = datetime.now()
start_date = end_date - timedelta(days=YEARS * 365)

print(f"\n=== BACKTEST SOL {YEARS} ANOS ({INTERVAL}) ===")
print(f"Periodo: {start_date.strftime('%Y-%m-%d')} => {end_date.strftime('%Y-%m-%d')}")

df = yf.download(TICKER, start=start_date, end=end_date,
                 interval=INTERVAL, progress=False, auto_adjust=True)
if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.droplevel(1)
df = df[['Open','High','Low','Close','Volume']].dropna()

config = StrategyConfig()
df = calculate_indicators(df, config)
print(f"Datos cargados: {len(df)} velas diarias | {df.index[0].date()} -> {df.index[-1].date()}")

# ============================================================
# CARGAR MODELO — inferir state_dim desde el checkpoint
# ============================================================
checkpoint = torch.load(MODEL_PATH, map_location=device, weights_only=True)
state_dim  = checkpoint['feature_layer.0.weight'].shape[1]
print(f"state_dim detectado del modelo: {state_dim}")

model = DuelingDQN(state_dim, 5, config.hidden_dim).to(device)
model.load_state_dict(checkpoint)
model.eval()
print(f"Modelo cargado: {MODEL_PATH}")


# ============================================================
# EJECUTAR BACKTEST
# ============================================================
config.initial_capital = INITIAL_CAP
env = TradingEnvironment(df, config)
state = env.reset()

action_names  = {0:"Flat", 1:"Long 50%", 2:"Long 100%", 3:"Short 50%", 4:"Short 100%"}
equity_hist   = []
actions_taken = []
timestamps    = []
prices        = []
trades        = []
current_trade = None
done          = False
step          = 0

print(f"\nEjecutando backtest sobre {len(df) - config.lookback_window} dias...\n")

while not done:
    with torch.no_grad():
        st = torch.FloatTensor(state).unsqueeze(0).to(device)
        action = model(st).argmax().item()

    prev_position = env.position
    prev_balance  = env.balance
    next_state, _, done, _ = env.step(action)

    idx = min(env.current_step - 1, len(df) - 1)
    current_price = float(df.iloc[idx]['Close'])
    ts = str(df.index[idx].date())

    equity_hist.append(env.equity_curve[-1])
    actions_taken.append(action)
    timestamps.append(ts)
    prices.append(current_price)

    # Tracking trades
    if prev_position == 0 and env.position != 0:
        current_trade = {'entry_time': ts, 'entry_price': current_price,
                         'direction': 'Long' if env.position > 0 else 'Short'}
    elif prev_position != 0 and env.position == 0 and current_trade:
        pnl = env.balance - prev_balance
        current_trade.update({'exit_time': ts, 'exit_price': current_price, 'pnl': pnl})
        trades.append(current_trade)
        current_trade = None
    elif prev_position != 0 and env.position != 0 and current_trade and np.sign(prev_position) != np.sign(env.position):
        pnl = env.balance - prev_balance
        current_trade.update({'exit_time': ts, 'exit_price': current_price, 'pnl': pnl})
        trades.append(current_trade)
        current_trade = {'entry_time': ts, 'entry_price': current_price,
                         'direction': 'Long' if env.position > 0 else 'Short'}

    state = next_state
    step += 1
    if step % 200 == 0:
        eq  = equity_hist[-1]
        pct = (eq - INITIAL_CAP) / INITIAL_CAP * 100
        print(f"  Dia {step}/{len(df)} | {ts} | Equity: ${eq:,.0f} ({pct:+.1f}%) | {action_names[action]}")

# ============================================================
# CALCULAR METRICAS
# ============================================================
equity  = np.array(equity_hist)
initial = INITIAL_CAP
final   = env.equity_curve[-1]

total_return = (final - initial) / initial * 100

if len(equity) > 1:
    rets   = np.diff(equity) / np.maximum(equity[:-1], 1e-8)
    rets   = rets[np.isfinite(rets)]
    sharpe = (np.mean(rets) / np.std(rets) * np.sqrt(365)) if np.std(rets) > 0 else 0.0
else:
    sharpe = 0.0

peak   = np.maximum.accumulate(equity)
dd     = (peak - equity) / np.maximum(peak, 1e-8)
max_dd = float(np.max(dd) * 100)
calmar = total_return / max_dd if max_dd > 0 else 0.0

wins       = [t for t in trades if t.get('pnl', 0) > 0]
losses     = [t for t in trades if t.get('pnl', 0) <= 0]
win_rate   = len(wins) / len(trades) * 100 if trades else 0
avg_win    = np.mean([t['pnl'] for t in wins])    if wins    else 0
avg_loss   = abs(np.mean([t['pnl'] for t in losses])) if losses else 0
profit_f   = (sum(t['pnl'] for t in wins) / abs(sum(t['pnl'] for t in losses))
              if losses else 999.0)

action_counts = {i: actions_taken.count(i) for i in range(5)}
total_acts    = sum(action_counts.values()) or 1

print(f"\n{'='*50}")
print(f"RESULTADOS SOL {YEARS} ANOS")
print(f"{'='*50}")
print(f"Retorno:       {total_return:+.2f}%")
print(f"Capital Final: ${final:,.0f}")
print(f"Sharpe:        {sharpe:.2f}")
print(f"Max Drawdown:  -{max_dd:.2f}%")
print(f"Calmar:        {calmar:.2f}")
print(f"Win Rate:      {win_rate:.1f}%")
print(f"Profit Factor: {profit_f:.2f}")
print(f"Total Trades:  {len(trades):,}")
print(f"{'='*50}")

# ============================================================
# GENERAR HTML
# ============================================================
ret_color = "#00ff88" if total_return >= 0 else "#ff4444"

equity_js = ",".join(f"{e:.2f}" for e in equity)
ts_js     = ",".join(f'"{t}"' for t in timestamps)
price_js  = ",".join(f"{p:.2f}" for p in prices)

trade_rows = ""
for t in trades[-60:]:
    pnl = t.get('pnl', 0)
    col = "#00ff88" if pnl > 0 else "#ff4444"
    trade_rows += f"""
    <tr>
      <td>{t.get('entry_time','')}</td><td>{t.get('exit_time','')}</td>
      <td>{t.get('direction','')}</td>
      <td>${t.get('entry_price',0):.2f}</td><td>${t.get('exit_price',0):.2f}</td>
      <td style="color:{col}">${pnl:.2f}</td>
    </tr>"""

act_rows = ""
for i, name in action_names.items():
    cnt = action_counts.get(i, 0)
    act_rows += f"<tr><td>{name}</td><td>{cnt}</td><td>{cnt/total_acts*100:.1f}%</td></tr>"

html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>TAMC — SOL {YEARS} Anos</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
  *{{margin:0;padding:0;box-sizing:border-box;}}
  body{{background:#0a0e1a;color:#e0e6f0;font-family:'Segoe UI',sans-serif;padding:20px;}}
  h1{{color:#7c83fd;text-align:center;font-size:2em;padding:20px 0 5px;}}
  .sub{{text-align:center;color:#8892b0;margin-bottom:30px;font-size:0.9em;}}
  .kpi-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:15px;margin-bottom:30px;}}
  .kpi{{background:linear-gradient(135deg,#13192d,#1a2235);border:1px solid #2a3050;border-radius:12px;padding:20px;text-align:center;}}
  .kpi .val{{font-size:1.8em;font-weight:700;margin-top:8px;}}
  .kpi .lbl{{color:#8892b0;font-size:0.75em;text-transform:uppercase;letter-spacing:1px;}}
  .card{{background:#13192d;border:1px solid #2a3050;border-radius:12px;padding:25px;margin-bottom:25px;}}
  .card h2{{color:#7c83fd;margin-bottom:15px;font-size:1em;text-transform:uppercase;letter-spacing:1px;}}
  canvas{{max-height:320px;}}
  table{{width:100%;border-collapse:collapse;font-size:0.85em;}}
  th{{background:#1a2235;color:#8892b0;padding:9px;text-align:left;border-bottom:1px solid #2a3050;}}
  td{{padding:8px 10px;border-bottom:1px solid #1a2235;}}
  tr:hover td{{background:#1a2235;}}
  .g{{color:#00ff88;}} .r{{color:#ff4444;}} .b{{color:#7c83fd;}}
</style>
</head>
<body>
<h1>TAMC — SOL-USD {YEARS} Anos</h1>
<p class="sub">Backtest {start_date.strftime('%Y-%m-%d')} → {end_date.strftime('%Y-%m-%d')} | Intervalo: {INTERVAL} | Modelo: {MODEL_PATH} | Capital: ${INITIAL_CAP:,.0f}</p>

<div class="kpi-grid">
  <div class="kpi"><div class="lbl">Retorno Total</div><div class="val" style="color:{ret_color}">{total_return:+.2f}%</div></div>
  <div class="kpi"><div class="lbl">Capital Final</div><div class="val b">${final:,.0f}</div></div>
  <div class="kpi"><div class="lbl">Sharpe Ratio</div><div class="val {'g' if sharpe>1 else 'r'}">{sharpe:.2f}</div></div>
  <div class="kpi"><div class="lbl">Max Drawdown</div><div class="val r">-{max_dd:.2f}%</div></div>
  <div class="kpi"><div class="lbl">Calmar Ratio</div><div class="val b">{calmar:.2f}</div></div>
  <div class="kpi"><div class="lbl">Win Rate</div><div class="val b">{win_rate:.1f}%</div></div>
  <div class="kpi"><div class="lbl">Total Trades</div><div class="val b">{len(trades):,}</div></div>
  <div class="kpi"><div class="lbl">Profit Factor</div><div class="val {'g' if profit_f>=1 else 'r'}">{profit_f:.2f}</div></div>
</div>

<div class="card">
  <h2>Curva de Equity — {YEARS} Anos</h2>
  <canvas id="equity_chart"></canvas>
</div>

<div class="card">
  <h2>Precio SOL vs Equity (%)</h2>
  <canvas id="dual_chart"></canvas>
</div>

<div class="card" style="display:grid;grid-template-columns:1fr 1fr;gap:25px;">
  <div>
    <h2>Distribucion de Acciones</h2>
    <table><thead><tr><th>Accion</th><th>N</th><th>%</th></tr></thead><tbody>{act_rows}</tbody></table>
  </div>
  <div>
    <h2>Stats de Trades</h2>
    <table>
      <tr><td>Total</td><td>{len(trades):,}</td></tr>
      <tr><td>Ganadores</td><td class="g">{len(wins)}</td></tr>
      <tr><td>Perdedores</td><td class="r">{len(losses)}</td></tr>
      <tr><td>Avg Win</td><td class="g">${avg_win:.2f}</td></tr>
      <tr><td>Avg Loss</td><td class="r">-${avg_loss:.2f}</td></tr>
      <tr><td>Ratio W/L</td><td>{(avg_win/avg_loss if avg_loss>0 else 0):.2f}x</td></tr>
    </table>
  </div>
</div>

<div class="card">
  <h2>Ultimos 60 Trades</h2>
  <table><thead><tr><th>Entrada</th><th>Salida</th><th>Dir</th><th>P. Entrada</th><th>P. Salida</th><th>PnL</th></tr></thead>
  <tbody>{trade_rows}</tbody></table>
</div>

<script>
const labels  = [{ts_js}];
const equity  = [{equity_js}];
const prices  = [{price_js}];
const pctChg  = equity.map(e => ((e - {INITIAL_CAP}) / {INITIAL_CAP} * 100).toFixed(2));
const grid    = {{color:'#1a2235'}};
const tick    = {{color:'#8892b0'}};

new Chart(document.getElementById('equity_chart'), {{
  type:'line',
  data:{{labels, datasets:[{{
    label:'Equity ($)',data:equity,
    borderColor:'#7c83fd',backgroundColor:'rgba(124,131,253,0.08)',
    fill:true,pointRadius:0,tension:0.3
  }}]}},
  options:{{responsive:true,plugins:{{legend:{{labels:{{color:'#8892b0'}}}}}},
    scales:{{x:{{ticks:{{...tick,maxTicksLimit:10}},grid}},y:{{ticks:tick,grid}}}}}}
}});

new Chart(document.getElementById('dual_chart'), {{
  type:'line',
  data:{{labels, datasets:[
    {{label:'Precio SOL ($)',data:prices,borderColor:'#f0b429',pointRadius:0,tension:0.3,yAxisID:'y'}},
    {{label:'Equity (%)',data:pctChg,borderColor:'#00ff88',pointRadius:0,tension:0.3,yAxisID:'y1'}}
  ]}},
  options:{{responsive:true,plugins:{{legend:{{labels:{{color:'#8892b0'}}}}}},
    scales:{{
      x:{{ticks:{{...tick,maxTicksLimit:10}},grid}},
      y:{{ticks:{{color:'#f0b429'}},grid,position:'left'}},
      y1:{{ticks:{{color:'#00ff88'}},position:'right',grid:{{drawOnChartArea:false}}}}
    }}
  }}
}});
</script>
</body>
</html>"""

with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
    f.write(html)
print(f"\nReporte guardado: {OUTPUT_HTML}")
