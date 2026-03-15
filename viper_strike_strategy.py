"""
╔══════════════════════════════════════════════════════════════╗
║  VIPER STRIKE - Volatility Squeeze + Structure + Pyramiding ║
║  Estrategia Agresiva Multi-Mercado                          ║
║  Aplicable a: Criptos (BTC, ETH) + Mercados (QQQ, SPY, NQ) ║
╚══════════════════════════════════════════════════════════════╝

Concepto:
  1. Detecta compresión de volatilidad (Bollinger dentro de Keltner = SQUEEZE)
  2. Espera la explosión (expansión de volatilidad)
  3. Confirma dirección con Market Structure (HH/HL vs LH/LL) + ADX
  4. Entra agresivamente y PIRAMIDA en posiciones ganadoras (hasta 3 niveles)
  5. Trailing stop dinámico basado en ATR

Diferencias vs estrategias existentes:
  - NO usa SuperTrend, RSI, MACD ni EMA como señal principal
  - USA detección de régimen (squeeze/trending)
  - USA pyramiding real (añadir a winners)
  - USA market structure breaks (pivots HH/HL/LH/LL)
"""

import pandas as pd
import numpy as np
import yfinance as yf
from backtesting import Backtest, Strategy
import itertools
import sys
import io
import warnings
warnings.filterwarnings('ignore')

# Fix Windows console encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


# ═══════════════════════════════════════════
# INDICADORES
# ═══════════════════════════════════════════

def calc_atr(high, low, close, period=10):
    """ATR - Average True Range"""
    high = pd.Series(high)
    low = pd.Series(low)
    close = pd.Series(close)
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def calc_bollinger(close, period=20, std_mult=2.0):
    """Bollinger Bands"""
    close = pd.Series(close)
    sma = close.rolling(period).mean()
    std = close.rolling(period).std()
    upper = sma + (std * std_mult)
    lower = sma - (std * std_mult)
    return upper, sma, lower


def calc_keltner(high, low, close, period=20, atr_mult=1.5):
    """Keltner Channel"""
    high = pd.Series(high)
    low = pd.Series(low)
    close = pd.Series(close)
    ema = close.ewm(span=period, adjust=False).mean()
    atr = calc_atr(high, low, close, period)
    upper = ema + (atr * atr_mult)
    lower = ema - (atr * atr_mult)
    return upper, ema, lower


def calc_adx(high, low, close, period=10):
    """ADX - Average Directional Index"""
    high = pd.Series(high)
    low = pd.Series(low)
    close = pd.Series(close)
    
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


def detect_squeeze(high, low, close, bb_period=20, bb_std=2.0, 
                   kc_period=20, kc_atr_mult=1.5):
    """
    Detecta Volatility Squeeze: Bollinger Bands dentro del Keltner Channel.
    
    Returns:
        squeeze: 1 si hay squeeze (compresión), 0 si no
        squeeze_release: 1 si se acaba de liberar el squeeze (explosión)
    """
    bb_upper, bb_mid, bb_lower = calc_bollinger(close, bb_period, bb_std)
    kc_upper, kc_mid, kc_lower = calc_keltner(high, low, close, kc_period, kc_atr_mult)
    
    # Squeeze: BB está DENTRO de KC
    in_squeeze = ((bb_lower > kc_lower) & (bb_upper < kc_upper)).astype(int)
    
    # Squeeze release: estaba en squeeze y ahora no
    squeeze_release = ((in_squeeze.shift(1) == 1) & (in_squeeze == 0)).astype(int)
    
    return in_squeeze, squeeze_release


