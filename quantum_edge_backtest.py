"""
╔══════════════════════════════════════════════════════════════╗
║          QUANTUM EDGE - Motor de Backtest                   ║
║          Reporte HTML Interactivo con Plotly                 ║
╚══════════════════════════════════════════════════════════════╝

Uso:
    python quantum_edge_backtest.py --ticker SOL-USD --period 2y
    python quantum_edge_backtest.py --ticker BTC-USD --period 2y
"""

import argparse
import sys
import io
import numpy as np
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Fix Windows encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from quantum_edge_strategy import QuantumEdge, QuantumConfig, MarketRegime


def download_data(ticker: str, period: str, interval: str = "1h") -> pd.DataFrame:
    """Descarga datos OHLCV de Yahoo Finance."""
    print(f"  Descargando {period} de datos {interval} para {ticker}...")

    # yfinance limita 1h a 730 días máx
    if period == "2y":
        download_period = "730d"
    elif period == "1y":
        download_period = "365d"
    else:
        download_period = period

    df = yf.download(ticker, period=download_period, interval=interval, progress=False)

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel('Ticker')

    df.dropna(inplace=True)
    print(f"  Datos descargados: {len(df)} velas ({df.index[0].strftime('%Y-%m-%d')} → {df.index[-1].strftime('%Y-%m-%d')})")
    return df


