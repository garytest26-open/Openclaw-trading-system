"""
Script de Backtest para la Estrategia Agresiva de Breakout del NASDAQ (QQQ)
==============================================================================
Este script ejecuta un backtest completo de la estrategia optimizada
usando la librería backtesting.py con datos reales de QQQ.
"""
import pandas as pd
import yfinance as yf
from backtesting import Backtest
from final_aggressive_breakout_strategy import AgresivaBreakoutQQQ
from datetime import datetime, timedelta

# ======================
# CONFIGURACIÓN
# ======================
SYMBOL = 'QQQ'
INTERVAL = '15m'  # Estrategia optimizada para 15 minutos
CAPITAL_INICIAL = 10000  # $10,000 USD
COMMISSION = 0.001  # 0.1% comisión por operación

# Obtener últimos 60 días (máximo para intervalo de 15m en yfinance)
end_date = datetime.now()
start_date = end_date - timedelta(days=60)

print("=" * 70)
print("BACKTEST - ESTRATEGIA DONCHIAN BREAKOUT AGRESIVA (QQQ)")
print("=" * 70)
print(f"\nSímbolo: {SYMBOL}")
print(f"Intervalo: {INTERVAL} (15 minutos)")
print(f"Capital Inicial: ${CAPITAL_INICIAL:,.2f}")
print(f"Comisión: {COMMISSION * 100}%")
print(f"Período: {start_date.strftime('%Y-%m-%d')} a {end_date.strftime('%Y-%m-%d')}")
print("=" * 70)

# ======================
# DESCARGA DE DATOS
# ======================
print("\n[1/3] Descargando datos históricos de Yahoo Finance...")
data = yf.download(
    SYMBOL, 
    start=start_date, 
    end=end_date, 
    interval=INTERVAL,
    progress=False
)

if data.empty:
    print("❌ ERROR: No se pudieron obtener datos. Verifica tu conexión.")
    exit(1)

# Preparar datos para backtesting.py
data.index.name = 'datetime'
data.columns = [col.capitalize() for col in data.columns]
data = data[['Open', 'High', 'Low', 'Close', 'Volume']]

print(f"✓ Datos descargados: {len(data)} velas")
print(f"  - Primera vela: {data.index[0]}")
print(f"  - Última vela: {data.index[-1]}")

# ======================
# EJECUTAR BACKTEST
# ======================
print("\n[2/3] Ejecutando backtest con parámetros optimizados...")
print("  - Lookback (Entrada): 37 períodos")
print("  - Exit Lookback (Salida): 2 períodos")
print("  - ATR Stop Multiplier: 1.0x")

bt = Backtest(
    data, 
    AgresivaBreakoutQQQ, 
    cash=CAPITAL_INICIAL,
    commission=COMMISSION,
    exclusive_orders=True
)

# Ejecutar backtest
stats = bt.run()

# ======================
# MOSTRAR RESULTADOS
# ======================
print("\n[3/3] ✓ Backtest completado!\n")
print("=" * 70)
print("RESULTADOS DEL BACKTEST")
print("=" * 70)

# Métricas principales
print(f"\n📊 RENDIMIENTO")
print(f"   Retorno Total:        {stats['Return [%]']:.2f}%")
print(f"   Capital Final:        ${stats['Equity Final [$]']:,.2f}")
print(f"   Ganancia/Pérdida:     ${stats['Equity Final [$]'] - CAPITAL_INICIAL:,.2f}")

print(f"\n📈 OPERACIONES")
print(f"   Total de Trades:      {stats['# Trades']}")
print(f"   Win Rate:             {stats['Win Rate [%]']:.2f}%")
print(f"   Mejor Trade:          {stats['Best Trade [%]']:.2f}%")
print(f"   Peor Trade:           {stats['Worst Trade [%]']:.2f}%")
print(f"   Promedio Trade:       {stats['Avg. Trade [%]']:.2f}%")

print(f"\n⚠️  RIESGO")
print(f"   Max Drawdown:         {stats['Max. Drawdown [%]']:.2f}%")
print(f"   Sharpe Ratio:         {stats['Sharpe Ratio']:.2f}")
print(f"   Sortino Ratio:        {stats['Sortino Ratio']:.2f}")
print(f"   Calmar Ratio:         {stats['Calmar Ratio']:.2f}")

print(f"\n⏱️  DURACIÓN")
print(f"   Promedio por Trade:   {stats['Avg. Trade Duration']}")
print(f"   Exposición al Mercado:{stats['Exposure Time [%]']:.2f}%")

print("\n" + "=" * 70)

# ======================
# ANÁLISIS ADICIONAL
# ======================
print("\n💡 ANÁLISIS")

# Calcular retorno mensual anualizado
dias_trading = (data.index[-1] - data.index[0]).days
if dias_trading > 0:
    retorno_diario = stats['Return [%]'] / dias_trading
    retorno_mensual_aprox = retorno_diario * 30
    print(f"   Retorno Mensual Aprox: ~{retorno_mensual_aprox:.2f}%")

# Profit Factor
if stats['# Trades'] > 0:
    print(f"   Profit Factor:         {stats.get('Profit Factor', 'N/A')}")

# Valoración
if stats['Win Rate [%]'] >= 70:
    print("\n✅ Estrategia con alta tasa de acierto (≥70%)")
elif stats['Win Rate [%]'] >= 50:
    print("\n⚠️  Estrategia con tasa de acierto moderada (50-70%)")
else:
    print("\n❌ Estrategia con baja tasa de acierto (<50%)")

if stats['Sharpe Ratio'] >= 2.0:
    print("✅ Excelente ratio riesgo/retorno (Sharpe ≥2)")
elif stats['Sharpe Ratio'] >= 1.0:
    print("⚠️  Buen ratio riesgo/retorno (Sharpe 1-2)")
else:
    print("❌ Ratio riesgo/retorno bajo (Sharpe <1)")

print("\n" + "=" * 70)

# ======================
# GUARDAR RESULTADOS
# ======================
print("\n📁 Guardando resultados...")

# Guardar gráfico HTML interactivo
output_file = "backtest_final_aggressive_results.html"
bt.plot(filename=output_file, open_browser=False)
print(f"✓ Gráfico guardado: {output_file}")

# Guardar estadísticas detalladas en txt
stats_file = "backtest_final_aggressive_stats.txt"
with open(stats_file, 'w', encoding='utf-8') as f:
    f.write("BACKTEST - ESTRATEGIA DONCHIAN BREAKOUT AGRESIVA (QQQ)\n")
    f.write("=" * 70 + "\n\n")
    f.write(f"Fecha de ejecución: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write(f"Símbolo: {SYMBOL}\n")
    f.write(f"Intervalo: {INTERVAL}\n")
    f.write(f"Capital Inicial: ${CAPITAL_INICIAL:,.2f}\n")
    f.write(f"Período: {start_date.strftime('%Y-%m-%d')} a {end_date.strftime('%Y-%m-%d')}\n\n")
    f.write("=" * 70 + "\n")
    f.write("ESTADÍSTICAS COMPLETAS\n")
    f.write("=" * 70 + "\n\n")
    f.write(str(stats))

print(f"✓ Estadísticas guardadas: {stats_file}")

print("\n✨ ¡Backtest completado exitosamente!")
print("=" * 70)
