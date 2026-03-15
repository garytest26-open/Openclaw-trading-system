import ccxt
import pandas as pd
import time
import json
import os
import logging
import importlib
from datetime import datetime, time
import config

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("trading_bot_multi.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("MultiBot")

class MultiStrategyBot:
    def __init__(self):
        self.config = config
        self.exchange = self._init_exchange()
        self.strategies = {} # {'strategy_name': strategy_instance}
        self.state = self._load_state()
        
        # Cargar estrategias
        self._load_strategies()
        
        logger.info(f"Bot Multi-Estrategia Inicializado. Modo Dry Run: {config.DRY_RUN}")
        logger.info(f"Estrategias activas: {list(self.strategies.keys())}")
        
    def _init_exchange(self):
        try:
            exchange_class = getattr(ccxt, config.EXCHANGE_ID)
            
            if config.EXCHANGE_ID == 'hyperliquid':
                exchange = exchange_class({
                    'walletAddress': config.WALLET_ADDRESS,
                    'privateKey': config.PRIVATE_KEY,
                    'enableRateLimit': True,
                })
            else:
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

    def _load_strategies(self):
        """
        Carga e inicializa las estrategias definidas.
        Aquí definimos hardcoded las 3 estrategias por ahora, 
        pero podría leerse de un archivo config en el futuro.
        """
        try:
            # 1. Breakout Strategy
            from strategies.breakout import BreakoutStrategy
            self.strategies['Breakout'] = BreakoutStrategy({
                'timeframe': config.TIMEFRAME,
                'entry_window': 20, 
                'exit_window': 10,
                'stop_loss_pct': 2.0,
                'take_profit_pct': 4.0
            })

            # 2. ORB Strategy
            from strategies.orb_live import ORBStrategyLive
            self.strategies['ORB'] = ORBStrategyLive({
                'timeframe': config.TIMEFRAME,
                'or_start_time': time(14, 30), # 9:30 EST
                'or_end_time': time(15, 0),    # 10:00 EST
                'ema_fast': 5,
                'ema_slow': 60,
                'vol_mult': 1.0,
                'stop_loss_pct': 1.0,  # Default fallback
                'take_profit_pct': 2.0 # Default fallback
            })
            
            # 3. Mean Reversion Strategy
            from strategies.mean_reversion import MeanReversionStrategy
            self.strategies['MeanReversion'] = MeanReversionStrategy({
                'timeframe': config.TIMEFRAME,
                'bb_length': 20,
                'bb_std': 2.0,
                'rsi_length': 14,
                'rsi_lower': 30,
                'rsi_upper': 70,
                'stop_loss_pct': 2.0,
                'take_profit_pct': 3.0
            })

            # Restaurar estado de cada estrategia si existe
            for name, strategy in self.strategies.items():
                if name in self.state:
                    s_state = self.state[name]
                    if s_state.get('in_position'):
                        strategy.enter_position(
                            s_state.get('position_type'), 
                            s_state.get('entry_price')
                        )

        except Exception as e:
            logger.error(f"Error cargando estrategias: {e}")
            raise

    def _load_state(self):
        if os.path.exists("bot_state_multi.json"):
            try:
                with open("bot_state_multi.json", 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error cargando estado: {e}")
        return {}

    def _save_state(self):
        # Guardar estado de cada estrategia
        state_to_save = {}
        for name, strategy in self.strategies.items():
            state_to_save[name] = strategy.get_position_info()
            
        try:
            with open("bot_state_multi.json", 'w') as f:
                json.dump(state_to_save, f, indent=4)
        except Exception as e:
            logger.error(f"Error guardando estado: {e}")

    def fetch_data(self, limit=100):
        try:
            ohlcv = self.exchange.fetch_ohlcv(config.SYMBOL, config.TIMEFRAME, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception as e:
            logger.error(f"Error obteniendo datos: {e}")
            return None

    def execute_trade(self, strategy_name, side, amount, price):
        if config.DRY_RUN:
            logger.info(f"[DRY RUN] [{strategy_name}] Ejecutaría orden {side}: {amount:.6f} {config.SYMBOL} @ {price}")
            return True
        
        try:
            # Nota: Gestión de riesgos compartida debería ir aquí (e.g. max exposure total)
            order = self.exchange.create_order(config.SYMBOL, 'market', side, amount)
            logger.info(f"[{strategy_name}] Orden Ejecutada: {order['id']} - {side} @ {price}")
            return True
        except Exception as e:
            logger.error(f"[{strategy_name}] Trade falló: {e}")
            return False

    def run_cycle(self):
        df = self.fetch_data()
        if df is None or len(df) < 50: # Mínimo buffer
            logger.warning("Datos insuficientes.")
            return

        current_price = df.iloc[-1]['close']
        
        # Iterar sobre cada estrategia
        for name, strategy in self.strategies.items():
            try:
                # 1. Calcular indicadores
                df_strat = strategy.calculate_indicators(df.copy())
                
                # 2. Verificar condiciones de salida si estamos en posición
                info = strategy.get_position_info()
                if info['in_position']:
                    should_exit = strategy.check_exit_conditions(current_price)
                    if should_exit:
                        # Determinar lado opuesto
                        side = 'sell' if info['position_type'] == 'long' else 'buy'
                        logger.info(f"[{name}] Señal de SALIDA (Stop/TP/Exit Rule).")
                        if self.execute_trade(name, side, 0.0, current_price): # Amount 0.0 simulado, calcular real
                             strategy.exit_position()
                             self._save_state()
                    else:
                        # Algunas estrategias tienen señales de salida explícitas aparte de TP/SL
                        signal = strategy.generate_signal(df_strat, len(df_strat)-1) # -1 para vela cerrada o actual según lógica
                        if (info['position_type'] == 'long' and signal == 'close_long') or \
                           (info['position_type'] == 'short' and signal == 'close_short'):
                            logger.info(f"[{name}] Señal de SALIDA por indicador.")
                            if self.execute_trade(name, 'sell' if info['position_type'] == 'long' else 'buy', 0.0, current_price):
                                strategy.exit_position()
                                self._save_state()

                # 3. Verificar condiciones de entrada si NO estamos en posición
                else:
                    signal = strategy.generate_signal(df_strat, len(df_strat)-1)
                    
                    if signal in ['buy', 'sell']:
                        amount = config.RISK_AMOUNT_USD / current_price
                        logger.info(f"[{name}] Señal de ENTRADA: {signal}")
                        
                        if self.execute_trade(name, signal, amount, current_price):
                            strategy.enter_position('long' if signal == 'buy' else 'short', current_price)
                            self._save_state()
                            
            except Exception as e:
                logger.error(f"Error ejecutando estrategia {name}: {e}")

    def start(self):
        logger.info("Bot Multi-Estrategia iniciando bucle...")
        try:
            while True:
                self.run_cycle()
                time.sleep(config.CHECK_INTERVAL)
        except KeyboardInterrupt:
            logger.info("Bot detenido por el usuario.")

if __name__ == "__main__":
    bot = MultiStrategyBot()
    bot.start()
