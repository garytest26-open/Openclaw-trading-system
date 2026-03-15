"""
VIPER STRIKE BOT - Hyperliquid TESTNET
Volatility Squeeze + Market Structure + Pyramiding

Soporta BTC y ETH con parametros optimizados independientes.
Usa .env para credenciales (WALLET_ADDRESS, PRIVATE_KEY).
"""
import ccxt
import pandas as pd
import numpy as np
import time
import os
import logging
import argparse
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ─── CONFIGURACION POR ACTIVO ───
CONFIGS = {
    'BTC': {
        'symbol': 'BTC/USDC:USDC',
        'bb_period': 15,
        'bb_std': 1.5,
        'kc_period': 15,
        'kc_atr_mult': 1.5,
        'adx_period': 14,
        'adx_threshold': 15,
        'pivot_len': 7,
        'mom_period': 10,
        'atr_period': 10,
        'trail_atr_mult': 2.0,
    },
    'ETH': {
        'symbol': 'ETH/USDC:USDC',
        'bb_period': 20,
        'bb_std': 1.5,
        'kc_period': 20,
        'kc_atr_mult': 2.0,
        'adx_period': 14,
        'adx_threshold': 15,
        'pivot_len': 5,
        'mom_period': 10,
        'atr_period': 10,
        'trail_atr_mult': 2.0,
    },
    'SOL': {
        'symbol': 'SOL/USDC:USDC',
        'bb_period': 15,
        'bb_std': 1.5,
        'kc_period': 15,
        'kc_atr_mult': 2.0,
        'adx_period': 10,
        'adx_threshold': 15,
        'pivot_len': 5,
        'mom_period': 10,
        'atr_period': 10,
        'trail_atr_mult': 2.5,
    },
}

TIMEFRAME = '1h'
CHECK_INTERVAL = 60        # segundos entre checks
COMPOUND_RATIO = 0.90      # % del balance a usar
LEVERAGE = 1
BASE_SIZE_PCT = 0.30       # 30% del capital como posicion base
PYRAMID_2_THRESHOLD = 1.0  # ATR de profit para nivel 2
PYRAMID_3_THRESHOLD = 2.0  # ATR de profit para nivel 3


# ─── INDICADORES ───

def calc_atr(high, low, close, period):
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def calc_bollinger(close, period, std_mult):
    sma = close.rolling(period).mean()
    std = close.rolling(period).std()
    return sma + (std * std_mult), sma, sma - (std * std_mult)


def calc_keltner(high, low, close, period, atr_mult):
    ema = close.ewm(span=period, adjust=False).mean()
    atr = calc_atr(high, low, close, period)
    return ema + (atr * atr_mult), ema, ema - (atr * atr_mult)


def calc_adx(high, low, close, period):
    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)
    
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    atr = tr.rolling(period).mean()
    plus_di = 100 * (plus_dm.rolling(period).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(period).mean() / atr)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    adx = dx.rolling(period).mean()
    return adx, plus_di, minus_di


def detect_squeeze(high, low, close, cfg):
    bb_upper, _, bb_lower = calc_bollinger(close, cfg['bb_period'], cfg['bb_std'])
    kc_upper, _, kc_lower = calc_keltner(high, low, close, cfg['kc_period'], cfg['kc_atr_mult'])
    in_squeeze = ((bb_lower > kc_lower) & (bb_upper < kc_upper)).astype(int)
    squeeze_release = ((in_squeeze.shift(1) == 1) & (in_squeeze == 0)).astype(int)
    return in_squeeze, squeeze_release


def detect_structure(high, low, pivot_len):
    pivot_high = high.rolling(window=2*pivot_len+1, center=True).max()
    pivot_low = low.rolling(window=2*pivot_len+1, center=True).min()
    is_ph = (high == pivot_high)
    is_pl = (low == pivot_low)
    
    structure = pd.Series(0.0, index=high.index)
    last_ph = prev_ph = last_pl = prev_pl = np.nan
    
    for i in range(len(high)):
        if is_ph.iloc[i]:
            prev_ph, last_ph = last_ph, high.iloc[i]
        if is_pl.iloc[i]:
            prev_pl, last_pl = last_pl, low.iloc[i]
        
        if not np.isnan(prev_ph) and not np.isnan(prev_pl):
            hh = last_ph > prev_ph
            hl = last_pl > prev_pl
            lh = last_ph < prev_ph
            ll = last_pl < prev_pl
            
            if hh and hl: structure.iloc[i] = 1
            elif lh and ll: structure.iloc[i] = -1
            elif hh or hl: structure.iloc[i] = 0.5
            elif lh or ll: structure.iloc[i] = -0.5
    
    return structure


