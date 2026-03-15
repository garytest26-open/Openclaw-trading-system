"""
╔══════════════════════════════════════════════════════════════╗
║  NEXUS OMEGA — Backtest Suite con Reporte HTML Interactivo  ║
╚══════════════════════════════════════════════════════════════╝

Ejecuta backtest de SOL-USD y BTC-USD (2 años, 1h) con la
estrategia NEXUS OMEGA y genera un reporte HTML con Plotly.

Uso:
    python backtest_nexus_omega.py
"""

import sys
import io
import os
import numpy as np
import pandas as pd
import yfinance as yf
import warnings
from datetime import datetime

warnings.filterwarnings('ignore')

# Fix Windows console encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from nexus_omega_strategy import NexusOmegaConfig, NexusOmega, MarketRegime


def download_data(ticker: str, period: str = "2y", interval: str = "1h") -> pd.DataFrame:
    """Descarga datos OHLCV de Yahoo Finance."""
    print(f"\n{'='*60}")
    print(f"  Descargando datos: {ticker} | {period} | {interval}")
    print(f"{'='*60}")
    df = yf.download(ticker, period=period, interval=interval, progress=False)
    if df.empty:
        raise ValueError(f"No se obtuvieron datos para {ticker}")
    # Limpiar columnas multi-index si existen
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.dropna(inplace=True)
    print(f"  → {len(df)} velas descargadas ({df.index[0]} a {df.index[-1]})")
    return df


