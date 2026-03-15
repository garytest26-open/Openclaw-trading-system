"""
VIPER STRIKE BOT - Hyperliquid LIVE (DINERO REAL)
Volatility Squeeze + Market Structure + Pyramiding

PRECAUCION: Este script opera con DINERO REAL.
Usa .env para credenciales (WALLET_ADDRESS, PRIVATE_KEY).

Uso:
    python viper_strike_live.py --asset ETH
    python viper_strike_live.py --asset BTC
"""
import argparse
from viper_strike_testnet import ViperStrikeBot


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Viper Strike Bot - Hyperliquid LIVE")
    parser.add_argument('--asset', type=str, default='ETH', choices=['BTC', 'ETH', 'SOL'],
                        help='Activo a operar (default: ETH)')
    parser.add_argument('--confirm', action='store_true',
                        help='Confirmar que deseas operar con dinero real')
    args = parser.parse_args()
    
    if not args.confirm:
        print("="*55)
        print("  !! ATENCION: MODO LIVE - DINERO REAL !!")
        print("="*55)
        print(f"  Activo: {args.asset}")
        print(f"  Para confirmar, ejecuta:")
        print(f"    python viper_strike_live.py --asset {args.asset} --confirm")
        print("="*55)
    else:
        print("="*55)
        print(f"  LIVE MODE ACTIVADO - {args.asset}")
        print("="*55)
        bot = ViperStrikeBot(asset=args.asset, testnet=False)
        bot.run()
