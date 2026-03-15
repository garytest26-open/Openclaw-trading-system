"""
╔══════════════════════════════════════════════════════════════╗
║          QUANTUM EDGE - Estrategia Cuantitativa             ║
║          Adaptativa por Régimen de Mercado                  ║
║                                                             ║
║  Capas:                                                     ║
║    1. Detector de Régimen (Hidden Markov Model)             ║
║    2. Motor de Señales Multi-Factor (5 independientes)      ║
║    3. Gestión de Riesgo Adaptativa (Kelly + ATR)            ║
║                                                             ║
║  VERSIÓN OPTIMIZADA: Pre-cálculo vectorizado de señales     ║
╚══════════════════════════════════════════════════════════════╝
"""

import numpy as np
import pandas as pd
import warnings
from dataclasses import dataclass, field
from typing import Tuple, Optional, List, Dict
from enum import IntEnum

warnings.filterwarnings('ignore')

# ============================================================
# CONFIGURACIÓN
# ============================================================

class MarketRegime(IntEnum):
    BULL_TREND = 0
    BEAR_TREND = 1
    MEAN_REVERSION = 2  # Lateral / Choppy
    HIGH_VOLATILITY = 3  # Crisis / Expansión extrema


@dataclass
class QuantumConfig:
    """Configuración central de Quantum Edge."""
    ticker: str = "SOL-USD"
    period: str = "2y"
    interval: str = "1h"

    # Régimen HMM
    hmm_n_states: int = 4
    hmm_lookback: int = 500
    hmm_refit_every: int = 500
    hmm_features_windows: List[int] = field(default_factory=lambda: [24, 72, 168])

    # Señales
    confluence_threshold: int = 60
    pivot_lookback: int = 20  # Utilizado ahora como periodo Donchian Breakout
    obv_divergence_window: int = 14
    roc_period: int = 6
    zscore_window: int = 12
    bb_period: int = 20
    bb_std: float = 2.0
    kc_period: int = 20
    kc_atr_mult: float = 1.5

    # Riesgo
    initial_capital: float = 10000.0
    commission_pct: float = 0.0005
    max_positions: int = 2
    kelly_lookback: int = 30
    kelly_fraction: float = 0.50
    max_risk_per_trade: float = 0.03
    atr_period: int = 14
    trail_atr_mult_trend: float = 3.0
    trail_atr_mult_range: float = 2.0
    trail_atr_mult_volatile: float = 3.5
    daily_max_drawdown: float = 0.08
    vol_reduction_factor: float = 0.8
    # Setup Específico por Activo
    tp_atr_mult: float = 5.0
    sl_atr_mult: float = 2.0

    def __post_init__(self):
        # Ajuste dinámico de parámetros según el nivel de ruido del activo
        if "BTC" in self.ticker:
            # Bitcoin es sucio en 1H: requiere entrar rápido (Threshold bajo)
            # y darle MUCHÍSIMO oxígeno al trade (SL Inmenso) para no ser stopeado por mechas.
            self.confluence_threshold = 45 
            self.tp_atr_mult = 5.0 # RR ~ 1:1.4
            self.sl_atr_mult = 3.5 
        else:
            # Altcoins volátiles: Trend Following agresivo (movimientos limpios)
            self.confluence_threshold = 60
            self.tp_atr_mult = 5.0 # RR 1:2.5
            self.sl_atr_mult = 2.0


# ============================================================
# INDICADORES VECTORIZADOS
# ============================================================

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
    """SMA vectorizada con cumsum."""
    cumsum = np.cumsum(np.insert(data, 0, 0))
    sma = np.full_like(data, np.nan)
    sma[period - 1:] = (cumsum[period:] - cumsum[:-period]) / period
    return sma


def calc_rolling_std(data: np.ndarray, period: int) -> np.ndarray:
    """Desviación estándar rolling vectorizada."""
    sma = calc_sma(data, period)
    cumsum_sq = np.cumsum(np.insert(data ** 2, 0, 0))
    mean_sq = (cumsum_sq[period:] - cumsum_sq[:-period]) / period
    result = np.full_like(data, np.nan)
    # Varianza = E[X²] - E[X]²
    var = mean_sq - sma[period - 1:] ** 2
    var = np.maximum(var, 0)  # Evitar negativos numéricos
    result[period - 1:] = np.sqrt(var)
    return result

