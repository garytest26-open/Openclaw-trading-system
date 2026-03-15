import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import warnings
warnings.filterwarnings('ignore')

print("==================================================")
print("  SIMULADOR INSTITUCIONAL NEXUS (SINDICATO ALPHA) ")
print("  Vectorizando 2 Años de Datos (Resolución 1H)    ")
print("==================================================")

# --- 1. DESCARGA DE DATOS ---
def get_data(ticker):
    print(f"Descargando datos históricos para {ticker}...")
    df = yf.download(ticker, period="2y", interval="1h", progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)
    df.dropna(inplace=True)
    return df

try:
    btc_df = get_data("BTC-USD")
    eth_df = get_data("ETH-USD")
    sol_df = get_data("SOL-USD")
except Exception as e:
    print(f"Error descargando datos: {e}")
    exit()

# Alinear índices (Misma estampa de tiempo para todos)
common_idx = btc_df.index.intersection(eth_df.index).intersection(sol_df.index)
btc_df = btc_df.loc[common_idx].copy()
eth_df = eth_df.loc[common_idx].copy()
sol_df = sol_df.loc[common_idx].copy()

# --- 2. VECTORIZACIÓN DE ESTRATEGIAS (PMs) ---

# PM 1: Viper Strike proxy (BTC) - Breakout de Volatilidad (Proxy simplificado)
def simulate_viper(df):
    df['SMA_20'] = df['Close'].rolling(20).mean()
    df['STD_20'] = df['Close'].rolling(20).std()
    df['Upper_BB'] = df['SMA_20'] + 2 * df['STD_20']
    df['Lower_BB'] = df['SMA_20'] - 2 * df['STD_20']
    
    # Keltner
    df['ATR_20'] = (df['High'] - df['Low']).rolling(20).mean()
    df['Upper_KC'] = df['SMA_20'] + 1.5 * df['ATR_20']
    df['Lower_KC'] = df['SMA_20'] - 1.5 * df['ATR_20']
    
    # Squeeze: BB inside KC
    df['Squeeze_On'] = (df['Lower_BB'] > df['Lower_KC']) & (df['Upper_BB'] < df['Upper_KC'])
    df['Squeeze_Off'] = ~df['Squeeze_On']
    df['Squeeze_Release'] = df['Squeeze_Off'] & df['Squeeze_On'].shift(1)
    
    df['Momentum'] = df['Close'] - df['Close'].shift(12)
    
    df['Signal'] = 0
    # Long Buy (con proxy ML: exigir aumento de volumen y RSI > 50 para evitar falsos breakouts bajistas)
    df['Vol_SMA'] = df['Volume'].rolling(20).mean()
    ml_long_filter_proxy = (df['Volume'] > df['Vol_SMA'] * 0.9) # proxy simplificado de que el volumen acompaña
    df.loc[(df['Squeeze_Release']) & (df['Momentum'] > 0) & ml_long_filter_proxy, 'Signal'] = 1
    # Short Sell
    df.loc[(df['Squeeze_Release']) & (df['Momentum'] < 0), 'Signal'] = -1
    
    # Posición se mantiene por 8 horas o hasta señal contraria (acortamos la toma de ganancias por el ML)
    df['Position'] = df['Signal'].replace(to_replace=0, method='ffill', limit=8).fillna(0)
    
    df['Returns'] = df['Close'].pct_change()
    df['Strategy_Returns'] = df['Position'].shift(1) * df['Returns']
    return df['Strategy_Returns'].fillna(0)

# PM 2: Sniper proxy (ETH) - Mean Reversion RSI Extremo
def simulate_sniper(df):
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    df['SMA_20'] = df['Close'].rolling(20).mean()
    df['STD_20'] = df['Close'].rolling(20).std()
    df['Lower_BB'] = df['SMA_20'] - 2 * df['STD_20']
    df['Upper_BB'] = df['SMA_20'] + 2 * df['STD_20']
    
    df['Signal'] = 0
    
    # Proxy L2 Orderbook Imbalance: Exigimos vela pequeña de rechazo o spike de volumen para simular rebote ballena
    df['Vol_SMA'] = df['Volume'].rolling(20).mean()
    l2_buy_proxy = (df['Volume'] > df['Vol_SMA'] * 1.2) # Muro absorbiendo ventas
    l2_sell_proxy = (df['Volume'] > df['Vol_SMA'] * 1.2)
    
    # Compra soporte extremo (con confirmación de caída frenada L2)
    df.loc[(df['RSI'] < 30) & (df['Close'] <= df['Lower_BB']) & l2_buy_proxy, 'Signal'] = 1
    # Vende euforia extrema
    df.loc[(df['RSI'] > 70) & (df['Close'] >= df['Upper_BB']) & l2_sell_proxy, 'Signal'] = -1
    
    # Mantiene por 6 horas máximo esperando el rebote a la media
    df['Position'] = df['Signal'].replace(to_replace=0, method='ffill', limit=6).fillna(0)
    
    df['Returns'] = df['Close'].pct_change()
    df['Strategy_Returns'] = df['Position'].shift(1) * df['Returns']
    return df['Strategy_Returns'].fillna(0)

