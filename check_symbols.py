
import ccxt
import os

print("Conectando a Hyperliquid...")
try:
    exchange = ccxt.hyperliquid()
    markets = exchange.load_markets()
    print(f"Total mercados encontrados: {len(markets)}")
    
    print("\n--- Buscando BTC ---")
    for symbol in markets:
        if 'BTC' in symbol:
            print(f"Símbolo: {symbol} | ID: {markets[symbol]['id']}")

except Exception as e:
    print(f"Error: {e}")