def generate_html_report(df: pd.DataFrame, metrics: dict, ticker: str,
                         output_file: str):
    """Genera un reporte HTML interactivo completo con Plotly."""

    equity_curve = metrics['equity_curve']
    trades = metrics['trades']
    regimes = metrics['regimes']

    # Ajustar longitud de equity_curve vs index
    warmup = max(500, 168 + 50)  # Mismo warmup del backtest
    eq_len = len(equity_curve)
    df_len = len(df)

    # Crear timestamps para equity (offset por append extra)
    if eq_len == df_len + 1:
        eq_timestamps = list(df.index) + [df.index[-1]]
    elif eq_len <= df_len:
        eq_timestamps = list(df.index[:eq_len])
    else:
        eq_timestamps = list(df.index) + [df.index[-1]] * (eq_len - df_len)

    # --- Crear figura con 4 subplots ---
    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        subplot_titles=(
            'Curva de Equity ($)',
            f'Precio {ticker} + Trades',
            'Régimen de Mercado (HMM)',
            'Drawdown (%)'
        ),
        row_heights=[0.35, 0.30, 0.15, 0.20]
    )

    # ═══════════════════════════
    # ROW 1: Curva de Equity
    # ═══════════════════════════
    eq_array = np.array(equity_curve)
    fig.add_trace(go.Scatter(
        x=eq_timestamps,
        y=eq_array,
        mode='lines',
        name='Quantum Edge Equity',
        line=dict(color='#00ff88', width=2),
        fill='tozeroy',
        fillcolor='rgba(0, 255, 136, 0.1)'
    ), row=1, col=1)

    # Línea base del capital inicial
    fig.add_hline(y=metrics['initial_capital'], line_dash="dash",
                  line_color="rgba(255,255,255,0.3)", row=1, col=1)

    # Buy & Hold para comparación
    bnh_start_price = df['Close'].iloc[warmup]
    bnh_equity = [metrics['initial_capital']]
    for i in range(warmup + 1, len(df)):
        bnh_val = metrics['initial_capital'] * (df['Close'].iloc[i] / bnh_start_price)
        bnh_equity.append(bnh_val)

    bnh_timestamps = list(df.index[warmup:warmup + len(bnh_equity)])
    if len(bnh_timestamps) < len(bnh_equity):
        bnh_equity = bnh_equity[:len(bnh_timestamps)]

    fig.add_trace(go.Scatter(
        x=bnh_timestamps,
        y=bnh_equity,
        mode='lines',
        name='Buy & Hold',
        line=dict(color='rgba(255, 165, 0, 0.6)', width=1, dash='dot')
    ), row=1, col=1)

    # ═══════════════════════════
    # ROW 2: Precio + Trades
    # ═══════════════════════════
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        name='Precio',
        increasing_line_color='#26a69a',
        decreasing_line_color='#ef5350',
        showlegend=False
    ), row=2, col=1)

    # Marcar trades en el gráfico
    for trade in trades:
        entry_time = df.index[trade['entry_idx']] if trade['entry_idx'] < len(df) else df.index[-1]
        exit_time = df.index[trade['exit_idx']] if trade['exit_idx'] < len(df) else df.index[-1]

        # Entrada
        entry_color = '#00ff88' if trade['side'] == 'long' else '#ff4444'
        entry_symbol = 'triangle-up' if trade['side'] == 'long' else 'triangle-down'

        fig.add_trace(go.Scatter(
            x=[entry_time],
            y=[trade['entry_price']],
            mode='markers',
            marker=dict(color=entry_color, size=8, symbol=entry_symbol,
                       line=dict(width=1, color='white')),
            name=f"{'Long' if trade['side'] == 'long' else 'Short'} Entry",
            showlegend=False,
            hovertext=f"{trade['side'].upper()} Entry @ ${trade['entry_price']:.2f}"
        ), row=2, col=1)

        # Salida
        exit_color = '#00ff88' if trade['pnl'] > 0 else '#ff4444'
        fig.add_trace(go.Scatter(
            x=[exit_time],
            y=[trade['exit_price']],
            mode='markers',
            marker=dict(color=exit_color, size=8, symbol='x',
                       line=dict(width=1, color='white')),
            name=f"Exit ({trade['exit_reason']})",
            showlegend=False,
            hovertext=f"Exit @ ${trade['exit_price']:.2f} | PnL: {trade['pnl_pct']:+.2f}%"
        ), row=2, col=1)

    # ═══════════════════════════
    # ROW 3: Régimen de Mercado
    # ═══════════════════════════
    regime_colors = {
        MarketRegime.BULL_TREND: '#00ff88',
        MarketRegime.BEAR_TREND: '#ff4444',
        MarketRegime.MEAN_REVERSION: '#ffaa00',
        MarketRegime.HIGH_VOLATILITY: '#ff00ff',
    }
    regime_names = {
        MarketRegime.BULL_TREND: 'Tendencia Alcista',
        MarketRegime.BEAR_TREND: 'Tendencia Bajista',
        MarketRegime.MEAN_REVERSION: 'Lateral/Choppy',
        MarketRegime.HIGH_VOLATILITY: 'Alta Volatilidad',
    }

    for regime_val in MarketRegime:
        mask = regimes == regime_val
        regime_y = np.where(mask, regime_val + 1, np.nan)
        fig.add_trace(go.Scatter(
            x=df.index,
            y=regime_y,
            mode='markers',
            marker=dict(color=regime_colors[regime_val], size=3),
            name=regime_names[regime_val],
        ), row=3, col=1)

    # ═══════════════════════════
    # ROW 4: Drawdown
    # ═══════════════════════════
    running_max = np.maximum.accumulate(eq_array)
    drawdown_pct = (eq_array - running_max) / running_max * 100

    fig.add_trace(go.Scatter(
        x=eq_timestamps,
        y=drawdown_pct,
        mode='lines',
        name='Drawdown',
        line=dict(color='#ff4444', width=1),
        fill='tozeroy',
        fillcolor='rgba(255, 68, 68, 0.2)'
    ), row=4, col=1)

    # ═══════════════════════════
    # LAYOUT Y ANOTACIONES
    # ═══════════════════════════

    # Calcular stats de régimen
    regime_stats_text = ""
    total_regime = len(regimes[regimes != MarketRegime.MEAN_REVERSION]) + len(regimes[regimes == MarketRegime.MEAN_REVERSION])
    for r in MarketRegime:
        count = np.sum(regimes[warmup:] == r)
        pct = count / max(1, len(regimes) - warmup) * 100
        regime_stats_text += f"{regime_names[r]}: {pct:.1f}% | "

    # Resumen de métricas como anotación
    win_trades = len([t for t in trades if t['pnl'] > 0])
    lose_trades = len([t for t in trades if t['pnl'] <= 0])

    title_text = (
        f"<b>QUANTUM EDGE — {ticker}</b><br>"
        f"<span style='font-size:12px'>"
        f"Retorno: <b>{metrics['total_return_pct']:+.2f}%</b> | "
        f"B&H: {metrics['buy_hold_return_pct']:+.2f}% | "
        f"Sharpe: {metrics['sharpe_ratio']:.2f} | "
        f"Sortino: {metrics['sortino_ratio']:.2f} | "
        f"Max DD: {metrics['max_drawdown_pct']:.2f}% | "
        f"Trades: {metrics['total_trades']} ({win_trades}W/{lose_trades}L) | "
        f"Win Rate: {metrics['win_rate_pct']:.1f}% | "
        f"PF: {metrics['profit_factor']:.2f}"
        f"</span>"
    )

    fig.update_layout(
        title=dict(text=title_text, x=0.5, xanchor='center'),
        template='plotly_dark',
        height=1200,
        hovermode='x unified',
        xaxis_rangeslider_visible=False,
        xaxis2_rangeslider_visible=False,
        xaxis3_rangeslider_visible=False,
        xaxis4_rangeslider_visible=False,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.08,
            xanchor="center",
            x=0.5
        ),
        font=dict(family="Roboto Mono, monospace"),
        paper_bgcolor='#0a0a0a',
        plot_bgcolor='#111111',
    )

    fig.update_yaxes(title_text="Capital ($)", row=1, col=1, gridcolor='rgba(255,255,255,0.05)')
    fig.update_yaxes(title_text="Precio ($)", row=2, col=1, gridcolor='rgba(255,255,255,0.05)')
    fig.update_yaxes(title_text="Régimen", row=3, col=1, gridcolor='rgba(255,255,255,0.05)',
                     tickvals=[1, 2, 3, 4],
                     ticktext=['Bull', 'Bear', 'Lateral', 'HighVol'])
    fig.update_yaxes(title_text="DD %", row=4, col=1, gridcolor='rgba(255,255,255,0.05)')

    # Agregar tabla de resumen como anotación
    summary_table = (
        f"<br><b>═══ RESUMEN DETALLADO ═══</b><br>"
        f"Capital Inicial: ${metrics['initial_capital']:,.2f}<br>"
        f"Capital Final: ${metrics['final_capital']:,.2f}<br>"
        f"Ganancia/Pérdida Avg: +{metrics['avg_win_pct']:.2f}% / {metrics['avg_loss_pct']:.2f}%<br>"
        f"{regime_stats_text}<br>"
    )

    fig.add_annotation(
        text=summary_table,
        xref="paper", yref="paper",
        x=0.01, y=0.98,
        showarrow=False,
        font=dict(size=10, color='#aaaaaa'),
        align="left",
        bordercolor='#333333',
        borderwidth=1,
        borderpad=8,
        bgcolor='rgba(0,0,0,0.7)',
        row=1, col=1
    )

    fig.write_html(output_file)
    print(f"  Reporte HTML guardado: {output_file}")


