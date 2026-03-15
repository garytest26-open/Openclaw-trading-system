import ccxt
import pandas as pd
import numpy as np
import time
import os
import argparse
import logging
from dotenv import load_dotenv

from quantum_edge_strategy import (
    QuantumConfig, MarketRegime, RegimeDetector, AdaptiveRiskManager,
    precompute_all_signals, calc_atr
)

# Load Environment Variables
load_dotenv()

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("quantum_edge_live.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("QuantumEdgeBot")

class QuantumEdgeLiveBot:
    def __init__(self, ticker: str, network: str):
        self.ticker = ticker
        self.symbol = f"{ticker.split('-')[0]}/USDC:USDC"  # Hyperliquid format
        self.network = network

        self.wallet_address = os.getenv('WALLET_ADDRESS')
        self.private_key = os.getenv('PRIVATE_KEY')
        
        if not self.wallet_address or not self.private_key:
            logger.error("Missing WALLET_ADDRESS or PRIVATE_KEY in .env")
            raise ValueError("Credentials missing")

        self.exchange = self._init_exchange()
        
        # Strategy Config & Components
        self.config = QuantumConfig(ticker=ticker, interval="1h")
        self.regime_detector = RegimeDetector(self.config)
        self.risk_manager = AdaptiveRiskManager(self.config)
        
        # Internals
        self.check_interval = 60  # seconds
        self.leverage = 1
        
        # Posición local trackeada para TP/SL simulados via Market Orders
        self.local_position = None

    def _init_exchange(self):
        try:
            if hasattr(ccxt, 'hyperliquid'):
                exchange_class = getattr(ccxt, 'hyperliquid')
            elif 'hyperliquid' in ccxt.exchanges:
                exchange_class = getattr(ccxt, 'hyperliquid')
            else:
                raise ImportError("Hyperliquid not supported in this CCXT version.")

            exchange = exchange_class({
                'walletAddress': self.wallet_address,
                'privateKey': self.private_key,
                'enableRateLimit': True,
                'options': {'defaultType': 'swap'}, 
            })
            
            if self.network == 'testnet':
                exchange.set_sandbox_mode(True)
                logger.info("Connected to Hyperliquid TESTNET")
            else:
                logger.warning("Connected to Hyperliquid MAINNET (LIVE FUNDS!)")
                
            return exchange
        except Exception as e:
            logger.error(f"Exchange Init Failed: {e}")
            raise

    def fetch_data(self, limit=1000):
        try:
            ohlcv = self.exchange.fetch_ohlcv(self.symbol, self.config.interval, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception as e:
            logger.error(f"Fetch Data Failed: {e}")
            return pd.DataFrame()

    def get_position(self):
        try:
            positions = self.exchange.fetch_positions([self.symbol])
            if positions:
                for pos in positions:
                    if pos['symbol'] == self.symbol and float(pos['contracts']) != 0:
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

    def close_position(self, current_pos, current_price, reason="signal_reversal"):
        if current_pos is None:
            return
            
        current_size = float(current_pos['contracts'])
        current_side = current_pos['side']
        close_side = 'sell' if current_side == 'long' else 'buy'
        
        logger.info(f"Closing existing {current_side} position ({reason})...")
        try:
            self.exchange.create_order(self.symbol, 'market', close_side, abs(current_size), current_price, params={'reduceOnly': True})
            time.sleep(2)
            
            # Record local trade
            if self.local_position:
                pnl = 0.0
                if current_side == 'long':
                    pnl = (current_price - self.local_position['entry']) / self.local_position['entry']
                else:
                    pnl = (self.local_position['entry'] - current_price) / self.local_position['entry']
                
                self.risk_manager.record_trade({'pnl_pct': pnl})
                self.local_position = None
                
        except Exception as e:
            logger.error(f"Close Failed: {e}")

    def execute_trade(self, action, current_price, df_hist):
        current_pos = self.get_position()
        current_side = current_pos['side'] if current_pos else None
        target_side = 'buy' if action == 'long' else 'sell'
        
        # 1. Close if wrong direction
        if current_pos:
            if current_side == action:
                logger.info(f"Already {action}. Holding.")
                return
            else:
                self.close_position(current_pos, current_price, "signal_reversal")

        # 2. Open New
        balance = self.get_balance()
        if balance < 10:
            logger.warning(f"Balance too low (${balance}).")
            return

        # Sizing using AdaptiveRiskManager
        high = np.asarray(df_hist['high'], dtype=float).ravel()
        low = np.asarray(df_hist['low'], dtype=float).ravel()
        close = np.asarray(df_hist['close'], dtype=float).ravel()
        
        atr_arr = calc_atr(high, low, close)
        current_atr = atr_arr[-1] if not np.isnan(atr_arr[-1]) else current_price * 0.02
        
        # For execution we assume typical regime or re-fit online
        # Fast approach: assume NORMAL regime for sizing
        regime = MarketRegime.BULL_TREND if action == 'long' else MarketRegime.BEAR_TREND
        usd_size = self.risk_manager.get_position_size(balance, current_price, current_atr, regime)
        
        # Hyperliquid constraints (minimums apply but we delegate to exchange)
        amount = (usd_size * self.leverage) / current_price
        
        logger.info(f"Signal: {action.upper()} | ATR: {current_atr:.2f} | Risk Sizing: {amount:.4f} {self.ticker}")
        
        if amount <= 0:
            logger.warning("Calculated size is 0. Aborting trade.")
            return

        try:
            self.exchange.create_order(self.symbol, 'market', target_side, amount, current_price)
            logger.info("Trade Executed.")
            
            # Setup TP/SL tracking
            sl_dist = current_atr * 2.0
            tp_dist = current_atr * 5.0
            
            if action == 'long':
                sl = current_price - sl_dist
                tp = current_price + tp_dist
            else:
                sl = current_price + sl_dist
                tp = current_price - tp_dist
                
            self.local_position = {
                'side': action,
                'entry': current_price,
                'sl': sl,
                'tp': tp
            }
            logger.info(f"Targets Set -> SL: {sl:.2f}, TP: {tp:.2f}")
            
        except Exception as e:
            logger.error(f"Open Trade Failed: {e}")

    def run(self):
        logger.info(f"Starting Quantum Edge Live on {self.ticker}")
        logger.info("Waiting for data / next cycles...")
        
        while True:
            try:
                df = self.fetch_data(limit=1000)
                if df.empty or len(df) < 500: # Need enough for signals
                    time.sleep(10)
                    continue
                
                # Check Local TP/SL if in position
                current_price = df.iloc[-1]['close']
                current_high = df.iloc[-1]['high']
                current_low = df.iloc[-1]['low']
                current_pos = self.get_position()
                
                if current_pos and self.local_position:
                    side = self.local_position['side']
                    # Long TP/SL
                    if side == 'long':
                        if current_high >= self.local_position['tp']:
                            self.close_position(current_pos, self.local_position['tp'], "Take Profit")
                            continue
                        elif current_low <= self.local_position['sl']:
                            self.close_position(current_pos, self.local_position['sl'], "Stop Loss")
                            continue
                    # Short TP/SL
                    else:
                        if current_low <= self.local_position['tp']:
                            self.close_position(current_pos, self.local_position['tp'], "Take Profit")
                            continue
                        elif current_high >= self.local_position['sl']:
                            self.close_position(current_pos, self.local_position['sl'], "Stop Loss")
                            continue
                elif not current_pos:
                    self.local_position = None # Reset if manually closed
                
                # Strategy Signals Calculation (on CLOSED candles)
                df_closed = df.iloc[:-1].copy()
                n = len(df_closed)
                
                signals = precompute_all_signals(
                    df_closed['high'].values,
                    df_closed['low'].values,
                    df_closed['close'].values,
                    df_closed['volume'].values,
                    self.config
                )
                
                ls = signals['long_score']
                ss = signals['short_score']
                
                # Crossover logic
                last_ls = int(ls[-1])
                prev_ls = int(ls[-2])
                last_ss = int(ss[-1])
                prev_ss = int(ss[-2])
                
                logger.debug(f"{df_closed.iloc[-1]['timestamp']} -> L_Score: {last_ls} | S_Score: {last_ss}")
                
                action = None
                thresh = self.config.confluence_threshold
                
                if last_ls >= thresh and last_ls > last_ss and prev_ls < thresh:
                    action = 'long'
                elif last_ss >= thresh and last_ss > last_ls and prev_ss < thresh:
                    action = 'short'

                if action is not None:
                    logger.info(f"⚡ CROSSOVER SIGNAL TRIGGERED: {action.upper()}")
                    self.execute_trade(action, current_price, df_closed)
                
                time.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Loop Error: {e}", exc_info=True)
                time.sleep(self.check_interval)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--ticker', type=str, required=True, help="Ticker (e.g. SOL-USD)")
    parser.add_argument('--network', type=str, choices=['mainnet', 'testnet'], default='testnet')
    args = parser.parse_args()
    
    bot = QuantumEdgeLiveBot(args.ticker, args.network)
    bot.run()