def detect_market_structure(high, low, pivot_len=5):
    """
    Detecta Market Structure: Higher Highs/Higher Lows (alcista)
    vs Lower Highs/Lower Lows (bajista).
    
    Returns:
        structure: 1 (bullish HH/HL), -1 (bearish LH/LL), 0 (indefinido)
    """
    high = pd.Series(high)
    low = pd.Series(low)
    
    # Encontrar pivot highs y lows
    pivot_high = high.rolling(window=2*pivot_len+1, center=True).max()
    pivot_low = low.rolling(window=2*pivot_len+1, center=True).min()
    
    is_pivot_high = (high == pivot_high)
    is_pivot_low = (low == pivot_low)
    
    structure = pd.Series(0, index=high.index, dtype=float)
    
    last_ph = np.nan  # Último pivot high
    last_pl = np.nan  # Último pivot low
    prev_ph = np.nan  # Penúltimo pivot high
    prev_pl = np.nan  # Penúltimo pivot low
    
    for i in range(len(high)):
        if is_pivot_high.iloc[i]:
            prev_ph = last_ph
            last_ph = high.iloc[i]
        if is_pivot_low.iloc[i]:
            prev_pl = last_pl
            last_pl = low.iloc[i]
        
        if not np.isnan(prev_ph) and not np.isnan(prev_pl):
            hh = last_ph > prev_ph  # Higher High
            hl = last_pl > prev_pl  # Higher Low
            lh = last_ph < prev_ph  # Lower High
            ll = last_pl < prev_pl  # Lower Low
            
            if hh and hl:
                structure.iloc[i] = 1   # Bullish
            elif lh and ll:
                structure.iloc[i] = -1  # Bearish
            # Si es mixto, mantener la última estructura
            elif hh or hl:
                structure.iloc[i] = 0.5   # Sesgo alcista
            elif lh or ll:
                structure.iloc[i] = -0.5  # Sesgo bajista
    
    return structure


def calc_momentum_direction(close, period=10):
    """
    Dirección del momentum lineal (pendiente de regresión).
    Complementa la señal de squeeze release indicando la dirección.
    """
    close = pd.Series(close)
    momentum = close - close.shift(period)
    mom_smooth = momentum.rolling(3).mean()
    direction = pd.Series(0, index=close.index, dtype=float)
    direction[mom_smooth > 0] = 1
    direction[mom_smooth < 0] = -1
    return direction


# ═══════════════════════════════════════════
# WRAPPERS PARA backtesting.py (devuelven arrays)
# ═══════════════════════════════════════════

def squeeze_indicator(high, low, close, bb_period, bb_std, kc_period, kc_atr_mult):
    """Wrapper: devuelve señal de squeeze release"""
    _, release = detect_squeeze(high, low, close, bb_period, bb_std, kc_period, kc_atr_mult)
    return release


def squeeze_state(high, low, close, bb_period, bb_std, kc_period, kc_atr_mult):
    """Wrapper: devuelve si está en squeeze"""
    sq, _ = detect_squeeze(high, low, close, bb_period, bb_std, kc_period, kc_atr_mult)
    return sq


def adx_indicator(high, low, close, period):
    """Wrapper: devuelve ADX"""
    adx, _, _ = calc_adx(high, low, close, period)
    return adx


def di_plus_indicator(high, low, close, period):
    """Wrapper: devuelve +DI"""
    _, plus_di, _ = calc_adx(high, low, close, period)
    return plus_di


def di_minus_indicator(high, low, close, period):
    """Wrapper: devuelve -DI"""
    _, _, minus_di = calc_adx(high, low, close, period)
    return minus_di


def structure_indicator(high, low, pivot_len):
    """Wrapper: devuelve market structure"""
    return detect_market_structure(high, low, pivot_len)


def momentum_indicator(close, period):
    """Wrapper: devuelve dirección de momentum"""
    return calc_momentum_direction(close, period)


def atr_indicator(high, low, close, period):
    """Wrapper: devuelve ATR"""
    return calc_atr(high, low, close, period)


# ═══════════════════════════════════════════
# ESTRATEGIA PRINCIPAL: VIPER STRIKE
# ═══════════════════════════════════════════