def print_results(metrics: dict, ticker: str):
    """Imprime resultados en consola."""
    trades = metrics['trades']
    win_trades = [t for t in trades if t['pnl'] > 0]
    lose_trades = [t for t in trades if t['pnl'] <= 0]

    print()
    print("=" * 60)
    print(f"  QUANTUM EDGE — RESULTADOS DEL BACKTEST — {ticker}")
    print("=" * 60)
    print(f"  Capital Inicial:       ${metrics['initial_capital']:>12,.2f}")
    print(f"  Capital Final:         ${metrics['final_capital']:>12,.2f}")
    print(f"  Retorno Neto:          {metrics['total_return_pct']:>+12.2f}%")
    print(f"  Buy & Hold:            {metrics['buy_hold_return_pct']:>+12.2f}%")
    print("-" * 60)
    print(f"  Sharpe Ratio:          {metrics['sharpe_ratio']:>12.2f}")
    print(f"  Sortino Ratio:         {metrics['sortino_ratio']:>12.2f}")
    print(f"  Max Drawdown:          {metrics['max_drawdown_pct']:>12.2f}%")
    print(f"  Profit Factor:         {metrics['profit_factor']:>12.2f}")
    print("-" * 60)
    print(f"  Total Trades:          {metrics['total_trades']:>12d}")
    print(f"  Ganadores:             {len(win_trades):>12d}")
    print(f"  Perdedores:            {len(lose_trades):>12d}")
    print(f"  Win Rate:              {metrics['win_rate_pct']:>12.1f}%")
    print(f"  Avg Win:               {metrics['avg_win_pct']:>+12.2f}%")
    print(f"  Avg Loss:              {metrics['avg_loss_pct']:>+12.2f}%")
    print("-" * 60)

    # Top 5 mejores y peores trades
    if trades:
        sorted_trades = sorted(trades, key=lambda t: t['pnl'], reverse=True)
        print("  Top 3 Mejores Trades:")
        for t in sorted_trades[:3]:
            print(f"    {t['side'].upper():>5} | PnL: ${t['pnl']:>+10.2f} ({t['pnl_pct']:>+6.2f}%) | Salida: {t['exit_reason']}")
        print("  Top 3 Peores Trades:")
        for t in sorted_trades[-3:]:
            print(f"    {t['side'].upper():>5} | PnL: ${t['pnl']:>+10.2f} ({t['pnl_pct']:>+6.2f}%) | Salida: {t['exit_reason']}")

    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Quantum Edge Backtest Engine")
    parser.add_argument('--ticker', type=str, default='SOL-USD',
                        help='Ticker symbol (default: SOL-USD)')
    parser.add_argument('--period', type=str, default='2y',
                        help='Período de datos (default: 2y)')
    parser.add_argument('--capital', type=float, default=10000.0,
                        help='Capital inicial (default: 10000)')
    args = parser.parse_args()

    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║       QUANTUM EDGE — Motor de Backtest Cuantitativo      ║")
    print("╠══════════════════════════════════════════════════════════╣")
    print(f"║  Ticker: {args.ticker:<15}  Período: {args.period:<10}           ║")
    print(f"║  Capital: ${args.capital:>10,.2f}                              ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()

    # 1. Descargar datos
    df = download_data(args.ticker, args.period)
    if len(df) < 600:
        print("ERROR: Datos insuficientes. Se necesitan al menos 600 velas.")
        return

    # 2. Configurar estrategia
    config = QuantumConfig()
    config.ticker = args.ticker
    config.period = args.period
    config.initial_capital = args.capital

    # 3. Ejecutar
    print("\n  Ejecutando Quantum Edge Backtest...")
    print("  Esto puede tardar unos minutos (walk-forward HMM + 5 señales multi-factor)")
    print()

    engine = QuantumEdge(config)
    metrics = engine.run_backtest(df)

    # 4. Resultados
    print_results(metrics, args.ticker)

    # 5. Generar reporte HTML
    safe_ticker = args.ticker.replace("-", "_").lower()
    output_file = f"quantum_edge_{safe_ticker}_{args.period}.html"
    generate_html_report(df, metrics, args.ticker, output_file)

    print(f"\n  Abre {output_file} en tu navegador para ver el reporte interactivo.")


if __name__ == '__main__':
    main()