def calc_momentum(close, period):
    mom = (close - close.shift(period)).rolling(3).mean()
    direction = pd.Series(0.0, index=close.index)
    direction[mom > 0] = 1
    direction[mom < 0] = -1
    return direction


# ─── BOT PRINCIPAL ───

class ViperStrikeBot:
    def __init__(self, asset='ETH', testnet=True, nexus_mode=False):
        self.asset = asset.upper()
        self.testnet = testnet
        self.nexus_mode = nexus_mode
        self.cfg = CONFIGS[self.asset]
        self.symbol = self.cfg['symbol']
        
        if self.nexus_mode:
            import redis
            import json
            self.r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        
        # Estado de pyramiding
        self.pyramid_level = 0
        self.entry_price = 0
        self.trail_stop = 0
        self.best_price = 0
        self.position_side = None  # 'long' o 'short'
        
        # Machine Learning Model (Edge 1)
        self.ml_model = None
        if self.asset == 'BTC':
            model_path = os.path.join(os.path.dirname(__file__), 'models', 'viper_ml_filter.txt')
            if os.path.exists(model_path):
                try:
                    import lightgbm as lgb
                    self.ml_model = lgb.Booster(model_file=model_path)
                    self.logger.info(f"🧠 Módulo LightGBM Anti-Trampas Activado (Edge = ON). File: {model_path}")
                except Exception as e:
                    self.logger.error(f"Error cargando ML model: {e}")
        
        # Credenciales
        self.wallet_address = os.getenv('WALLET_ADDRESS')
        self.private_key = os.getenv('PRIVATE_KEY')
        if not self.wallet_address or not self.private_key:
            raise ValueError("Faltan WALLET_ADDRESS o PRIVATE_KEY en .env")
        
        # Logger
        mode_str = "TESTNET" if testnet else "LIVE"
        log_file = f"viper_{self.asset.lower()}_{mode_str.lower()}.log"
        logging.basicConfig(
            level=logging.INFO,
            format=f'%(asctime)s - %(levelname)s - {mode_str} - %(message)s',
            handlers=[logging.FileHandler(log_file), logging.StreamHandler()]
        )
        self.logger = logging.getLogger(f"ViperStrike_{self.asset}_{mode_str}")
        
        # Exchange
        self.exchange = self._init_exchange()
    
    def _init_exchange(self):
        self.logger.info(f"CCXT Version: {ccxt.__version__}")
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
                self.logger.info("== MODO TESTNET ACTIVADO ==")
            else:
                self.logger.info("!! MODO LIVE - DINERO REAL !!")
            
            return exchange
        except Exception as e:
            self.logger.error(f"Exchange Init Failed: {e}")
            raise
    
    def fetch_data(self, limit=300):
        try:
            ohlcv = self.exchange.fetch_ohlcv(self.symbol, TIMEFRAME, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception as e:
            self.logger.error(f"Fetch Data Failed: {e}")
            return pd.DataFrame()
    
    def calculate_signals(self, df):
        """Calcula todos los indicadores Viper Strike y devuelve señales."""
        h, l, c = df['high'], df['low'], df['close']
        cfg = self.cfg
        
        # Indicadores
        atr = calc_atr(h, l, c, cfg['atr_period'])
        _, sq_release = detect_squeeze(h, l, c, cfg)
        adx, di_plus, di_minus = calc_adx(h, l, c, cfg['adx_period'])
        structure = detect_structure(h, l, cfg['pivot_len'])
        momentum = calc_momentum(c, cfg['mom_period'])
        
        # ML Features for BTC Filter
        ml_approved = True
        ml_prob = 1.0
        
        if self.asset == 'BTC' and self.ml_model:
            try:
                c_s = df['close']
                v_s = df['volume']
                
                volatility_ratio = atr.iloc[-1] / c.iloc[-1] * 100
                mom_s = c_s - c_s.shift(10)
                momentum_slope = mom_s.iloc[-1] - mom_s.iloc[-6] if len(mom_s) > 6 else 0
                
                vol_sma20 = v_s.rolling(20).mean().iloc[-1]
                volume_surge = v_s.iloc[-1] / vol_sma20 if vol_sma20 > 0 else 1
                
                sma20 = c_s.rolling(20).mean().iloc[-1]
                sma200 = c_s.rolling(200).mean().iloc[-1] if len(c_s) >= 200 else sma20
                
                close_sma20_dist = (c.iloc[-1] - sma20) / c.iloc[-1] * 100
                close_sma200_dist = (c.iloc[-1] - sma200) / c.iloc[-1] * 100
                
                delta = c_s.diff()
                gain = (delta.where(delta > 0, 0)).rolling(14).mean().iloc[-1]
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean().iloc[-1]
                rs = gain / loss if loss > 0 else 100
                rsi_14 = 100 - (100 / (1 + rs)) if loss > 0 else 100
                
                features = [[volatility_ratio, momentum_slope, volume_surge, close_sma20_dist, close_sma200_dist, rsi_14]]
                ml_prob = self.ml_model.predict(features)[0]
                ml_approved = ml_prob > 0.65
            except Exception as e:
                self.logger.error(f"Error en calculo ML: {e}")

        return {
            'atr': atr.iloc[-1],
            'sq_release': sq_release.iloc[-1],
            'sq_release_recent': any(sq_release.iloc[-i] == 1 for i in range(1, min(4, len(df)))),
            'adx': adx.iloc[-1],
            'di_plus': di_plus.iloc[-1],
            'di_minus': di_minus.iloc[-1],
            'structure': structure.iloc[-1],
            'momentum': momentum.iloc[-1],
            'ml_approved': ml_approved,
            'ml_prob': ml_prob,
        }
    
    def get_position(self):
        try:
            positions = self.exchange.fetch_positions([self.symbol])
            if positions:
                for pos in positions:
                    if pos['symbol'] == self.symbol and float(pos['contracts']) != 0:
                        return pos
            return None
        except Exception as e:
            self.logger.error(f"Get Position Failed: {e}")
            return None
    
    def get_balance(self):
        try:
            bal = self.exchange.fetch_balance()
            return float(bal['USDC']['free'])
        except Exception as e:
            self.logger.error(f"Get Balance Failed: {e}")
            return 0.0
    
    def place_order(self, side, amount, price):
        """Coloca una orden de mercado."""
        if self.nexus_mode:
            import json
            msg = {
                "agent_id": "viper",
                "action": side,
                "asset": self.asset,
                "amount": amount,
                "price": price
            }
            self.r.publish('nexus_orders', json.dumps(msg))
            self.logger.info(f"📡 NEXUS: Solicitud de {side.upper()} enviada al CEO.")
            return True
        else:
            try:
                self.exchange.create_order(self.symbol, 'market', side, amount, price)
                self.logger.info(f"Orden ejecutada: {side.upper()} {amount:.6f}")
                return True
            except Exception as e:
                self.logger.error(f"Order Failed: {e}")
                return False
    
    def close_position(self, price):
        """Cierra la posicion actual completamente."""
        pos = self.get_position()
        if not pos:
            return
        
        size = abs(float(pos['contracts']))
        side = pos['side']
        close_side = 'sell' if side == 'long' else 'buy'
        
        self.logger.info(f"Cerrando posicion {side} ({size:.6f})...")
        
        # Calcular PNL Pct para entrenar al CEO de Nexus
        entry_price = float(pos.get('entryPrice', self.entry_price))
        pnl_pct = 0.0
        if entry_price > 0:
             pnl_pct = ((price - entry_price) / entry_price) * 100.0 if side == 'long' else ((entry_price - price) / entry_price) * 100.0
        
        if self.nexus_mode:
            import json
            msg = {
                "agent_id": "viper",
                "action": "close",
                "asset": self.asset,
                "amount": size,
                "price": price,
                "close_side": close_side
            }
            self.r.publish('nexus_orders', json.dumps(msg))
            
            pnl_msg = {
                "agent_id": "viper",
                "pnl_pct": pnl_pct
            }
            self.r.publish('nexus_pnl', json.dumps(pnl_msg))
            self.logger.info(f"📡 NEXUS: Señal de cierre enviada. Reportando PNL al CEO: {pnl_pct:.2f}%")
            
            time.sleep(2)
            self.pyramid_level = 0
            self.position_side = None
            self.trail_stop = 0
            self.best_price = 0
            self.entry_price = 0
        else:
            try:
                self.exchange.create_order(self.symbol, 'market', close_side, size, price, 
                                           params={'reduceOnly': True})
                time.sleep(2)
                self.pyramid_level = 0
                self.position_side = None
                self.trail_stop = 0
                self.best_price = 0
                self.entry_price = 0
                self.logger.info("Posicion cerrada.")
            except Exception as e:
                self.logger.error(f"Close Failed: {e}")
    
    def open_position(self, side, price, size_pct=None):
        """Abre nueva posicion o añade pyramiding."""
        balance = self.get_balance()
        if balance < 5:
            self.logger.warning(f"Balance muy bajo (${balance:.2f})")
            return False
        
        if size_pct is None:
            size_pct = BASE_SIZE_PCT
        
        trade_value = balance * COMPOUND_RATIO * LEVERAGE * size_pct
        amount = trade_value / price
        
        self.logger.info(f"Abriendo {side.upper()} | Bal: ${balance:.2f} | Size: {amount:.6f} | Pct: {size_pct*100:.0f}%")
        return self.place_order(side, amount, price)
    
    def check_entry(self, signals, price):
        """Evalua condiciones de entrada Viper Strike."""
        is_release = signals['sq_release'] == 1
        recent_release = signals['sq_release_recent']
        
        if not (is_release or recent_release):
            return None
        
        adx_strong = signals['adx'] > self.cfg['adx_threshold']
        struct = signals['structure']
        mom = signals['momentum']
        di_bull = signals['di_plus'] > signals['di_minus']
        di_bear = signals['di_minus'] > signals['di_plus']
        
        # LONG
        bull = sum([struct >= 0.5, mom == 1, di_bull, adx_strong])
        if bull >= 3:
            if not signals['ml_approved']:
                self.logger.warning(f"🧠 AI VETO: Rompimiento LONG descartado (Fake Breakout Probabilidad Éxito: {signals['ml_prob']:.2f} < 0.65)")
                return None
            return 'buy'
        
        # SHORT
        bear = sum([struct <= -0.5, mom == -1, di_bear, adx_strong])
        if bear >= 3:
            return 'sell'
        
        return None
    
    def manage_position(self, signals, price):
        """Gestiona trailing stop y pyramiding."""
        atr_val = signals['atr']
        if np.isnan(atr_val) or atr_val == 0:
            return
        
        is_long = self.position_side == 'long'
        
        # ─── TRAILING STOP ───
        if is_long:
            if price > self.best_price:
                self.best_price = price
                new_stop = price - (atr_val * self.cfg['trail_atr_mult'])
                self.trail_stop = max(self.trail_stop, new_stop)
            
            if price <= self.trail_stop:
                self.logger.info(f"TRAILING STOP HIT (long) @ {price:.2f} (stop: {self.trail_stop:.2f})")
                self.close_position(price)
                return
        else:
            if price < self.best_price or self.best_price == 0:
                self.best_price = price
                new_stop = price + (atr_val * self.cfg['trail_atr_mult'])
                if self.trail_stop == 0:
                    self.trail_stop = new_stop
                else:
                    self.trail_stop = min(self.trail_stop, new_stop)
            
            if price >= self.trail_stop:
                self.logger.info(f"TRAILING STOP HIT (short) @ {price:.2f} (stop: {self.trail_stop:.2f})")
                self.close_position(price)
                return
        
        # ─── PYRAMIDING ───
        if is_long:
            profit_atr = (price - self.entry_price) / atr_val
        else:
            profit_atr = (self.entry_price - price) / atr_val
        
        side = 'buy' if is_long else 'sell'
        
        if self.pyramid_level == 1 and profit_atr > PYRAMID_2_THRESHOLD:
            self.logger.info(f"PYRAMID LVL 2 | Profit: {profit_atr:.1f} ATR")
            if self.open_position(side, price, size_pct=BASE_SIZE_PCT * 0.5):
                self.pyramid_level = 2
                # Tighten trailing
                mult = self.cfg['trail_atr_mult'] * 0.8
                if is_long:
                    self.trail_stop = max(self.trail_stop, price - (atr_val * mult))
                else:
                    self.trail_stop = min(self.trail_stop, price + (atr_val * mult))
        
        elif self.pyramid_level == 2 and profit_atr > PYRAMID_3_THRESHOLD:
            self.logger.info(f"PYRAMID LVL 3 | Profit: {profit_atr:.1f} ATR")
            if self.open_position(side, price, size_pct=BASE_SIZE_PCT * 0.25):
                self.pyramid_level = 3
                mult = self.cfg['trail_atr_mult'] * 0.6
                if is_long:
                    self.trail_stop = max(self.trail_stop, price - (atr_val * mult))
                else:
                    self.trail_stop = min(self.trail_stop, price + (atr_val * mult))
        
        # ─── SEÑAL CONTRARIA ───
        if signals['sq_release'] == 1:
            if is_long and signals['momentum'] == -1 and signals['structure'] <= -0.5:
                self.logger.info("SENAL CONTRARIA detectada - cerrando long")
                self.close_position(price)
            elif not is_long and signals['momentum'] == 1 and signals['structure'] >= 0.5:
                self.logger.info("SENAL CONTRARIA detectada - cerrando short")
                self.close_position(price)
    
    def run(self):
        mode = "TESTNET" if self.testnet else "LIVE"
        self.logger.info(f"=== VIPER STRIKE BOT [{self.asset}] - {mode} ===")
        self.logger.info(f"Symbol: {self.symbol} | TF: {TIMEFRAME}")
        self.logger.info(f"Config: {self.cfg}")
        self.logger.info("Esperando cierre de vela...")
        
        while True:
            try:
                df = self.fetch_data(limit=300)
                if df.empty or len(df) < 50:
                    self.logger.warning("Datos insuficientes, esperando...")
                    time.sleep(30)
                    continue
                
                # Usar velas cerradas para calculos
                df_closed = df.iloc[:-1].copy()
                current_price = df.iloc[-1]['close']
                
                # Calcular señales
                signals = self.calculate_signals(df_closed)
                
                last_time = df_closed.iloc[-1]['timestamp']
                
                # Estado actual
                pos = self.get_position()
                pos_info = "FLAT"
                if pos:
                    pos_side = pos['side']
                    pos_size = float(pos['contracts'])
                    pos_info = f"{pos_side.upper()} {pos_size:.6f}"
                
                self.logger.info(
                    f"T: {last_time} | Price: {current_price:.2f} | "
                    f"ADX: {signals['adx']:.1f} | Struct: {signals['structure']:.1f} | "
                    f"Mom: {signals['momentum']:.0f} | SqRel: {signals['sq_release']:.0f} | "
                    f"Pos: {pos_info} | Pyramid: {self.pyramid_level}"
                )
                
                # Logica principal
                if pos and float(pos['contracts']) != 0:
                    # Sincronizar estado con exchange
                    self.position_side = pos['side']
                    if self.pyramid_level == 0:
                        # Posicion detectada pero no trackeada (restart?)
                        self.pyramid_level = 1
                        self.entry_price = float(pos.get('entryPrice', current_price))
                        self.best_price = current_price
                        atr_val = signals['atr']
                        if self.position_side == 'long':
                            self.trail_stop = current_price - (atr_val * self.cfg['trail_atr_mult'])
                        else:
                            self.trail_stop = current_price + (atr_val * self.cfg['trail_atr_mult'])
                    
                    self.manage_position(signals, current_price)
                else:
                    # Sin posicion - buscar entrada
                    self.pyramid_level = 0
                    self.position_side = None
                    
                    signal = self.check_entry(signals, current_price)
                    if signal:
                        atr_val = signals['atr']
                        if self.open_position(signal, current_price):
                            self.entry_price = current_price
                            self.pyramid_level = 1
                            self.best_price = current_price
                            self.position_side = 'long' if signal == 'buy' else 'short'
                            if signal == 'buy':
                                self.trail_stop = current_price - (atr_val * self.cfg['trail_atr_mult'])
                            else:
                                self.trail_stop = current_price + (atr_val * self.cfg['trail_atr_mult'])
                            self.logger.info(
                                f"NUEVA POSICION: {signal.upper()} @ {current_price:.2f} | "
                                f"Trail: {self.trail_stop:.2f}"
                            )
                
                time.sleep(CHECK_INTERVAL)
                
            except KeyboardInterrupt:
                self.logger.info("Bot detenido por el usuario.")
                break
            except Exception as e:
                self.logger.error(f"Loop Error: {e}")
                time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Viper Strike Bot - Hyperliquid")
    parser.add_argument('--asset', type=str, default='ETH', choices=['BTC', 'ETH', 'SOL'],
                        help='Activo a operar (default: ETH)')
    parser.add_argument('--live', action='store_true', help='Ejecutar en la MAINNET (dinero real)')
    parser.add_argument('--nexus', action='store_true', help='Modo Sindicato (Delega ejecución al CEO conectándose por Redis)')
    args = parser.parse_args()
    
    is_testnet = not args.live
    bot = ViperStrikeBot(asset=args.asset, testnet=is_testnet, nexus_mode=args.nexus)
    bot.run()