class ViperStrike(Strategy):
    """
    Estrategia Viper Strike - Volatility Squeeze + Structure + Pyramiding
    
    ENTRADAS:
      - Squeeze release detectado (Bollinger sale de Keltner)
      - Market Structure confirma dirección (HH/HL = long, LH/LL = short)
      - ADX > umbral (tendencia fuerte)
      - Momentum confirma dirección
    
    PYRAMIDING:
      - Nivel 2: si en profit > 1 ATR → añadir 50% del tamaño original
      - Nivel 3: si en profit > 2 ATR → añadir 25% del tamaño original
    
    SALIDAS:
      - Trailing stop de trail_atr_mult * ATR desde mejor precio
      - Señal contraria (squeeze release en dirección opuesta)
    """
    
    # === Parámetros optimizables ===
    bb_period = 20
    bb_std = 2.0
    kc_period = 20
    kc_atr_mult = 1.5
    adx_period = 10
    adx_threshold = 20
    pivot_len = 5
    mom_period = 10
    atr_period = 10
    trail_atr_mult = 2.0
    
    def init(self):
        # Squeeze
        self.sq_release = self.I(squeeze_indicator,
                                  self.data.High, self.data.Low, self.data.Close,
                                  self.bb_period, self.bb_std, self.kc_period, self.kc_atr_mult)
        self.sq_state = self.I(squeeze_state,
                                self.data.High, self.data.Low, self.data.Close,
                                self.bb_period, self.bb_std, self.kc_period, self.kc_atr_mult)
        
        # ADX + DI
        self.adx = self.I(adx_indicator, self.data.High, self.data.Low, self.data.Close, self.adx_period)
        self.di_plus = self.I(di_plus_indicator, self.data.High, self.data.Low, self.data.Close, self.adx_period)
        self.di_minus = self.I(di_minus_indicator, self.data.High, self.data.Low, self.data.Close, self.adx_period)
        
        # Market Structure
        self.structure = self.I(structure_indicator, self.data.High, self.data.Low, self.pivot_len)
        
        # Momentum Direction
        self.momentum = self.I(momentum_indicator, self.data.Close, self.mom_period)
        
        # ATR para trailing y pyramiding
        self.atr = self.I(atr_indicator, self.data.High, self.data.Low, self.data.Close, self.atr_period)
        
        # Estado interno para pyramiding y trailing
        self._pyramid_level = 0
        self._entry_price = 0
        self._trail_stop = 0
        self._best_price = 0
        self._base_size = 0.30  # 30% del capital como base (pyramiding lo sube)
    
    def next(self):
        # Esperar suficientes datos
        if len(self.data) < 50:
            return
        
        price = self.data.Close[-1]
        atr_val = self.atr[-1]
        
        if np.isnan(atr_val) or atr_val == 0:
            return
        
        # ─── GESTIÓN DE POSICIÓN EXISTENTE ───
        if self.position:
            self._manage_position(price, atr_val)
            return
        
        # ─── BUSCAR NUEVA ENTRADA ───
        self._check_entry(price, atr_val)
    
    def _check_entry(self, price, atr_val):
        """Evalúa condiciones de entrada"""
        
        # Condición 1: Squeeze release
        is_release = self.sq_release[-1] == 1
        
        # Condición alternativa: squeeze reciente (últimas 3 barras)
        recent_release = any(self.sq_release[-i] == 1 for i in range(1, min(4, len(self.data))))
        
        if not (is_release or recent_release):
            return
        
        # Condición 2: ADX muestra fuerza
        adx_strong = self.adx[-1] > self.adx_threshold
        
        # Condición 3: Dirección del momentum
        mom_dir = self.momentum[-1]
        
        # Condición 4: Market structure
        struct = self.structure[-1]
        
        # Condición 5: DI confirma
        di_bullish = self.di_plus[-1] > self.di_minus[-1]
        di_bearish = self.di_minus[-1] > self.di_plus[-1]
        
        # ═══ SEÑAL LONG ═══
        # Squeeze release + estructura alcista + momentum positivo + DI+>DI-
        bull_signals = sum([
            struct >= 0.5,       # Estructura bullish o sesgo alcista  
            mom_dir == 1,        # Momentum positivo
            di_bullish,          # +DI > -DI
            adx_strong,          # ADX fuerte
        ])
        
        if bull_signals >= 3:  # Al menos 3 de 4 confirman
            self._entry_price = price
            self._pyramid_level = 1
            self._trail_stop = price - (atr_val * self.trail_atr_mult)
            self._best_price = price
            self.buy(size=self._base_size)
            return
        
        # ═══ SEÑAL SHORT ═══
        bear_signals = sum([
            struct <= -0.5,      # Estructura bearish o sesgo bajista
            mom_dir == -1,       # Momentum negativo 
            di_bearish,          # -DI > +DI
            adx_strong,          # ADX fuerte
        ])
        
        if bear_signals >= 3:
            self._entry_price = price
            self._pyramid_level = 1
            self._trail_stop = price + (atr_val * self.trail_atr_mult)
            self._best_price = price
            self.sell(size=self._base_size)
            return
    
    def _manage_position(self, price, atr_val):
        """Gestiona posición: trailing stop + pyramiding"""
        
        is_long = self.position.is_long
        
        # ─── TRAILING STOP ───
        if is_long:
            # Actualizar mejor precio
            if price > self._best_price:
                self._best_price = price
                # Mover trailing stop arriba
                new_stop = price - (atr_val * self.trail_atr_mult)
                self._trail_stop = max(self._trail_stop, new_stop)
            
            # ¿Stop activado?
            if price <= self._trail_stop:
                self.position.close()
                self._pyramid_level = 0
                return
        else:
            # Short
            if price < self._best_price or self._best_price == 0:
                self._best_price = price
                new_stop = price + (atr_val * self.trail_atr_mult)
                if self._trail_stop == 0:
                    self._trail_stop = new_stop
                else:
                    self._trail_stop = min(self._trail_stop, new_stop)
            
            if price >= self._trail_stop:
                self.position.close()
                self._pyramid_level = 0
                return
        
        # ─── PYRAMIDING ───
        profit_in_atr = 0
        if is_long:
            profit_in_atr = (price - self._entry_price) / atr_val
        else:
            profit_in_atr = (self._entry_price - price) / atr_val
        
        # Nivel 2: profit > 1 ATR → añadir 50% del size base
        if self._pyramid_level == 1 and profit_in_atr > 1.0:
            try:
                if is_long:
                    self.buy(size=self._base_size * 0.5)
                else:
                    self.sell(size=self._base_size * 0.5)
                self._pyramid_level = 2
                # Ajustar trailing más tight
                if is_long:
                    self._trail_stop = max(self._trail_stop, 
                                           price - (atr_val * self.trail_atr_mult * 0.8))
                else:
                    self._trail_stop = min(self._trail_stop,
                                           price + (atr_val * self.trail_atr_mult * 0.8))
            except:
                pass
        
        # Nivel 3: profit > 2 ATR → añadir 25% del size base
        elif self._pyramid_level == 2 and profit_in_atr > 2.0:
            try:
                if is_long:
                    self.buy(size=self._base_size * 0.25)
                else:
                    self.sell(size=self._base_size * 0.25)
                self._pyramid_level = 3
                # Trailing aún más tight
                if is_long:
                    self._trail_stop = max(self._trail_stop,
                                           price - (atr_val * self.trail_atr_mult * 0.6))
                else:
                    self._trail_stop = min(self._trail_stop,
                                           price + (atr_val * self.trail_atr_mult * 0.6))
            except:
                pass
        
        # ─── SEÑAL CONTRARIA: salir inmediatamente ───
        is_release = self.sq_release[-1] == 1
        if is_release:
            if is_long and self.momentum[-1] == -1 and self.structure[-1] <= -0.5:
                self.position.close()
                self._pyramid_level = 0
            elif not is_long and self.momentum[-1] == 1 and self.structure[-1] >= 0.5:
                self.position.close()
                self._pyramid_level = 0


