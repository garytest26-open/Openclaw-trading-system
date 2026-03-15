import ccxt
import os
import json
from dotenv import load_dotenv

load_dotenv()

wallet_address = os.getenv('WALLET_ADDRESS')
private_key = os.getenv('PRIVATE_KEY')

exchange = ccxt.hyperliquid({
    'walletAddress': wallet_address,
    'privateKey': private_key,
    'enableRateLimit': True,
    'options': {'defaultType': 'swap'},
})
exchange.set_sandbox_mode(True)

SYMBOL = 'BTC/USDC:USDC'

# Fetch position
positions = exchange.fetch_positions([SYMBOL])
pos = None
for p in positions:
    if p['symbol'] == SYMBOL and float(p['contracts']) != 0:
        pos = p
        break

if not pos:
    print("No open position.")
else:
    size = abs(float(pos['contracts']))
    side = pos['side']
    close_side = 'sell' if side == 'long' else 'buy'
    print(f"Position found: {side} {size}. Closing with {close_side}...")
    
    # Fetch ticker for current price
    ticker = exchange.fetch_ticker(SYMBOL)
    price = ticker['last']
    print(f"Current price: {price}")
    
    try:
        # standard 
        print("Attempting market close...")
        exchange.create_order(SYMBOL, 'market', close_side, size, price, params={'reduceOnly': True})
        print("Success!")
    except Exception as e:
        print(f"Failed standard: {e}")
        try:
            print("Attempting 'price' in params...")
            exchange.create_order(SYMBOL, 'market', close_side, size, None, params={'reduceOnly': True, 'price': price, 'slippage': 0.05})
            print("Success with params!")
        except Exception as e2:
            print(f"Failed with params: {e2}")

