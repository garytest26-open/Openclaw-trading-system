import argparse
import sys
import os

sys.path.append(os.getcwd())

try:
    from tamc_strategy import train_tamc
except ImportError:
    print("Error: No se pudo importar la estrategia. Verifica que estás en el directorio correcto.")
    sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Ejecutar Estrategia TAMC (Deep RL)")
    parser.add_argument("--mode", type=str, default="train", choices=["train", "test"])
    parser.add_argument("--episodes", type=int, default=50)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--ticker", type=str, default="BTC-USD", help="Ticker a entrenar, e.g. SOL-USD, ETH-USD")

    args = parser.parse_args()

    if args.mode == 'train':
        print(f"Iniciando entrenamiento TAMC | {args.ticker} | {args.episodes} episodios...")
        train_tamc(episodes=args.episodes, data_limit=args.limit, ticker=args.ticker)
    else:
        print("Modo test aún no implementado completamente en este wrapper.")

if __name__ == "__main__":
    main()