# ═══════════════════════════════════════════
# DATOS Y BACKTESTING
# ═══════════════════════════════════════════

def get_data(ticker="BTC-USD", period="729d", interval="1h"):
    """Descarga datos de Yahoo Finance"""
    print(f"  [DL] Descargando {ticker} ({period}, {interval})...")
    try:
        df = yf.download(ticker, period=period, interval=interval, 
                         progress=False, auto_adjust=True)
    except Exception as e:
        print(f"  [ERROR] Error descarga: {e}")
        return pd.DataFrame()
    
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)
    
    df = df[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()
    df = df[df['Volume'] > 0]
    df = df[~df.index.duplicated(keep='first')]
    print(f"  [OK] {len(df)} barras cargadas ({df.index[0]} -> {df.index[-1]})")
    return df


def run_backtest(df, name, cash=10_000_000, commission=0.001):
    """Ejecuta backtest y devuelve stats"""
    if len(df) < 100:
        print(f"  [WARN] {name}: datos insuficientes ({len(df)} barras)")
        return None, None
    
    bt = Backtest(df, ViperStrike, cash=cash, commission=commission, 
                  exclusive_orders=False, hedging=True)
    
    stats = bt.run()
    return stats, bt


def optimize_strategy(bt, name):
    """Optimización con grid search de parámetros clave"""
    print(f"\n  [OPT] Optimizando {name}...")
    
    param_grid = list(itertools.product(
        [15, 20],           # bb_period
        [1.5, 2.0],         # bb_std
        [1.0, 1.5, 2.0],    # kc_atr_mult
        [8, 10, 14],        # adx_period  
        [15, 20, 25],       # adx_threshold
        [1.5, 2.0, 2.5],    # trail_atr_mult
    ))
    
    print(f"  [GRID] Probando {len(param_grid)} combinaciones...")
    
    best_stats = None
    best_return = -999999
    best_params = {}
    
    for i, (bb_p, bb_s, kc_m, adx_p, adx_t, trail) in enumerate(param_grid):
        ViperStrike.bb_period = bb_p
        ViperStrike.bb_std = bb_s
        ViperStrike.kc_atr_mult = kc_m
        ViperStrike.adx_period = adx_p
        ViperStrike.adx_threshold = adx_t
        ViperStrike.trail_atr_mult = trail
        
        try:
            s = bt.run()
            ret = s['Return [%]']
            n_trades = s['# Trades']
            
            if i % 50 == 0:
                print(f"    Run {i}/{len(param_grid)}: R={ret:.2f}%, T={n_trades}")
            
            # Solo considerar combinaciones con suficientes trades
            if n_trades >= 5 and ret > best_return:
                best_return = ret
                best_stats = s
                best_params = {
                    'bb_period': bb_p, 'bb_std': bb_s, 'kc_atr_mult': kc_m,
                    'adx_period': adx_p, 'adx_threshold': adx_t, 'trail_atr_mult': trail
                }
        except Exception:
            pass
    
    return best_stats, best_params, best_return


def print_results(stats, name, params=None):
    """Imprime resultados formateados"""
    if stats is None:
        print(f"\n  [ERROR] {name}: Sin resultados")
        return
    
    print(f"\n  {'='*50}")
    print(f"  >> RESULTADOS: {name}")
    print(f"  {'='*50}")
    
    if params:
        print(f"  Parámetros: {params}")
    
    key_metrics = [
        'Return [%]', 'Buy & Hold Return [%]', 
        'Sharpe Ratio', 'Max. Drawdown [%]',
        '# Trades', 'Win Rate [%]', 
        'Profit Factor', 'Avg. Trade [%]',
        'Avg. Trade Duration', 'Expectancy [%]'
    ]
    
    for metric in key_metrics:
        if metric in stats:
            val = stats[metric]
            if isinstance(val, float):
                print(f"  {metric:.<35} {val:>10.2f}")
            else:
                print(f"  {metric:.<35} {str(val):>10s}")
    
    # Evaluación
    ret = stats.get('Return [%]', 0)
    bh = stats.get('Buy & Hold Return [%]', 0)
    if isinstance(ret, (int, float)) and isinstance(bh, (int, float)):
        alpha = ret - bh
        tag = "[+]" if alpha > 0 else "[-]"
        print(f"  {tag} Alpha vs Buy&Hold:{'':.<18} {alpha:>10.2f}%")


# ═══════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════

def main():
    print("====================================================")
    print("   VIPER STRIKE - Estrategia Agresiva")
    print("   Squeeze + Structure + Pyramiding")
    print("====================================================")
    
    # ─── ACTIVOS A TESTEAR ───
    assets = [
        {"ticker": "BTC-USD",  "name": "Bitcoin (BTC)",      "period": "729d", "interval": "1h"},
        {"ticker": "ETH-USD",  "name": "Ethereum (ETH)",     "period": "729d", "interval": "1h"},
        {"ticker": "QQQ",      "name": "Nasdaq 100 (QQQ)",   "period": "2y",   "interval": "1h"},
    ]
    
    all_results = {}
    
    for asset in assets:
        print(f"\n{'-'*55}")
        print(f"  >> {asset['name']}")
        print(f"{'-'*55}")
        
        # 1. Descargar datos
        df = get_data(asset['ticker'], asset['period'], asset['interval'])
        if df.empty:
            continue
        
        # 2. Backtest inicial con parámetros por defecto
        print(f"\n  > Backtest inicial (parametros por defecto)...")
        
        # Reset parámetros a default
        ViperStrike.bb_period = 20
        ViperStrike.bb_std = 2.0
        ViperStrike.kc_period = 20
        ViperStrike.kc_atr_mult = 1.5
        ViperStrike.adx_period = 10
        ViperStrike.adx_threshold = 20
        ViperStrike.pivot_len = 5
        ViperStrike.mom_period = 10
        ViperStrike.atr_period = 10
        ViperStrike.trail_atr_mult = 2.0
        
        stats_default, bt = run_backtest(df, asset['name'])
        if stats_default is not None:
            print_results(stats_default, f"{asset['name']} (Default)")
        
        # 3. Optimización
        if bt is not None:
            best_stats, best_params, best_return = optimize_strategy(bt, asset['name'])
            
            if best_stats is not None:
                print_results(best_stats, f"{asset['name']} (Optimizado)", best_params)
                
                # 4. Guardar HTML con mejores parámetros
                for k, v in best_params.items():
                    setattr(ViperStrike, k, v)
                
                bt.run()
                html_file = f"viper_strike_{asset['ticker'].replace('-', '_').lower()}.html"
                bt.plot(filename=html_file, open_browser=False)
                print(f"\n  [SAVE] Reporte guardado: {html_file}")
                
                all_results[asset['name']] = {
                    'stats': best_stats,
                    'params': best_params,
                    'return': best_return
                }
            else:
                print(f"\n  [WARN] No se encontro combinacion profitable para {asset['name']}")
    
    # ─── RESUMEN FINAL ───
    print(f"\n{'='*55}")
    print(f"  RESUMEN FINAL - VIPER STRIKE")
    print(f"{'='*55}")
    
    if all_results:
        for name, res in all_results.items():
            ret = res['return']
            tag = "[+]" if ret > 0 else "[-]"
            trades = res['stats']['# Trades']
            wr = res['stats'].get('Win Rate [%]', 0)
            dd = res['stats'].get('Max. Drawdown [%]', 0)
            print(f"  {tag} {name:.<25} R={ret:>8.2f}% | T={trades:>3} | WR={wr:.1f}% | DD={dd:.1f}%")
            print(f"     Params: {res['params']}")
    else:
        print("  [WARN] No se obtuvieron resultados. Revisar datos.")
    
    print(f"\n  {'='*50}")
    print(f"  Archivos HTML generados para analisis visual.")
    print(f"  {'='*50}")


if __name__ == "__main__":
    main()
