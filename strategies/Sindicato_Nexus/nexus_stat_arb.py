import time
import json
import logging
import redis
import argparse
import pandas as pd
import numpy as np
import ccxt
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - ⚖️ STAT-ARB PM - %(message)s',
    handlers=[logging.StreamHandler(), logging.FileHandler("nexus_statarb.log")]
)
logger = logging.getLogger("StatArbPM")


class StatArbAgent:
    """
    Agente Quant de Arbitraje Estadístico (Pairs Trading).
    Opera Market Neutral. Busca cointegración BTC vs ETH.
    Si el Spread se desvía de la media (Z-Score > 2), vende el caro y compra el barato.
    """
    def __init__(self, asset_1='BTC', asset_2='ETH', testnet=True, nexus_mode=True):
        self.asset_1 = asset_1
        self.asset_2 = asset_2
        self.symbol_1 = f"{self.asset_1}/USDC:USDC"
        self.symbol_2 = f"{self.asset_2}/USDC:USDC"
        
        self.agent_id = "statarb"
        self.testnet = testnet
        self.nexus_mode = nexus_mode
        self.lookback_period = 100 # Periodos para la media movil del Spread
        self.z_score_threshold = 2.0 # Gatillo de entrada
        self.exit_z_score = 0.5 # Gatillo de salida (Toma de ganancia hacia la media)
        
        # Conexión Redis Sindicato
        if self.nexus_mode:
            self.r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
            logger.info(f"🔗 MODO NEXUS ACTIVADO. Monitoreando Cointegración {self.asset_1} vs {self.asset_2}.")
            
        self.wallet_address = os.getenv('WALLET_ADDRESS')
        self.private_key = os.getenv('PRIVATE_KEY')
        self.exchange = self._init_exchange()
        
        # State (Doble Posicionamiento)
        self.in_position = False
        self.long_asset = None # Que cripto estamos en LONG
        self.short_asset = None # Que cripto estamos en SHORT
        self.entry_spread = 0.0

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

    def fetch_pair_data(self):
        """Descarga velas de 5m de ambos activos para calcular el Spread."""
        try:
            ohlcv1 = self.exchange.fetch_ohlcv(self.symbol_1, '5m', limit=self.lookback_period + 50)
            df1 = pd.DataFrame(ohlcv1, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            ohlcv2 = self.exchange.fetch_ohlcv(self.symbol_2, '5m', limit=self.lookback_period + 50)
            df2 = pd.DataFrame(ohlcv2, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            df = pd.DataFrame()
            df['px1'] = df1['close'].astype(float)
            df['px2'] = df2['close'].astype(float)
            
            # Cálculo del Spread Matemático y Z-Score
            # Normalizamos ambos precios tomando logaritmo para comparar manzanas con manzanas
            df['log_px1'] = np.log(df['px1'])
            df['log_px2'] = np.log(df['px2'])
            
            df['spread'] = df['log_px1'] - df['log_px2']
            
            df['spread_mean'] = df['spread'].rolling(window=self.lookback_period).mean()
            df['spread_std'] = df['spread'].rolling(window=self.lookback_period).std()
            
            df['z_score'] = (df['spread'] - df['spread_mean']) / df['spread_std']
            
            return df
        except Exception as e:
            logger.error(f"Error descargando datos del par: {e}")
            return pd.DataFrame()

    def transmit_order(self, action, asset, price, close=False, pnl=None):
        if not self.nexus_mode: return
        try:
            msg = {
                "agent_id": self.agent_id,
                "action": "close" if close else action,
                "asset": asset,
                "amount": 0.0, # CEO decide
                "price": price
            }
            if close:
                 msg["close_side"] = "sell" if action == "buy" else "buy"
                 
            self.r.publish('nexus_orders', json.dumps(msg))
            
            if pnl is not None:
                pnl_msg = {
                    "agent_id": self.agent_id,
                    "pnl_pct": pnl
                }
                self.r.publish('nexus_pnl', json.dumps(pnl_msg))
                
        except Exception as e:
             logger.error(f"Error Redis: {e}")

    def run(self):
        logger.info(f"--- QUANT ÁRBITRO ({self.asset_1}-{self.asset_2}) INICIADO ---")
        
        while True:
            try:
                df = self.fetch_pair_data()
                if df.empty or len(df) < self.lookback_period:
                    time.sleep(10)
                    continue
                
                current = df.iloc[-1]
                z_score = current['z_score']
                px1 = current['px1']
                px2 = current['px2']
                
                logger.info(f"Spread Z-Score: {z_score:.2f} | {self.asset_1}: {px1:.1f} | {self.asset_2}: {px2:.1f}")
                
                # LA MAGIA DEL PAIRS TRADING (Market Neutral)
                
                if not self.in_position:
                    # El Spread es muy positivo (Ej: BTC subió muy rápido sin ETH)
                    if z_score > self.z_score_threshold:
                        logger.warning(f"🚨 Anomalía Alta (Z={z_score:.2f}). {self.asset_1} sobrevalorado vs {self.asset_2}.")
                        logger.info(f"Iniciando Arbitraje: SHORT {self.asset_1} / LONG {self.asset_2}")
                        
                        self.transmit_order("sell", self.asset_1, px1)
                        self.transmit_order("buy", self.asset_2, px2)
                        
                        self.in_position = True
                        self.long_asset = self.asset_2
                        self.short_asset = self.asset_1
                        self.entry_spread = z_score
                        
                        time.sleep(30) # Anti-Spam
                        
                    # El Spread es muy negativo (Ej: ETH subió muy rápido sin BTC)
                    elif z_score < -self.z_score_threshold:
                        logger.warning(f"🚨 Anomalía Baja (Z={z_score:.2f}). {self.asset_2} sobrevalorado vs {self.asset_1}.")
                        logger.info(f"Iniciando Arbitraje: LONG {self.asset_1} / SHORT {self.asset_2}")
                        
                        self.transmit_order("buy", self.asset_1, px1)
                        self.transmit_order("sell", self.asset_2, px2)
                        
                        self.in_position = True
                        self.long_asset = self.asset_1
                        self.short_asset = self.asset_2
                        self.entry_spread = z_score
                        
                        time.sleep(30) # Anti-Spam
                        
                else:
                    # GESTIÓN DE SALIDA (Reversión a la Media Lograda)
                    # Si entramos por Spread Alto (Z > 2), salimos cuando Z baje a 0.5
                    if self.entry_spread > 0 and z_score <= self.exit_z_score:
                        logger.info(f"✅ Equilibrio Restaurado (Z={z_score:.2f}). Cerrando patas del Arbitraje. Tomando Ganancias.")
                        # Estábamos Short Asset 1, Long Asset 2
                        self.transmit_order("buy", self.asset_1, px1, close=True, pnl=1.0)
                        self.transmit_order("sell", self.asset_2, px2, close=True)
                        self.in_position = False
                        time.sleep(30)
                        
                    # Si entramos por Spread Bajo (Z < -2), salimos cuando Z suba a -0.5
                    elif self.entry_spread < 0 and z_score >= -self.exit_z_score:
                        logger.info(f"✅ Equilibrio Restaurado (Z={z_score:.2f}). Cerrando patas del Arbitraje. Tomando Ganancias.")
                        # Estábamos Long Asset 1, Short Asset 2
                        self.transmit_order("sell", self.asset_1, px1, close=True, pnl=1.0)
                        self.transmit_order("buy", self.asset_2, px2, close=True)
                        self.in_position = False
                        time.sleep(30)
                        
                    # Cortar pérdidas (La cointegración se rompió definitivamente, Z-Score voló a > 4)
                    elif abs(z_score) > self.z_score_threshold * 2:
                        logger.error(f"💥 Ruptura del Modelo (Z={z_score:.2f}). Cortando pérdidas del arbitraje de emergencia.")
                        if self.long_asset == self.asset_1:
                            self.transmit_order("sell", self.asset_1, px1, close=True, pnl=-2.0)
                            self.transmit_order("buy", self.asset_2, px2, close=True)
                        else:
                            self.transmit_order("buy", self.asset_1, px1, close=True, pnl=-2.0)
                            self.transmit_order("sell", self.asset_2, px2, close=True)
                        self.in_position = False
                        time.sleep(180) # Esperar a que el mercado loco pase
                
                time.sleep(15) 
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Error: {e}")
                time.sleep(15)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Nexus Stat-Arb PM")
    parser.add_argument('--live', action='store_true', help='Desactivar testnet local API (usar MAINNET URLs)')
    args = parser.parse_args()
    
    bot = StatArbAgent(testnet=not args.live, nexus_mode=True)
    bot.run()