def calc_keltner(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 20, mult: float = 1.5) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    sma = calc_sma(close, period)
    atr = calc_atr(high, low, close, period)
    upper = sma + (atr * mult)
    lower = sma - (atr * mult)
    return sma, upper, lower

def calc_obv(close: np.ndarray, volume: np.ndarray) -> np.ndarray:
    direction = np.sign(np.diff(close, prepend=close[0]))
    direction[0] = 0
    return np.cumsum(direction * volume)


def calc_rsi(close: np.ndarray, period: int = 14) -> np.ndarray:
    close = np.asarray(close, dtype=float).ravel()
    delta = np.diff(close, prepend=close[0])
    gain = np.where(delta > 0, delta, 0.0)
    loss = np.where(delta < 0, -delta, 0.0)
    
    avg_gain = np.zeros_like(close)
    avg_loss = np.zeros_like(close)
    
    if len(close) > period:
        avg_gain[period] = np.mean(gain[1:period+1])
        avg_loss[period] = np.mean(loss[1:period+1])
        for i in range(period + 1, len(close)):
            avg_gain[i] = (avg_gain[i-1] * (period - 1) + gain[i]) / period
            avg_loss[i] = (avg_loss[i-1] * (period - 1) + loss[i]) / period
            
    # Manejar división por cero
    rs = np.divide(avg_gain, avg_loss, out=np.zeros_like(avg_gain), where=avg_loss!=0)
    rsi = 100 - (100 / (1 + rs))
    # Si avg_loss es 0 y avg_gain > 0, rsi es 100
    rsi = np.where((avg_loss == 0) & (avg_gain > 0), 100, rsi)
    # Si ambos son 0, rsi es 50
    rsi = np.where((avg_loss == 0) & (avg_gain == 0), 50, rsi)
    rsi[:period] = np.nan
    return rsi

