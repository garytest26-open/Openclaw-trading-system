import ccxt
import pandas as pd
import numpy as np
import time
import json
import os
import logging
from datetime import datetime
from dotenv import load_dotenv

# Load Environment Variables
load_dotenv()

# Configuration
SYMBOL = 'BTC/USDC:USDC'  
TIMEFRAME = '1h'
ATR_PERIOD = 10
ATR_MULTIPLIER = 5.0
CHECK_INTERVAL = 60       
COMPOUND_RATIO = 0.95     
LEVERAGE = 1              
TRAILING_STOP_ATR_MULT = 4.5

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - TESTNET - %(message)s',
    handlers=[
        logging.FileHandler("btc_supertrend_testnet.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("SuperTrendBot_Testnet")

class SuperTrendBotTestnet:
    def __init__(self):
        self.wallet_address = os.getenv('WALLET_ADDRESS')
        self.private_key = os.getenv('PRIVATE_KEY')
        
        if not self.wallet_address or not self.private_key:
            logger.error("Missing WALLET_ADDRESS or PRIVATE_KEY in .env")
            raise ValueError("Credentials missing")

        self.exchange = self._init_exchange()
        self.position = None 
        self.entry_price = 0.0
        self.best_price = 0.0
        self.trail_stop = 0.0
        
    def _init_exchange(self):
        logger.info(f"CCXT Version: {ccxt.__version__}")
        try:
            # Robust way to access exchange class
            if hasattr(ccxt, 'hyperliquid'):
                exchange_class = getattr(ccxt, 'hyperliquid')
            else:
                logger.error("Hyperliquid not found in ccxt attributes. Checking exchanges list...")
                if 'hyperliquid' in ccxt.exchanges:
                    exchange_class = getattr(ccxt, 'hyperliquid')
                else:
                    raise ImportError("Hyperliquid not supported in this CCXT version.")

            exchange = exchange_class({
                'walletAddress': self.wallet_address,
                'privateKey': self.private_key,
                'enableRateLimit': True,
                'options': {'defaultType': 'swap'}, 
            })
            
            # --- ACTIVAR MODO TESTNET ---
            exchange.set_sandbox_mode(True) 
            logger.info("⚠️ MODO TESTNET ACTIVADO ⚠️ - Usando red de pruebas de Hyperliquid")
            
            return exchange
        except Exception as e:
            logger.error(f"Exchange Init Failed: {e}")
            raise

    def fetch_data(self, limit=100):
        try:
            ohlcv = self.exchange.fetch_ohlcv(SYMBOL, TIMEFRAME, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception as e:
            logger.error(f"Fetch Data Failed: {e}")
            return pd.DataFrame()

    def calculate_supertrend(self, df):
        # ATR
        high = df['high']
        low = df['low']
        close = df['close']
        
        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(ATR_PERIOD).mean().bfill()
        
        # Basic Bands
        hl2 = (high + low) / 2
        basic_upper = hl2 + (ATR_MULTIPLIER * atr)
        basic_lower = hl2 - (ATR_MULTIPLIER * atr)
        
        # Arrays
        c = close.values
        bu = basic_upper.values
        bl = basic_lower.values
        
        fu = np.zeros_like(c)
        fl = np.zeros_like(c)
        trend = np.zeros_like(c) # 1 = Up, -1 = Down
        
        # Init
        fu[0] = bu[0]
        fl[0] = bl[0]
        trend[0] = 1
        
        for i in range(1, len(c)):
            # Final Upper
            if bu[i] < fu[i-1] or c[i-1] > fu[i-1]:
                fu[i] = bu[i]
            else:
                fu[i] = fu[i-1]
                
            # Final Lower
            if bl[i] > fl[i-1] or c[i-1] < fl[i-1]:
                fl[i] = bl[i]
            else:
                fl[i] = fl[i-1]
                
            # Trend
            prev_trend = trend[i-1]
            if prev_trend == -1:
                if c[i] > fu[i-1]:
                    trend[i] = 1
                else:
                    trend[i] = -1
            else:
                if c[i] < fl[i-1]:
                    trend[i] = -1
                else:
                    trend[i] = 1
                    
        return trend[-1], fu[-1], fl[-1]

    def get_position(self):
        try:
            positions = self.exchange.fetch_positions([SYMBOL])
            if positions:
                for pos in positions:
                    if pos['symbol'] == SYMBOL and float(pos['contracts']) != 0:
                        self.entry_price = float(pos.get('entryPrice', self.entry_price))
                        return pos
            return None
        except Exception as e:
            logger.error(f"Get Position Failed: {e}")
            return None

    def get_balance(self):
        try:
            bal = self.exchange.fetch_balance()
            return float(bal['USDC']['free'])
        except Exception as e:
            logger.error(f"Get Balance Failed: {e}")
            return 0.0

    def execute_trade(self, signal, price):
        current_pos = self.get_position()
        current_size = 0.0
        current_side = None
        
        if current_pos:
            current_size = float(current_pos['contracts'])
            current_side = current_pos['side'] 
            
        target_side = 'buy' if signal == 1 else 'sell'
        
        if current_pos:
            if current_side == 'long' and signal == 1:
                return
            if current_side == 'short' and signal == -1:
                return
                
            logger.info(f"Closing existing {current_side} position...")
            close_side = 'sell' if current_side == 'long' else 'buy'
            try:
                # Hyperliquid requires price for market orders
                exec_price = float(price) if price is not None else None
                self.exchange.create_order(SYMBOL, 'market', close_side, abs(current_size), exec_price, params={'reduceOnly': True})
                self.trail_stop = 0.0
                self.best_price = 0.0
                time.sleep(2) 
            except Exception as e:
                logger.error(f"Close Failed: {e}")
                return

        balance = self.get_balance()
        if balance < 5: 
            logger.warning(f"Testnet Balance too low (${balance}). Go to Faucet!")
            return

        trade_value = balance * COMPOUND_RATIO * LEVERAGE
        amount = trade_value / price
        
        logger.info(f"Opening {target_side.upper()} | Bal: ${balance:.2f} | Size: {amount:.4f} BTC")
        
        try:
            # Hyperliquid requires price for market orders to calc slippage
            exec_price = float(price) if price is not None else None
            self.exchange.create_order(SYMBOL, 'market', target_side, amount, exec_price)
            self.entry_price = float(price)
            self.best_price = float(price)
            self.trail_stop = 0.0 # Will be calc'd on next tick
            logger.info("Trade Executed Successfully (Testnet).")
        except Exception as e:
            logger.error(f"Open Trade Failed: {e}")

    def run(self):
        logger.info("--- BOT INICIADO EN HYPERLIQUID TESTNET ---")
        logger.info("Esperando cierre de vela...")
        while True:
            try:
                df = self.fetch_data(limit=100) 
                if df.empty:
                    time.sleep(10)
                    continue

                df_closed = df.iloc[:-1].copy()
                current_price = df.iloc[-1]['close'] 
                
                # Calculate SuperTrend
                trend, fu, fl = self.calculate_supertrend(df_closed)
                
                # Calculate ATR for Trailing Stop
                high = df_closed['high']
                low = df_closed['low']
                close = df_closed['close']
                tr1 = high - low
                tr2 = (high - close.shift()).abs()
                tr3 = (low - close.shift()).abs()
                tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
                atr = tr.rolling(ATR_PERIOD).mean().bfill()
                current_atr = atr.iloc[-1]
                
                last_time = df_closed.iloc[-1]['timestamp']
                
                # Retrieve current position
                current_pos = self.get_position()
                
                pos_str = "FLAT"
                
                # Evaluate Trailing Stop if position exists
                if current_pos:
                    current_side = current_pos['side']
                    current_size = float(current_pos['contracts'])
                    pos_str = f"{current_side.upper()} {current_size}"
                    
                    if current_side == 'long':
                        if current_price > self.best_price:
                            self.best_price = current_price
                            self.trail_stop = max(self.trail_stop, current_price - (current_atr * TRAILING_STOP_ATR_MULT))
                        
                        if current_price <= self.trail_stop and self.trail_stop > 0:
                            logger.info(f"TRAILING STOP HIT (long) @ {current_price:.2f} (Stop was: {self.trail_stop:.2f})")
                            self.exchange.create_order(SYMBOL, 'market', 'sell', abs(current_size), current_price, params={'reduceOnly': True})
                            self.entry_price = 0.0
                            self.trail_stop = 0.0
                            self.best_price = 0.0
                            time.sleep(CHECK_INTERVAL)
                            continue
                            
                    elif current_side == 'short':
                        if current_price < self.best_price or self.best_price == 0:
                            self.best_price = current_price
                            new_stop = current_price + (current_atr * TRAILING_STOP_ATR_MULT)
                            if self.trail_stop == 0:
                                self.trail_stop = new_stop
                            else:
                                self.trail_stop = min(self.trail_stop, new_stop)
                        
                        if current_price >= self.trail_stop and self.trail_stop > 0:
                            logger.info(f"TRAILING STOP HIT (short) @ {current_price:.2f} (Stop was: {self.trail_stop:.2f})")
                            self.exchange.create_order(SYMBOL, 'market', 'buy', abs(current_size), current_price, params={'reduceOnly': True})
                            self.entry_price = 0.0
                            self.trail_stop = 0.0
                            self.best_price = 0.0
                            time.sleep(CHECK_INTERVAL)
                            continue

                logger.info(f"Time: {last_time} | Price: {current_price:.2f} | Trend: {trend} | Pos: {pos_str} | TS: {self.trail_stop:.2f}")

                self.execute_trade(trend, current_price)
                
                time.sleep(CHECK_INTERVAL)
                
            except Exception as e:
                logger.error(f"Loop Error: {e}")
                time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    bot = SuperTrendBotTestnet()
    bot.run()
