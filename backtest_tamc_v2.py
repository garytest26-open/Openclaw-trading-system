import os
import pandas as pd
import numpy as np
import torch
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys

from tamc_strategy import StrategyConfig, TradingEnvironment, PPOActorCritic, get_market_data, device

def run_backtest():
    print("="*60)
    print("Iniciando Backtest de 1 Año - TAMC 2.0 (PPO + LSTM)")
    print("="*60)
    
    # 1. Configuración
    config = StrategyConfig()
    config.ticker = "SOL-USD"
    config.period = "1y" # Descargar exactamente 1 año
    config.n_features = 10
    config.hidden_dim = 256 # Coincidir con el entrenamiento GPU
    lstm_layers = 2         # Coincidir con el entrenamiento GPU
    
    model_path = "models/tamc2_improved_4090.pth"
    if not os.path.exists(model_path):
        model_path = "tamc2_improved_4090.pth" # Fallback
        
    if not os.path.exists(model_path):
        print(f"Error: Modelo mejorado (4090) no encontrado.")
        return
        
    # 2. Cargar Datos
    print("Descargando historial de 1 año (Multi-Timeframe)...")
    df = get_market_data(config)
    if df.empty:
        print("Error: No se pudieron descargar los datos.")
        return
        
    print(f"Datos preparados: {len(df)} velas de 1 hora.")
    
    # 3. Cargar Modelo
    print("Cargando red neuronal PPO-LSTM (Arquitectura 5090)...")
    state_dim = config.n_features + 7
    model = PPOActorCritic(state_dim, 5, config.hidden_dim, lstm_layers=lstm_layers).to(device)
    
    # Cargar y limpiar claves si vienen de torch.compile()
    state_dict = torch.load(model_path, map_location=device, weights_only=True)
    new_state_dict = {}
    for k, v in state_dict.items():
        name = k.replace("_orig_mod.", "") # Eliminar prefijo de compilación
        new_state_dict[name] = v
        
    model.load_state_dict(new_state_dict)
    model.eval()
    
    # 4. Configurar Entorno Simulado
    print("Iniciando simulación de trading (con 0.05% comisiones por trade)...")
    env = TradingEnvironment(df, config)
    state_seq = env.reset()
    done = False
    
    action_names = {0: "Flat", 1: "Long 50%", 2: "Long 100%", 3: "Short 50%", 4: "Short 100%"}
    trade_history = []
    
    # Métrica: Trades count
    trades_executed = 0
    winning_trades = 0
    losing_trades = 0
    last_action = 0
    
    equity_timestamps = [df.index[config.seq_length]]
    
    while not done:
        # Inferencia determinística (Argmax) para testing
        state_tensor = torch.FloatTensor(state_seq).unsqueeze(0).to(device)
        with torch.no_grad():
            action_probs, _, _ = model(state_tensor)
            action = torch.argmax(action_probs).item()
            
        next_state_seq, reward, done, _ = env.step(action)
        
        # Trackear trade para estadísticas si hay un cruce Flat -> Long/Short o reversiones
        if action != last_action and action != 0 and last_action == 0:
            trades_executed += 1
            # Lógica simple: si equity sube respecto a cuando entramos, es win
            # Se calculará de forma más precisa viendo la curva final
            
        last_action = action
        state_seq = next_state_seq
        
        if env.current_step < len(df):
             equity_timestamps.append(df.index[env.current_step])
        
    # 5. Calcular Métricas Finales
    initial_cap = config.initial_capital
    final_cap = env.equity_curve[-1]
    total_return = (final_cap - initial_cap) / initial_cap * 100
    
    # Calcular Drawdown de la curva
    equity_series = pd.Series(env.equity_curve)
    rolling_max = equity_series.rolling(window=len(equity_series), min_periods=1).max()
    drawdowns = (equity_series - rolling_max) / rolling_max * 100
    max_drawdown = drawdowns.min()
    
    # Retorno Buy & Hold para comparar
    first_price = df.iloc[config.seq_length]['Close']
    last_price = df.iloc[-1]['Close']
    bnh_return = (last_price - first_price) / first_price * 100
    
    print("\n" + "="*40)
    print("📈 RESULTADOS DEL BACKTEST (1 AÑO) 📉")
    print("="*40)
    print(f"Capital Inicial:     ${initial_cap:,.2f}")
    print(f"Capital Final:       ${final_cap:,.2f}")
    print(f"Retorno Neto TAMC:   {total_return:+.2f}%")
    print(f"Retorno Buy & Hold:  {bnh_return:+.2f}%")
    print("-" * 40)
    print(f"Drawdown Máximo:     {max_drawdown:.2f}%")
    print("="*40)
    
    # 6. Generar Gráfico HTML
    generate_html_report(df, equity_timestamps, env.equity_curve, total_return, max_drawdown, bnh_return)

def generate_html_report(df, times, equity, total_return, max_drawdown, bnh_return):
    print("Generando reporte interactivo HTML...")
    
    # Asegurar que times y equity tienen misma longitud recortando el último si sobra
    min_len = min(len(times), len(equity))
    times = times[:min_len]
    equity = equity[:min_len]
    
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.03, subplot_titles=('Capital de la Cuenta (Equity)', 'Precio SOL-USD'),
                        row_width=[0.3, 0.7])

    # Curva de Equity Bot
    fig.add_trace(go.Scatter(
        x=times, y=equity,
        line=dict(color='#00ff00' if total_return >= 0 else '#ff0000', width=2),
        name='Capital IA ($)'
    ), row=1, col=1)

    # Gráfico de Precio Base
    price_slice = df.loc[times[0]:times[-1]]
    
    fig.add_trace(go.Candlestick(
        x=price_slice.index,
        open=price_slice['Open'],
        high=price_slice['High'],
        low=price_slice['Low'],
        close=price_slice['Close'],
        name='Precio SOL'
    ), row=2, col=1)

    # Layout styling
    fig.update_layout(
        title=f"TAMC 2.0 (PPO-LSTM) Backtest 1 Año | Retorno: {total_return:.2f}% | Max DD: {max_drawdown:.2f}% | B&H: {bnh_return:.2f}%",
        yaxis_title='Dólares ($)',
        yaxis2_title='Precio ($)',
        xaxis_rangeslider_visible=False,
        template='plotly_dark',
        height=800,
        hovermode="x unified"
    )

    filename = "tamc2_backtest_1y_sol.html"
    fig.write_html(filename)
    print(f"✅ Reporte guardado en: {filename}")
    print("¡Abre este archivo en tu navegador web para ver los gráficos interactivos!")

if __name__ == "__main__":
    run_backtest()