def calc_macd(close: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    ema_fast = calc_ema(close, fast)
    ema_slow = calc_ema(close, slow)
    macd_line = ema_fast - ema_slow
    
    # Filtrar NaNs para el cálculo de la señal, luego rellenar
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

# ============================================================
# PRE-CALCULADOR DE SEÑALES VECTORIZADO
# ============================================================

def precompute_all_signals(high: np.ndarray, low: np.ndarray,
                           close: np.ndarray, volume: np.ndarray,
                           config: QuantumConfig) -> Dict[str, np.ndarray]:
    """
    Pre-calcula TODAS las señales vectorizadamente.
    Retorna arrays de scores (long, short) para cada señal.
    """
    high = np.asarray(high, dtype=float).ravel()
    low = np.asarray(low, dtype=float).ravel()
    close = np.asarray(close, dtype=float).ravel()
    volume = np.asarray(volume, dtype=float).ravel()
    
    n = len(close)
    print("  Pre-calculando señales vectorizadas...")

    # ─── MODO TREND FOLLOWING (Estándar para todos los Tickers) ───
    print("  [INFO] Ejecutando motor de señales en modo TREND FOLLOWING.")
    # ─── Señal 1: EMA Trend Alignment ───
    s1_long = np.zeros(n, dtype=int)
    s1_short = np.zeros(n, dtype=int)
    ema9 = calc_ema(close, 9)
    ema21 = calc_ema(close, 21)
    
    for i in range(21, n):
        if ema9[i] > ema21[i]:
            s1_long[i] = 20
        elif ema9[i] < ema21[i]:
            s1_short[i] = 20

    # ─── Señal 2: RSI Trend ───
    s2_long = np.zeros(n, dtype=int)
    s2_short = np.zeros(n, dtype=int)
    rsi = calc_rsi(close, 14)

    for i in range(15, n):
        if np.isnan(rsi[i]): continue
        if rsi[i] >= 55:
            s2_long[i] = 20
        elif rsi[i] <= 45:
            s2_short[i] = 20
        elif rsi[i] > 50:
            s2_long[i] = 10
        elif rsi[i] < 50:
            s2_short[i] = 10

        # ─── Señal 3: Momentum ROC ───
        s3_long = np.zeros(n, dtype=int)
        s3_short = np.zeros(n, dtype=int)
        roc_p = 6
        for i in range(roc_p, n):
            roc_val = (close[i] - close[i - roc_p]) / close[i - roc_p]
            if roc_val > 0.01:
                s3_long[i] = 20
            elif roc_val < -0.01:
                s3_short[i] = 20
            elif roc_val > 0:
                s3_long[i] = 10
            elif roc_val < 0:
                s3_short[i] = 10

        # ─── Señal 4: MACD Histogram ───
        s4_long = np.zeros(n, dtype=int)
        s4_short = np.zeros(n, dtype=int)
        _, _, macd_hist = calc_macd(close)
        
        for i in range(26, n):
            if np.isnan(macd_hist[i]): continue
            if macd_hist[i] > 0:
                s4_long[i] = 20
            elif macd_hist[i] < 0:
                s4_short[i] = 20

        # ─── Señal 5: Price vs SMA50 ───
        s5_long = np.zeros(n, dtype=int)
        s5_short = np.zeros(n, dtype=int)
        sma50 = calc_sma(close, 50)
        
        for i in range(50, n):
            if np.isnan(sma50[i]): continue
            if close[i] > sma50[i]:
                s5_long[i] = 20
            elif close[i] < sma50[i]:
                s5_short[i] = 20

    long_score = s1_long + s2_long + s3_long + s4_long + s5_long
    short_score = s1_short + s2_short + s3_short + s4_short + s5_short

    print(f"  Señales pre-calculadas para {n} velas.")

    return {
        'long_score': long_score,
        'short_score': short_score,
        's1_long': s1_long, 's1_short': s1_short,
        's2_long': s2_long, 's2_short': s2_short,
        's3_long': s3_long, 's3_short': s3_short,
        's4_long': s4_long, 's4_short': s4_short,
        's5_long': s5_long, 's5_short': s5_short,
    }


# ============================================================
# CAPA 1: DETECTOR DE RÉGIMEN (HMM)
# ============================================================

class RegimeDetector:
    """HMM Gaussiano para clasificar régimen de mercado."""

    def __init__(self, config: QuantumConfig):
        self.config = config
        self.model = None
        self.is_fitted = False
        self._state_mapping = {}
        self._feat_mean = None
        self._feat_std = None

    def _extract_features(self, close: np.ndarray) -> np.ndarray:
        """Feature extraction vectorizada para HMM."""
        log_ret = np.diff(np.log(close), prepend=np.log(close[0]))
        features_list = []
        for w in self.config.hmm_features_windows:
            # Cumulative return (rolling sum via cumsum)
            cumsum = np.cumsum(log_ret)
            cumret = np.zeros_like(log_ret)
            cumret[w:] = cumsum[w:] - cumsum[:-w]
            features_list.append(cumret)

            # Realized volatility (rolling std)
            vol = calc_rolling_std(log_ret, w)
            vol = np.nan_to_num(vol, nan=0.0)
            features_list.append(vol)
        return np.column_stack(features_list)

    def _normalize_features(self, features: np.ndarray, fit: bool = False) -> np.ndarray:
        if fit:
            self._feat_mean = np.mean(features, axis=0)
            self._feat_std = np.std(features, axis=0)
            self._feat_std = np.where(self._feat_std < 1e-10, 1.0, self._feat_std)
        if self._feat_mean is None:
            return features
        return (features - self._feat_mean) / self._feat_std

    def _map_states(self, means: np.ndarray):
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

    def fit(self, close: np.ndarray):
        from hmmlearn.hmm import GaussianHMM
        features = self._extract_features(close)
        max_w = max(self.config.hmm_features_windows)
        features_valid = features[max_w:]
        if len(features_valid) < 50:
            return

        features_valid = self._normalize_features(features_valid, fit=True)
        try:
            self.model = GaussianHMM(
                n_components=self.config.hmm_n_states,
                covariance_type="diag",
                n_iter=30,
                random_state=42,
                tol=0.01
            )
            self.model.fit(features_valid)
            self._map_states(self.model.means_)
            self.is_fitted = True
        except Exception:
            if not self.is_fitted:
                self._state_mapping = {i: MarketRegime.MEAN_REVERSION
                                       for i in range(self.config.hmm_n_states)}

    def predict(self, close: np.ndarray) -> MarketRegime:
        if not self.is_fitted:
            return MarketRegime.MEAN_REVERSION
        try:
            features = self._extract_features(close)
            max_w = max(self.config.hmm_features_windows)
            features_valid = features[max_w:]
            if len(features_valid) == 0:
                return MarketRegime.MEAN_REVERSION
            features_valid = self._normalize_features(features_valid, fit=False)
            states = self.model.predict(features_valid)
            return self._state_mapping.get(states[-1], MarketRegime.MEAN_REVERSION)
        except Exception:
            return MarketRegime.MEAN_REVERSION


# ============================================================
# CAPA 3: GESTIÓN DE RIESGO ADAPTATIVA
# ============================================================

class AdaptiveRiskManager:
    def __init__(self, config: QuantumConfig):
        self.config = config
        self.trade_history: List[Dict] = []

    def get_kelly_fraction(self) -> float:
        recent = self.trade_history[-self.config.kelly_lookback:]
        if len(recent) < 5:
            return self.config.max_risk_per_trade * 0.5

        wins = [t for t in recent if t['pnl_pct'] > 0]
        losses = [t for t in recent if t['pnl_pct'] <= 0]
        win_rate = len(wins) / len(recent)
        if len(wins) == 0 or len(losses) == 0:
            return self.config.max_risk_per_trade * 0.5

        avg_win = np.mean([t['pnl_pct'] for t in wins])
        avg_loss = abs(np.mean([t['pnl_pct'] for t in losses]))
        if avg_loss == 0:
            return self.config.max_risk_per_trade

        b = avg_win / avg_loss
        q = 1 - win_rate
        kelly = (win_rate * b - q) / b
        kelly_adjusted = max(0, kelly * self.config.kelly_fraction)
        
        # Floor de riesgo mínimo para nunca dejar de operar (20% del riesgo máximo)
        risk_floor = self.config.max_risk_per_trade * 0.2
        final_kelly = max(risk_floor, kelly_adjusted)
        
        return min(final_kelly, self.config.max_risk_per_trade)

    def get_position_size(self, capital: float, entry_price: float,
                          atr: float, regime: MarketRegime) -> float:
        kelly_frac = self.get_kelly_fraction()
        risk_amount = capital * kelly_frac
        
        if regime == MarketRegime.HIGH_VOLATILITY:
            risk_amount *= self.config.vol_reduction_factor
            
        # Stop loss distance is set dynamically based on asset config
        sl_distance = atr * self.config.sl_atr_mult
        
        if sl_distance <= 0 or entry_price <= 0:
            return 0.0
        return risk_amount / sl_distance

    def record_trade(self, trade_info: Dict):
        self.trade_history.append(trade_info)

    def check_circuit_breaker(self, current_equity: float,
                               day_start_equity: float) -> bool:
        if day_start_equity <= 0:
            return False
        daily_return = (current_equity - day_start_equity) / day_start_equity
        return daily_return <= -self.config.daily_max_drawdown


# ============================================================
# MOTOR PRINCIPAL: QUANTUM EDGE
# ============================================================

class QuantumEdge:
    def __init__(self, config: QuantumConfig):
        self.config = config
        self.regime_detector = RegimeDetector(config)
        self.risk_manager = AdaptiveRiskManager(config)

    def run_backtest(self, df: pd.DataFrame) -> Dict:
        """Ejecuta backtest vectorizado + walk-forward HMM."""
        high_arr = df['High'].values.astype(float)
        low_arr = df['Low'].values.astype(float)
        close_arr = df['Close'].values.astype(float)
        volume_arr = df['Volume'].values.astype(float)

        n = len(df)
        capital = self.config.initial_capital
        equity_curve = [capital]
        regimes = np.full(n, MarketRegime.MEAN_REVERSION)
        atr_arr = calc_atr(high_arr, low_arr, close_arr, self.config.atr_period)

        # ═══ PRE-CALCULAR TODAS LAS SEÑALES ═══
        signals = precompute_all_signals(high_arr, low_arr, close_arr, volume_arr, self.config)
        long_scores = signals['long_score']
        short_scores = signals['short_score']

        # Estado
        position = None
        trades = []
        warmup = max(500, max(self.config.hmm_features_windows) + 50)
        last_fit_idx = 0
        current_day = None
        day_start_equity = capital

        print(f"\n  Ejecutando simulación de trading: {n} velas, warmup={warmup}")

        for i in range(n):
            price = close_arr[i]

            # Día (circuit breaker)
            ts = df.index[i]
            day = ts.date() if hasattr(ts, 'date') else None
            if day != current_day:
                current_day = day
                day_start_equity = capital

            if i < warmup:
                equity_curve.append(capital)
                continue

            # Progreso
            if i % 2000 == 0:
                print(f"    Progreso: {i}/{n} velas ({i*100//n}%)")

            # ═══ CAPA 1: Régimen HMM (walk-forward) ═══
            if not self.regime_detector.is_fitted or (i - last_fit_idx) >= self.config.hmm_refit_every:
                fit_start = max(0, i - self.config.hmm_lookback)
                self.regime_detector.fit(close_arr[fit_start:i + 1])
                last_fit_idx = i

            regime = self.regime_detector.predict(
                close_arr[max(0, i - self.config.hmm_lookback):i + 1]
            )
            regimes[i] = regime

            # Circuit breaker
            if self.risk_manager.check_circuit_breaker(capital, day_start_equity):
                if position is not None:
                    pnl = self._close_position(position, price)
                    capital += pnl
                    trades.append(self._make_trade_record(
                        position, i, price, pnl, capital, regime, 'circuit_breaker'))
                    self.risk_manager.record_trade(trades[-1])
                    position = None
                equity_curve.append(capital)
                continue

            current_atr = atr_arr[i] if not np.isnan(atr_arr[i]) else price * 0.02

            # ═══ GESTIÓN DE POSICIÓN ABIERTA (TP / SL Fijos) ═══
            if position is not None:
                if position['side'] == 'long':
                    # Chequear Take Profit
                    if high_arr[i] >= position['tp']:
                        exit_price = position['tp']
                        pnl = self._close_position(position, exit_price)
                        capital += pnl
                        trades.append(self._make_trade_record(
                            position, i, exit_price, pnl, capital, regime, 'take_profit'))
                        self.risk_manager.record_trade(trades[-1])
                        position = None
                    # Chequear Stop Loss
                    elif low_arr[i] <= position['sl']:
                        exit_price = position['sl']
                        pnl = self._close_position(position, exit_price)
                        capital += pnl
                        trades.append(self._make_trade_record(
                            position, i, exit_price, pnl, capital, regime, 'stop_loss'))
                        self.risk_manager.record_trade(trades[-1])
                        position = None
                else:  # short
                    if low_arr[i] <= position['tp']:
                        exit_price = position['tp']
                        pnl = self._close_position(position, exit_price)
                        capital += pnl
                        trades.append(self._make_trade_record(
                            position, i, exit_price, pnl, capital, regime, 'take_profit'))
                        self.risk_manager.record_trade(trades[-1])
                        position = None
                    elif high_arr[i] >= position['sl']:
                        exit_price = position['sl']
                        pnl = self._close_position(position, exit_price)
                        capital += pnl
                        trades.append(self._make_trade_record(
                            position, i, exit_price, pnl, capital, regime, 'stop_loss'))
                        self.risk_manager.record_trade(trades[-1])
                        position = None

                if position is not None:
                    if position['side'] == 'long':
                        unrealized = (price - position['entry']) * position['size']
                    else:
                        unrealized = (position['entry'] - price) * position['size']
                    equity_curve.append(capital + unrealized)
                    continue

            # ═══ CAPA 2: Señales (pre-calculadas) ═══
            ls = int(long_scores[i])
            ss = int(short_scores[i])
            action = None

            # ═══ CAPA 3: Ejecutar ═══
            prev_ls = int(long_scores[i-1]) if i > 0 else 0
            prev_ss = int(short_scores[i-1]) if i > 0 else 0
            
            # Disparo por Crossover para Trend Following (Cruza la barrera hoy)
            if ls >= self.config.confluence_threshold and ls > ss and prev_ls < self.config.confluence_threshold:
                action = 'long'
            elif ss >= self.config.confluence_threshold and ss > ls and prev_ss < self.config.confluence_threshold:
                action = 'short'

            # ═══ CAPA 3: Ejecutar ═══
            if action is not None:
                size = self.risk_manager.get_position_size(
                    capital, price, current_atr, regime)

                if size > 0 and capital > 0:
                    entry_cost = size * price * self.config.commission_pct
                    capital -= entry_cost

                    # Risk:Reward dinámico según la configuración del activo
                    sl_dist = current_atr * self.config.sl_atr_mult
                    tp_dist = current_atr * self.config.tp_atr_mult

                    if action == 'long':
                        sl = price - sl_dist
                        tp = price + tp_dist
                    else:
                        sl = price + sl_dist
                        tp = price - tp_dist

                    position = {
                        'side': action,
                        'entry': price,
                        'size': size,
                        'sl': sl,
                        'tp': tp,
                        'entry_idx': i,
                    }

            equity_curve.append(capital)

        # Cerrar posición al final
        if position is not None:
            exit_price = close_arr[-1]
            pnl = self._close_position(position, exit_price)
            capital += pnl
            trades.append(self._make_trade_record(
                position, n - 1, exit_price, pnl, capital, int(regimes[-1]), 'end_of_data'))
            equity_curve[-1] = capital

        # Métricas
        metrics = self._compute_metrics(equity_curve, trades, df, close_arr, warmup)
        metrics['trades'] = trades
        metrics['equity_curve'] = equity_curve
        metrics['regimes'] = regimes
        return metrics

    def _close_position(self, pos: Dict, exit_price: float) -> float:
        if pos['side'] == 'long':
            gross_pnl = (exit_price - pos['entry']) * pos['size']
        else:
            gross_pnl = (pos['entry'] - exit_price) * pos['size']
        commission = pos['size'] * exit_price * self.config.commission_pct
        return gross_pnl - commission

    def _make_trade_record(self, pos: Dict, exit_idx: int, exit_price: float,
                           pnl: float, capital: float, regime: int,
                           exit_reason: str) -> Dict:
        return {
            'entry_idx': pos['entry_idx'],
            'exit_idx': exit_idx,
            'side': pos['side'],
            'entry_price': pos['entry'],
            'exit_price': exit_price,
            'pnl': pnl,
            'pnl_pct': pnl / capital * 100 if capital > 0 else 0,
            'regime': int(regime),
            'exit_reason': exit_reason,
        }

    def _compute_metrics(self, equity_curve: List[float], trades: List[Dict],
                         df: pd.DataFrame, close: np.ndarray,
                         warmup: int) -> Dict:
        eq = np.array(equity_curve)
        initial = self.config.initial_capital
        final = eq[-1]
        total_return = (final - initial) / initial * 100

        running_max = np.maximum.accumulate(eq)
        drawdown = (eq - running_max) / running_max * 100
        max_dd = np.min(drawdown)

        returns = np.diff(eq) / eq[:-1]
        returns = returns[~np.isnan(returns)]
        if len(returns) > 0 and np.std(returns) > 0:
            sharpe = np.mean(returns) / np.std(returns) * np.sqrt(8760)
        else:
            sharpe = 0.0

        downside = returns[returns < 0]
        if len(downside) > 0 and np.std(downside) > 0:
            sortino = np.mean(returns) / np.std(downside) * np.sqrt(8760)
        else:
            sortino = 0.0

        if len(trades) > 0:
            wins = [t for t in trades if t['pnl'] > 0]
            losses_list = [t for t in trades if t['pnl'] <= 0]
            win_rate = len(wins) / len(trades) * 100
            avg_win = np.mean([t['pnl_pct'] for t in wins]) if wins else 0
            avg_loss = np.mean([t['pnl_pct'] for t in losses_list]) if losses_list else 0
            gross_profit = sum(t['pnl'] for t in trades if t['pnl'] > 0)
            gross_loss = abs(sum(t['pnl'] for t in trades if t['pnl'] < 0))
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        else:
            win_rate = avg_win = avg_loss = profit_factor = 0

        bnh_return = (close[-1] - close[warmup]) / close[warmup] * 100

        return {
            'initial_capital': initial,
            'final_capital': final,
            'total_return_pct': total_return,
            'buy_hold_return_pct': bnh_return,
            'max_drawdown_pct': max_dd,
            'sharpe_ratio': sharpe,
            'sortino_ratio': sortino,
            'total_trades': len(trades),
            'win_rate_pct': win_rate,
            'avg_win_pct': avg_win,
            'avg_loss_pct': avg_loss,
            'profit_factor': profit_factor,
        }