# PM 3: Trend Follower (SOL) - SuperTrend Proxy
def simulate_trend(df):
    df['SMA_50'] = df['Close'].rolling(50).mean()
    df['SMA_200'] = df['Close'].rolling(200).mean()
    
    df['Position'] = 0
    df.loc[df['SMA_50'] > df['SMA_200'], 'Position'] = 1
    df.loc[df['SMA_50'] < df['SMA_200'], 'Position'] = -1
    
    df['Returns'] = df['Close'].pct_change()
    df['Strategy_Returns'] = df['Position'].shift(1) * df['Returns']
    return df['Strategy_Returns'].fillna(0)

print("Calculando Retornos Individuales de los Agentes...")
btc_returns = simulate_viper(btc_df)
eth_returns = simulate_sniper(eth_df)
sol_returns = simulate_trend(sol_df)

# PM 4: Stat Arb (Pairs Trading BTC/ETH) Market Neutral
def simulate_stat_arb(df1, df2):
    # df1 = BTC, df2 = ETH
    log_px1 = np.log(df1['Close'])
    log_px2 = np.log(df2['Close'])
    spread = log_px1 - log_px2
    
    spread_mean = spread.rolling(100).mean()
    spread_std = spread.rolling(100).std()
    z_score = (spread - spread_mean) / spread_std
    
    pos = pd.Series(0, index=df1.index)
    
    # z > 2 => Short BTC, Long ETH
    pos.loc[z_score > 2.0] = -1 
    # z < -2 => Long BTC, Short ETH
    pos.loc[z_score < -2.0] = 1 
    
    # Salir en 0.5
    pos.loc[(z_score < 0.5) & (z_score > -0.5)] = 0
    
    pos = pos.replace(to_replace=0, method='ffill').fillna(0)
    
    ret_btc = df1['Close'].pct_change()
    ret_eth = df2['Close'].pct_change()
    
    # Si pos == 1 => Long BTC, Short ETH => return_btc - return_eth
    # Si pos == -1 => Short BTC, Long ETH => -return_btc + return_eth
    arb_returns = pos.shift(1) * (ret_btc - ret_eth)
    
    return arb_returns.fillna(0)

stat_arb_returns = simulate_stat_arb(btc_df, eth_df)

# Combinar en un DF
agents_df = pd.DataFrame({
    'Viper_ML_BTC': btc_returns,
    'Sniper_L2_ETH': eth_returns,
    'Trend_SOL': sol_returns,
    'StatArb_Neutral': stat_arb_returns
}, index=common_idx)


# --- 3. EL CEO (IA CAPITAL ALLOCATOR) ---
print("Simulando IA del CEO (Capital Allocator 4 PMs)...")
capital_weights = np.zeros(agents_df.shape)
# Inicialmente el capital se divide en 4
capital_weights[0] = [0.25, 0.25, 0.25, 0.25]

q_values = np.array([1.0, 1.0, 1.0, 1.0])
learning_rate = 0.05
momentum_lookback = 48 # Tiempo de evaluación ajustado para 4 PMs

for i in range(1, len(agents_df)):
    if i < momentum_lookback:
        capital_weights[i] = [0.25, 0.25, 0.25, 0.25]
        continue
        
    # Recompensa = Retorno acumulado en las últimas 24H
    recent_rewards = agents_df.iloc[i-momentum_lookback:i].sum().values
    
    # Q-Learning Update
    q_values = q_values + learning_rate * (recent_rewards - q_values)
    
    # Softmax para pesos
    exp_q = np.exp(q_values * 5) # Factor 5 para hacer las decisiones más agresivas
    weights = exp_q / np.sum(exp_q)
    
    capital_weights[i] = weights

