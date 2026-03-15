import ccxt
import numpy as np
import os
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

try:
    exchange.create_order('BTC/USDC:USDC', 'market', 'sell', 0.01, np.float64(66000), params={'reduceOnly': True})
except Exception as e:
    print(f"Error NP: {repr(e)}")

try:
    exchange.create_order('BTC/USDC:USDC', 'market', 'sell', 0.01, float(66000), params={'reduceOnly': True})
except Exception as e:
    print(f"Error Float: {repr(e)}")
