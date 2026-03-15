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
import os
import sys
import torch
from dataclasses import dataclass, field
from typing import Tuple, Optional, List, Dict
from enum import IntEnum

# Parche de compatibilidad para cargar modelos de Colab/Vast
try:
    from nexus_omega_rl_layer import RLConfig
    import __main__
    __main__.RLConfig = RLConfig
except ImportError:
    pass

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

    # ── Capa 8: RL Layer (IA) ──
    use_rl_layer: bool = True
    rl_model_name: str = "nexus_omega_rl_sol_usd_ep300.pt"
    rl_model_dir: str = "models"

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
        
        # Capa 8: RL
        self.rl_agent = None
        if self.config.use_rl_layer:
            self._init_rl_layer()

    def _init_rl_layer(self):
        """Inicializa la Capa 8 (RL) cargando el modelo entrenado."""
        try:
            from nexus_omega_rl_layer import PPOAgent, RLConfig, device
            model_path = os.path.join(self.config.rl_model_dir, self.config.rl_model_name)
            if not os.path.exists(model_path):
                print(f"  [RL] ❌ No se encontró modelo en {model_path}. Capa 8 desactivada.")
                return

            # Cargar config desde checkpoint para consistencia de arquitectura
            checkpoint = torch.load(model_path, map_location=device, weights_only=False)
            rl_config = checkpoint.get('config', RLConfig())
            
            # Input dim base del sistema (28 - ver nexus_omega_rl_layer.py)
            self.rl_agent = PPOAgent(state_dim=28, config=rl_config)
            self.rl_agent.model.load_state_dict(checkpoint['model_state'])
            self.rl_agent.model.eval()
            print(f"  [RL] ✅ Capa 8 Activada: {self.config.rl_model_name}")
        except Exception as e:
            print(f"  [RL] ⚠️ Error inicializando Capa 8: {e}")
            self.rl_agent = None

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

            # ═══ CAPA 8: FILTRADO RL (IA) ═══
            if action is not None and self.rl_agent is not None:
                # El RL agent requiere una secuencia de estados
                # Como es costoso reconstruirlo en cada paso de backtest, 
                # usamos el objeto environment interno de la capa RL si está disponible o 
                # un helper que extraiga el estado actual.
                try:
                    from nexus_omega_rl_layer import NexusOmegaRLEnv
                    if not hasattr(self, '_rl_env'):
                        self._rl_env = NexusOmegaRLEnv(df, self.rl_agent.config)
                    
                    # Sincronizamos el índice del entorno RL con el actual
                    self._rl_env.step_idx = i
                    state_seq = self._rl_env._get_state_sequence()
                    
                    # IA decide: 0=LONG, 1=SHORT, 2=HOLD
                    rl_action, _, _ = self.rl_agent.select_action(state_seq, deterministic=True)
                    
                    # Filtro: ¿Coincide la intención de la IA con la técnica?
                    if action == 'long' and rl_action != 0:
                        action = None # IA dice que no es momento para LONG
                    elif action == 'short' and rl_action != 1:
                        action = None # IA dice que no es momento para SHORT
                        
                except Exception as e:
                    # Si falla el RL por algún motivo, seguimos con la técnica para no romper el proceso
                    pass

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