def generate_html_report(results: dict, ticker: str, df: pd.DataFrame) -> str:
    """Genera reporte HTML interactivo con Plotly CDN."""
    metrics = results
    trades = results['trades']
    equity = results['equity_curve']
    regimes = results['regimes']

    # Preparar datos para gráficos
    eq_arr = np.array(equity)
    running_max = np.maximum.accumulate(eq_arr)
    drawdown = (eq_arr - running_max) / np.where(running_max > 0, running_max, 1) * 100

    # Timestamps para equity (uno más que velas)
    timestamps = [str(t) for t in df.index.tolist()]
    ts_equity = ['Start'] + timestamps

    # Trades para scatter
    entries_x, entries_y, entries_side = [], [], []
    exits_x, exits_y, exits_reason = [], [], []
    for t in trades:
        if 0 <= t['entry_idx'] < len(timestamps):
            entries_x.append(timestamps[t['entry_idx']])
            entries_y.append(t['entry_price'])
            entries_side.append(t['side'].upper())
        if 0 <= t['exit_idx'] < len(timestamps):
            exits_x.append(timestamps[t['exit_idx']])
            exits_y.append(t['exit_price'])
            exits_reason.append(t['exit_reason'])

    # Regímenes
    regime_names = {0: 'Bull', 1: 'Bear', 2: 'Range', 3: 'Volatile'}
    regime_colors = {0: '#00C853', 1: '#FF1744', 2: '#FFD600', 3: '#AA00FF'}
    regime_counts = {}
    for r in regimes:
        name = regime_names.get(int(r), 'Unknown')
        regime_counts[name] = regime_counts.get(name, 0) + 1

    # PnL por trade
    pnl_values = [t['pnl'] for t in trades]
    pnl_colors = ['#00C853' if p > 0 else '#FF1744' for p in pnl_values]
    trade_labels = [f"#{i+1} {t['side'].upper()}" for i, t in enumerate(trades)]

    # Distribución de salidas
    exit_reasons = {}
    for t in trades:
        r = t['exit_reason']
        exit_reasons[r] = exit_reasons.get(r, 0) + 1

    # Win rate por régimen
    regime_stats = {}
    for t in trades:
        rname = regime_names.get(t['regime'], 'Unknown')
        if rname not in regime_stats:
            regime_stats[rname] = {'wins': 0, 'total': 0}
        regime_stats[rname]['total'] += 1
        if t['pnl'] > 0:
            regime_stats[rname]['wins'] += 1

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NEXUS OMEGA — {ticker} Backtest Report</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', system-ui, sans-serif;
            background: #0a0a1a;
            color: #e0e0e0;
            padding: 20px;
        }}
        .header {{
            text-align: center;
            padding: 30px;
            background: linear-gradient(135deg, #1a1a3e, #0d0d2b);
            border-radius: 16px;
            margin-bottom: 24px;
            border: 1px solid #333;
        }}
        .header h1 {{
            font-size: 2.2em;
            background: linear-gradient(90deg, #00f5ff, #7c4dff, #ff4081);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 8px;
        }}
        .header .subtitle {{ color: #888; font-size: 1.1em; }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }}
        .metric-card {{
            background: linear-gradient(135deg, #1a1a3e, #12122d);
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            border: 1px solid #2a2a5a;
        }}
        .metric-card .label {{ color: #888; font-size: 0.85em; text-transform: uppercase; }}
        .metric-card .value {{
            font-size: 1.8em;
            font-weight: bold;
            margin-top: 8px;
        }}
        .positive {{ color: #00C853; }}
        .negative {{ color: #FF1744; }}
        .neutral {{ color: #FFD600; }}
        .chart-container {{
            background: #12122d;
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 24px;
            border: 1px solid #2a2a5a;
        }}
        .chart-title {{
            font-size: 1.2em;
            margin-bottom: 12px;
            color: #aaa;
        }}
        .two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }}
        .three-col {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 24px; }}
        .footer {{ text-align: center; padding: 20px; color: #555; font-size: 0.8em; }}
        @media (max-width: 900px) {{
            .two-col, .three-col {{ grid-template-columns: 1fr; }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>⚡ NEXUS OMEGA</h1>
        <div class="subtitle">Estrategia Revolucionaria de 7 Capas — {ticker} — Backtest Report</div>
        <div style="margin-top:8px;color:#666;">Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
    </div>

    <div class="metrics-grid">
        <div class="metric-card">
            <div class="label">Retorno Total</div>
            <div class="value {'positive' if metrics['total_return_pct'] > 0 else 'negative'}">
                {metrics['total_return_pct']:.2f}%
            </div>
        </div>
        <div class="metric-card">
            <div class="label">Buy & Hold</div>
            <div class="value {'positive' if metrics['buy_hold_return_pct'] > 0 else 'negative'}">
                {metrics['buy_hold_return_pct']:.2f}%
            </div>
        </div>
        <div class="metric-card">
            <div class="label">Sharpe Ratio</div>
            <div class="value {'positive' if metrics['sharpe_ratio'] > 1 else 'neutral'}">
                {metrics['sharpe_ratio']:.2f}
            </div>
        </div>
        <div class="metric-card">
            <div class="label">Sortino Ratio</div>
            <div class="value {'positive' if metrics['sortino_ratio'] > 1 else 'neutral'}">
                {metrics['sortino_ratio']:.2f}
            </div>
        </div>
        <div class="metric-card">
            <div class="label">Max Drawdown</div>
            <div class="value negative">{metrics['max_drawdown_pct']:.2f}%</div>
        </div>
        <div class="metric-card">
            <div class="label">Win Rate</div>
            <div class="value {'positive' if metrics['win_rate_pct'] > 50 else 'neutral'}">
                {metrics['win_rate_pct']:.1f}%
            </div>
        </div>
        <div class="metric-card">
            <div class="label">Total Trades</div>
            <div class="value neutral">{metrics['total_trades']}</div>
        </div>
        <div class="metric-card">
            <div class="label">Profit Factor</div>
            <div class="value {'positive' if metrics['profit_factor'] > 1.5 else 'neutral'}">
                {metrics['profit_factor']:.2f}
            </div>
        </div>
        <div class="metric-card">
            <div class="label">Capital Final</div>
            <div class="value {'positive' if metrics['final_capital'] > metrics['initial_capital'] else 'negative'}">
                ${metrics['final_capital']:,.2f}
            </div>
        </div>
    </div>

    <!-- Equity Curve -->
    <div class="chart-container">
        <div class="chart-title">📈 Curva de Equity</div>
        <div id="equityChart" style="height:400px;"></div>
    </div>

    <!-- Drawdown -->
    <div class="chart-container">
        <div class="chart-title">📉 Drawdown</div>
        <div id="ddChart" style="height:250px;"></div>
    </div>

    <div class="two-col">
        <!-- PnL por trade -->
        <div class="chart-container">
            <div class="chart-title">💰 PnL por Trade</div>
            <div id="pnlChart" style="height:350px;"></div>
        </div>
        <!-- Distribución salidas -->
        <div class="chart-container">
            <div class="chart-title">🎯 Distribución de Salidas</div>
            <div id="exitChart" style="height:350px;"></div>
        </div>
    </div>

    <div class="two-col">
        <!-- Régimen pie -->
        <div class="chart-container">
            <div class="chart-title">🧠 Distribución de Régimen</div>
            <div id="regimeChart" style="height:350px;"></div>
        </div>
        <!-- Win Rate por Régimen -->
        <div class="chart-container">
            <div class="chart-title">📊 Win Rate por Régimen</div>
            <div id="regimeWinChart" style="height:350px;"></div>
        </div>
    </div>

    <div class="footer">
        NEXUS OMEGA v1.0 — Estrategia de Trading Revolucionaria de 7 Capas<br>
        HMM Régimen · 8 Señales · Squeeze · Estructura · Meta-Learner · Riesgo Institucional · Anti-Drawdown
    </div>

    <script>
    const layout_base = {{
        paper_bgcolor: '#12122d',
        plot_bgcolor: '#12122d',
        font: {{ color: '#e0e0e0', family: 'Segoe UI' }},
        margin: {{ t: 30, b: 40, l: 60, r: 20 }},
        xaxis: {{ gridcolor: '#1e1e4a', showgrid: true }},
        yaxis: {{ gridcolor: '#1e1e4a', showgrid: true }},
    }};

    // Equity
    Plotly.newPlot('equityChart', [{{
        x: {ts_equity.__repr__()},
        y: {eq_arr.tolist()},
        type: 'scatter', mode: 'lines',
        line: {{ color: '#7c4dff', width: 2 }},
        fill: 'tozeroy',
        fillcolor: 'rgba(124,77,255,0.1)',
        name: 'Equity'
    }}], {{...layout_base, yaxis: {{...layout_base.yaxis, title: 'Capital ($)'}}}});

    // Drawdown
    Plotly.newPlot('ddChart', [{{
        x: {ts_equity.__repr__()},
        y: {drawdown.tolist()},
        type: 'scatter', mode: 'lines',
        line: {{ color: '#FF1744', width: 1.5 }},
        fill: 'tozeroy',
        fillcolor: 'rgba(255,23,68,0.15)',
        name: 'Drawdown %'
    }}], {{...layout_base, yaxis: {{...layout_base.yaxis, title: 'Drawdown (%)'}}}});

    // PnL
    Plotly.newPlot('pnlChart', [{{
        x: {trade_labels.__repr__()},
        y: {pnl_values},
        type: 'bar',
        marker: {{ color: {pnl_colors.__repr__()} }},
        name: 'PnL'
    }}], {{...layout_base, yaxis: {{...layout_base.yaxis, title: 'PnL ($)'}}}});

    // Exit Reasons
    Plotly.newPlot('exitChart', [{{
        labels: {list(exit_reasons.keys())},
        values: {list(exit_reasons.values())},
        type: 'pie',
        marker: {{ colors: ['#00C853', '#FF1744', '#FFD600', '#AA00FF', '#00B0FF'] }},
        textfont: {{ color: '#fff' }}
    }}], {{...layout_base}});

    // Régimen
    Plotly.newPlot('regimeChart', [{{
        labels: {list(regime_counts.keys())},
        values: {list(regime_counts.values())},
        type: 'pie',
        marker: {{ colors: ['#00C853', '#FF1744', '#FFD600', '#AA00FF'] }},
        textfont: {{ color: '#fff' }}
    }}], {{...layout_base}});

    // Win Rate por Régimen
    const regimeNames = {list(regime_stats.keys())};
    const winRates = {[round(v['wins']/v['total']*100, 1) if v['total'] > 0 else 0 for v in regime_stats.values()]};
    Plotly.newPlot('regimeWinChart', [{{
        x: regimeNames,
        y: winRates,
        type: 'bar',
        marker: {{ color: ['#00C853', '#FF1744', '#FFD600', '#AA00FF'].slice(0, regimeNames.length) }},
        name: 'Win Rate %'
    }}], {{...layout_base, yaxis: {{...layout_base.yaxis, title: 'Win Rate (%)'}}}});
    </script>
</body>
</html>"""
    return html


def run_single_backtest(ticker: str, period: str = "2y"):
    """Ejecuta backtest para un ticker y genera reporte."""
    config = NexusOmegaConfig(ticker=ticker, period=period)
    df = download_data(ticker, period, config.interval)
    engine = NexusOmega(config)
    results = engine.run_backtest(df)

    # Imprimir resumen
    print(f"\n{'='*60}")
    print(f"  RESULTADOS — NEXUS OMEGA — {ticker}")
    print(f"{'='*60}")
    print(f"  Capital Inicial:   ${results['initial_capital']:>12,.2f}")
    print(f"  Capital Final:     ${results['final_capital']:>12,.2f}")
    print(f"  Retorno Total:     {results['total_return_pct']:>11.2f}%")
    print(f"  Buy & Hold:        {results['buy_hold_return_pct']:>11.2f}%")
    print(f"  ──────────────────────────────────────")
    print(f"  Sharpe Ratio:      {results['sharpe_ratio']:>11.2f}")
    print(f"  Sortino Ratio:     {results['sortino_ratio']:>11.2f}")
    print(f"  Max Drawdown:      {results['max_drawdown_pct']:>11.2f}%")
    print(f"  ──────────────────────────────────────")
    print(f"  Total Trades:      {results['total_trades']:>11d}")
    print(f"  Win Rate:          {results['win_rate_pct']:>11.1f}%")
    print(f"  Avg Win:           {results['avg_win_pct']:>11.2f}%")
    print(f"  Avg Loss:          {results['avg_loss_pct']:>11.2f}%")
    print(f"  Profit Factor:     {results['profit_factor']:>11.2f}")
    print(f"{'='*60}")

    # Generar HTML
    safe_ticker = ticker.replace('-', '_').lower()
    html_filename = f"nexus_omega_{safe_ticker}_{period}.html"
    html_content = generate_html_report(results, ticker, df)

    filepath = os.path.join(os.path.dirname(__file__), html_filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"\n  ✅ Reporte HTML guardado: {html_filename}")

    return results


def main():
    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║           NEXUS OMEGA — Backtest Suite v1.0                 ║")
    print("║     Estrategia Revolucionaria de Trading — 7 Capas          ║")
    print("╚══════════════════════════════════════════════════════════════╝")

    tickers = ["SOL-USD", "BTC-USD"]
    all_results = {}

    for ticker in tickers:
        try:
            results = run_single_backtest(ticker)
            all_results[ticker] = results
        except Exception as e:
            print(f"\n  ❌ Error en {ticker}: {e}")
            import traceback
            traceback.print_exc()

    # Comparativa
    if len(all_results) > 1:
        print("\n")
        print("╔══════════════════════════════════════════════════════════════╗")
        print("║                COMPARATIVA NEXUS OMEGA                      ║")
        print("╠══════════════════════════════════════════════════════════════╣")
        header = f"  {'Métrica':<22} |"
        for t in all_results:
            header += f" {t:>12} |"
        print(header)
        print(f"  {'─'*22}─┼" + "─" * 14 + "┼" * (len(all_results) - 1) + "─" * 14 + "┤")

        rows = [
            ('Retorno %', 'total_return_pct', '.2f'),
            ('Buy & Hold %', 'buy_hold_return_pct', '.2f'),
            ('Sharpe', 'sharpe_ratio', '.2f'),
            ('Sortino', 'sortino_ratio', '.2f'),
            ('Max DD %', 'max_drawdown_pct', '.2f'),
            ('Trades', 'total_trades', 'd'),
            ('Win Rate %', 'win_rate_pct', '.1f'),
            ('Profit Factor', 'profit_factor', '.2f'),
        ]
        for label, key, fmt in rows:
            line = f"  {label:<22} |"
            for t in all_results:
                val = all_results[t][key]
                line += f" {val:>12{fmt}} |"
            print(line)
        print("╚══════════════════════════════════════════════════════════════╝")


if __name__ == "__main__":
    main()
