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
SYMBOL = 'BTC/USDC:USDC'  # Hyperliquid uses USDC collateral
TIMEFRAME = '1h'
ATR_PERIOD = 10
ATR_MULTIPLIER = 5.0
CHECK_INTERVAL = 60       # Check every 60 seconds
COMPOUND_RATIO = 0.95     # Use 95% of available balance per trade (Compound Interest)
LEVERAGE = 1              # Default Leverage

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("btc_supertrend_live.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("SuperTrendBot")

class SuperTrendBot:
    def __init__(self):
        self.wallet_address = os.getenv('WALLET_ADDRESS')
        self.private_key = os.getenv('PRIVATE_KEY')
        
        if not self.wallet_address or not self.private_key:
            logger.error("Missing WALLET_ADDRESS or PRIVATE_KEY in .env")
            raise ValueError("Credentials missing")

        self.exchange = self._init_exchange()
        self.position = None # Current position state
        
    def _init_exchange(self):
        try:
            # Robust way to access exchange class
            if hasattr(ccxt, 'hyperliquid'):
                exchange_class = getattr(ccxt, 'hyperliquid')
            else:
                if 'hyperliquid' in ccxt.exchanges:
                    exchange_class = getattr(ccxt, 'hyperliquid')
                else:
                    raise ImportError("Hyperliquid not supported in this CCXT version.")

            exchange = exchange_class({
                'walletAddress': self.wallet_address,
                'privateKey': self.private_key,
                'enableRateLimit': True,
                'options': {'defaultType': 'swap'}, # Perpetual Swaps
            })
            # exchange.set_sandbox_mode(True) # Uncomment for Testnet
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
        # Using bfill to match our backtest fix
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
        # signal: 1 (Long), -1 (Short)
        
        # 1. Check Current Position
        current_pos = self.get_position()
        current_size = 0.0
        current_side = None
        
        if current_pos:
            current_size = float(current_pos['contracts'])
            current_side = current_pos['side'] # 'long' or 'short'
            
        # 2. Logic
        # Target: Be Long if Signal 1, Be Short if Signal -1
        
        target_side = 'buy' if signal == 1 else 'sell'
        
        # If already correctly positioned, do nothing (Stay "Always In")
        if current_pos:
            is_long = (current_size > 0) # Hyperliquid returns signed size often or side field
            # Check 'side' field explicitly from ccxt
            if current_side == 'long' and signal == 1:
                logger.info("Already Long. Holding.")
                return
            if current_side == 'short' and signal == -1:
                logger.info("Already Short. Holding.")
                return
                
            # If wrong side, Close First
            logger.info(f"Closing existing {current_side} position...")
            close_side = 'sell' if current_side == 'long' else 'buy'
            try:
                # Hyperliquid requires price for market orders
                self.exchange.create_order(SYMBOL, 'market', close_side, abs(current_size), price, params={'reduceOnly': True})
                time.sleep(2) # Wait for fill
            except Exception as e:
                logger.error(f"Close Failed: {e}")
                return

        # 3. Open New Position (Compound Interest)
        balance = self.get_balance()
        if balance < 5: # Min trade size check
            logger.warning(f"Balance too low (${balance}). Waiting.")
            return

        # Calculate Size
        # Value to trade = Balance * Ratio * Leverage
        trade_value = balance * COMPOUND_RATIO * LEVERAGE
        amount = trade_value / price
        
        logger.info(f"Opening {target_side.upper()} | Bal: ${balance:.2f} | Size: {amount:.4f} BTC")
        
        try:
            # Hyperliquid requires price for market orders to calc slippage
            self.exchange.create_order(SYMBOL, 'market', target_side, amount, price)
            logger.info("Trade Executed Successfully.")
        except Exception as e:
            logger.error(f"Open Trade Failed: {e}")

    def run(self):
        logger.info("Bot Started. Waiting for next candle close...")
        while True:
            try:
                # Sync logic: Ensure candle closed?
                # Actually SuperTrend can repaint if using current close price. 
                # Better to use Last Completed Candle [-2] for signal? 
                # Or wait until minute 00 of hour?
                # The script calculates on limit=100. calculate_supertrend uses all checks.
                # Standard practice: Check signal on COMPLETED candle [-2] to avoid repaint.
                # However, our backtest uses [-1] (Close) implying verification at Close time.
                # For live: Use last closed candle [-2] to be safe.
                
                df = self.fetch_data(limit=50) # enough for ATR period
                if df.empty:
                    time.sleep(10)
                    continue

                # IMPORTANT: Use [-2] (last fully closed candle) for signal confirmation
                # DataFrame: ... [Index -2: Closed 1h ago], [Index -1: Open/Current]
                
                # Slicing to exclude current open candle for calculation
                df_closed = df.iloc[:-1].copy()
                
                # Current Price (Realtime for execution)
                current_price = df.iloc[-1]['close'] 
                
                # Calculate Trend on CLOSED history
                trend, fu, fl = self.calculate_supertrend(df_closed)
                
                last_time = df_closed.iloc[-1]['timestamp']
                logger.info(f"Time: {last_time} | Price: {current_price:.2f} | Trend: {trend} (1=Bull, -1=Bear)")
                
                # Execute Logic
                self.execute_trade(trend, current_price) # Logic handles "Already In"
                
                # Sleep
                time.sleep(CHECK_INTERVAL)
                
            except Exception as e:
                logger.error(f"Loop Error: {e}")
                time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    bot = SuperTrendBot()
    bot.run()
