"""
Descarga datos SOL-USDT 4 años (1h) desde data.binance.vision
y ejecuta el backtest TAMC de 4 años.
"""
import sys, os, glob
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.append(os.getcwd())

import numpy as np
import pandas as pd
import torch
import warnings
from datetime import datetime

warnings.filterwarnings('ignore')

# ============================================================
# PASO 1: DESCARGAR DATOS
# ============================================================
DATA_DIR    = "./data/binance_sol"
TICKER      = "SOLUSDT"
START_DATE  = "2022-01-01"
END_DATE    = datetime.now().strftime("%Y-%m-%d")
MODEL_PATH  = "models/tamc_sol_best.pth"
OUTPUT_HTML = "tamc_backtest_4y_sol_1h.html"
INITIAL_CAP = 10_000.0

if __name__ == '__main__':
    print("="*60)
    print("TAMC — BACKTEST SOL 4 ANOS (datos Binance 1h)")
    print("="*60)
    print(f"Descargando SOLUSDT 1h desde {START_DATE} hasta {END_DATE}")
    print("Esto puede tardar 1-2 minutos (descarga de ~35 archivos ZIP)...")

    try:
        from binance_historical_data import BinanceDataDumper
        
        dumper = BinanceDataDumper(
            DATA_DIR,
            asset_class="spot",
            data_type="klines",
            data_frequency="1h"
        )
        dumper.dump_data(
            tickers=[TICKER],
            date_start=datetime.strptime(START_DATE, "%Y-%m-%d").date(),
            date_end=datetime.strptime(END_DATE, "%Y-%m-%d").date(),
        )
        print("Descarga completada.")
    except Exception as e:
        print(f"Error en descarga: {e}")
        sys.exit(1)

    # ============================================================
    # PASO 2: COMBINAR CSVS
    # ============================================================
    print("\nCombinando archivos de datos...")
    pattern = os.path.join(DATA_DIR, "**", f"{TICKER}-1h-*.csv")
    files   = sorted(glob.glob(pattern, recursive=True))

    if not files:
        # Busqueda alternativa
        pattern2 = os.path.join(DATA_DIR, "spot", "monthly", "klines", TICKER, "1h", "*.csv")
        files = sorted(glob.glob(pattern2, recursive=True))
        if not files:
            # Busqueda mas amplia
            for root, dirs, fs in os.walk(DATA_DIR):
                for f in fs:
                    if f.endswith('.csv') and TICKER in f:
                        files.append(os.path.join(root, f))
            files = sorted(files)

    print(f"Archivos encontrados: {len(files)}")
    if not files:
        print(f"No se encontraron archivos CSV en {DATA_DIR}")
        # Listar lo que hay en el directorio
        for root, dirs, fs in os.walk(DATA_DIR):
            for f in fs[:10]:
                print(f"  Encontrado: {root}/{f}")
        sys.exit(1)

    cols = ['open_time','open','high','low','close','volume',
            'close_time','quote_vol','trades','taker_buy_base',
            'taker_buy_quote','ignore']

    dfs = []
    for f in files:
        try:
            tmp = pd.read_csv(f, header=None, names=cols)
            dfs.append(tmp)
        except Exception as e:
            print(f"  Error leyendo {f}: {e}")

    if not dfs:
        print("No se pudo leer ningún archivo.")
        sys.exit(1)

    df_raw = pd.concat(dfs, ignore_index=True)
    df_raw = df_raw.drop_duplicates('open_time').sort_values('open_time')

    # Convertir a formato OHLCV estándar
    timestamps = df_raw['open_time'].astype(float)
    # Algunos archivos de binance vienen con timestamp en microsegundos (16 digitos)
    timestamps = np.where(timestamps > 1e14, timestamps / 1000, timestamps)
    df_raw['Datetime'] = pd.to_datetime(timestamps, unit='ms')
    df_raw = df_raw.set_index('Datetime')
    df = df_raw[['open','high','low','close','volume']].copy()
    df.columns = ['Open','High','Low','Close','Volume']
    df = df.astype(float).dropna()

    print(f"Datos combinados: {len(df)} velas | {df.index[0]} -> {df.index[-1]}")

    # ============================================================
    # PASO 3: CALCULAR INDICADORES Y CARGAR MODELO
    # ============================================================
    from tamc_strategy import (
        StrategyConfig, DuelingDQN, TradingEnvironment,
        calculate_indicators, device
    )

    config = StrategyConfig()
    config.ticker = "SOLUSDT"
    df = calculate_indicators(df, config)
    print(f"Indicadores calculados. Velas validas: {len(df)}")

    checkpoint = torch.load(MODEL_PATH, map_location=device, weights_only=True)
    state_dim  = checkpoint['feature_layer.0.weight'].shape[1]
    print(f"state_dim del modelo: {state_dim}")

    model = DuelingDQN(state_dim, 5, config.hidden_dim).to(device)
    model.load_state_dict(checkpoint)
    model.eval()
    print(f"Modelo cargado: {MODEL_PATH}")

    # ============================================================
    # PASO 4: EJECUTAR BACKTEST
    # ============================================================
    config.initial_capital = INITIAL_CAP
    env   = TradingEnvironment(df, config)
    state = env.reset()

    action_names  = {0:"Flat", 1:"Long 50%", 2:"Long 100%", 3:"Short 50%", 4:"Short 100%"}
    equity_hist   = []
    actions_taken = []
    timestamps    = []
    prices_hist   = []
    trades        = []
    current_trade = None
    done          = False
    step          = 0
    total_steps   = len(df) - config.lookback_window

    print(f"\nEjecutando backtest sobre {total_steps} velas horarias...\n")

    while not done:
        with torch.no_grad():
            st     = torch.FloatTensor(state).unsqueeze(0).to(device)
            action = model(st).argmax().item()

        prev_pos = env.position
        prev_bal = env.balance
        next_state, _, done, _ = env.step(action)

        idx   = min(env.current_step - 1, len(df) - 1)
        price = float(df.iloc[idx]['Close'])
        ts    = str(df.index[idx])[:16]

        equity_hist.append(env.equity_curve[-1])
        actions_taken.append(action)
        timestamps.append(ts)
        prices_hist.append(price)

        # Tracking trades
        if prev_pos == 0 and env.position != 0:
            current_trade = {'entry_time': ts, 'entry_price': price,
                             'direction': 'Long' if env.position > 0 else 'Short'}
        elif prev_pos != 0 and env.position == 0 and current_trade:
            pnl = env.balance - prev_bal
            current_trade.update({'exit_time': ts, 'exit_price': price, 'pnl': pnl})
            trades.append(current_trade)
            current_trade = None
        elif prev_pos != 0 and env.position != 0 and current_trade and np.sign(prev_pos) != np.sign(env.position):
            pnl = env.balance - prev_bal
            current_trade.update({'exit_time': ts, 'exit_price': price, 'pnl': pnl})
            trades.append(current_trade)
            current_trade = {'entry_time': ts, 'entry_price': price,
                             'direction': 'Long' if env.position > 0 else 'Short'}

        state = next_state
        step += 1
        if step % 2000 == 0:
            eq  = equity_hist[-1]
            pct = (eq - INITIAL_CAP) / INITIAL_CAP * 100
            print(f"  Paso {step:,}/{total_steps:,} | {ts} | Equity: ${eq:,.0f} ({pct:+.1f}%) | {action_names[action]}")

    # ============================================================
    # PASO 5: CALCULAR METRICAS
    # ============================================================
    equity  = np.array(equity_hist)
    final   = env.equity_curve[-1]
    total_return = (final - INITIAL_CAP) / INITIAL_CAP * 100

    if len(equity) > 1:
        rets   = np.diff(equity) / np.maximum(equity[:-1], 1e-8)
        rets   = rets[np.isfinite(rets)]
        sharpe = (np.mean(rets) / np.std(rets) * np.sqrt(8760)) if np.std(rets) > 0 else 0.0
    else:
        sharpe = 0.0

    peak   = np.maximum.accumulate(equity)
    dd     = (peak - equity) / np.maximum(peak, 1e-8)
    max_dd = float(np.max(dd) * 100)
    calmar = total_return / max_dd if max_dd > 0 else 0.0

    wins     = [t for t in trades if t.get('pnl', 0) > 0]
    losses   = [t for t in trades if t.get('pnl', 0) <= 0]
    win_rate = len(wins) / len(trades) * 100 if trades else 0
    avg_win  = np.mean([t['pnl'] for t in wins])              if wins   else 0
    avg_loss = abs(np.mean([t['pnl'] for t in losses]))       if losses else 0
    profit_f = (sum(t['pnl'] for t in wins) / abs(sum(t['pnl'] for t in losses))
                if losses else 999.0)

    action_counts = {i: actions_taken.count(i) for i in range(5)}
    total_acts    = sum(action_counts.values()) or 1

    print(f"\n{'='*60}")
    print(f"RESULTADOS SOL 4 ANOS (1h — Binance)")
    print(f"{'='*60}")
    print(f"Retorno:       {total_return:+.2f}%")
    print(f"Capital Final: ${final:,.0f}")
    print(f"Sharpe:        {sharpe:.2f}")
    print(f"Max Drawdown:  -{max_dd:.2f}%")
    print(f"Calmar:        {calmar:.2f}")
    print(f"Win Rate:      {win_rate:.1f}%")
    print(f"Profit Factor: {profit_f:.2f}")
    print(f"Total Trades:  {len(trades):,}")
    print(f"{'='*60}")

    # ============================================================
    # PASO 6: GENERAR HTML
    # ============================================================
    ret_color = "#00ff88" if total_return >= 0 else "#ff4444"

    # Submuestrear para performance del HTML (1 punto cada 6 horas)
    step_plot = max(1, len(equity) // 2000)
    eq_plot   = equity[::step_plot].tolist()
    ts_plot   = timestamps[::step_plot]
    pr_plot   = prices_hist[::step_plot]

    equity_js = ",".join(f"{e:.2f}" for e in eq_plot)
    ts_js     = ",".join(f'"{t}"'   for t in ts_plot)
    price_js  = ",".join(f"{p:.2f}" for p in pr_plot)

    trade_rows = ""
    for t in trades[-80:]:
        pnl = t.get('pnl', 0)
        col = "#00ff88" if pnl > 0 else "#ff4444"
        trade_rows += f"""
        <tr>
          <td>{t.get('entry_time','')}</td><td>{t.get('exit_time','')}</td>
          <td>{t.get('direction','')}</td>
          <td>${t.get('entry_price',0):.4f}</td><td>${t.get('exit_price',0):.4f}</td>
          <td style="color:{col}">${pnl:,.2f}</td>
        </tr>"""

    act_rows = ""
    for i, name in action_names.items():
        cnt = action_counts.get(i, 0)
        act_rows += f"<tr><td>{name}</td><td>{cnt:,}</td><td>{cnt/total_acts*100:.1f}%</td></tr>"

    html = f"""<!DOCTYPE html>
    <html lang="es">
    <head>
    <meta charset="UTF-8">
    <title>TAMC — SOL 4 Anos (1h Binance)</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
      *{{margin:0;padding:0;box-sizing:border-box;}}
      body{{background:#0a0e1a;color:#e0e6f0;font-family:'Segoe UI',sans-serif;padding:20px;}}
      h1{{color:#7c83fd;text-align:center;font-size:2em;padding:20px 0 5px;}}
      .sub{{text-align:center;color:#8892b0;margin-bottom:30px;font-size:0.9em;}}
      .kpi-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(155px,1fr));gap:15px;margin-bottom:30px;}}
      .kpi{{background:linear-gradient(135deg,#13192d,#1a2235);border:1px solid #2a3050;border-radius:12px;padding:20px;text-align:center;}}
      .kpi .val{{font-size:1.8em;font-weight:700;margin-top:8px;}}
      .kpi .lbl{{color:#8892b0;font-size:0.75em;text-transform:uppercase;letter-spacing:1px;}}
      .card{{background:#13192d;border:1px solid #2a3050;border-radius:12px;padding:25px;margin-bottom:25px;}}
      .card h2{{color:#7c83fd;margin-bottom:15px;font-size:1em;text-transform:uppercase;letter-spacing:1px;}}
      canvas{{max-height:340px;}}
      table{{width:100%;border-collapse:collapse;font-size:0.85em;}}
      th{{background:#1a2235;color:#8892b0;padding:9px;text-align:left;border-bottom:1px solid #2a3050;}}
      td{{padding:8px 10px;border-bottom:1px solid #1a2235;}}
      tr:hover td{{background:#1a2235;}}
      .g{{color:#00ff88;}} .r{{color:#ff4444;}} .b{{color:#7c83fd;}}
      .badge{{display:inline-block;padding:3px 10px;border-radius:20px;font-size:0.75em;font-weight:600;}}
      .badge-g{{background:rgba(0,255,136,0.15);color:#00ff88;border:1px solid rgba(0,255,136,0.3);}}
      .badge-r{{background:rgba(255,68,68,0.15);color:#ff4444;border:1px solid rgba(255,68,68,0.3);}}
    </style>
    </head>
    <body>
    <h1>TAMC — SOL-USDT 4 Anos (1h)</h1>
    <p class="sub">
      Datos: Binance data.binance.vision | Periodo: {START_DATE} → {END_DATE} | 
      Intervalo: 1h | Modelo: {MODEL_PATH} | Capital: ${INITIAL_CAP:,.0f}
    </p>

    <div class="kpi-grid">
      <div class="kpi"><div class="lbl">Retorno Total</div><div class="val" style="color:{ret_color}">{total_return:+.2f}%</div></div>
      <div class="kpi"><div class="lbl">Capital Final</div><div class="val b">${final:,.0f}</div></div>
      <div class="kpi"><div class="lbl">Sharpe (anual)</div><div class="val {'g' if sharpe>1 else 'r'}">{sharpe:.2f}</div></div>
      <div class="kpi"><div class="lbl">Max Drawdown</div><div class="val r">-{max_dd:.2f}%</div></div>
      <div class="kpi"><div class="lbl">Calmar Ratio</div><div class="val b">{calmar:.2f}</div></div>
      <div class="kpi"><div class="lbl">Win Rate</div><div class="val b">{win_rate:.1f}%</div></div>
      <div class="kpi"><div class="lbl">Profit Factor</div><div class="val {'g' if profit_f>=1 else 'r'}">{profit_f:.2f}</div></div>
      <div class="kpi"><div class="lbl">Total Trades</div><div class="val b">{len(trades):,}</div></div>
    </div>

    <div class="card">
      <h2>Curva de Equity — 4 Anos horario</h2>
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
          <tr><td>Total Trades</td><td>{len(trades):,}</td></tr>
          <tr><td>Ganadores</td><td class="g">{len(wins):,}</td></tr>
          <tr><td>Perdedores</td><td class="r">{len(losses):,}</td></tr>
          <tr><td>Avg Win</td><td class="g">${avg_win:,.2f}</td></tr>
          <tr><td>Avg Loss</td><td class="r">-${avg_loss:,.2f}</td></tr>
          <tr><td>Ratio W/L</td><td>{(avg_win/avg_loss if avg_loss>0 else 0):.2f}x</td></tr>
        </table>
      </div>
    </div>

    <div class="card">
      <h2>Ultimos 80 Trades</h2>
      <div style="max-height:400px;overflow-y:auto;">
      <table><thead><tr><th>Entrada</th><th>Salida</th><th>Dir</th><th>P. Entrada</th><th>P. Salida</th><th>PnL</th></tr></thead>
      <tbody>{trade_rows}</tbody></table>
      </div>
    </div>

    <script>
    const labels = [{ts_js}];
    const equity = [{equity_js}];
    const prices = [{price_js}];
    const pctChg = equity.map(e => ((e - {INITIAL_CAP}) / {INITIAL_CAP} * 100).toFixed(2));
    const grid   = {{color:'rgba(42,48,80,0.6)'}};
    const tick   = {{color:'#8892b0',font:{{size:10}}}};

    new Chart(document.getElementById('equity_chart'), {{
      type:'line',
      data:{{labels, datasets:[{{
        label:'Equity ($)',data:equity,
        borderColor:'#7c83fd',backgroundColor:'rgba(124,131,253,0.08)',
        fill:true,pointRadius:0,tension:0.2,borderWidth:1.5
      }}]}},
      options:{{
        responsive:true,animation:false,
        plugins:{{legend:{{labels:{{color:'#8892b0'}}}}}},
        scales:{{
          x:{{ticks:{{...tick,maxTicksLimit:12}},grid}},
          y:{{ticks:tick,grid,callback:v=>'$'+v.toLocaleString()}}
        }}
      }}
    }});

    new Chart(document.getElementById('dual_chart'), {{
      type:'line',
      data:{{labels, datasets:[
        {{label:'Precio SOL (USDT)',data:prices,borderColor:'#f0b429',pointRadius:0,tension:0.2,yAxisID:'y',borderWidth:1.5}},
        {{label:'Equity (%)',data:pctChg,borderColor:'#00ff88',pointRadius:0,tension:0.2,yAxisID:'y1',borderWidth:1.5}}
      ]}},
      options:{{
        responsive:true,animation:false,
        plugins:{{legend:{{labels:{{color:'#8892b0'}}}}}},
        scales:{{
          x:{{ticks:{{...tick,maxTicksLimit:12}},grid}},
          y:{{ticks:{{color:'#f0b429',font:{{size:10}}}},grid,position:'left',callback:v=>'$'+v}},
          y1:{{ticks:{{color:'#00ff88',font:{{size:10}}}},position:'right',grid:{{drawOnChartArea:false}},callback:v=>v+'%'}}
        }}
      }}
    }});
    </script>
    </body>
    </html>"""

    with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"\nReporte guardado: {OUTPUT_HTML}")
    print("Backtest completado.")
