import ccxt
import os
import json
from dotenv import load_dotenv

load_dotenv()

def debug_balance():
    print("--- DIAGNÓSTICO DE SALDO HYPERLIQUID (TESTNET) ---")
    
    wallet = os.getenv('WALLET_ADDRESS')
    private_key = os.getenv('PRIVATE_KEY')
    
    print(f"Wallet Configurada: {wallet}")
    
    # Init Exchange
    try:
        if hasattr(ccxt, 'hyperliquid'):
            exchange_class = getattr(ccxt, 'hyperliquid')
        else:
             exchange_class = getattr(ccxt, 'hyperliquid') if 'hyperliquid' in ccxt.exchanges else None

        if not exchange_class:
            print("Error: Hyperliquid no encontrado en CCXT.")
            return

        exchange = exchange_class({
            'walletAddress': wallet,
            'privateKey': private_key,
            'enableRateLimit': True,
            'options': {'defaultType': 'swap'}, 
        })
        exchange.set_sandbox_mode(True)
        
        # Fetch Balance
        print(f"API Base URL: {exchange.urls['api']}")
        
        print("\n--- INTENTO 1: Default ---")
        try:
            bal1 = exchange.fetch_balance()
            print(f"USDC: {bal1.get('USDC', {})}")
        except Exception as e:
            print(f"Error Default: {e}")

        print("\n--- INTENTO 2: Type='swap' ---")
        try:
            bal2 = exchange.fetch_balance({'type': 'swap'})
            print(f"USDC: {bal2.get('USDC', {})}")
        except Exception as e:
            print(f"Error Swap: {e}")
            
        print("\n--- INTENTO 3: Type='spot' ---")
        try:
            bal3 = exchange.fetch_balance({'type': 'spot'})
            print(f"USDC: {bal3.get('USDC', {})}")
        except Exception as e:
            print(f"Error Spot: {e}")
        
        print("\n--- BUSCANDO FONDOS ---")
        usdc_free = balance.get('USDC', {}).get('free', 0)
        usdc_total = balance.get('USDC', {}).get('total', 0)
        
        print(f"USDC Free (Disponible): {usdc_free}")
        print(f"USDC Total: {usdc_total}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_balance()