# Calcular el equity combinado del sindicato
syndicate_returns = np.sum(agents_df.values * capital_weights, axis=1)
agents_df['Syndicate'] = syndicate_returns

# Benchmark: Hold BTC
agents_df['HODL_BTC'] = btc_df['Close'].pct_change().fillna(0)

# Calcular Curvas de Equidad (Empezando en $1000)
equity = (1 + agents_df).cumprod() * 1000

print("\n--- RESULTADOS FINALES (A 2 AÑOS) ---")
ret_syndicate = (equity['Syndicate'].iloc[-1] / 1000 - 1) * 100
ret_hodl = (equity['HODL_BTC'].iloc[-1] / 1000 - 1) * 100
print(f"Retorno Sindicato Alpha: {ret_syndicate:.2f}%")
print(f"Retorno Buy & Hold BTC:  {ret_hodl:.2f}%")

# --- 4. EXPORTAR REPORTE HTML ---
print("Generando Reporte Gráfico en backtest_nexus_report.html...")

fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                    vertical_spacing=0.03, row_heights=[0.7, 0.3])

# Equity Curves
fig.add_trace(go.Scatter(x=equity.index, y=equity['Syndicate'], mode='lines', name='👑 Sindicato Alpha (Combinado)', line=dict(color='gold', width=3)), row=1, col=1)
fig.add_trace(go.Scatter(x=equity.index, y=equity['HODL_BTC'], mode='lines', name='HODL BTC', line=dict(color='gray', width=2, dash='dash')), row=1, col=1)

# Agentes Individuales
fig.add_trace(go.Scatter(x=equity.index, y=equity['Viper_ML_BTC'], mode='lines', name='Viper ML Edge (BTC)', line=dict(color='red', width=1), opacity=0.5), row=1, col=1)
fig.add_trace(go.Scatter(x=equity.index, y=equity['Sniper_L2_ETH'], mode='lines', name='Sniper L2 Edge (ETH)', line=dict(color='blue', width=1), opacity=0.5), row=1, col=1)
fig.add_trace(go.Scatter(x=equity.index, y=equity['Trend_SOL'], mode='lines', name='Trend (SOL)', line=dict(color='green', width=1), opacity=0.5), row=1, col=1)
fig.add_trace(go.Scatter(x=equity.index, y=equity['StatArb_Neutral'], mode='lines', name='Stat Arb Quant', line=dict(color='orange', width=2), opacity=0.8), row=1, col=1)

# Evolución de Pesos de Capital (Area)
weights_df = pd.DataFrame(capital_weights, index=equity.index, columns=['Viper', 'Sniper', 'Trend', 'StatArb'])

# Smooth para reducir ruido en el grafico
weights_df = weights_df.rolling(48).mean() 

fig.add_trace(go.Scatter(x=weights_df.index, y=weights_df['Viper'], mode='lines', name='% Capital Viper', stackgroup='one', fillcolor='rgba(255,0,0,0.5)', line=dict(color='red', width=0)), row=2, col=1)
fig.add_trace(go.Scatter(x=weights_df.index, y=weights_df['Sniper'], mode='lines', name='% Capital Sniper', stackgroup='one', fillcolor='rgba(0,0,255,0.5)', line=dict(color='blue', width=0)), row=2, col=1)
fig.add_trace(go.Scatter(x=weights_df.index, y=weights_df['Trend'], mode='lines', name='% Capital Trend', stackgroup='one', fillcolor='rgba(0,255,0,0.5)', line=dict(color='green', width=0)), row=2, col=1)
fig.add_trace(go.Scatter(x=weights_df.index, y=weights_df['StatArb'], mode='lines', name='% Capital StatArb', stackgroup='one', fillcolor='rgba(255,165,0,0.5)', line=dict(color='orange', width=0)), row=2, col=1)

fig.update_layout(
    title='Proyecto Nexus V2: Sindicato Alpha Edges Cuantitativos (2 Años)',
    template='plotly_dark',
    height=800,
    hovermode='x unified',
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)
fig.update_yaxes(title_text="Capital ($)", row=1, col=1)
fig.update_yaxes(title_text="Alocación de Capital", row=2, col=1, tickformat=".0%")

fig.write_html('backtest_nexus_report.html')
print("¡Completado!")
