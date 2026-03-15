import ccxt
import pandas as pd
import numpy as np
import time
import os
import logging
import torch
from dotenv import load_dotenv
from tamc_strategy import StrategyConfig, PPOActorCritic, calculate_indicators, align_daily_features, device

# Load Environment Variables
load_dotenv()

# Configuration
SYMBOL = 'SOL/USDC:USDC'  
TIMEFRAME = '1h'
CHECK_INTERVAL_SECONDS = 60       
COMPOUND_RATIO = 0.95     
LEVERAGE = 1

# NOTE: Must run train_tamc_v2.py for SOL-USD first to generate this!
MODEL_PATH = "models/tamc2_sol_ppo.pth"

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - TESTNET - %(message)s',
    handlers=[
        logging.FileHandler("tamc_sol_testnet.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("TAMC_SOL_Testnet_V2")

class TAMC_SOL_BotTestnet:
    def __init__(self, nexus_mode=False, agent_name="hive", testnet=True):
        self.nexus_mode = nexus_mode
        self.agent_name = agent_name
        self.testnet = testnet
        self.wallet_address = os.getenv('WALLET_ADDRESS')
        self.private_key = os.getenv('PRIVATE_KEY')
        
        if self.nexus_mode:
            import redis
            self.r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
            logger.info(f"🔗 MODO NEXUS ACTIVADO para PM: {self.agent_name}")
            
        if not self.wallet_address or not self.private_key:
            logger.error("Missing WALLET_ADDRESS or PRIVATE_KEY in .env")
            raise ValueError("Credentials missing")

        self.exchange = self._init_exchange()
        self.config = StrategyConfig()
        self.config.ticker = "SOL-USD"
        self.config.n_features = 10 
        
        self.model = self._load_model()
        
        self.action_names = {0: "Flat", 1: "Long 50%", 2: "Long 100%", 3: "Short 50%", 4: "Short 100%"}
        self.last_entry_candle = None
        
    def _init_exchange(self):
        try:
            if hasattr(ccxt, 'hyperliquid'):
                exchange_class = getattr(ccxt, 'hyperliquid')
            else:
                exchange_class = ccxt.hyperliquid

            exchange = exchange_class({
                'walletAddress': self.wallet_address,
                'privateKey': self.private_key,
                'enableRateLimit': True,
                'options': {'defaultType': 'swap'}, 
            })
            
            if self.testnet:
                exchange.set_sandbox_mode(True) 
                logger.info("⚠️ MODO TESTNET ACTIVADO ⚠️ - Usando red de pruebas de Hyperliquid")
            else:
                logger.info("🔥 MODO LIVE ACTIVADO 🔥 - OPERANDO CON DINERO REAL EN MAINNET")
            
            return exchange
        except Exception as e:
            logger.error(f"Exchange Init Failed: {e}")
            raise

    def _load_model(self):
        try:
            if not os.path.exists(MODEL_PATH):
                logger.error(f"MODELO NO ENCONTRADO en {MODEL_PATH}.")
                logger.error("DEBES EJECUTAR `python train_tamc_v2.py --ticker SOL-USD` PRIMERO PARA ENTRENAR LA IA TAMC 2.0")
                raise FileNotFoundError(f"Missing model: {MODEL_PATH}")
                
            state_dim = self.config.n_features + 7
            model = PPOActorCritic(state_dim, 5, self.config.hidden_dim).to(device)
            model.load_state_dict(torch.load(MODEL_PATH, map_location=device, weights_only=True))
            model.eval()
            logger.info(f"Modelo PPO-LSTM cargado correctamente desde {MODEL_PATH}")
            return model
        except Exception as e:
            logger.error(f"Error cargando el modelo: {e}")
            raise

    def fetch_data(self, limit=300):
        try:
            # 1H Data
            ohlcv = self.exchange.fetch_ohlcv(SYMBOL, TIMEFRAME, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # SAFECAST: Fallaba sumando NoneType y Str a veces con fechas corruptas en CCXT Hyperliquid 
            df['timestamp'] = pd.to_numeric(df['timestamp'], errors='coerce')
            df.dropna(subset=['timestamp'], inplace=True)
            
            df['Datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('Datetime', inplace=True)
            df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}, inplace=True)
            df = df[['Open', 'High', 'Low', 'Close', 'Volume']].astype(float)
            
            return df
        except Exception as e:
            logger.error(f"Fetch Data Failed: {e}")
            return pd.DataFrame()

    def get_position(self):
        try:
            positions = self.exchange.fetch_positions([SYMBOL])
            if positions:
                for pos in positions:
                    if pos['symbol'] == SYMBOL and float(pos['contracts']) != 0:
                        return pos
            return None
        except Exception as e:
            logger.error(f"Get Position Failed: {e}")
            return None

    def get_balance(self):
        try:
            bal = self.exchange.fetch_balance()
            if 'USDC' in bal:
                return float(bal['USDC']['free'])
            return 0.0
        except Exception as e:
            logger.error(f"Get Balance Failed: {e}")
            return 0.0

    def get_model_action(self, df_1h):
        try:
            # Calcular indicadores y multi-timeframe
            df_ind = calculate_indicators(df_1h, self.config)
            df_ind = align_daily_features(df_ind, self.config.ticker, "1mo") # 1 mes es suficiente para el lookback diario reciente
            
            if len(df_ind) < self.config.seq_length:
                logger.warning(f"Insuficientes datos ({len(df_ind)}) para la secuencia requerida ({self.config.seq_length}).")
                return 0 # Flat
                
            
            # Obtener estado cuenta
            current_pos = self.get_position()
            pos_val = 0.0
            unrealized_pnl = 0.0
            
            if current_pos:
                side = current_pos['side']
                pos_val = float(current_pos['contracts']) * (1.0 if side == 'long' else -1.0)
                unrealized_pnl = float(current_pos.get('unrealizedPnl', 0.0))
            
            position_state = np.array([
                1.0 if pos_val > 0 else 0.0,
                1.0 if pos_val < 0 else 0.0,
                1.0 if pos_val == 0 else 0.0,
                unrealized_pnl * 10,
                0.0, 0.0, 0.0 
            ])
            
            # Construir la Secuencia LSTM temporal (últimas 24 filas)
            seq = []
            features_cols = [
                'RSI_Norm', 'MACD_Hist_Norm', 'Dist_SMA200_Norm', 'Log_Ret_Norm', 
                'Vol_Rel_Norm', 'ATR_Ratio_Norm', 'BB_Width_Norm', 'Dist_VWAP_Norm',
                'Daily_RSI_Norm', 'Daily_Log_Ret_Norm'
            ]
            
            for i in range(len(df_ind) - self.config.seq_length, len(df_ind)):
                market_features = df_ind.iloc[i][features_cols].values.astype(float)
                # OJO: En modo live pura usamos state actual para la secuencia entera para simplificar, 
                # o el historial real si lo llevásemos en variables de clase
                state_data = np.concatenate([market_features, position_state])
                seq.append(state_data)
                
            state_seq = np.array(seq)
            state_tensor = torch.FloatTensor(state_seq).unsqueeze(0).to(device)
            
            with torch.no_grad():
                action_probs, _, _ = self.model(state_tensor)
                # Argumento estocástico max-likelihood en evaluación = Argmax
                action = torch.argmax(action_probs).item()
                
            return action
        except Exception as e:
            logger.error(f"Error prediciendo accion PPO LSTM: {e}")
            import traceback
            traceback.print_exc()
            return 0 

    def execute_trade(self, action_id, current_price, current_candle_time=None):
        action_name = self.action_names.get(action_id, "Flat")
        
        current_pos = self.get_position()
        current_size = 0.0
        current_side = None
        
        if current_pos:
            current_size = float(current_pos['contracts'])
            current_side = current_pos['side'] 
            
        logger.info(f"PPO Action: {action_name} | Current Pos: {current_side} {current_size}")

        if action_id == 0:
            if current_pos:
                self._close_position(current_side, current_size, current_price)
            return

        target_side = 'buy' if action_id in [1, 2] else 'sell'
        target_exposure = 0.5 if action_id in [1, 3] else 1.0

        if current_pos:
            if (current_side == 'long' and target_side == 'sell') or \
               (current_side == 'short' and target_side == 'buy'):
                self._close_position(current_side, current_size, current_price)
                time.sleep(2)
            elif (current_side == 'long' and target_side == 'buy') or \
                 (current_side == 'short' and target_side == 'sell'):
                # Evita spammear en consola
                return
        else:
             # Anti-Whipsaw (Evitar abrir 20 trades en la misma vela si algo nos cierra prematuramente)
             if current_candle_time is not None and self.last_entry_candle == current_candle_time:
                 logger.debug("Whipsaw Protection Lock: Ya se abrio una posicion en esta vela. Ignorando re-entrada.")
                 return

        balance = self.get_balance()
        if balance < 10: 
            logger.warning(f"Testnet Balance too low (${balance}).")
            return

        trade_value = balance * COMPOUND_RATIO * LEVERAGE * target_exposure
        amount = trade_value / current_price
        amount = round(amount, 2)
        if amount <= 0: return

        logger.info(f"Opening {target_side.upper()} | Bal: ${balance:.2f} | Size: {amount} SOL")
        
        if self.nexus_mode:
            import json
            msg = {
                "agent_id": self.agent_name,
                "action": target_side,
                "asset": "SOL",
                "amount": amount,
                "price": float(current_price)
            }
            self.r.publish('nexus_orders', json.dumps(msg))
            logger.info(f"📡 NEXUS: Señal de {target_side.upper()} enviada al CEO.")
            self.last_entry_candle = current_candle_time
        else:
            try:
                exec_price = float(current_price) if current_price is not None else None
                self.exchange.create_order(SYMBOL, 'market', target_side, amount, exec_price)
                logger.info("Trade Executed Successfully.")
                self.last_entry_candle = current_candle_time
            except Exception as e:
                logger.error(f"Open Trade Failed: {e}")

    def _close_position(self, current_side, current_size, price):
        logger.info(f"Closing existing {current_side} position...")
        close_side = 'sell' if current_side == 'long' else 'buy'
        
        if self.nexus_mode:
            import json
            current_pos = self.get_position()
            pnl_pct = 0.0
            if current_pos:
                entry_price = float(current_pos.get('entryPrice', 0))
                if entry_price > 0:
                     pnl_pct = ((price - entry_price) / entry_price) * 100.0 if current_side == 'long' else ((entry_price - price) / entry_price) * 100.0
                     
            msg = {
                "agent_id": self.agent_name,
                "action": "close",
                "asset": "SOL",
                "amount": abs(current_size),
                "price": float(price),
                "close_side": close_side
            }
            self.r.publish('nexus_orders', json.dumps(msg))
            
            pnl_msg = {
                "agent_id": self.agent_name,
                "pnl_pct": pnl_pct
            }
            self.r.publish('nexus_pnl', json.dumps(pnl_msg))
            logger.info(f"📡 NEXUS: Señal de Cierre enviada al CEO. Reportando PNL al Sindicato: {pnl_pct:.2f}%")
        else:
            try:
                exec_price = float(price) if price is not None else None
                self.exchange.create_order(SYMBOL, 'market', close_side, abs(current_size), exec_price, params={'reduceOnly': True})
                logger.info("Position Closed.")
            except Exception as e:
                logger.error(f"Close Failed: {e}")

    def run(self):
        logger.info("--- BOT TAMC 2.0 SOL INICIADO EN HYPERLIQUID TESTNET ---")
        
        while True:
            try:
                df = self.fetch_data(limit=300) 
                if df.empty:
                    time.sleep(10)
                    continue

                df_closed = df.iloc[:-1].copy()
                current_price = df.iloc[-1]['Close'] 
                last_time = df_closed.index[-1]
                
                action_id = self.get_model_action(df_closed)
                
                logger.info(f"Time: {last_time} | Price: {current_price:.2f} | IA (TAMC 2.0): {self.action_names[action_id]}")
                
                self.execute_trade(action_id, current_price, current_candle_time=last_time)
                
                time.sleep(CHECK_INTERVAL_SECONDS)
                
            except Exception as e:
                logger.error(f"Loop Error: {e}")
                time.sleep(CHECK_INTERVAL_SECONDS)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--live', action='store_true', help='Ejecutar en la MAINNET (dinero real)')
    args = parser.parse_args()
    
    bot = TAMC_SOL_BotTestnet(testnet=not args.live)
    bot.run()


