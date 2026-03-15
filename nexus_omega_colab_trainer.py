"""
# ==============================================================================
# 🚀 NEXUS OMEGA — ENTRENAMIENTO EN GOOGLE COLAB (GPU)
# ==============================================================================
# Instrucciones para Google Colab:
# 1. Abre Google Colab: https://colab.research.google.com/
# 2. Crea un nuevo notebook.
# 3. Ve a Entorno de ejecución -> Cambiar tipo de entorno -> Hardware > T4 GPU.
# 4. Pega este código completo en una celda en blanco.
# 5. Modifica la configuración al final si lo deseas (ticker, episodios).
# 6. Ejecuta la celda (Shift + Enter). 
#    - Se instalarán las librerías necesarias.
#    - Descargará los datos y empezará a entrenar.
# ==============================================================================
"""

import os
import sys
import subprocess

# ==============================================================================
# 🚀 BLOQUE DE INSTALACIÓN (Ejecutar primero si faltan librerías)
# ==============================================================================
def install_dependencies():
    print("Verificando dependencias...")
    required = ["yfinance", "hmmlearn", "plotly", "torch", "pandas", "numpy"]
    missing = []
    for lib in required:
        try:
            __import__(lib)
        except ImportError:
            missing.append(lib)
    
    if missing:
        print(f"Instalando librerías faltantes: {missing}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing)
        print("✅ Instalación completada. Por favor, REINICIA EL KERNEL o vuelve a ejecutar esta celda.")
        # Intentar forzar la recarga en el sistema
        import importlib
        for lib in missing:
            importlib.invalidate_caches()
    else:
        print("✅ Todas las dependencias están presentes.")

try:
    import pandas as pd
    import yfinance as yf
    import hmmlearn
except ImportError:
    install_dependencies()
    import pandas as pd
    import yfinance as yf
    import hmmlearn

# ==============================================================================
# 1. ESTRATEGIA BASE NEXUS OMEGA (7 CAPAS)
# ==============================================================================
"""
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║              ███╗   ██╗███████╗██╗  ██╗██╗   ██╗███████╗             ║
║              ████╗  ██║██╔════╝╚██╗██╔╝██║   ██║██╔════╝             ║
║              ██╔██╗ ██║█████╗   ╚███╔╝ ██║   ██║███████╗             ║
║              ██║╚██╗██║██╔══╝   ██╔██╗ ██║   ██║╚════██║             ║
║              ██║ ╚████║███████╗██╔╝ ██╗╚██████╔╝███████║             ║
║              ╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝ ╚═════╝╚══════╝             ║
║                        ╔═╗╔╦╗╔═╗╔═╗╔═╗                              ║
║                        ║ ║║║║║╣ ║ ╦╠═╣                              ║
║                        ╚═╝╩ ╩╚═╝╚═╝╩ ╩                              ║
║                                                                      ║
║  Estrategia Revolucionaria de Trading — 7 Capas de Inteligencia      ║
║                                                                      ║
║  Capa 1: Detector de Régimen HMM v2 (Multi-Feature + Volumen)       ║
║  Capa 2: Motor de 8 Señales Multi-Factor (120 pts max)              ║
║  Capa 3: Filtro Volatility Squeeze (Bollinger ∩ Keltner)            ║
║  Capa 4: Filtro Estructura de Mercado (HH/HL vs LH/LL)             ║
║  Capa 5: Meta-Learner Adaptativo (pesos por régimen)                ║
║  Capa 6: Gestión de Riesgo Institucional (Kelly + Trailing + Pyr.)  ║
║  Capa 7: Anti-Drawdown (Circuit Breaker + Cooldown + Kill Switch)   ║
║                                                                      ║
║  Fusiona: Quantum Edge + Viper Strike + TAMC + Nexus                ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import numpy as np
import pandas as pd
import warnings
from dataclasses import dataclass, field
from typing import Tuple, Optional, List, Dict
from enum import IntEnum

warnings.filterwarnings('ignore')


# ════════════════════════════════════════════════════════════════
# ENUMS Y CONFIGURACIÓN
# ════════════════════════════════════════════════════════════════

class MarketRegime(IntEnum):
    BULL_TREND = 0
    BEAR_TREND = 1
    MEAN_REVERSION = 2
    HIGH_VOLATILITY = 3


@dataclass
class NexusOmegaConfig:
    """Configuración central de NEXUS OMEGA."""
    ticker: str = "SOL-USD"
    period: str = "2y"
    interval: str = "1h"

    # ── Régimen HMM ──
    hmm_n_states: int = 4
    hmm_lookback: int = 500
    hmm_refit_every: int = 500
    hmm_features_windows: List[int] = field(default_factory=lambda: [24, 72, 168])

    # ── Señales (8 factores, 15 pts cada uno = 120 max) ──
    signal_max_per_factor: int = 15
    squeeze_bonus: int = 25

    # ── Umbrales de confluencia por régimen ──
    confluence_bull: int = 40
    confluence_bear: int = 40
    confluence_range: int = 55   # Más estricto en lateral
    confluence_volatile: int = 50
    min_bars_between_trades: int = 3  # Cooldown mínimo entre trades

    # ── Indicadores ──
    ema_fast: int = 9
    ema_mid: int = 21
    ema_slow: int = 50
    sma_200: int = 200
    rsi_period: int = 14
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    roc_period: int = 6
    atr_period: int = 14
    adx_period: int = 14
    bb_period: int = 20
    bb_std: float = 2.0
    kc_period: int = 20
    kc_atr_mult: float = 1.5
    obv_div_window: int = 14
    pivot_len: int = 5
    momentum_period: int = 10

    # ── Riesgo ──
    initial_capital: float = 10000.0
    commission_pct: float = 0.0005
    kelly_lookback: int = 30
    kelly_fraction: float = 0.50
    max_risk_per_trade: float = 0.03
    # TP/SL por régimen
    tp_atr_mult_trend: float = 3.5
    sl_atr_mult_trend: float = 1.5
    tp_atr_mult_range: float = 2.5
    sl_atr_mult_range: float = 1.2
    tp_atr_mult_volatile: float = 4.0
    sl_atr_mult_volatile: float = 2.5
    # Trailing
    trail_atr_mult_trend: float = 2.5
    trail_atr_mult_range: float = 1.8
    trail_atr_mult_volatile: float = 3.5
    # Pyramiding
    pyramid_max_adds: int = 2
    pyramid_atr_threshold: float = 1.0  # Profit > N ATR para pyramidar

    # ── Anti-Drawdown ──
    daily_max_drawdown: float = 0.08
    weekly_drawdown_reduce: float = 0.05
    consecutive_stops_cooldown: int = 3
    cooldown_bars: int = 12     # 12 velas de pausa tras 3 stops
    kill_switch_pct: float = 0.15
    kill_switch_bars: int = 48  # 48h equiv en velas

    # ── Meta-Learner ──
    meta_lookback: int = 50     # Últimos N trades para calibrar

    def __post_init__(self):
        if "BTC" in self.ticker:
            self.confluence_bull = 35
            self.confluence_bear = 35
            self.confluence_range = 50
            self.sl_atr_mult_trend = 2.5
            self.sl_atr_mult_volatile = 3.0


# ════════════════════════════════════════════════════════════════
# INDICADORES VECTORIZADOS
# ════════════════════════════════════════════════════════════════

def calc_atr(high: np.ndarray, low: np.ndarray, close: np.ndarray,
             period: int = 14) -> np.ndarray:
    prev_close = np.roll(close, 1)
    prev_close[0] = close[0]
    tr = np.maximum(high - low,
                    np.maximum(np.abs(high - prev_close),
                               np.abs(low - prev_close)))
    atr = np.full_like(tr, np.nan)
    atr[period - 1] = np.mean(tr[:period])
    for i in range(period, len(tr)):
        atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period
    return atr


def calc_ema(data: np.ndarray, period: int) -> np.ndarray:
    ema = np.full_like(data, np.nan, dtype=float)
    if len(data) < period:
        return ema
    ema[period - 1] = np.mean(data[:period])
    mult = 2.0 / (period + 1)
    for i in range(period, len(data)):
        ema[i] = data[i] * mult + ema[i - 1] * (1 - mult)
    return ema


def calc_sma(data: np.ndarray, period: int) -> np.ndarray:
    cumsum = np.cumsum(np.insert(data, 0, 0))
    sma = np.full_like(data, np.nan)
    sma[period - 1:] = (cumsum[period:] - cumsum[:-period]) / period
    return sma


def calc_rolling_std(data: np.ndarray, period: int) -> np.ndarray:
    sma = calc_sma(data, period)
    cumsum_sq = np.cumsum(np.insert(data ** 2, 0, 0))
    mean_sq = (cumsum_sq[period:] - cumsum_sq[:-period]) / period
    result = np.full_like(data, np.nan)
    var = mean_sq - sma[period - 1:] ** 2
    var = np.maximum(var, 0)
    result[period - 1:] = np.sqrt(var)
    return result


def calc_rsi(close: np.ndarray, period: int = 14) -> np.ndarray:
    close = np.asarray(close, dtype=float).ravel()
    delta = np.diff(close, prepend=close[0])
    gain = np.where(delta > 0, delta, 0.0)
    loss = np.where(delta < 0, -delta, 0.0)
    avg_gain = np.zeros_like(close)
    avg_loss = np.zeros_like(close)
    if len(close) > period:
        avg_gain[period] = np.mean(gain[1:period + 1])
        avg_loss[period] = np.mean(loss[1:period + 1])
        for i in range(period + 1, len(close)):
            avg_gain[i] = (avg_gain[i - 1] * (period - 1) + gain[i]) / period
            avg_loss[i] = (avg_loss[i - 1] * (period - 1) + loss[i]) / period
    rs = np.divide(avg_gain, avg_loss, out=np.zeros_like(avg_gain), where=avg_loss != 0)
    rsi = 100 - (100 / (1 + rs))
    rsi = np.where((avg_loss == 0) & (avg_gain > 0), 100, rsi)
    rsi = np.where((avg_loss == 0) & (avg_gain == 0), 50, rsi)
    rsi[:period] = np.nan
    return rsi


def calc_macd(close: np.ndarray, fast: int = 12, slow: int = 26,
              signal: int = 9) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    ema_fast = calc_ema(close, fast)
    ema_slow = calc_ema(close, slow)
    macd_line = ema_fast - ema_slow
    valid_idx = np.where(~np.isnan(macd_line))[0]
    if len(valid_idx) == 0:
        return macd_line, np.full_like(macd_line, np.nan), np.full_like(macd_line, np.nan)
    first_valid = valid_idx[0]
    valid_macd = macd_line[first_valid:]
    valid_signal = calc_ema(valid_macd, signal)
    signal_line = np.full_like(macd_line, np.nan)
    signal_line[first_valid:] = valid_signal
    macd_hist = macd_line - signal_line
    return macd_line, signal_line, macd_hist


def calc_obv(close: np.ndarray, volume: np.ndarray) -> np.ndarray:
    direction = np.sign(np.diff(close, prepend=close[0]))
    direction[0] = 0
    return np.cumsum(direction * volume)


def calc_adx(high: np.ndarray, low: np.ndarray, close: np.ndarray,
             period: int = 14) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Retorna (ADX, +DI, -DI)."""
    n = len(close)
    plus_dm = np.zeros(n)
    minus_dm = np.zeros(n)
    for i in range(1, n):
        up = high[i] - high[i - 1]
        down = low[i - 1] - low[i]
        plus_dm[i] = up if (up > down and up > 0) else 0
        minus_dm[i] = down if (down > up and down > 0) else 0

    atr = calc_atr(high, low, close, period)
    smooth_plus = calc_ema(plus_dm, period)
    smooth_minus = calc_ema(minus_dm, period)

    plus_di = np.divide(smooth_plus, atr, out=np.zeros(n), where=atr > 0) * 100
    minus_di = np.divide(smooth_minus, atr, out=np.zeros(n), where=atr > 0) * 100

    dx = np.divide(np.abs(plus_di - minus_di), plus_di + minus_di,
                   out=np.zeros(n), where=(plus_di + minus_di) > 0) * 100
    adx = calc_ema(dx, period)
    return adx, plus_di, minus_di


def calc_keltner(high: np.ndarray, low: np.ndarray, close: np.ndarray,
                 period: int = 20, mult: float = 1.5):
    sma = calc_sma(close, period)
    atr = calc_atr(high, low, close, period)
    upper = sma + (atr * mult)
    lower = sma - (atr * mult)
    return sma, upper, lower


def detect_squeeze(high, low, close, bb_period=20, bb_std=2.0,
                   kc_period=20, kc_atr_mult=1.5):
    """Detecta Volatility Squeeze: BB dentro de KC."""
    bb_sma = calc_sma(close, bb_period)
    bb_std_arr = calc_rolling_std(close, bb_period)
    bb_upper = bb_sma + bb_std_arr * bb_std
    bb_lower = bb_sma - bb_std_arr * bb_std

    _, kc_upper, kc_lower = calc_keltner(high, low, close, kc_period, kc_atr_mult)

    n = len(close)
    squeeze = np.zeros(n, dtype=int)
    squeeze_release = np.zeros(n, dtype=int)

    for i in range(max(bb_period, kc_period), n):
        if np.isnan(bb_upper[i]) or np.isnan(kc_upper[i]):
            continue
        is_squeeze = (bb_upper[i] < kc_upper[i]) and (bb_lower[i] > kc_lower[i])
        squeeze[i] = 1 if is_squeeze else 0
        if i > 0 and squeeze[i] == 0 and squeeze[i - 1] == 1:
            squeeze_release[i] = 1
    return squeeze, squeeze_release


def detect_market_structure(high, low, pivot_len=5):
    """Detecta HH/HL (alcista=1), LH/LL (bajista=-1), indefinido=0."""
    n = len(high)
    structure = np.zeros(n, dtype=int)
    pivot_highs = []
    pivot_lows = []

    for i in range(pivot_len, n - pivot_len):
        if high[i] == np.max(high[i - pivot_len:i + pivot_len + 1]):
            pivot_highs.append((i, high[i]))
        if low[i] == np.min(low[i - pivot_len:i + pivot_len + 1]):
            pivot_lows.append((i, low[i]))

    last_struct = 0
    ph_idx = 0
    pl_idx = 0

    for i in range(pivot_len, n):
        while ph_idx < len(pivot_highs) - 1 and pivot_highs[ph_idx + 1][0] <= i:
            ph_idx += 1
        while pl_idx < len(pivot_lows) - 1 and pivot_lows[pl_idx + 1][0] <= i:
            pl_idx += 1

        if ph_idx >= 1 and pl_idx >= 1:
            hh = pivot_highs[ph_idx][1] > pivot_highs[ph_idx - 1][1]
            hl = pivot_lows[pl_idx][1] > pivot_lows[pl_idx - 1][1]
            lh = pivot_highs[ph_idx][1] < pivot_highs[ph_idx - 1][1]
            ll = pivot_lows[pl_idx][1] < pivot_lows[pl_idx - 1][1]

            if hh and hl:
                last_struct = 1
            elif lh and ll:
                last_struct = -1
        structure[i] = last_struct
    return structure


def calc_momentum_direction(close, period=10):
    """Dirección de momentum via regresión lineal."""
    n = len(close)
    mom = np.zeros(n)
    x = np.arange(period, dtype=float)
    x_mean = x.mean()
    x_var = np.sum((x - x_mean) ** 2)
    if x_var == 0:
        return mom
    for i in range(period, n):
        y = close[i - period:i]
        slope = np.sum((x - x_mean) * (y - y.mean())) / x_var
        mom[i] = slope
    return mom


# ════════════════════════════════════════════════════════════════
# CAPA 1: DETECTOR DE RÉGIMEN HMM v2
# ════════════════════════════════════════════════════════════════

class RegimeDetectorV2:
    """HMM Gaussiano mejorado con feature de volumen."""

    def __init__(self, config: NexusOmegaConfig):
        self.config = config
        self.model = None
        self.is_fitted = False
        self._state_mapping = {}
        self._feat_mean = None
        self._feat_std = None

    def _extract_features(self, close: np.ndarray,
                          volume: np.ndarray = None) -> np.ndarray:
        log_ret = np.diff(np.log(close), prepend=np.log(close[0]))
        features_list = []
        for w in self.config.hmm_features_windows:
            cumsum = np.cumsum(log_ret)
            cumret = np.zeros_like(log_ret)
            cumret[w:] = cumsum[w:] - cumsum[:-w]
            features_list.append(cumret)
            vol = calc_rolling_std(log_ret, w)
            vol = np.nan_to_num(vol, nan=0.0)
            features_list.append(vol)
        # Feature extra: volumen normalizado (rolling z-score)
        if volume is not None and len(volume) == len(close):
            vol_sma = calc_sma(volume.astype(float), 72)
            vol_std = calc_rolling_std(volume.astype(float), 72)
            vol_std = np.where(vol_std < 1e-10, 1.0, vol_std)
            vol_zscore = np.nan_to_num((volume - vol_sma) / vol_std, nan=0.0)
            features_list.append(vol_zscore)
        return np.column_stack(features_list)

    def _normalize_features(self, features, fit=False):
        if fit:
            self._feat_mean = np.mean(features, axis=0)
            self._feat_std = np.std(features, axis=0)
            self._feat_std = np.where(self._feat_std < 1e-10, 1.0, self._feat_std)
        if self._feat_mean is None:
            return features
        return (features - self._feat_mean) / self._feat_std

    def _map_states(self, means):
        n = means.shape[0]
        ret_24h = means[:, 0]
        vol_24h = means[:, 1]
        assigned = set()
        mapping = {}

        bull_idx = int(np.argmax(ret_24h))
        mapping[bull_idx] = MarketRegime.BULL_TREND
        assigned.add(bull_idx)

        remaining_ret = ret_24h.copy()
        remaining_ret[list(assigned)] = np.inf
        bear_idx = int(np.argmin(remaining_ret))
        mapping[bear_idx] = MarketRegime.BEAR_TREND
        assigned.add(bear_idx)

        remaining_vol = vol_24h.copy()
        remaining_vol[list(assigned)] = -np.inf
        vol_idx = int(np.argmax(remaining_vol))
        mapping[vol_idx] = MarketRegime.HIGH_VOLATILITY
        assigned.add(vol_idx)

        for i in range(n):
            if i not in assigned:
                mapping[i] = MarketRegime.MEAN_REVERSION
                break
        self._state_mapping = mapping

    def fit(self, close, volume=None):
        from hmmlearn.hmm import GaussianHMM
        features = self._extract_features(close, volume)
        max_w = max(self.config.hmm_features_windows)
        features_valid = features[max_w:]
        if len(features_valid) < 50:
            return
        features_valid = self._normalize_features(features_valid, fit=True)
        try:
            self.model = GaussianHMM(
                n_components=self.config.hmm_n_states,
                covariance_type="diag", n_iter=30,
                random_state=42, tol=0.01)
            self.model.fit(features_valid)
            self._map_states(self.model.means_)
            self.is_fitted = True
        except Exception:
            if not self.is_fitted:
                self._state_mapping = {i: MarketRegime.MEAN_REVERSION
                                       for i in range(self.config.hmm_n_states)}

    def predict(self, close, volume=None) -> MarketRegime:
        if not self.is_fitted:
            return MarketRegime.MEAN_REVERSION
        try:
            features = self._extract_features(close, volume)
            max_w = max(self.config.hmm_features_windows)
            features_valid = features[max_w:]
            if len(features_valid) == 0:
                return MarketRegime.MEAN_REVERSION
            features_valid = self._normalize_features(features_valid, fit=False)
            states = self.model.predict(features_valid)
            return self._state_mapping.get(states[-1], MarketRegime.MEAN_REVERSION)
        except Exception:
            return MarketRegime.MEAN_REVERSION


# ════════════════════════════════════════════════════════════════
# CAPA 2: MOTOR DE 8 SEÑALES MULTI-FACTOR
# ════════════════════════════════════════════════════════════════

def precompute_8_signals(high, low, close, volume, config: NexusOmegaConfig):
    """Pre-calcula 8 señales independientes. Retorna arrays de scores."""
    high = np.asarray(high, dtype=float).ravel()
    low = np.asarray(low, dtype=float).ravel()
    close = np.asarray(close, dtype=float).ravel()
    volume = np.asarray(volume, dtype=float).ravel()
    n = len(close)
    P = config.signal_max_per_factor  # 15 pts max por señal

    # Arrays de score por señal
    s = {f's{i}_l': np.zeros(n, dtype=int) for i in range(1, 9)}
    s.update({f's{i}_s': np.zeros(n, dtype=int) for i in range(1, 9)})

    # ── S1: EMA Triple Stack (9/21/50) ──
    ema9 = calc_ema(close, config.ema_fast)
    ema21 = calc_ema(close, config.ema_mid)
    ema50 = calc_ema(close, config.ema_slow)
    for i in range(config.ema_slow, n):
        if np.isnan(ema9[i]) or np.isnan(ema50[i]):
            continue
        if ema9[i] > ema21[i] > ema50[i]:
            s['s1_l'][i] = P
        elif ema9[i] > ema21[i]:
            s['s1_l'][i] = P // 2
        if ema9[i] < ema21[i] < ema50[i]:
            s['s1_s'][i] = P
        elif ema9[i] < ema21[i]:
            s['s1_s'][i] = P // 2

    # ── S2: RSI Trend + Divergencia ──
    rsi = calc_rsi(close, config.rsi_period)
    for i in range(config.rsi_period + 1, n):
        if np.isnan(rsi[i]):
            continue
        if rsi[i] >= 55:
            s['s2_l'][i] = P
        elif rsi[i] > 50:
            s['s2_l'][i] = P // 2
        if rsi[i] <= 45:
            s['s2_s'][i] = P
        elif rsi[i] < 50:
            s['s2_s'][i] = P // 2

    # ── S3: MACD Histogram + Aceleración ──
    _, _, macd_hist = calc_macd(close, config.macd_fast, config.macd_slow, config.macd_signal)
    for i in range(config.macd_slow + config.macd_signal, n):
        if np.isnan(macd_hist[i]):
            continue
        if macd_hist[i] > 0:
            accel = macd_hist[i] > macd_hist[i - 1] if not np.isnan(macd_hist[i - 1]) else False
            s['s3_l'][i] = P if accel else P * 2 // 3
        elif macd_hist[i] < 0:
            accel = macd_hist[i] < macd_hist[i - 1] if not np.isnan(macd_hist[i - 1]) else False
            s['s3_s'][i] = P if accel else P * 2 // 3

    # ── S4: Rate of Change (Momentum) ──
    roc_p = config.roc_period
    for i in range(roc_p, n):
        if close[i - roc_p] == 0:
            continue
        roc = (close[i] - close[i - roc_p]) / close[i - roc_p]
        if roc > 0.015:
            s['s4_l'][i] = P
        elif roc > 0:
            s['s4_l'][i] = P // 2
        if roc < -0.015:
            s['s4_s'][i] = P
        elif roc < 0:
            s['s4_s'][i] = P // 2

    # ── S5: Precio vs SMA 50/200 (Macro-Trend) ──
    sma50 = calc_sma(close, config.ema_slow)
    sma200 = calc_sma(close, config.sma_200)
    for i in range(config.sma_200, n):
        if np.isnan(sma50[i]) or np.isnan(sma200[i]):
            continue
        above50 = close[i] > sma50[i]
        above200 = close[i] > sma200[i]
        if above50 and above200:
            s['s5_l'][i] = P
        elif above50:
            s['s5_l'][i] = P // 2
        below50 = close[i] < sma50[i]
        below200 = close[i] < sma200[i]
        if below50 and below200:
            s['s5_s'][i] = P
        elif below50:
            s['s5_s'][i] = P // 2

    # ── S6: OBV Divergencia ──
    obv = calc_obv(close, volume)
    obv_sma = calc_sma(obv, config.obv_div_window)
    for i in range(config.obv_div_window + 5, n):
        if np.isnan(obv_sma[i]):
            continue
        price_up = close[i] > close[i - 5]
        obv_up = obv[i] > obv_sma[i]
        if price_up and obv_up:
            s['s6_l'][i] = P
        elif obv_up:
            s['s6_l'][i] = P // 2
        price_down = close[i] < close[i - 5]
        obv_down = obv[i] < obv_sma[i]
        if price_down and obv_down:
            s['s6_s'][i] = P
        elif obv_down:
            s['s6_s'][i] = P // 2

    # ── S7: Keltner Channel Breakout ──
    _, kc_upper, kc_lower = calc_keltner(high, low, close, config.kc_period, config.kc_atr_mult)
    for i in range(config.kc_period, n):
        if np.isnan(kc_upper[i]):
            continue
        if close[i] > kc_upper[i]:
            s['s7_l'][i] = P
        if close[i] < kc_lower[i]:
            s['s7_s'][i] = P

    # ── S8: ADX Strength ──
    adx, plus_di, minus_di = calc_adx(high, low, close, config.adx_period)
    for i in range(config.adx_period * 2, n):
        if np.isnan(adx[i]):
            continue
        if adx[i] > 25:
            if plus_di[i] > minus_di[i]:
                s['s8_l'][i] = P
            else:
                s['s8_s'][i] = P
        elif adx[i] > 20:
            if plus_di[i] > minus_di[i]:
                s['s8_l'][i] = P // 2
            else:
                s['s8_s'][i] = P // 2

    # Scores totales
    long_score = sum(s[f's{i}_l'] for i in range(1, 9))
    short_score = sum(s[f's{i}_s'] for i in range(1, 9))

    return {
        'long_score': long_score,
        'short_score': short_score,
        **s
    }


# ════════════════════════════════════════════════════════════════
# CAPA 5: META-LEARNER ADAPTATIVO
# ════════════════════════════════════════════════════════════════

class MetaLearner:
    """Ajusta pesos de señales y umbral según rendimiento por régimen."""

    def __init__(self, config: NexusOmegaConfig):
        self.config = config
        # Historial de trades por régimen
        self.regime_trades: Dict[int, List[Dict]] = {r: [] for r in MarketRegime}
        # Pesos por régimen (8 señales) - empiezan iguales
        self.regime_weights: Dict[int, np.ndarray] = {
            r: np.ones(8) for r in MarketRegime
        }

    def get_confluence_threshold(self, regime: MarketRegime) -> int:
        thresholds = {
            MarketRegime.BULL_TREND: self.config.confluence_bull,
            MarketRegime.BEAR_TREND: self.config.confluence_bear,
            MarketRegime.MEAN_REVERSION: self.config.confluence_range,
            MarketRegime.HIGH_VOLATILITY: self.config.confluence_volatile,
        }
        return thresholds.get(regime, 60)

    def record_trade(self, trade: Dict, regime: MarketRegime):
        self.regime_trades[regime].append(trade)
        # Auto-calibración cada N trades
        if len(self.regime_trades[regime]) >= self.config.meta_lookback:
            self._recalibrate(regime)

    def _recalibrate(self, regime: MarketRegime):
        """Recalibra pesos basándose en rendimiento reciente."""
        recent = self.regime_trades[regime][-self.config.meta_lookback:]
        if len(recent) < 10:
            return
        # Analizar qué señales estaban presentes en trades ganadores vs perdedores
        wins = [t for t in recent if t.get('pnl', 0) > 0]
        losses = [t for t in recent if t.get('pnl', 0) <= 0]
        if not wins or not losses:
            return
        win_rate = len(wins) / len(recent)
        # Ajuste conservador: solo modificamos hasta ±30%
        weights = self.regime_weights[regime].copy()
        if win_rate > 0.55:
            weights *= 1.05  # Reforzar configuración actual
        elif win_rate < 0.40:
            weights *= 0.95  # Reducir confianza
        # Normalizar para mantener escala
        weights = np.clip(weights, 0.7, 1.3)
        self.regime_weights[regime] = weights

    def apply_weights(self, signal_scores: Dict, regime: MarketRegime):
        """Aplica pesos del meta-learner a las señales."""
        w = self.regime_weights[regime]
        weighted_long = sum(signal_scores[f's{i}_l'] * w[i - 1] for i in range(1, 9))
        weighted_short = sum(signal_scores[f's{i}_s'] * w[i - 1] for i in range(1, 9))
        return weighted_long, weighted_short


# ════════════════════════════════════════════════════════════════
# CAPA 6: GESTIÓN DE RIESGO INSTITUCIONAL
# ════════════════════════════════════════════════════════════════

class InstitutionalRiskManager:
    def __init__(self, config: NexusOmegaConfig):
        self.config = config
        self.trade_history: List[Dict] = []
        self.consecutive_stops = 0

    def get_kelly_fraction(self) -> float:
        recent = self.trade_history[-self.config.kelly_lookback:]
        if len(recent) < 5:
            return self.config.max_risk_per_trade * 0.5
        wins = [t for t in recent if t['pnl'] > 0]
        losses = [t for t in recent if t['pnl'] <= 0]
        win_rate = len(wins) / len(recent)
        if not wins or not losses:
            return self.config.max_risk_per_trade * 0.5
        avg_win = np.mean([t['pnl_pct'] for t in wins])
        avg_loss = abs(np.mean([t['pnl_pct'] for t in losses]))
        if avg_loss == 0:
            return self.config.max_risk_per_trade
        b = avg_win / avg_loss
        q = 1 - win_rate
        kelly = (win_rate * b - q) / b
        kelly_adj = max(0, kelly * self.config.kelly_fraction)
        risk_floor = self.config.max_risk_per_trade * 0.2
        return min(max(risk_floor, kelly_adj), self.config.max_risk_per_trade)

    def get_tp_sl_multipliers(self, regime: MarketRegime):
        if regime == MarketRegime.BULL_TREND or regime == MarketRegime.BEAR_TREND:
            return self.config.tp_atr_mult_trend, self.config.sl_atr_mult_trend
        elif regime == MarketRegime.MEAN_REVERSION:
            return self.config.tp_atr_mult_range, self.config.sl_atr_mult_range
        else:
            return self.config.tp_atr_mult_volatile, self.config.sl_atr_mult_volatile

    def get_trail_mult(self, regime: MarketRegime) -> float:
        if regime == MarketRegime.BULL_TREND or regime == MarketRegime.BEAR_TREND:
            return self.config.trail_atr_mult_trend
        elif regime == MarketRegime.MEAN_REVERSION:
            return self.config.trail_atr_mult_range
        return self.config.trail_atr_mult_volatile

    def get_position_size(self, capital, entry_price, atr, regime,
                          drawdown_factor=1.0):
        kelly_frac = self.get_kelly_fraction()
        risk_amount = capital * kelly_frac * drawdown_factor
        if regime == MarketRegime.HIGH_VOLATILITY:
            risk_amount *= 0.7
        _, sl_mult = self.get_tp_sl_multipliers(regime)
        sl_distance = atr * sl_mult
        if sl_distance <= 0 or entry_price <= 0:
            return 0.0
        return risk_amount / sl_distance

    def record_trade(self, trade: Dict):
        self.trade_history.append(trade)
        if trade.get('exit_reason') == 'stop_loss':
            self.consecutive_stops += 1
        else:
            self.consecutive_stops = 0


# ════════════════════════════════════════════════════════════════
# CAPA 7: ANTI-DRAWDOWN SYSTEM
# ════════════════════════════════════════════════════════════════

class AntiDrawdownSystem:
    def __init__(self, config: NexusOmegaConfig):
        self.config = config
        self.peak_equity = config.initial_capital
        self.cooldown_until = 0
        self.kill_switch_until = 0
        self.week_start_equity = config.initial_capital
        self.week_start_bar = 0

    def update(self, bar_idx: int, equity: float, day_start_equity: float,
               consecutive_stops: int):
        """Retorna (can_trade: bool, size_factor: float)."""
        # Actualizar peak
        if equity > self.peak_equity:
            self.peak_equity = equity

        # Kill switch check
        if self.peak_equity > 0:
            dd_from_peak = (self.peak_equity - equity) / self.peak_equity
            if dd_from_peak >= self.config.kill_switch_pct:
                self.kill_switch_until = bar_idx + self.config.kill_switch_bars
        if bar_idx < self.kill_switch_until:
            return False, 0.0

        # Cooldown por stops consecutivos
        if consecutive_stops >= self.config.consecutive_stops_cooldown:
            self.cooldown_until = bar_idx + self.config.cooldown_bars
        if bar_idx < self.cooldown_until:
            return False, 0.0

        # Circuit breaker diario
        if day_start_equity > 0:
            daily_dd = (day_start_equity - equity) / day_start_equity
            if daily_dd >= self.config.daily_max_drawdown:
                return False, 0.0

        # Reducción semanal (cada 168 velas ~ 1 semana)
        size_factor = 1.0
        if bar_idx - self.week_start_bar >= 168:
            self.week_start_equity = equity
            self.week_start_bar = bar_idx
        if self.week_start_equity > 0:
            weekly_dd = (self.week_start_equity - equity) / self.week_start_equity
            if weekly_dd >= self.config.weekly_drawdown_reduce:
                size_factor = 0.5

        return True, size_factor


# ════════════════════════════════════════════════════════════════
# MOTOR PRINCIPAL: NEXUS OMEGA
# ════════════════════════════════════════════════════════════════

class NexusOmega:
    def __init__(self, config: NexusOmegaConfig):
        self.config = config
        self.regime_detector = RegimeDetectorV2(config)
        self.risk_manager = InstitutionalRiskManager(config)
        self.meta_learner = MetaLearner(config)
        self.anti_dd = AntiDrawdownSystem(config)

    def run_backtest(self, df: pd.DataFrame) -> Dict:
        """Ejecuta backtest con las 7 capas de NEXUS OMEGA."""
        high = df['High'].values.astype(float)
        low = df['Low'].values.astype(float)
        close = df['Close'].values.astype(float)
        vol = df['Volume'].values.astype(float)
        n = len(df)

        capital = self.config.initial_capital
        equity_curve = [capital]
        regimes = np.full(n, MarketRegime.MEAN_REVERSION)
        atr_arr = calc_atr(high, low, close, self.config.atr_period)

        # ═══ PRE-CÁLCULOS VECTORIZADOS ═══
        print("  [NEXUS OMEGA] Pre-calculando 8 señales multi-factor...")
        signals = precompute_8_signals(high, low, close, vol, self.config)

        print("  [NEXUS OMEGA] Pre-calculando squeeze + estructura...")
        squeeze_state, squeeze_release = detect_squeeze(
            high, low, close, self.config.bb_period, self.config.bb_std,
            self.config.kc_period, self.config.kc_atr_mult)
        structure = detect_market_structure(high, low, self.config.pivot_len)
        momentum = calc_momentum_direction(close, self.config.momentum_period)

        # Estado
        position = None
        pyramid_count = 0
        trades = []
        warmup = max(500, max(self.config.hmm_features_windows) + 50,
                     self.config.sma_200 + 10)
        last_fit_idx = 0
        current_day = None
        day_start_equity = capital
        last_trade_bar = -999  # Para cooldown entre trades

        print(f"\n  [NEXUS OMEGA] Simulación: {n} velas, warmup={warmup}")
        print(f"  [NEXUS OMEGA] Ticker: {self.config.ticker}")

        for i in range(n):
            price = close[i]

            # Día
            ts = df.index[i]
            day = ts.date() if hasattr(ts, 'date') else None
            if day != current_day:
                current_day = day
                day_start_equity = capital

            if i < warmup:
                equity_curve.append(capital)
                continue

            if i % 2000 == 0:
                print(f"    Progreso: {i}/{n} ({i * 100 // n}%)")

            # ═══ CAPA 1: Régimen HMM v2 ═══
            if not self.regime_detector.is_fitted or (i - last_fit_idx) >= self.config.hmm_refit_every:
                fit_start = max(0, i - self.config.hmm_lookback)
                self.regime_detector.fit(close[fit_start:i + 1], vol[fit_start:i + 1])
                last_fit_idx = i

            regime = self.regime_detector.predict(
                close[max(0, i - self.config.hmm_lookback):i + 1],
                vol[max(0, i - self.config.hmm_lookback):i + 1])
            regimes[i] = regime

            # ═══ CAPA 7: Anti-Drawdown ═══
            can_trade, size_factor = self.anti_dd.update(
                i, capital, day_start_equity,
                self.risk_manager.consecutive_stops)

            current_atr = atr_arr[i] if not np.isnan(atr_arr[i]) else price * 0.02
            tp_mult, sl_mult = self.risk_manager.get_tp_sl_multipliers(regime)
            trail_mult = self.risk_manager.get_trail_mult(regime)

            # ═══ GESTIÓN DE POSICIÓN ABIERTA ═══
            if position is not None:
                # Trailing stop update
                if position['side'] == 'long':
                    new_trail = price - current_atr * trail_mult
                    if new_trail > position['sl']:
                        position['sl'] = new_trail
                    # TP
                    if high[i] >= position['tp']:
                        pnl = self._close_pos(position, position['tp'])
                        capital += pnl
                        t = self._make_record(position, i, position['tp'], pnl,
                                              capital, regime, 'take_profit')
                        trades.append(t)
                        self.risk_manager.record_trade(t)
                        self.meta_learner.record_trade(t, regime)
                        position = None
                        pyramid_count = 0
                    # SL
                    elif low[i] <= position['sl']:
                        pnl = self._close_pos(position, position['sl'])
                        capital += pnl
                        t = self._make_record(position, i, position['sl'], pnl,
                                              capital, regime, 'stop_loss')
                        trades.append(t)
                        self.risk_manager.record_trade(t)
                        self.meta_learner.record_trade(t, regime)
                        position = None
                        pyramid_count = 0
                else:  # short
                    new_trail = price + current_atr * trail_mult
                    if new_trail < position['sl']:
                        position['sl'] = new_trail
                    if low[i] <= position['tp']:
                        pnl = self._close_pos(position, position['tp'])
                        capital += pnl
                        t = self._make_record(position, i, position['tp'], pnl,
                                              capital, regime, 'take_profit')
                        trades.append(t)
                        self.risk_manager.record_trade(t)
                        self.meta_learner.record_trade(t, regime)
                        position = None
                        pyramid_count = 0
                    elif high[i] >= position['sl']:
                        pnl = self._close_pos(position, position['sl'])
                        capital += pnl
                        t = self._make_record(position, i, position['sl'], pnl,
                                              capital, regime, 'stop_loss')
                        trades.append(t)
                        self.risk_manager.record_trade(t)
                        self.meta_learner.record_trade(t, regime)
                        position = None
                        pyramid_count = 0

                # Pyramiding
                if position is not None and pyramid_count < self.config.pyramid_max_adds:
                    if position['side'] == 'long':
                        profit_atr = (price - position['entry']) / current_atr
                    else:
                        profit_atr = (position['entry'] - price) / current_atr
                    if profit_atr >= self.config.pyramid_atr_threshold * (pyramid_count + 1):
                        add_size = self.risk_manager.get_position_size(
                            capital, price, current_atr, regime, size_factor) * 0.5
                        if add_size > 0:
                            position['size'] += add_size
                            pyramid_count += 1
                            entry_cost = add_size * price * self.config.commission_pct
                            capital -= entry_cost

                if position is not None:
                    if position['side'] == 'long':
                        unrealized = (price - position['entry']) * position['size']
                    else:
                        unrealized = (position['entry'] - price) * position['size']
                    equity_curve.append(capital + unrealized)
                    continue

            if not can_trade:
                equity_curve.append(capital)
                continue

            # ═══ CAPA 2+5: Señales + Meta-Learner ═══
            weighted_long, weighted_short = self.meta_learner.apply_weights(
                {k: signals[k][i] for k in signals if k.startswith('s')}, regime)

            # ═══ CAPA 3: Squeeze Bonus ═══
            if squeeze_release[i] == 1:
                if momentum[i] > 0:
                    weighted_long += self.config.squeeze_bonus
                elif momentum[i] < 0:
                    weighted_short += self.config.squeeze_bonus

            # ═══ CAPA 4: Market Structure Penalty (suavizado) ═══
            struct = structure[i]
            if struct == -1:
                weighted_long *= 0.4  # Penalizar longs en estructura bajista
            elif struct == 1:
                weighted_short *= 0.4  # Penalizar shorts en estructura alcista

            # Threshold adaptativo
            threshold = self.meta_learner.get_confluence_threshold(regime)

            # Score absoluto + cooldown entre trades
            action = None
            bars_since_last = i - last_trade_bar
            if bars_since_last >= self.config.min_bars_between_trades:
                if weighted_long >= threshold and weighted_long > weighted_short:
                    action = 'long'
                elif weighted_short >= threshold and weighted_short > weighted_long:
                    action = 'short'

            # ═══ EJECUCIÓN ═══
            if action is not None:
                last_trade_bar = i
                size = self.risk_manager.get_position_size(
                    capital, price, current_atr, regime, size_factor)
                if size > 0 and capital > 0:
                    entry_cost = size * price * self.config.commission_pct
                    capital -= entry_cost
                    sl_dist = current_atr * sl_mult
                    tp_dist = current_atr * tp_mult
                    if action == 'long':
                        sl = price - sl_dist
                        tp = price + tp_dist
                    else:
                        sl = price + sl_dist
                        tp = price - tp_dist
                    position = {
                        'side': action, 'entry': price, 'size': size,
                        'sl': sl, 'tp': tp, 'entry_idx': i,
                    }
                    pyramid_count = 0

            equity_curve.append(capital)

        # Cerrar posición final
        if position is not None:
            pnl = self._close_pos(position, close[-1])
            capital += pnl
            trades.append(self._make_record(
                position, n - 1, close[-1], pnl, capital,
                int(regimes[-1]), 'end_of_data'))
            equity_curve[-1] = capital

        metrics = self._compute_metrics(equity_curve, trades, df, close, warmup)
        metrics['trades'] = trades
        metrics['equity_curve'] = equity_curve
        metrics['regimes'] = regimes
        return metrics

    def _close_pos(self, pos, exit_price):
        if pos['side'] == 'long':
            gross = (exit_price - pos['entry']) * pos['size']
        else:
            gross = (pos['entry'] - exit_price) * pos['size']
        comm = pos['size'] * exit_price * self.config.commission_pct
        return gross - comm

    def _make_record(self, pos, exit_idx, exit_price, pnl, capital, regime, reason):
        return {
            'entry_idx': pos['entry_idx'], 'exit_idx': exit_idx,
            'side': pos['side'], 'entry_price': pos['entry'],
            'exit_price': exit_price, 'pnl': pnl,
            'pnl_pct': pnl / capital * 100 if capital > 0 else 0,
            'regime': int(regime), 'exit_reason': reason,
        }

    def _compute_metrics(self, equity_curve, trades, df, close, warmup):
        eq = np.array(equity_curve)
        initial = self.config.initial_capital
        final = eq[-1]
        total_return = (final - initial) / initial * 100

        running_max = np.maximum.accumulate(eq)
        drawdown = (eq - running_max) / np.where(running_max > 0, running_max, 1) * 100
        max_dd = np.min(drawdown)

        returns = np.diff(eq) / np.where(eq[:-1] > 0, eq[:-1], 1)
        returns = returns[~np.isnan(returns)]
        sharpe = (np.mean(returns) / np.std(returns) * np.sqrt(8760)
                  if len(returns) > 0 and np.std(returns) > 0 else 0.0)

        downside = returns[returns < 0]
        sortino = (np.mean(returns) / np.std(downside) * np.sqrt(8760)
                   if len(downside) > 0 and np.std(downside) > 0 else 0.0)

        if trades:
            wins = [t for t in trades if t['pnl'] > 0]
            losses_l = [t for t in trades if t['pnl'] <= 0]
            win_rate = len(wins) / len(trades) * 100
            avg_win = np.mean([t['pnl_pct'] for t in wins]) if wins else 0
            avg_loss = np.mean([t['pnl_pct'] for t in losses_l]) if losses_l else 0
            gp = sum(t['pnl'] for t in trades if t['pnl'] > 0)
            gl = abs(sum(t['pnl'] for t in trades if t['pnl'] < 0))
            profit_factor = gp / gl if gl > 0 else float('inf')
        else:
            win_rate = avg_win = avg_loss = profit_factor = 0

        bnh = (close[-1] - close[warmup]) / close[warmup] * 100 if close[warmup] > 0 else 0

        return {
            'initial_capital': initial, 'final_capital': final,
            'total_return_pct': total_return, 'buy_hold_return_pct': bnh,
            'max_drawdown_pct': max_dd, 'sharpe_ratio': sharpe,
            'sortino_ratio': sortino, 'total_trades': len(trades),
            'win_rate_pct': win_rate, 'avg_win_pct': avg_win,
            'avg_loss_pct': avg_loss, 'profit_factor': profit_factor,
        }


# ==============================================================================
# 2. CAPA 8: FILTRO DE SEÑALES RL (PPO-LSTM)
# ==============================================================================

"""
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║   NEXUS OMEGA — CAPA 8: RL SIGNAL FILTER (PPO-LSTM)                ║
║                                                                      ║
║   Filtro de señales basado en Reinforcement Learning.                ║
║   Usa PPO (Proximal Policy Optimization) con backbone LSTM          ║
║   para decidir si EJECUTAR o RECHAZAR las señales de las            ║
║   capas 1-7 de NEXUS OMEGA.                                         ║
║                                                                      ║
║   PREPARADO PARA ENTRENAR EN GPU CLOUD.                             ║
║   NO se entrena automáticamente — requiere ejecución manual.        ║
║                                                                      ║
║   Uso:                                                               ║
║     1. Entrenar:  python nexus_omega_rl_layer.py --train             ║
║     2. Evaluar:   python nexus_omega_rl_layer.py --eval              ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import io
import argparse
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from torch.distributions import Categorical
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
import warnings
import time

warnings.filterwarnings('ignore')

# Evitar error en Colab con sys.stdout
if hasattr(sys.stdout, 'buffer') and sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"[RL Layer] Dispositivo: {device}")


# ════════════════════════════════════════════════════════════════
# CONFIGURACIÓN RL
# ════════════════════════════════════════════════════════════════

@dataclass
class RLConfig:
    """Configuración del módulo RL."""
    # Arquitectura
    hidden_dim: int = 256
    lstm_layers: int = 2
    seq_len: int = 32          # Ventana temporal del LSTM
    dropout: float = 0.1

    # PPO Hiperparámetros
    lr: float = 3e-4
    gamma: float = 0.99        # Factor de descuento
    gae_lambda: float = 0.95   # GAE lambda
    clip_epsilon: float = 0.2  # PPO clipping
    value_coef: float = 0.5    # Weight del value loss
    entropy_coef: float = 0.01 # Bonus de entropía
    max_grad_norm: float = 0.5 # Gradient clipping
    ppo_epochs: int = 4        # Épocas PPO por update
    batch_size: int = 64

    # Training
    n_episodes: int = 100      # Episodios de entrenamiento
    eval_every: int = 10       # Evaluar cada N episodios
    save_every: int = 25       # Guardar modelo cada N episodios
    warmup_steps: int = 500    # Pasos de warmup (sin entrenar)

    # Reward Shaping
    commission_pct: float = 0.0005
    sortino_window: int = 48   # Ventana para calcular Sortino reward

    # Paths
    model_dir: str = "models"
    model_name: str = "nexus_omega_rl"

    # Ticker
    ticker: str = "SOL-USD"
    period: str = "2y"
    interval: str = "1h"


# ════════════════════════════════════════════════════════════════
# PPO ACTOR-CRITIC CON LSTM
# ════════════════════════════════════════════════════════════════

class PPOActorCritic(nn.Module):
    """
    Red Actor-Critic con backbone LSTM para filtrado de señales.

    Input: estado del mercado (indicadores + scores de confluencia + régimen)
    Output:
      - Actor: probabilidad de [EJECUTAR_LONG, EJECUTAR_SHORT, NO_OPERAR]
      - Critic: valor estimado del estado
    """

    def __init__(self, input_dim: int, action_dim: int = 3,
                 hidden_dim: int = 256, lstm_layers: int = 2,
                 dropout: float = 0.1):
        super().__init__()

        # Feature extractor
        self.fc_in = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
        )

        # LSTM temporal
        self.lstm = nn.LSTM(
            input_size=hidden_dim,
            hidden_size=hidden_dim,
            num_layers=lstm_layers,
            batch_first=True,
            dropout=dropout if lstm_layers > 1 else 0,
        )

        # Actor head (3 acciones: LONG, SHORT, HOLD)
        self.actor = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.GELU(),
            nn.Linear(hidden_dim // 2, action_dim),
        )

        # Critic head
        self.critic = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.GELU(),
            nn.Linear(hidden_dim // 2, 1),
        )

    def forward(self, x: torch.Tensor, hidden=None):
        """
        x: [batch, seq_len, features]
        Returns: action_logits, value, hidden_state
        """
        batch = x.shape[0]
        seq = x.shape[1]

        # Feature extraction
        x = self.fc_in(x)  # [batch, seq_len, hidden]

        # LSTM
        lstm_out, hidden = self.lstm(x, hidden)

        # Usar último timestep
        last = lstm_out[:, -1, :]  # [batch, hidden]

        action_logits = self.actor(last)
        value = self.critic(last)

        return action_logits, value.squeeze(-1), hidden


# ════════════════════════════════════════════════════════════════
# ENTORNO DE TRADING PARA RL
# ════════════════════════════════════════════════════════════════

class NexusOmegaRLEnv:
    """
    Entorno de RL que usa las señales pre-calculadas de NEXUS OMEGA.

    Estado = [8 señales long, 8 señales short, squeeze_release, structure,
              momentum, régimen (one-hot 4), RSI, MACD_hist, ATR_norm,
              posición actual, PnL no realizado normalizado]
    = 8 + 8 + 1 + 1 + 1 + 4 + 3 + 2 = 28 features

    Acciones = [0: EJECUTAR_LONG, 1: EJECUTAR_SHORT, 2: NO_OPERAR]
    """

    def __init__(self, df: pd.DataFrame, config: RLConfig):
        self.config = config
        self.df = df

        # Pre-calcular todo usando NEXUS OMEGA


        omega_config = NexusOmegaConfig(ticker=config.ticker)

        high = df['High'].values.astype(float)
        low = df['Low'].values.astype(float)
        close = df['Close'].values.astype(float)
        volume = df['Volume'].values.astype(float)

        self.close = close
        self.high = high
        self.low = low
        self.n = len(close)

        # Señales de las 7 capas
        print("  [RL Env] Pre-calculando señales NEXUS OMEGA...")
        self.signals = precompute_8_signals(high, low, close, volume, omega_config)
        _, self.squeeze_release = detect_squeeze(
            high, low, close, omega_config.bb_period, omega_config.bb_std,
            omega_config.kc_period, omega_config.kc_atr_mult)
        self.structure = detect_market_structure(high, low, omega_config.pivot_len)
        self.momentum = calc_momentum_direction(close, omega_config.momentum_period)
        self.atr = calc_atr(high, low, close, omega_config.atr_period)
        self.rsi = calc_rsi(close, omega_config.rsi_period)
        macd_line, _, self.macd_hist = calc_macd(close)

        # Régimen HMM
        print("  [RL Env] Ajustando HMM para régimen...")
        self.regime_detector = RegimeDetectorV2(omega_config)
        self.regimes = np.zeros(self.n, dtype=int)
        hmm_lookback = omega_config.hmm_lookback
        refit_every = omega_config.hmm_refit_every
        last_fit = 0

        for i in range(500, self.n):
            if not self.regime_detector.is_fitted or (i - last_fit) >= refit_every:
                fit_start = max(0, i - hmm_lookback)
                self.regime_detector.fit(close[fit_start:i+1], volume[fit_start:i+1])
                last_fit = i
            self.regimes[i] = self.regime_detector.predict(
                close[max(0, i - hmm_lookback):i+1],
                volume[max(0, i - hmm_lookback):i+1])

        # Normalizar features
        self.atr_norm = self.atr / np.where(close > 0, close, 1) * 100
        self.rsi_norm = (self.rsi - 50) / 50  # [-1, 1]
        macd_std = np.nanstd(self.macd_hist)
        self.macd_norm = self.macd_hist / (macd_std if macd_std > 0 else 1)

        # Estado del entorno
        self.n_features = 28
        self.warmup = config.warmup_steps
        self.reset()

    @property
    def state_dim(self):
        return self.n_features

    def reset(self):
        self.step_idx = self.warmup
        self.capital = 10000.0
        self.position = None
        self.equity_history = [self.capital]
        self.trades = []
        self.returns = []
        return self._get_state_sequence()

    def _get_single_state(self, idx: int) -> np.ndarray:
        """Extrae vector de estado para un timestep."""
        state = np.zeros(self.n_features, dtype=np.float32)

        if idx < 0 or idx >= self.n:
            return state

        # 8 señales long (normalizadas a [0,1])
        for j in range(1, 9):
            state[j-1] = self.signals[f's{j}_l'][idx] / 15.0

        # 8 señales short
        for j in range(1, 9):
            state[7+j] = self.signals[f's{j}_s'][idx] / 15.0

        # Squeeze release, structure, momentum
        state[16] = float(self.squeeze_release[idx])
        state[17] = float(self.structure[idx])
        state[18] = np.clip(self.momentum[idx] * 100, -1, 1)

        # Régimen one-hot (4)
        regime = int(self.regimes[idx])
        if 0 <= regime < 4:
            state[19 + regime] = 1.0

        # RSI, MACD, ATR normalizados
        state[23] = self.rsi_norm[idx] if not np.isnan(self.rsi_norm[idx]) else 0
        state[24] = np.clip(self.macd_norm[idx] if not np.isnan(self.macd_norm[idx]) else 0, -3, 3) / 3
        state[25] = np.clip(self.atr_norm[idx] if not np.isnan(self.atr_norm[idx]) else 0, 0, 10) / 10

        # Posición actual: 1 = long, -1 = short, 0 = flat
        if self.position is not None:
            state[26] = 1.0 if self.position['side'] == 'long' else -1.0
            # PnL no realizado normalizado
            if self.position['side'] == 'long':
                unrealized = (self.close[idx] - self.position['entry']) / self.position['entry']
            else:
                unrealized = (self.position['entry'] - self.close[idx]) / self.position['entry']
            state[27] = np.clip(unrealized * 10, -1, 1)

        return state

    def _get_state_sequence(self) -> np.ndarray:
        """Retorna secuencia [seq_len, features] para LSTM."""
        seq = np.zeros((self.config.seq_len, self.n_features), dtype=np.float32)
        for j in range(self.config.seq_len):
            idx = self.step_idx - self.config.seq_len + 1 + j
            seq[j] = self._get_single_state(idx)
        return seq

    def step(self, action: int) -> Tuple[np.ndarray, float, bool]:
        """
        Ejecuta acción en el entorno.
        action: 0=LONG, 1=SHORT, 2=HOLD

        Returns: (next_state, reward, done)
        """
        idx = self.step_idx
        price = self.close[idx]
        atr = self.atr[idx] if not np.isnan(self.atr[idx]) else price * 0.02
        reward = 0.0

        # Cerrar posición existente si hay señal contraria
        if self.position is not None:
            if self.position['side'] == 'long':
                unrealized = (price - self.position['entry']) / self.position['entry']
                # Cerrar si: acción SHORT, o SL/TP hit
                sl_hit = self.low[idx] <= self.position['sl']
                tp_hit = self.high[idx] >= self.position['tp']
                close_pos = (action == 1) or sl_hit or tp_hit

                if close_pos:
                    if tp_hit:
                        exit_price = self.position['tp']
                    elif sl_hit:
                        exit_price = self.position['sl']
                    else:
                        exit_price = price
                    pnl_pct = (exit_price - self.position['entry']) / self.position['entry']
                    pnl_pct -= self.config.commission_pct * 2  # Entry + exit commission
                    self.returns.append(pnl_pct)
                    reward = pnl_pct * 100  # Escalar para RL
                    self.capital *= (1 + pnl_pct)
                    self.trades.append({
                        'pnl_pct': pnl_pct * 100,
                        'side': 'long',
                        'entry': self.position['entry'],
                        'exit': exit_price
                    })
                    self.position = None

            elif self.position['side'] == 'short':
                sl_hit = self.high[idx] >= self.position['sl']
                tp_hit = self.low[idx] <= self.position['tp']
                close_pos = (action == 0) or sl_hit or tp_hit

                if close_pos:
                    if tp_hit:
                        exit_price = self.position['tp']
                    elif sl_hit:
                        exit_price = self.position['sl']
                    else:
                        exit_price = price
                    pnl_pct = (self.position['entry'] - exit_price) / self.position['entry']
                    pnl_pct -= self.config.commission_pct * 2
                    self.returns.append(pnl_pct)
                    reward = pnl_pct * 100
                    self.capital *= (1 + pnl_pct)
                    self.trades.append({
                        'pnl_pct': pnl_pct * 100,
                        'side': 'short',
                        'entry': self.position['entry'],
                        'exit': exit_price
                    })
                    self.position = None

        # Abrir nueva posición
        if self.position is None:
            if action == 0:  # LONG
                sl = price - atr * 1.5
                tp = price + atr * 3.5
                self.position = {
                    'side': 'long', 'entry': price,
                    'sl': sl, 'tp': tp
                }
                reward -= 0.001  # Pequeño costo por trading

            elif action == 1:  # SHORT
                sl = price + atr * 1.5
                tp = price - atr * 3.5
                self.position = {
                    'side': 'short', 'entry': price,
                    'sl': sl, 'tp': tp
                }
                reward -= 0.001

        # Reward shaping: bonus por Sortino
        if len(self.returns) >= self.config.sortino_window:
            recent = np.array(self.returns[-self.config.sortino_window:])
            downside = recent[recent < 0]
            if len(downside) > 0 and np.std(downside) > 0:
                sortino = np.mean(recent) / np.std(downside)
                reward += sortino * 0.1  # Bonus suave

        # Avanzar
        self.equity_history.append(self.capital)
        self.step_idx += 1
        done = self.step_idx >= self.n - 1

        if done:
            # Cerrar posición al final
            if self.position is not None:
                exit_price = self.close[self.step_idx] if self.step_idx < self.n else price
                if self.position['side'] == 'long':
                    pnl_pct = (exit_price - self.position['entry']) / self.position['entry']
                else:
                    pnl_pct = (self.position['entry'] - exit_price) / self.position['entry']
                pnl_pct -= self.config.commission_pct * 2
                self.capital *= (1 + pnl_pct)
                self.position = None

        return self._get_state_sequence(), reward, done


# ════════════════════════════════════════════════════════════════
# PPO AGENT
# ════════════════════════════════════════════════════════════════

class PPOMemory:
    """Buffer de experiencias para PPO."""
    def __init__(self):
        self.states = []
        self.actions = []
        self.rewards = []
        self.values = []
        self.log_probs = []
        self.dones = []

    def store(self, state, action, reward, value, log_prob, done):
        self.states.append(state)
        self.actions.append(action)
        self.rewards.append(reward)
        self.values.append(value)
        self.log_probs.append(log_prob)
        self.dones.append(done)

    def clear(self):
        self.states.clear()
        self.actions.clear()
        self.rewards.clear()
        self.values.clear()
        self.log_probs.clear()
        self.dones.clear()

    def compute_gae(self, last_value: float, gamma: float, lam: float):
        """Calcula Generalized Advantage Estimation."""
        rewards = np.array(self.rewards)
        values = np.array(self.values + [last_value])
        dones = np.array(self.dones)

        advantages = np.zeros_like(rewards, dtype=np.float32)
        gae = 0
        for t in reversed(range(len(rewards))):
            delta = rewards[t] + gamma * values[t+1] * (1 - dones[t]) - values[t]
            gae = delta + gamma * lam * (1 - dones[t]) * gae
            advantages[t] = gae

        returns = advantages + np.array(self.values)
        return advantages, returns


class PPOAgent:
    """Agente PPO para el filtrado de señales."""

    def __init__(self, state_dim: int, config: RLConfig):
        self.config = config
        self.model = PPOActorCritic(
            input_dim=state_dim,
            action_dim=3,
            hidden_dim=config.hidden_dim,
            lstm_layers=config.lstm_layers,
            dropout=config.dropout,
        ).to(device)

        self.optimizer = optim.Adam(
            self.model.parameters(),
            lr=config.lr,
            eps=1e-5,
        )
        self.scheduler = optim.lr_scheduler.CosineAnnealingLR(
            self.optimizer, T_max=config.n_episodes, eta_min=1e-5
        )
        self.memory = PPOMemory()

    def select_action(self, state_seq: np.ndarray, deterministic: bool = False):
        """Selecciona acción."""
        state_t = torch.FloatTensor(state_seq).unsqueeze(0).to(device)

        with torch.no_grad():
            logits, value, _ = self.model(state_t)
            dist = Categorical(logits=logits)

            if deterministic:
                action = torch.argmax(logits, dim=-1)
            else:
                action = dist.sample()

            log_prob = dist.log_prob(action)

        return action.item(), value.item(), log_prob.item()

    def update(self):
        """Actualización PPO."""
        if len(self.memory.states) < self.config.batch_size:
            self.memory.clear()
            return 0.0

        # Obtener último valor para GAE
        last_state = torch.FloatTensor(self.memory.states[-1]).unsqueeze(0).to(device)
        with torch.no_grad():
            _, last_val, _ = self.model(last_state)
        last_value = last_val.item()

        advantages, returns = self.memory.compute_gae(
            last_value, self.config.gamma, self.config.gae_lambda)

        # Convertir a tensores
        states = torch.FloatTensor(np.array(self.memory.states)).to(device)
        actions = torch.LongTensor(self.memory.actions).to(device)
        old_log_probs = torch.FloatTensor(self.memory.log_probs).to(device)
        advantages_t = torch.FloatTensor(advantages).to(device)
        returns_t = torch.FloatTensor(returns).to(device)

        # Normalizar ventajas
        adv_std = advantages_t.std()
        if adv_std > 0:
            advantages_t = (advantages_t - advantages_t.mean()) / (adv_std + 1e-8)

        total_loss = 0.0
        n = len(states)

        for _ in range(self.config.ppo_epochs):
            # Mini-batch random
            indices = torch.randperm(n)
            for start in range(0, n, self.config.batch_size):
                end = min(start + self.config.batch_size, n)
                batch_idx = indices[start:end]

                b_states = states[batch_idx]
                b_actions = actions[batch_idx]
                b_old_lp = old_log_probs[batch_idx]
                b_adv = advantages_t[batch_idx]
                b_ret = returns_t[batch_idx]

                logits, values, _ = self.model(b_states)
                dist = Categorical(logits=logits)
                new_log_probs = dist.log_prob(b_actions)
                entropy = dist.entropy().mean()

                # PPO clipped objective
                ratio = (new_log_probs - b_old_lp).exp()
                surr1 = ratio * b_adv
                surr2 = torch.clamp(ratio,
                                    1 - self.config.clip_epsilon,
                                    1 + self.config.clip_epsilon) * b_adv
                actor_loss = -torch.min(surr1, surr2).mean()

                # Value loss
                value_loss = nn.functional.mse_loss(values, b_ret)

                # Total loss
                loss = (actor_loss
                        + self.config.value_coef * value_loss
                        - self.config.entropy_coef * entropy)

                self.optimizer.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(self.model.parameters(),
                                         self.config.max_grad_norm)
                self.optimizer.step()
                total_loss += loss.item()

        self.scheduler.step()
        self.memory.clear()
        return total_loss

    def save(self, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        torch.save({
            'model_state': self.model.state_dict(),
            'optimizer_state': self.optimizer.state_dict(),
            'config': self.config,
        }, path)
        print(f"  [RL] Modelo guardado: {path}")

    def load(self, path: str):
        checkpoint = torch.load(path, map_location=device, weights_only=False)
        self.model.load_state_dict(checkpoint['model_state'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state'])
        print(f"  [RL] Modelo cargado: {path}")


# ════════════════════════════════════════════════════════════════
# TRAINING LOOP
# ════════════════════════════════════════════════════════════════

def train_rl_filter(config: RLConfig):
    """Entrena el filtro RL sobre datos históricos."""
    import yfinance as yf

    print("\n" + "=" * 60)
    print("  NEXUS OMEGA — Entrenamiento Capa 8 RL (PPO-LSTM)")
    print("=" * 60)
    print(f"  Ticker: {config.ticker}")
    print(f"  Dispositivo: {device}")
    print(f"  Episodios: {config.n_episodes}")
    print(f"  Hidden dim: {config.hidden_dim}")
    print(f"  LSTM layers: {config.lstm_layers}")
    print(f"  Seq len: {config.seq_len}")
    print("=" * 60)

    # Descargar datos
    print(f"\n  Descargando datos {config.ticker}...")
    df = yf.download(config.ticker, period=config.period,
                     interval=config.interval, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.dropna(inplace=True)
    print(f"  → {len(df)} velas")

    # Crear entorno
    print("\n  Creando entorno RL...")
    env = NexusOmegaRLEnv(df, config)

    # Crear agente
    agent = PPOAgent(env.state_dim, config)
    print(f"  → Parámetros del modelo: {sum(p.numel() for p in agent.model.parameters()):,}")

    # Training loop
    best_return = -float('inf')
    model_path = os.path.join(config.model_dir, f"{config.model_name}_{config.ticker.replace('-','_').lower()}.pt")

    print(f"\n  ▶ Iniciando entrenamiento...")
    start_time = time.time()

    for ep in range(1, config.n_episodes + 1):
        state = env.reset()
        total_reward = 0
        steps = 0

        while True:
            action, value, log_prob = agent.select_action(state)
            next_state, reward, done = env.step(action)
            agent.memory.store(state, action, reward, value, log_prob, done)
            state = next_state
            total_reward += reward
            steps += 1

            # Update cada 2048 steps o al final del episodio
            if len(agent.memory.states) >= 2048 or done:
                loss = agent.update()

            if done:
                break

        # Métricas del episodio
        final_capital = env.capital
        ep_return = (final_capital - 10000) / 10000 * 100
        n_trades = len(env.trades)
        win_trades = len([t for t in env.trades if t['pnl_pct'] > 0])
        win_rate = win_trades / n_trades * 100 if n_trades > 0 else 0

        if ep % config.eval_every == 0 or ep == 1:
            elapsed = time.time() - start_time
            print(f"  Ep {ep:4d}/{config.n_episodes} | "
                  f"Retorno: {ep_return:+7.2f}% | "
                  f"Trades: {n_trades:3d} | "
                  f"WR: {win_rate:5.1f}% | "
                  f"Reward: {total_reward:+8.2f} | "
                  f"Time: {elapsed:.0f}s")

        # Guardar mejor modelo
        if ep_return > best_return:
            best_return = ep_return
            agent.save(model_path)

        # Checkpoint periódico
        if ep % config.save_every == 0:
            checkpoint_path = os.path.join(
                config.model_dir,
                f"{config.model_name}_{config.ticker.replace('-','_').lower()}_ep{ep}.pt")
            agent.save(checkpoint_path)

    elapsed = time.time() - start_time
    print(f"\n  ✅ Entrenamiento completado en {elapsed:.0f}s")
    print(f"  Mejor retorno: {best_return:+.2f}%")
    print(f"  Modelo final: {model_path}")

    return agent


def eval_rl_filter(config: RLConfig):
    """Evalúa el filtro RL entrenado."""
    import yfinance as yf

    model_path = os.path.join(config.model_dir, f"{config.model_name}_{config.ticker.replace('-','_').lower()}.pt")
    if not os.path.exists(model_path):
        print(f"  ❌ No se encontró modelo en: {model_path}")
        print(f"     Primero entrena con: python nexus_omega_rl_layer.py --train")
        return

    print("\n" + "=" * 60)
    print("  NEXUS OMEGA — Evaluación Capa 8 RL")
    print("=" * 60)

    df = yf.download(config.ticker, period=config.period,
                     interval=config.interval, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.dropna(inplace=True)

    env = NexusOmegaRLEnv(df, config)
    agent = PPOAgent(env.state_dim, config)
    agent.load(model_path)
    agent.model.eval()

    # Evaluación determinista
    state = env.reset()
    while True:
        action, _, _ = agent.select_action(state, deterministic=True)
        state, _, done = env.step(action)
        if done:
            break

    final_capital = env.capital
    ep_return = (final_capital - 10000) / 10000 * 100
    n_trades = len(env.trades)
    win_trades = len([t for t in env.trades if t['pnl_pct'] > 0])
    win_rate = win_trades / n_trades * 100 if n_trades > 0 else 0

    print(f"  Capital Final:  ${final_capital:,.2f}")
    print(f"  Retorno:        {ep_return:+.2f}%")
    print(f"  Trades:         {n_trades}")
    print(f"  Win Rate:       {win_rate:.1f}%")
    print("=" * 60)


# ════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════


# ==============================================================================
# 3. EJECUCIÓN DIRECTA EN COLAB
# ==============================================================================
if __name__ == "__main__":
    import os
    
    print("\n\n" + "*"*60)
    print("  🚀 INICIANDO NEXUS OMEGA RL TRAINER EN COLAB")
    print("*"*60 + "\n")
    
    # ── Mapear Google Drive para no perder modelos ──
    try:
        from google.colab import drive
        print("Montando Google Drive para asegurar guardado...")
        drive.mount('/content/drive')
        model_save_dir = "/content/drive/MyDrive/NexusOmegaModels"
        os.makedirs(model_save_dir, exist_ok=True)
        print(f"✅ Modelos se guardarán permanentemente en: {model_save_dir}\n")
    except ImportError:
        # Modo local si no está en Colab
        model_save_dir = "models"
        os.makedirs(model_save_dir, exist_ok=True)

    # ── Configuración Editable ──
    TICKER = "SOL-USD"       # Ej: "BTC-USD", "ETH-USD"
    EPISODIOS = 300          # Número de episodios (aumentar para más precisión)
    LONGITUD_SECUENCIA = 32  # Ventana temporal de velas para el LSTM
    
    config = RLConfig(
        ticker=TICKER,
        n_episodes=EPISODIOS,
        hidden_dim=256,
        lstm_layers=2,
        seq_len=LONGITUD_SECUENCIA,
        lr=3e-4,
        model_dir=model_save_dir # Usar disco permanente!
    )
    
    # Ejecutar entrenamiento
    train_rl_filter(config)
    
    print("\n\n✅ ENTRENAMIENTO FINALIZADO.")
    print(f"El modelo se ha guardado permanentemente en: {model_save_dir}")
