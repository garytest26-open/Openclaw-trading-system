# ============================================================
# BACKTEST: Estrategia TAMC (Deep RL) - 6 Meses
# Carga el modelo entrenado y simula trading sobre datos históricos
# ============================================================

import numpy as np
import pandas as pd
import yfinance as yf
import torch
import os
import sys
import warnings
from datetime import datetime, timedelta
import json

warnings.filterwarnings('ignore')

# Fix Windows console encoding for emojis
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Importar componentes del módulo principal
from tamc_strategy import (
    StrategyConfig, DuelingDQN, TradingEnvironment,
    calculate_indicators, device
)

# ============================================================
# CONFIGURACIÓN DEL BACKTEST
# ============================================================

BACKTEST_MONTHS = 6
MODEL_PATH = "models/tamc_btc_best.pth"
INITIAL_CAPITAL = 10000.0
TICKER = "BTC-USD"
INTERVAL = "1h"

# ============================================================
# FUNCIONES DE BACKTEST
# ============================================================

def load_backtest_data(ticker: str, months: int, interval: str) -> pd.DataFrame:
    """Descarga datos de los últimos N meses para backtest"""
    end_date = datetime.now()
    # yfinance limita 1h a ~730 días, 6 meses = ~180 días, ok
    start_date = end_date - timedelta(days=months * 30)
    
    print(f"📥 Descargando datos {ticker} | {start_date.strftime('%Y-%m-%d')} → {end_date.strftime('%Y-%m-%d')} | {interval}")
    
    df = yf.download(ticker, start=start_date, end=end_date, interval=interval, progress=False, auto_adjust=True)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)
    
    df = df[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()
    
    config = StrategyConfig()
    df = calculate_indicators(df, config)
    
    print(f"✅ Datos cargados: {len(df)} velas ({df.index[0]} → {df.index[-1]})")
    return df


def load_model(model_path: str, config: StrategyConfig) -> torch.nn.Module:
    """Carga el modelo entrenado"""
    state_dim = config.n_features + 7
    action_dim = 5
    
    model = DuelingDQN(state_dim, action_dim, config.hidden_dim).to(device)
    model.load_state_dict(torch.load(model_path, map_location=device, weights_only=True))
    model.eval()
    print(f"🧠 Modelo cargado desde: {model_path}")
    return model


def run_backtest(model, df: pd.DataFrame, config: StrategyConfig) -> dict:
    """Ejecuta el backtest completo"""
    env = TradingEnvironment(df, config)
    state = env.reset()
    
    # Tracking
    actions_taken = []
    trades = []
    equity_history = []
    positions_history = []
    timestamps = []
    prices = []
    
    action_names = {0: "Flat", 1: "Long 50%", 2: "Long 100%", 3: "Short 50%", 4: "Short 100%"}
    
    current_trade = None
    done = False
    step_count = 0
    
    print(f"\n🚀 Ejecutando backtest sobre {len(df) - config.lookback_window} pasos...")
    
    while not done:
        # Seleccionar acción (Greedy - sin exploración)
        with torch.no_grad():
            state_t = torch.FloatTensor(state).unsqueeze(0).to(device)
            q_values = model(state_t)
            action = q_values.argmax().item()
        
        prev_position = env.position
        prev_balance = env.balance
        
        next_state, reward, done, info = env.step(action)
        
        current_price = df.iloc[env.current_step - 1]['Close']
        current_idx = df.index[env.current_step - 1] if env.current_step - 1 < len(df) else df.index[-1]
        
        actions_taken.append(action)
        equity_history.append(env.equity_curve[-1])
        positions_history.append(env.position)
        timestamps.append(str(current_idx))
        prices.append(float(current_price))
        
        # Detectar trades
        if prev_position == 0 and env.position != 0:
            # Apertura
            current_trade = {
                'entry_time': str(current_idx),
                'entry_price': float(current_price),
                'direction': 'Long' if env.position > 0 else 'Short',
                'size': abs(env.position)
            }
        elif prev_position != 0 and env.position == 0:
            # Cierre
            if current_trade:
                current_trade['exit_time'] = str(current_idx)
                current_trade['exit_price'] = float(current_price)
                pnl = env.balance - prev_balance
                current_trade['pnl'] = float(pnl)
                current_trade['pnl_pct'] = float(pnl / config.initial_capital * 100)
                trades.append(current_trade)
                current_trade = None
        elif prev_position != 0 and env.position != 0 and np.sign(prev_position) != np.sign(env.position):
            # Cambio de dirección
            if current_trade:
                current_trade['exit_time'] = str(current_idx)
                current_trade['exit_price'] = float(current_price)
                pnl = env.balance - prev_balance
                current_trade['pnl'] = float(pnl)
                current_trade['pnl_pct'] = float(pnl / config.initial_capital * 100)
                trades.append(current_trade)
            current_trade = {
                'entry_time': str(current_idx),
                'entry_price': float(current_price),
                'direction': 'Long' if env.position > 0 else 'Short',
                'size': abs(env.position)
            }
        
        state = next_state
        step_count += 1
        
        if step_count % 500 == 0:
            eq = env.equity_curve[-1]
            pct = (eq - config.initial_capital) / config.initial_capital * 100
            print(f"  Step {step_count}/{len(df)} | Equity: ${eq:.0f} ({pct:+.1f}%) | Action: {action_names[action]}")
    
    # Cerrar trade abierto al final
    if current_trade:
        last_price = float(df.iloc[-1]['Close'])
        current_trade['exit_time'] = str(df.index[-1])
        current_trade['exit_price'] = last_price
        pnl_final = env.balance - prev_balance if env.position == 0 else 0
        current_trade['pnl'] = float(pnl_final)
        current_trade['pnl_pct'] = float(pnl_final / config.initial_capital * 100)
        trades.append(current_trade)
    
    return {
        'equity_history': equity_history,
        'actions_taken': actions_taken,
        'trades': trades,
        'timestamps': timestamps,
        'prices': prices,
        'positions_history': positions_history,
        'final_equity': env.equity_curve[-1],
        'initial_capital': config.initial_capital
    }


def calculate_metrics(results: dict) -> dict:
    """Calcula métricas de rendimiento del backtest"""
    equity = np.array(results['equity_history'])
    initial = results['initial_capital']
    final = results['final_equity']
    trades = results['trades']
    
    # Return
    total_return = (final - initial) / initial * 100
    
    # Sharpe Ratio (anualizado, asumiendo 1h bars)
    if len(equity) > 1:
        returns = np.diff(equity) / equity[:-1]
        returns = returns[np.isfinite(returns)]
        if len(returns) > 0 and np.std(returns) > 0:
            hourly_sharpe = np.mean(returns) / np.std(returns)
            sharpe_ratio = hourly_sharpe * np.sqrt(24 * 365)  # Anualizar
        else:
            sharpe_ratio = 0.0
    else:
        sharpe_ratio = 0.0
    
    # Max Drawdown
    peak = np.maximum.accumulate(equity)
    drawdown = (peak - equity) / peak
    max_drawdown = np.max(drawdown) * 100
    
    # Win Rate
    if trades:
        winning_trades = [t for t in trades if t['pnl'] > 0]
        losing_trades = [t for t in trades if t['pnl'] <= 0]
        win_rate = len(winning_trades) / len(trades) * 100
        
        avg_win = np.mean([t['pnl'] for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([abs(t['pnl']) for t in losing_trades]) if losing_trades else 0
        profit_factor = (sum(t['pnl'] for t in winning_trades) / abs(sum(t['pnl'] for t in losing_trades))) if losing_trades and sum(t['pnl'] for t in losing_trades) != 0 else float('inf')
        
        total_pnl_trades = sum(t['pnl'] for t in trades)
    else:
        win_rate = 0
        avg_win = 0
        avg_loss = 0
        profit_factor = 0
        total_pnl_trades = 0
    
    # Action distribution
    actions = results['actions_taken']
    action_names = {0: "Flat", 1: "Long 50%", 2: "Long 100%", 3: "Short 50%", 4: "Short 100%"}
    action_dist = {}
    for a in range(5):
        count = actions.count(a)
        action_dist[action_names[a]] = f"{count} ({count/len(actions)*100:.1f}%)"
    
    # Calmar Ratio
    if max_drawdown > 0:
        # Anualizar return: total_return es sobre 6 meses
        annualized_return = total_return * 2  # Aproximación
        calmar_ratio = annualized_return / max_drawdown
    else:
        calmar_ratio = float('inf')
    
    metrics = {
        'Capital Inicial': f"${initial:,.0f}",
        'Capital Final': f"${final:,.0f}",
        'Retorno Total': f"{total_return:+.2f}%",
        'Retorno Anualizado (est.)': f"{total_return * 2:+.2f}%",
        'Sharpe Ratio (anual)': f"{sharpe_ratio:.2f}",
        'Max Drawdown': f"{max_drawdown:.2f}%",
        'Calmar Ratio': f"{calmar_ratio:.2f}",
        'Total Trades': len(trades),
        'Win Rate': f"{win_rate:.1f}%",
        'Avg Win': f"${avg_win:,.2f}",
        'Avg Loss': f"${avg_loss:,.2f}",
        'Profit Factor': f"{profit_factor:.2f}" if profit_factor != float('inf') else "∞",
        'PnL Total Trades': f"${total_pnl_trades:,.2f}",
        'Distribución Acciones': action_dist
    }
    
    return metrics


def generate_html_report(results: dict, metrics: dict, output_path: str):
    """Genera un reporte HTML interactivo con gráficos"""
    equity = results['equity_history']
    timestamps = results['timestamps']
    prices = results['prices']
    trades = results['trades']
    initial = results['initial_capital']
    
    # Reducir datos para el gráfico (cada 4 horas)
    step = max(1, len(timestamps) // 1000)
    t_sampled = timestamps[::step]
    e_sampled = equity[::step]
    p_sampled = prices[::step]
    
    # Drawdown
    eq_arr = np.array(equity)
    peak = np.maximum.accumulate(eq_arr)
    dd = ((peak - eq_arr) / peak * 100)
    dd_sampled = dd[::step].tolist()
    
    # Trades PnL
    trades_pnl = [t['pnl'] for t in trades]
    trades_labels = [f"T{i+1}" for i in range(len(trades))]
    trades_colors = ['#00e676' if p > 0 else '#ff5252' for p in trades_pnl]
    
    # Métricas para card
    metrics_html = ""
    for key, val in metrics.items():
        if key == 'Distribución Acciones':
            continue
        color = ''
        if 'Retorno' in key and isinstance(val, str) and '+' in val:
            color = 'color: #00e676;'
        elif 'Retorno' in key and isinstance(val, str) and '-' in val:
            color = 'color: #ff5252;'
        metrics_html += f'<div class="metric"><span class="metric-label">{key}</span><span class="metric-value" style="{color}">{val}</span></div>\n'
    
    # Action distribution
    action_dist = metrics.get('Distribución Acciones', {})
    action_html = ""
    for act, count_str in action_dist.items():
        action_html += f'<div class="metric"><span class="metric-label">{act}</span><span class="metric-value">{count_str}</span></div>\n'

    # Build trade rows outside f-string to avoid nested syntax issues
    trades_rows = ""
    for i, t in enumerate(trades):
        css_class = "positive" if t['pnl'] > 0 else "negative"
        entry_p = f"${t['entry_price']:,.0f}"
        exit_p = f"${t.get('exit_price', 0):,.0f}"
        pnl_str = f"${t['pnl']:+,.2f}"
        exit_time = t.get('exit_time', '?')[:16]
        trades_rows += f'<tr><td>{i+1}</td><td>{t["direction"]}</td><td>{t["entry_time"][:16]}</td><td>{exit_time}</td><td>{entry_p}</td><td>{exit_p}</td><td class="{css_class}">{pnl_str}</td></tr>\n'

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TAMC Backtest - BTC-USD 6 Meses</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ background: #0a0e17; color: #e0e6ed; font-family: 'Segoe UI', sans-serif; padding: 20px; }}
    .header {{ text-align: center; margin-bottom: 30px; }}
    .header h1 {{ font-size: 2em; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
    .header p {{ color: #8892a4; margin-top: 5px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 30px; }}
    .card {{ background: #131923; border-radius: 12px; padding: 20px; border: 1px solid #1e2a3a; }}
    .card h3 {{ color: #667eea; margin-bottom: 15px; font-size: 1.1em; }}
    .metric {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #1a2332; }}
    .metric:last-child {{ border-bottom: none; }}
    .metric-label {{ color: #8892a4; }}
    .metric-value {{ font-weight: 600; color: #e0e6ed; }}
    .chart-container {{ background: #131923; border-radius: 12px; padding: 20px; border: 1px solid #1e2a3a; margin-bottom: 20px; }}
    .chart-container h3 {{ color: #667eea; margin-bottom: 15px; }}
    canvas {{ width: 100% !important; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #1a2332; font-size: 0.9em; }}
    th {{ color: #667eea; background: #0d1320; }}
    .positive {{ color: #00e676; }}
    .negative {{ color: #ff5252; }}
    .trades-scroll {{ max-height: 400px; overflow-y: auto; }}
</style>
</head>
<body>
<div class="header">
    <h1>🤖 TAMC Strategy Backtest</h1>
    <p>BTC-USD | 6 Meses | Deep RL (DDQN + PER) | {timestamps[0][:10]} → {timestamps[-1][:10]}</p>
</div>

<div class="grid">
    <div class="card">
        <h3>📊 Métricas de Rendimiento</h3>
        {metrics_html}
    </div>
    <div class="card">
        <h3>🎯 Distribución de Acciones</h3>
        {action_html}
    </div>
</div>

<div class="chart-container">
    <h3>💰 Curva de Equity vs Precio BTC</h3>
    <canvas id="equityChart" height="100"></canvas>
</div>

<div class="chart-container">
    <h3>📉 Drawdown</h3>
    <canvas id="ddChart" height="60"></canvas>
</div>

<div class="chart-container">
    <h3>📈 PnL por Trade</h3>
    <canvas id="tradesChart" height="80"></canvas>
</div>

<div class="card">
    <h3>📋 Historial de Trades ({len(trades)} operaciones)</h3>
    <div class="trades-scroll">
    <table>
        <tr><th>#</th><th>Dir</th><th>Entrada</th><th>Salida</th><th>P. Entrada</th><th>P. Salida</th><th>PnL ($)</th></tr>
        {trades_rows}
    </table>
    </div>
</div>

<script>
const labels = {json.dumps(t_sampled[:])};
const equityData = {json.dumps([round(e, 2) for e in e_sampled])};
const priceData = {json.dumps([round(p, 2) for p in p_sampled])};
const ddData = {json.dumps([round(d, 2) for d in dd_sampled])};
const tradesPnl = {json.dumps([round(p, 2) for p in trades_pnl])};
const tradesLabels = {json.dumps(trades_labels)};
const tradesColors = {json.dumps(trades_colors)};

// Equity Chart
new Chart(document.getElementById('equityChart'), {{
    type: 'line',
    data: {{
        labels: labels.map(l => l.substring(5, 16)),
        datasets: [{{
            label: 'Equity ($)',
            data: equityData,
            borderColor: '#667eea',
            backgroundColor: 'rgba(102,126,234,0.1)',
            fill: true,
            tension: 0.3,
            pointRadius: 0,
            yAxisID: 'y'
        }}, {{
            label: 'BTC Precio ($)',
            data: priceData,
            borderColor: '#f7931a',
            backgroundColor: 'transparent',
            tension: 0.3,
            pointRadius: 0,
            yAxisID: 'y1'
        }}]
    }},
    options: {{
        responsive: true,
        interaction: {{ intersect: false, mode: 'index' }},
        scales: {{
            x: {{ display: true, ticks: {{ maxTicksLimit: 15, color: '#8892a4' }}, grid: {{ color: '#1a2332' }} }},
            y: {{ position: 'left', ticks: {{ color: '#667eea' }}, grid: {{ color: '#1a2332' }}, title: {{ display: true, text: 'Equity ($)', color: '#667eea' }} }},
            y1: {{ position: 'right', ticks: {{ color: '#f7931a' }}, grid: {{ display: false }}, title: {{ display: true, text: 'BTC ($)', color: '#f7931a' }} }}
        }},
        plugins: {{ legend: {{ labels: {{ color: '#e0e6ed' }} }} }}
    }}
}});

// Drawdown Chart
new Chart(document.getElementById('ddChart'), {{
    type: 'line',
    data: {{
        labels: labels.map(l => l.substring(5, 16)),
        datasets: [{{
            label: 'Drawdown (%)',
            data: ddData.map(d => -d),
            borderColor: '#ff5252',
            backgroundColor: 'rgba(255,82,82,0.15)',
            fill: true,
            tension: 0.3,
            pointRadius: 0
        }}]
    }},
    options: {{
        responsive: true,
        scales: {{
            x: {{ ticks: {{ maxTicksLimit: 15, color: '#8892a4' }}, grid: {{ color: '#1a2332' }} }},
            y: {{ ticks: {{ color: '#ff5252' }}, grid: {{ color: '#1a2332' }} }}
        }},
        plugins: {{ legend: {{ labels: {{ color: '#e0e6ed' }} }} }}
    }}
}});

// Trades PnL Chart
new Chart(document.getElementById('tradesChart'), {{
    type: 'bar',
    data: {{
        labels: tradesLabels,
        datasets: [{{
            label: 'PnL ($)',
            data: tradesPnl,
            backgroundColor: tradesColors,
            borderRadius: 4
        }}]
    }},
    options: {{
        responsive: true,
        scales: {{
            x: {{ ticks: {{ color: '#8892a4', maxTicksLimit: 30 }}, grid: {{ color: '#1a2332' }} }},
            y: {{ ticks: {{ color: '#e0e6ed' }}, grid: {{ color: '#1a2332' }} }}
        }},
        plugins: {{ legend: {{ labels: {{ color: '#e0e6ed' }} }} }}
    }}
}});
</script>
</body>
</html>"""
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"\n📄 Reporte HTML guardado en: {output_path}")


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 60)
    print("🤖 TAMC STRATEGY BACKTEST - BTC-USD 6 MESES")
    print("=" * 60)
    
    # Verificar modelo
    if not os.path.exists(MODEL_PATH):
        print(f"❌ Error: No se encontró el modelo en {MODEL_PATH}")
        print("   Ejecuta primero: python run_tamc.py --episodes 50")
        sys.exit(1)
    
    # Configurar
    config = StrategyConfig()
    config.n_features = 5
    config.initial_capital = INITIAL_CAPITAL
    
    # 1. Cargar datos
    df = load_backtest_data(TICKER, BACKTEST_MONTHS, INTERVAL)
    if df.empty:
        print("❌ No se pudieron cargar los datos.")
        sys.exit(1)
    
    # 2. Cargar modelo
    model = load_model(MODEL_PATH, config)
    
    # 3. Ejecutar backtest
    results = run_backtest(model, df, config)
    
    # 4. Calcular métricas
    metrics = calculate_metrics(results)
    
    # 5. Imprimir resultados
    print("\n" + "=" * 60)
    print("📊 RESULTADOS DEL BACKTEST")
    print("=" * 60)
    for key, val in metrics.items():
        if key == 'Distribución Acciones':
            print(f"\n🎯 {key}:")
            for act, count in val.items():
                print(f"   {act}: {count}")
        else:
            print(f"  {key}: {val}")
    print("=" * 60)
    
    # 6. Generar reporte HTML
    output_html = "tamc_backtest_6m.html"
    generate_html_report(results, metrics, output_html)
    
    print("\n✅ Backtest completado.")


if __name__ == "__main__":
    main()
