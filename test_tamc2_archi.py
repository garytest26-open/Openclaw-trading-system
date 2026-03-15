import torch
import pandas as pd
from tamc_strategy import get_market_data, StrategyConfig, TradingEnvironment, PPOAgent

print("Iniciando prueba de arquitectura TAMC 2.0...")

# 1. Init Config
config = StrategyConfig()
config.period = '1y' # Download less data for fast testing
config.n_features = 10 # 8 local + 2 daily

# 2. Test Data Pipeline
print("Probando descarga de datos Multi-Timeframe e indicadores...")
df = get_market_data(config)

if df.empty:
    print("ERROR: El dataframe esta vacio.")
else:
    print(f"EXITO: Dataframe generado con {len(df)} filas y {len(df.columns)} columnas.")
    print("Muestra de datos (ultimas filas):")
    print(df[['Close', 'RSI_Norm', 'MACD_Hist_Norm', 'ATR_Ratio_Norm', 'Daily_RSI_Norm']].tail())

# 3. Test Environment & States
print("\nProbando inicializacion del Entorno y features...")
env = TradingEnvironment(df, config)
state_seq = env.reset()

print(f"Forma de la secuencia de estado devuelta por el entorno: {state_seq.shape}")
print(f"Deberia ser: ({config.seq_length}, {config.n_features + 7})")

# 4. Test PPO Agent Forward Pass
print("\nProbando el step forward del Agente PPO LSTM...")
try:
    agent = PPOAgent(config)
    action, log_prob, val = agent.select_action(state_seq)
    
    print(f"EXITO: Forward pass completado.")
    print(f"  Accion seleccionada (índice): {action}")
    print(f"  Log Probabilidad: {log_prob:.4f}")
    print(f"  Valor del Estado (Critic): {val:.4f}")
    
    # 5. Test Environment Step
    print("\nProbando step del entorno con la accion...")
    next_state, reward, done, _ = env.step(action)
    print(f"EXITO: Step del entorno ejecutado.")
    print(f"  Reward asignada: {reward:.4f}")
    print(f"  Nuevo balance simulado: {env.balance:.2f}")
    
except Exception as e:
    print(f"ERROR en la inicializacion o inferencia del agente: {e}")
    import traceback
    traceback.print_exc()

print("\nPrueba de arquitectura finalizada.")
