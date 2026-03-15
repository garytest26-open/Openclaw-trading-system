import argparse
from tamc_strategy import train_tamc_ppo

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TAMC 2.0 (Expert Edition) Trainer")
    parser.add_argument('--ticker', type=str, default='SOL-USD', help='Ticker a entrenar (ej. SOL-USD, BTC-USD)')
    
    args = parser.parse_args()
    
    print(f"Iniciando entrenamiento PPO LSTM para {args.ticker}...")
    print("Este proceso descargara la historia del activo, simulara el entorno y optimizara los pesos de la red.")
    print("ADVERTENCIA: PPO con LSTM es computacionalmente pesado. Puede tomar desde varios minutos hasta algunas horas dependiendo del CPU/GPU.")
    print("El mejor modelo se guardara automaticamente en la carpeta 'models/'.")
    print("-" * 50)
    
    train_tamc_ppo(args.ticker)
    
    print("-" * 50)
    print("Proceso finalizado.")
