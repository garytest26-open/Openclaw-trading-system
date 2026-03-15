import time
import json
import logging
import redis
import argparse
import pandas as pd
import ccxt
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - 🎯 MEAN REVERSION PM - %(message)s',
    handlers=[logging.StreamHandler(), logging.FileHandler("nexus_sniper.log")]
)
logger = logging.getLogger("SniperPM")


class SniperMeanReversion:
    """
    Agente especialista del Sindicato (Portfolio Manager).
    Opera ÚNICAMENTE en mercados de rango utilizando RSI extremo y Bandas de Bollinger.
    """
    def __init__(self, asset='ETH', testnet=True, nexus_mode=True):
        self.asset = asset.upper()
        self.symbol = f"{self.asset}/USDC:USDC"
        self.agent_id = "sniper"
        self.testnet = testnet
        self.nexus_mode = nexus_mode
        
        # Conexión Redis Sindicato
        if self.nexus_mode:
            self.r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
            logger.info(f"🔗 MODO NEXUS ACTIVADO. Cuidando el activo {self.asset}.")
            
        # Exchange CCXT Data Provider
        self.wallet_address = os.getenv('WALLET_ADDRESS')
        self.private_key = os.getenv('PRIVATE_KEY')
        self.exchange = self._init_exchange()
        
        # State
        self.in_position = False
        self.position_side = None
        self.entry_price = 0.0

    def _init_exchange(self):
        try:
            exchange_class = getattr(ccxt, 'hyperliquid')
            exchange = exchange_class({
                'walletAddress': self.wallet_address,
                'privateKey': self.private_key,
                'enableRateLimit': True,
                'options': {'defaultType': 'swap'},
            })
            if self.testnet:
                exchange.set_sandbox_mode(True)
            return exchange
        except Exception as e:
            logger.error(f"Exchange Init Failed: {e}")
            raise

    def fetch_data(self):
        """Fetch 15-minute candles to scalp local ranges"""
        try:
            ohlcv = self.exchange.fetch_ohlcv(self.symbol, '15m', limit=100)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['close'] = df['close'].astype(float)
            
            # Calcular Bollinger Bands (Period: 20, Std: 2)
            sma = df['close'].rolling(20).mean()
            std = df['close'].rolling(20).std()
            df['upper_band'] = sma + (2 * std)
            df['lower_band'] = sma - (2 * std)
            
            # Calcular RSI (14)
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            df['rsi'] = 100 - (100 / (1 + rs))
            
            return df
        except Exception as e:
            logger.error(f"Error descargando datos: {e}")
            return pd.DataFrame()

    def virtual_get_position(self):
        """Revisa su posicionamiento real en el mercado consultando el Exchange."""
        try:
            positions = self.exchange.fetch_positions([self.symbol])
            if positions:
                for pos in positions:
                    if pos['symbol'] == self.symbol and float(pos['contracts']) != 0:
                        return pos
            return None
        except:
             return None

    def analyze_orderbook(self):
        """
        Calcula el desbalance (Imbalance) del Orderbook L2 (Bid vs Ask)
        para validar si hay una 'Ballena' protegiendo el suelo o techo.
        """
        try:
            # Traer solo los 20 niveles más cercanos al Market Price
            ob = self.exchange.fetch_order_book(self.symbol, limit=20)
            bids = ob['bids']
            asks = ob['asks']
            
            # Sumar la liquidez total (size/amount) disponible
            bid_vol = sum([amount for price, amount in bids])
            ask_vol = sum([amount for price, amount in asks])
            
            if ask_vol == 0: ask_vol = 1
            if bid_vol == 0: bid_vol = 1
            
            imbalance_ratio = bid_vol / ask_vol
            
            return imbalance_ratio, bid_vol, ask_vol
            
        except Exception as e:
            logger.error(f"Error leyendo Orderbook Nivel 2: {e}")
            return 1.0, 0, 0

    def close_position(self, current_price, size, close_side, entry_price, side):
        # Calcular PNL Pct
        pnl_pct = 0.0
        if entry_price > 0:
             pnl_pct = ((current_price - entry_price) / entry_price) * 100.0 if side == 'long' else ((entry_price - current_price) / entry_price) * 100.0
        
        if self.nexus_mode:
            msg = {
                "agent_id": self.agent_id,
                "action": "close",
                "asset": self.asset,
                "amount": size,
                "price": current_price,
                "close_side": close_side
            }
            self.r.publish('nexus_orders', json.dumps(msg))
            
            pnl_msg = {
                "agent_id": self.agent_id,
                "pnl_pct": pnl_pct
            }
            self.r.publish('nexus_pnl', json.dumps(pnl_msg))
            logger.info(f"📡 NEXUS: Señal de Cierre enviada al CEO. Reportando PNL a la mesa central: {pnl_pct:.2f}%")
        
        self.in_position = False
        self.entry_price = 0.0
        self.position_side = None

    def run(self):
        logger.info(f"--- FRANCOTIRADOR DE RANGOS LATERALES ({self.asset}) INICIADO ---")
        
        while True:
            try:
                df = self.fetch_data()
                if df.empty:
                    time.sleep(10)
                    continue
                
                # Trabajamos con vela cerrada
                current = df.iloc[-2]
                current_price = df.iloc[-1]['close'] # Live price
                
                pos = self.virtual_get_position()
                
                if pos:
                    size = abs(float(pos['contracts']))
                    side = pos['side']
                    entry_price = float(pos.get('entryPrice', self.entry_price))
                    self.in_position = True
                    self.position_side = side
                    self.entry_price = entry_price
                    
                    pnl_pct = ((current_price - entry_price) / entry_price) * 100.0 if side == 'long' else ((entry_price - current_price) / entry_price) * 100.0
                    
                    logger.info(f"Posición activa: {side.upper()} | PNL Virtual: {pnl_pct:.2f}% | Price: {current_price:.2f}")
                    
                    # LOGICA DE SALIDA (Reversión a la media)
                    # Tomar ganancias a la media, o cortar pérdida rápido
                    if side == 'long' and (current_price >= current['upper_band'] or pnl_pct > 1.0 or pnl_pct < -1.0):
                        self.close_position(current_price, size, 'sell', entry_price, side)
                        
                    elif side == 'short' and (current_price <= current['lower_band'] or pnl_pct > 1.0 or pnl_pct < -1.0):
                         self.close_position(current_price, size, 'buy', entry_price, side)
                        
                else:
                    self.in_position = False
                    
                    # LOGICA DE ENTRADA CONTRARIAN
                    # RSI Extremo + Toque de Bandas de Bollinger => Regresión a la Media
                    rsi = current['rsi']
                    lower_band = current['lower_band']
                    upper_band = current['upper_band']
                    
                    is_oversold = rsi < 30 and current['close'] < lower_band
                    is_overbought = rsi > 70 and current['close'] > upper_band
                    
                    logger.info(f"Buscando Rangos... Precio: {current_price:.2f} | RSI: {rsi:.1f} | B-Lower: {lower_band:.2f} | B-Upper: {upper_band:.2f}")
                    
                    if is_oversold:
                        logger.info("🔪 Pánico de mercado detectado (Oversold). Analizando L2...")
                        imbalance, bid_v, ask_v = self.analyze_orderbook()
                        
                        if imbalance >= 1.5:
                            logger.info(f"🐋 MURO DE COMPRAS CONFIRMADO (Ratio Bid/Ask: {imbalance:.2f}). Comprando soporte.")
                            if self.nexus_mode:
                                msg = {
                                    "agent_id": self.agent_id,
                                    "action": "buy",
                                    "asset": self.asset,
                                    "amount": 0.0, # El CEO decide el capital allocation
                                    "price": float(current_price)
                                }
                                self.r.publish('nexus_orders', json.dumps(msg))
                        else:
                            logger.warning(f"⚠️ FALSO SUELO Omitido. Cuchillo cayendo sin soporte ballena (Ratio: {imbalance:.2f}).")
                            
                        time.sleep(60) # Anti-Spam
                        
                    elif is_overbought:
                        logger.info("🎈 Sobre-euforia detectada (Overbought). Analizando L2...")
                        imbalance, bid_v, ask_v = self.analyze_orderbook()
                        
                        if imbalance <= 0.66: # Ask volume is > 1.5x Bid volume
                            logger.info(f"🐋 MURO DE VENTAS CONFIRMADO (Ratio Bid/Ask: {imbalance:.2f}). Acortando cima.")
                            if self.nexus_mode:
                                msg = {
                                    "agent_id": self.agent_id,
                                    "action": "sell",
                                    "asset": self.asset,
                                    "amount": 0.0,
                                    "price": float(current_price)
                                }
                                self.r.publish('nexus_orders', json.dumps(msg))
                        else:
                            logger.warning(f"⚠️ FALSO TECHO Omitido. Fuerte interés de compra empujando (Ratio: {imbalance:.2f}).")
                            
                        time.sleep(60) # Anti-Spam
                        
                time.sleep(15) 
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Error: {e}")
                time.sleep(15)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Nexus Sniper PM")
    parser.add_argument('--asset', type=str, default='ETH', help='Activo a operar (default: ETH)')
    parser.add_argument('--live', action='store_true', help='Desactivar testnet local API (usar MAINNET URLs)')
    args = parser.parse_args()
    
    bot = SniperMeanReversion(asset=args.asset, testnet=not args.live, nexus_mode=True)
    bot.run()
