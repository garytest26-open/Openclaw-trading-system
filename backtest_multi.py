# ============================================================
# BACKTEST MULTI-ACTIVO: Estrategia TAMC
# BTC-USD, ETH-USD, SOL-USD — 2 años de datos (1h)
# Genera reportes individuales + informe comparativo
# ============================================================

import numpy as np
import pandas as pd
import yfinance as yf
import torch
import os
import sys
import warnings
from datetime import datetime, timedelta

warnings.filterwarnings('ignore')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from tamc_strategy import (
    StrategyConfig, DuelingDQN, TradingEnvironment,
    calculate_indicators, device
)

# ============================================================
# CONFIGURACIÓN
# ============================================================

MODEL_PATH = "models/tamc_btc_best.pth"
INITIAL_CAPITAL = 10_000.0
INTERVAL = "1h"
PERIOD = "730d"   # ~2 años, máximo permitido por yfinance en 1h

TICKERS = {
    "BTC": "BTC-USD",
    "ETH": "ETH-USD",
    "SOL": "SOL-USD",
}

# ============================================================
# FUNCIONES
# ============================================================

def load_data(ticker_sym: str) -> pd.DataFrame:
    print(f"\n[{ticker_sym}] Descargando {PERIOD} de datos en {INTERVAL}...")
    df = yf.download(ticker_sym, period=PERIOD, interval=INTERVAL,
                     progress=False, auto_adjust=True)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)
    df = df[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()
    config = StrategyConfig()
    df = calculate_indicators(df, config)
    print(f"[{ticker_sym}] {len(df)} velas | {df.index[0]} -> {df.index[-1]}")
    return df


def load_model() -> torch.nn.Module:
    config = StrategyConfig()
    config.n_features = 5
    state_dim = config.n_features + 7
    model = DuelingDQN(state_dim, 5, config.hidden_dim).to(device)
    model.load_state_dict(torch.load(MODEL_PATH, map_location=device, weights_only=True))
    model.eval()
    print(f"Modelo cargado: {MODEL_PATH}")
    return model


def run_backtest(model, df: pd.DataFrame, ticker_name: str) -> dict:
    config = StrategyConfig()
    config.n_features = 5
    config.initial_capital = INITIAL_CAPITAL

    env = TradingEnvironment(df, config)
    state = env.reset()

    action_names = {0: "Flat", 1: "Long 50%", 2: "Long 100%",
                    3: "Short 50%", 4: "Short 100%"}
    equity_history, actions_taken, trades, timestamps, prices = [], [], [], [], []
    current_trade = None
    done = False
    step = 0
    prev_balance = config.initial_capital

    while not done:
        with torch.no_grad():
            state_t = torch.FloatTensor(state).unsqueeze(0).to(device)
            action = model(state_t).argmax().item()

        prev_position = env.position
        prev_balance = env.balance
        next_state, _, done, _ = env.step(action)

        idx = env.current_step - 1
        current_price = df.iloc[min(idx, len(df)-1)]['Close']
        ts = str(df.index[min(idx, len(df)-1)])

        equity_history.append(env.equity_curve[-1])
        actions_taken.append(action)
        timestamps.append(ts)
        prices.append(float(current_price))

        # Trade tracking
        if prev_position == 0 and env.position != 0:
            current_trade = {'entry_time': ts, 'entry_price': float(current_price),
                             'direction': 'Long' if env.position > 0 else 'Short',
                             'size': abs(env.position)}
        elif prev_position != 0 and env.position == 0 and current_trade:
            current_trade.update({'exit_time': ts, 'exit_price': float(current_price),
                                  'pnl': float(env.balance - prev_balance),
                                  'pnl_pct': float((env.balance - prev_balance) / INITIAL_CAPITAL * 100)})
            trades.append(current_trade)
            current_trade = None
        elif prev_position != 0 and env.position != 0 and current_trade and np.sign(prev_position) != np.sign(env.position):
            current_trade.update({'exit_time': ts, 'exit_price': float(current_price),
                                  'pnl': float(env.balance - prev_balance),
                                  'pnl_pct': float((env.balance - prev_balance) / INITIAL_CAPITAL * 100)})
            trades.append(current_trade)
            current_trade = {'entry_time': ts, 'entry_price': float(current_price),
                             'direction': 'Long' if env.position > 0 else 'Short',
                             'size': abs(env.position)}

        state = next_state
        step += 1
        if step % 2000 == 0:
            eq = equity_history[-1]
            print(f"  [{ticker_name}] Step {step}/{len(df)} | Equity: ${eq:,.0f} ({(eq-INITIAL_CAPITAL)/INITIAL_CAPITAL*100:+.1f}%) | {action_names[action]}")

    if current_trade:
        lp = float(df.iloc[-1]['Close'])
        current_trade.update({'exit_time': str(df.index[-1]), 'exit_price': lp, 'pnl': 0.0, 'pnl_pct': 0.0})
        trades.append(current_trade)

    return {'equity_history': equity_history, 'actions': actions_taken,
            'trades': trades, 'timestamps': timestamps, 'prices': prices,
            'final_equity': env.equity_curve[-1], 'initial_capital': INITIAL_CAPITAL}


def calculate_metrics(results: dict) -> dict:
    equity = np.array(results['equity_history'])
    initial, final = results['initial_capital'], results['final_equity']
    trades = results['trades']

    total_return = (final - initial) / initial * 100

    if len(equity) > 1:
        rets = np.diff(equity) / np.maximum(equity[:-1], 1e-8)
        rets = rets[np.isfinite(rets)]
        sharpe = (np.mean(rets) / np.std(rets) * np.sqrt(24*365)) if np.std(rets) > 0 else 0.0
    else:
        sharpe = 0.0

    peak = np.maximum.accumulate(equity)
    dd = (peak - equity) / np.maximum(peak, 1e-8)
    max_dd = float(np.max(dd) * 100)

    calmar = (total_return / max_dd) if max_dd > 0 else 0.0

    wins = [t for t in trades if t.get('pnl', 0) > 0]
    losses = [t for t in trades if t.get('pnl', 0) <= 0]
    win_rate = len(wins) / len(trades) * 100 if trades else 0
    avg_win = np.mean([t['pnl'] for t in wins]) if wins else 0
    avg_loss = abs(np.mean([t['pnl'] for t in losses])) if losses else 0
    gross_profit = sum(t['pnl'] for t in wins)
    gross_loss = abs(sum(t['pnl'] for t in losses))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 999.0

    action_counts = {i: results['actions'].count(i) for i in range(5)}
    action_names = {0:"Flat", 1:"Long 50%", 2:"Long 100%", 3:"Short 50%", 4:"Short 100%"}

    return {
        'total_return': total_return,
        'sharpe': sharpe,
        'max_dd': max_dd,
        'calmar': calmar,
        'total_trades': len(trades),
        'win_rate': win_rate,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'profit_factor': profit_factor,
        'final_equity': final,
        'action_counts': action_counts,
        'action_names': action_names,
    }


def generate_individual_html(ticker_name: str, results: dict, metrics: dict, filename: str):
    equity = results['equity_history']
    timestamps = results['timestamps']
    prices = results['prices']
    trades = results['trades']
    m = metrics
    action_names = m['action_names']
    action_counts = m['action_counts']
    total_actions = sum(action_counts.values()) or 1

    ret_color = "#00ff88" if m['total_return'] >= 0 else "#ff4444"

    # Build trade rows
    trade_rows_html = ""
    for t in trades[-50:]:
        pnl = t.get('pnl', 0)
        color = "#00ff88" if pnl > 0 else "#ff4444"
        trade_rows_html += f"""
        <tr>
            <td>{t.get('entry_time','')[:16]}</td>
            <td>{t.get('exit_time','')[:16]}</td>
            <td>{t.get('direction','')}</td>
            <td>${t.get('entry_price',0):.2f}</td>
            <td>${t.get('exit_price',0):.2f}</td>
            <td style="color:{color}">${pnl:.2f}</td>
        </tr>"""

    action_rows_html = ""
    for i, name in action_names.items():
        cnt = action_counts.get(i, 0)
        pct = cnt / total_actions * 100
        action_rows_html += f"<tr><td>{name}</td><td>{cnt:,}</td><td>{pct:.1f}%</td></tr>"

    equity_js = ",".join(f"{e:.2f}" for e in equity[::10])
    ts_js = ",".join(f'"{t[:16]}"' for t in timestamps[::10])
    price_js = ",".join(f"{p:.2f}" for p in prices[::10])

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>TAMC Backtest - {ticker_name} (2 Años)</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
  * {{margin:0;padding:0;box-sizing:border-box;}}
  body {{background:#0a0e1a;color:#e0e6f0;font-family:'Segoe UI',sans-serif;padding:20px;}}
  h1 {{color:#7c83fd;text-align:center;font-size:2em;padding:20px 0 5px;}}
  .subtitle {{text-align:center;color:#8892b0;margin-bottom:30px;font-size:0.95em;}}
  .kpi-grid {{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:15px;margin-bottom:30px;}}
  .kpi {{background:linear-gradient(135deg,#13192d,#1a2235);border:1px solid #2a3050;border-radius:12px;padding:20px;text-align:center;}}
  .kpi .val {{font-size:2em;font-weight:700;margin-top:8px;}}
  .kpi .lbl {{color:#8892b0;font-size:0.8em;text-transform:uppercase;letter-spacing:1px;}}
  .positive {{color:#00ff88;}} .negative {{color:#ff4444;}} .neutral {{color:#7c83fd;}}
  .card {{background:#13192d;border:1px solid #2a3050;border-radius:12px;padding:25px;margin-bottom:25px;}}
  .card h2 {{color:#7c83fd;margin-bottom:15px;font-size:1.1em;text-transform:uppercase;letter-spacing:1px;}}
  canvas {{max-height:320px;}}
  table {{width:100%;border-collapse:collapse;font-size:0.85em;}}
  th {{background:#1a2235;color:#8892b0;padding:10px;text-align:left;border-bottom:1px solid #2a3050;}}
  td {{padding:9px 10px;border-bottom:1px solid #1a2235;}}
  tr:hover td {{background:#1a2235;}}
</style>
</head>
<body>
<h1>TAMC — {ticker_name}</h1>
<p class="subtitle">Backtest 2 años | {INTERVAL} | Modelo: {MODEL_PATH} | Capital: ${INITIAL_CAPITAL:,.0f}</p>

<div class="kpi-grid">
  <div class="kpi"><div class="lbl">Retorno Total</div><div class="val" style="color:{ret_color}">{m['total_return']:+.2f}%</div></div>
  <div class="kpi"><div class="lbl">Capital Final</div><div class="val neutral">${m['final_equity']:,.0f}</div></div>
  <div class="kpi"><div class="lbl">Sharpe Ratio</div><div class="val {'positive' if m['sharpe']>0 else 'negative'}">{m['sharpe']:.2f}</div></div>
  <div class="kpi"><div class="lbl">Max Drawdown</div><div class="val negative">-{m['max_dd']:.2f}%</div></div>
  <div class="kpi"><div class="lbl">Calmar Ratio</div><div class="val neutral">{m['calmar']:.2f}</div></div>
  <div class="kpi"><div class="lbl">Win Rate</div><div class="val neutral">{m['win_rate']:.1f}%</div></div>
  <div class="kpi"><div class="lbl">Total Trades</div><div class="val neutral">{m['total_trades']:,}</div></div>
  <div class="kpi"><div class="lbl">Profit Factor</div><div class="val {'positive' if m['profit_factor']>1 else 'negative'}">{m['profit_factor']:.2f}</div></div>
</div>

<div class="card">
  <h2>Curva de Equity</h2>
  <canvas id="equity_chart"></canvas>
</div>

<div class="card">
  <h2>Precio vs Equity</h2>
  <canvas id="price_chart"></canvas>
</div>

<div class="card" style="display:grid;grid-template-columns:1fr 1fr;gap:25px;">
  <div>
    <h2>Distribución de Acciones</h2>
    <table><thead><tr><th>Acción</th><th>N</th><th>%</th></tr></thead><tbody>{action_rows_html}</tbody></table>
  </div>
  <div>
    <h2>Estadísticas de Trades</h2>
    <table><thead><tr><th>Métrica</th><th>Valor</th></tr></thead>
    <tbody>
      <tr><td>Avg Win</td><td style="color:#00ff88">${m['avg_win']:.2f}</td></tr>
      <tr><td>Avg Loss</td><td style="color:#ff4444">-${m['avg_loss']:.2f}</td></tr>
      <tr><td>Ratio W/L</td><td>{(m['avg_win']/m['avg_loss']):.2f}x</td></tr>
    </tbody></table>
  </div>
</div>

<div class="card">
  <h2>Últimos 50 Trades</h2>
  <table><thead><tr><th>Entrada</th><th>Salida</th><th>Dir</th><th>Precio E.</th><th>Precio S.</th><th>PnL</th></tr></thead>
  <tbody>{trade_rows_html}</tbody></table>
</div>

<script>
const labels = [{ts_js}];
const equity = [{equity_js}];
const prices = [{price_js}];
const pctChg = equity.map(e => ((e - {INITIAL_CAPITAL}) / {INITIAL_CAPITAL} * 100).toFixed(2));

const chartDefaults = {{
  plugins: {{legend: {{labels: {{color:'#8892b0'}}}}}},
  scales: {{x: {{ticks:{{color:'#8892b0',maxTicksLimit:12}}, grid:{{color:'#1a2235'}}}},
             y: {{ticks:{{color:'#8892b0'}}, grid:{{color:'#1a2235'}}}}}}
}};

new Chart(document.getElementById('equity_chart'), {{
  type: 'line',
  data: {{labels, datasets: [{{label: 'Equity ($)', data: equity,
    borderColor: '#7c83fd', backgroundColor: 'rgba(124,131,253,0.1)', fill:true, pointRadius:0, tension:0.3}}]}},
  options: {{...chartDefaults, responsive:true}}
}});

new Chart(document.getElementById('price_chart'), {{
  type: 'line',
  data: {{labels, datasets: [
    {{label: 'Precio {ticker_name}', data: prices, borderColor:'#f0b429', pointRadius:0, tension:0.3, yAxisID:'y'}},
    {{label: 'Equity %', data: pctChg, borderColor:'#00ff88', pointRadius:0, tension:0.3, yAxisID:'y1'}}
  ]}},
  options: {{...chartDefaults, responsive:true,
    scales: {{
      x: {{ticks:{{color:'#8892b0',maxTicksLimit:12}}, grid:{{color:'#1a2235'}}}},
      y: {{ticks:{{color:'#f0b429'}}, grid:{{color:'#1a2235'}}, position:'left'}},
      y1: {{ticks:{{color:'#00ff88'}}, position:'right', grid:{{drawOnChartArea:false}}}}
    }}
  }}
}});
</script>
</body>
</html>"""

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"[{ticker_name}] Reporte HTML guardado: {filename}")


def generate_comparative_html(all_metrics: dict, filename: str):
    rows = ""
    for name, m in all_metrics.items():
        ret_col = "#00ff88" if m['total_return'] >= 0 else "#ff4444"
        sh_col = "#00ff88" if m['sharpe'] >= 0 else "#ff4444"
        pf_col = "#00ff88" if m['profit_factor'] >= 1 else "#ff4444"
        rows += f"""
        <tr>
            <td style="font-weight:700;color:#7c83fd">{name}</td>
            <td style="color:{ret_col}">{m['total_return']:+.2f}%</td>
            <td>${m['final_equity']:,.0f}</td>
            <td style="color:{sh_col}">{m['sharpe']:.2f}</td>
            <td style="color:#ff6b6b">-{m['max_dd']:.2f}%</td>
            <td>{m['calmar']:.2f}</td>
            <td>{m['win_rate']:.1f}%</td>
            <td style="color:{pf_col}">{m['profit_factor']:.2f}</td>
            <td>{m['total_trades']:,}</td>
        </tr>"""

    # Build chart data
    labels_js = ",".join(f'"{n}"' for n in all_metrics.keys())
    returns_js = ",".join(f"{m['total_return']:.2f}" for m in all_metrics.values())
    sharpe_js = ",".join(f"{m['sharpe']:.2f}" for m in all_metrics.values())
    dd_js = ",".join(f"{m['max_dd']:.2f}" for m in all_metrics.values())
    colors = '["#7c83fd","#f0b429","#00ff88"]'
    border_colors = '["#7c83fd","#f0b429","#00ff88"]'

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>TAMC — Informe Comparativo Multi-Activo</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
  * {{margin:0;padding:0;box-sizing:border-box;}}
  body {{background:#0a0e1a;color:#e0e6f0;font-family:'Segoe UI',sans-serif;padding:30px;}}
  h1 {{color:#7c83fd;text-align:center;font-size:2.2em;padding:20px 0 5px;}}
  .subtitle {{text-align:center;color:#8892b0;margin-bottom:30px;}}
  .card {{background:#13192d;border:1px solid #2a3050;border-radius:12px;padding:25px;margin-bottom:25px;}}
  .card h2 {{color:#7c83fd;margin-bottom:20px;font-size:1.1em;text-transform:uppercase;letter-spacing:1px;}}
  .charts-grid {{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:20px;margin-bottom:25px;}}
  canvas {{max-height:300px;}}
  table {{width:100%;border-collapse:collapse;}}
  th {{background:#1a2235;color:#8892b0;padding:12px;text-align:left;border-bottom:1px solid #2a3050;font-size:0.85em;text-transform:uppercase;letter-spacing:1px;}}
  td {{padding:14px 12px;border-bottom:1px solid #1a2235;font-size:0.95em;}}
  tr:hover td {{background:#1a2235;}}
  .badge {{display:inline-block;padding:3px 10px;border-radius:20px;font-size:0.8em;font-weight:600;}}
  .winner {{background:rgba(0,255,136,0.15);color:#00ff88;border:1px solid #00ff88;}}
</style>
</head>
<body>
<h1>TAMC — Informe Comparativo</h1>
<p class="subtitle">Backtest 2 Años | {INTERVAL} | Modelo: {MODEL_PATH} | Capital inicial: ${INITIAL_CAPITAL:,.0f} por activo</p>

<div class="card">
  <h2>Tabla Comparativa</h2>
  <table>
    <thead>
      <tr>
        <th>Activo</th><th>Retorno</th><th>Capital Final</th>
        <th>Sharpe</th><th>Max DD</th><th>Calmar</th>
        <th>Win Rate</th><th>Profit F.</th><th>Trades</th>
      </tr>
    </thead>
    <tbody>{rows}</tbody>
  </table>
</div>

<div class="charts-grid">
  <div class="card">
    <h2>Retorno Total (%)</h2>
    <canvas id="chart_return"></canvas>
  </div>
  <div class="card">
    <h2>Sharpe Ratio</h2>
    <canvas id="chart_sharpe"></canvas>
  </div>
  <div class="card">
    <h2>Max Drawdown (%)</h2>
    <canvas id="chart_dd"></canvas>
  </div>
</div>

<script>
const labels = [{labels_js}];
const colors = {colors};
const borders = {border_colors};
const defOpts = {{
  plugins: {{legend: {{labels: {{color:'#8892b0'}}}}}},
  scales: {{x: {{ticks:{{color:'#8892b0'}}, grid:{{color:'#1a2235'}}}},
             y: {{ticks:{{color:'#8892b0'}}, grid:{{color:'#1a2235'}}}}}}
}};

new Chart(document.getElementById('chart_return'), {{
  type:'bar', data:{{labels, datasets:[{{label:'Retorno %',
    data:[{returns_js}], backgroundColor:colors, borderColor:borders, borderWidth:2}}]}},
  options:{{...defOpts}}
}});
new Chart(document.getElementById('chart_sharpe'), {{
  type:'bar', data:{{labels, datasets:[{{label:'Sharpe',
    data:[{sharpe_js}], backgroundColor:colors, borderColor:borders, borderWidth:2}}]}},
  options:{{...defOpts}}
}});
new Chart(document.getElementById('chart_dd'), {{
  type:'bar', data:{{labels, datasets:[{{label:'Max DD %',
    data:[{dd_js}], backgroundColor:['rgba(255,68,68,0.6)','rgba(255,68,68,0.6)','rgba(255,68,68,0.6)'],
    borderColor:['#ff4444','#ff4444','#ff4444'], borderWidth:2}}]}},
  options:{{...defOpts}}
}});
</script>
</body>
</html>"""

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"\nInforme comparativo guardado: {filename}")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("TAMC — BACKTEST MULTI-ACTIVO (2 AÑOS)")
    print("=" * 60)

    model = load_model()
    all_metrics = {}

    for name, sym in TICKERS.items():
        print(f"\n{'='*50}")
        print(f"  Procesando: {name} ({sym})")
        print(f"{'='*50}")

        df = load_data(sym)
        if df.empty or len(df) < 500:
            print(f"[{name}] Datos insuficientes, saltando...")
            continue

        results = run_backtest(model, df, name)
        metrics = calculate_metrics(results)
        all_metrics[name] = metrics

        # Imprimir resumen en consola
        m = metrics
        print(f"\n  [{name}] RESULTADOS:")
        print(f"    Retorno:      {m['total_return']:+.2f}%")
        print(f"    Capital Final: ${m['final_equity']:,.0f}")
        print(f"    Sharpe:       {m['sharpe']:.2f}")
        print(f"    Max DD:       -{m['max_dd']:.2f}%")
        print(f"    Win Rate:     {m['win_rate']:.1f}%")
        print(f"    Trades:       {m['total_trades']:,}")

        # Generar HTML individual
        html_file = f"tamc_backtest_2y_{name.lower()}.html"
        generate_individual_html(name, results, metrics, html_file)

    # Generar informe comparativo
    if len(all_metrics) > 0:
        generate_comparative_html(all_metrics, "tamc_informe_comparativo.html")

    print("\n" + "=" * 60)
    print("BACKTESTS COMPLETADOS")
    print("=" * 60)
    for name, m in all_metrics.items():
        sign = "+" if m['total_return'] >= 0 else ""
        print(f"  {name:4s}: {sign}{m['total_return']:.2f}% | Sharpe {m['sharpe']:.2f} | DD -{m['max_dd']:.2f}%")
    print("=" * 60)
