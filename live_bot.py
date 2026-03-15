import ccxt
import pandas as pd
import time
import json
import os
import logging
from datetime import datetime
import config

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("trading_bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("LiveBot")

class TradingBot:
    def __init__(self):
        self.config = config
        self.exchange = self._init_exchange()
        self.state = self._load_state()
        
        logger.info(f"Bot Inicializado. Estrategia: {config.STRATEGY_NAME}")
        logger.info(f"Símbolo: {config.SYMBOL}, Temporalidad: {config.TIMEFRAME}")
        logger.info(f"Modo Dry Run (Simulación): {config.DRY_RUN}")
        
    def _init_exchange(self):
        try:
            exchange_class = getattr(ccxt, config.EXCHANGE_ID)
            
            # Configuración específica para Hyperliquid
            if config.EXCHANGE_ID == 'hyperliquid':
                exchange = exchange_class({
                    'walletAddress': config.WALLET_ADDRESS,
                    'privateKey': config.PRIVATE_KEY,
                    'enableRateLimit': True,
                    # Hyperliquid es perpetuo por defecto
                })
            else:
                # Configuración estándar para otros exchanges (Binance, Bybit)
                exchange = exchange_class({
                    'apiKey': config.API_KEY,
                    'secret': config.SECRET,
                    'enableRateLimit': True,
                    'options': {'defaultType': 'future'} if config.LEVERAGE > 1.0 else {} 
                })

            if config.SANDBOX_MODE:
                exchange.set_sandbox_mode(True)
            return exchange
        except Exception as e:
            logger.error(f"Fallo al inicializar exchange: {e}")
            raise

    def _load_state(self):
        if os.path.exists(config.STATE_FILE):
            try:
                with open(config.STATE_FILE, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error cargando estado: {e}")
        return {"in_position": False, "entry_price": 0.0, "position_id": None}

    def _save_state(self):
        try:
            with open(config.STATE_FILE, 'w') as f:
                json.dump(self.state, f)
        except Exception as e:
            logger.error(f"Error guardando estado: {e}")

    def fetch_data(self):
        try:
            # Obtener suficientes velas para calcular la ventana de maximos
            limit = config.ENTRY_WINDOW + 5 
            ohlcv = self.exchange.fetch_ohlcv(config.SYMBOL, config.TIMEFRAME, limit=limit)
            
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception as e:
            logger.error(f"Error obteniendo datos: {e}")
            return None

    def calculate_levels(self, df):
        # Lógica Donchian (Tortuga):
        # La señal de compra NO es el high de hoy, sino el Máximo High de los N días ANTERIORES.
        # fetch_ohlcv() usualmente devuelve la vela actual (incompleta) como último elemento.
        # Debemos excluirla para evitar "repintado".
        
        # Tomamos todas las velas EXCEPTO la última (que asumimos es la actual/viva)
        completed_data = df.iloc[:-1] 
        
        if len(completed_data) < config.ENTRY_WINDOW:
            logger.warning("No hay suficientes velas COMPLETAS para calcular niveles.")
            # Retornar valores seguros que no disparen trades
            return df.iloc[-1]['close'], float('inf'), float('-inf')

        # Nivel de Entrada: Max High de los últimos ENTRY_WINDOW días (de velas cerradas)
        entry_level = completed_data['high'].rolling(window=config.ENTRY_WINDOW).max().iloc[-1]
        
        # Nivel de Salida: Min Low de los últimos EXIT_WINDOW días
        exit_level = completed_data['low'].rolling(window=config.EXIT_WINDOW).min().iloc[-1]
        
        current_price = df.iloc[-1]['close'] # Precio actual en vivo
        
        return current_price, entry_level, exit_level

    def execute_trade(self, side, price):
        amount = config.RISK_AMOUNT_USD / price
        
        if config.DRY_RUN:
            logger.info(f"[DRY RUN] Ejecutaría orden {side}: {amount:.6f} {config.SYMBOL} @ {price}")
            return True
        
        try:
            # Lógica de Orden Real
            # type='market' es riesgoso en baja liquidez, 'limit' es preferible usualmente.
            order = self.exchange.create_order(config.SYMBOL, 'market', side, amount)
            logger.info(f"Orden Ejecutada: {order['id']}")
            return True
        except Exception as e:
            logger.error(f"Trade falló: {e}")
            return False

    def run_cycle(self):
        df = self.fetch_data()
        if df is None or len(df) < config.ENTRY_WINDOW:
            logger.warning("No hay suficientes datos para operar.")
            return

        current_price, entry_level, exit_level = self.calculate_levels(df)
        
        logger.info(f"Precio: {current_price:.2f} | Entrada: >{entry_level:.2f} | Salida: <{exit_level:.2f} | Pos: {self.state['in_position']}")

        # LÓGICA
        if not self.state['in_position']:
            # Condición de Entrada
            if current_price > entry_level:
                logger.info(">>> SEÑAL DE RUPTURA (BREAKOUT) DETECTADA <<<")
                if self.execute_trade('buy', current_price):
                    self.state['in_position'] = True
                    self.state['entry_price'] = current_price
                    self._save_state()
        else:
            # Condición de Salida
            if current_price < exit_level:
                logger.info(">>> SEÑAL DE SALIDA DETECTADA <<<")
                if self.execute_trade('sell', current_price):
                    self.state['in_position'] = False
                    self.state['entry_price'] = 0.0
                    self._save_state()

    def start(self):
        logger.info("Bot iniciando bucle...")
        try:
            while True:
                self.run_cycle()
                time.sleep(config.CHECK_INTERVAL)
        except KeyboardInterrupt:
            logger.info("Bot detenido por el usuario.")

if __name__ == "__main__":
    # Asegurar configuración
    if not config.DRY_RUN:
        if config.EXCHANGE_ID == 'hyperliquid':
            if not config.WALLET_ADDRESS or not config.PRIVATE_KEY:
                logger.error("Faltan WALLET_ADDRESS y PRIVATE_KEY para Hyperliquid. Por favor configúrelas o use DRY_RUN=True.")
                exit(1)
        else:
            if not config.API_KEY or not config.SECRET:
                logger.error("Faltan API_KEY y SECRET. Por favor configúrelas o use DRY_RUN=True.")
                exit(1)
        
    bot = TradingBot()
    bot.start()
