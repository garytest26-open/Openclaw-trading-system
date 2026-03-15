import sys
import os
import pandas as pd
import torch
import warnings

warnings.filterwarnings('ignore')

from nexus_omega_strategy import NexusOmegaConfig
from nexus_omega_rl_layer import RLConfig, NexusOmegaRLEnv, PPOAgent, device

def evaluate_rl_model(model_filename, ticker="SOL-USD", period="2y", interval="1h"):
    """
    Carga un modelo .pt entrenado de la carpeta models/ y simula su rendimiento
    en un periodo histórico, imprimiendo el resultado exacto.
    """
    model_path = os.path.join("models", model_filename)
    if not os.path.exists(model_path):
        print(f"❌ Error: No se encontró el modelo en {model_path}")
        return

    print("=" * 60)
    print(f"  NEXUS OMEGA — BACKTEST CAPA 8 RL")
    print(f"  Modelo:  {model_filename}")
    print(f"  Ticker:  {ticker}")
    print(f"  Periodo: {period} ({interval})")
    print("=" * 60)

    import yfinance as yf
    print(f"\nDescargando datos históricos para {ticker}...")
    df = yf.download(ticker, period=period, interval=interval, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.dropna(inplace=True)
    print(f"→ Procesando {len(df)} velas históricas.")

    # Inferimos la arquitectura del checkpoint si es posible, 
    # asumiendo los valores óptimos estándar.
    config = RLConfig(
        ticker=ticker,
        period=period,
        interval=interval,
        hidden_dim=256,    # Por el JSON Trial 25 o config por defecto
        lstm_layers=2,     # Asumiendo 2 capas LSTM del Trial 19/25 o defecto
        seq_len=32,        # Ventana estándar
    )

    # El Trial 25 en el JSON usaba hidden_dim=256, lstm_layers=3, seq_len=64.
    # El archivo nexus_omega_rl_sol_usd_ep25.pt podría tener esa config guardada.
    # Vamos a leer el checkpoint para forzar la configuración exacta del agente.
    print(f"\nCargando configuración del checkpoint {model_filename}...")
    checkpoint = torch.load(model_path, map_location=device, weights_only=False)
    if 'config' in checkpoint:
        saved_config = checkpoint['config']
        print(f"→ Parámetros recuperados: Hidden={saved_config.hidden_dim}, LSTM={saved_config.lstm_layers}, Seq={saved_config.seq_len}")
        config.hidden_dim = saved_config.hidden_dim
        config.lstm_layers = saved_config.lstm_layers
        config.seq_len = saved_config.seq_len

    print("\nInicializando entorno de mercado...")
    env = NexusOmegaRLEnv(df, config)
    
    # Crear Agente
    agent = PPOAgent(env.state_dim, config)
    agent.model.load_state_dict(checkpoint['model_state'])
    agent.model.eval()

    print("\nEjecutando recorrido histórico. Por favor, espera...")
    state = env.reset()
    while True:
        # Acción determinista: elegir siempre la opción de mayor probabilidad enseñada
        action, _, _ = agent.select_action(state, deterministic=True)
        state, _, done = env.step(action)
        
        # Opcional: imprimir una barra de progreso
        if env.step_idx % 2000 == 0:
            print(f"  Procesando vela {env.step_idx}/{env.n}...")
            
        if done:
            break

    final_capital = env.capital
    ep_return = (final_capital - 10000) / 10000 * 100
    n_trades = len(env.trades)
    win_trades = len([t for t in env.trades if t['pnl_pct'] > 0])
    win_rate = win_trades / n_trades * 100 if n_trades > 0 else 0

    print("\n" + "=" * 60)
    print("  📉 RESULTADOS FINALES DEL BACKTEST (CAPA 8 RL) 📈")
    print("=" * 60)
    print(f"  Capital Inicial: $10,000.00")
    print(f"  Capital Final:   ${final_capital:,.2f}")
    print(f"  Retorno Total:   {ep_return:+.2f}%")
    print(f"  Total Trades:    {n_trades}")
    if n_trades > 0:
        print(f"  Win Rate:        {win_rate:.1f}%")
        
        # Estadísticas de trade
        pnls = [t['pnl_pct'] for t in env.trades]
        avg_pnl = sum(pnls) / len(pnls)
        max_win = max(pnls)
        max_loss = min(pnls)
        print(f"  Promedio/Trade:  {avg_pnl:+.2f}%")
        print(f"  Mejor Trade:     {max_win:+.2f}%")
        print(f"  Peor Trade:      {max_loss:+.2f}%")
    else:
        print("  El modelo decidió no operar en este periodo (Hold completo).")
    print("=" * 60)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, default="nexus_omega_rl_sol_usd_ep25.pt")
    parser.add_argument("--ticker", type=str, default="SOL-USD")
    args = parser.parse_args()
    
    evaluate_rl_model(args.model, ticker=args.ticker)
