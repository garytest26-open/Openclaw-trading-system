import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Claves API
API_KEY = os.getenv('EXCHANGE_API_KEY')
SECRET = os.getenv('EXCHANGE_SECRET')
# Hyperliquid usa Wallet y Private Key
WALLET_ADDRESS = os.getenv('WALLET_ADDRESS')
PRIVATE_KEY = os.getenv('PRIVATE_KEY')

# Configuración del Exchange
EXCHANGE_ID = 'hyperliquid' # id del exchange en ccxt (ej. 'binance', 'hyperliquid')
SANDBOX_MODE = False        # Poner en True si se usa Testnet del Exchange

# Configuración de Trading
# NOTA: Hyperliquid usa formato diferente: 'BTC/USDC:USDC' para perpetuos
# Binance/Bybit usan: 'BTC/USDT' o 'BTC/USDT:USDT' para perpetuos
SYMBOL = 'BTC/USDC:USDC'  # Par a operar (adaptado para Hyperliquid)
TIMEFRAME = '1d'          # '1d' es estándar para la Estrategia Tortuga
LEVERAGE = 1.0          # > 1.0 para Futuros/Margen (Por defecto seguro: 1.0)
RISK_AMOUNT_USD = 1000.0 # Cantidad a comprar por operación (Simple para empezar)

# Configuración de Estrategia
STRATEGY_NAME = 'TURTLE_BREAKOUT'
ENTRY_WINDOW = 20
EXIT_WINDOW = 10

# Configuración del Bot
DRY_RUN = True          # Si es True, NO envía órdenes reales. Solo las registra.
CHECK_INTERVAL = 60     # Segundos a esperar entre ciclos
STATE_FILE = 'bot_state.json'
