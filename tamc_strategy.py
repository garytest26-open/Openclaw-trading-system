# ============================================================
# ARCHIVO: tamc_strategy.py
# Estrategia de Trading Agresivo Multi-Capa (TAMC) 2.0
# Implementación: PPO (Proximal Policy Optimization) con LSTM
# Feature Engineering: Multi-Timeframe (1H + 1D), VWAP, BB Width
# ============================================================

import numpy as np
import pandas as pd
import yfinance as yf
from collections import deque
import random
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import warnings
import os
import pickle
import torch
import torch.nn as nn
import torch.optim as optim
from torch.distributions import Categorical

import warnings
import sys
# Fix Windows console encoding for emojis
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

warnings.filterwarnings('ignore')

# Configuración Global
SEED = 42
np.random.seed(SEED)
random.seed(SEED)
torch.manual_seed(SEED)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Usando dispositivo: {device}")

# ============================================================
# PARTE 1: CONFIGURACIÓN
# ============================================================

@dataclass
class StrategyConfig:
    """Configuración central de la estrategia TAMC 2.0 (Expert Edition)"""
    # General
    ticker: str = "BTC-USD"
    period: str = "2y"      
    interval: str = "1h"    
    initial_capital: float = 10000.0
    
    # RL Hyperparameters (PPO)
    n_features: int = 0
    seq_length: int = 24    # Longitud de la secuencia para LSTM (24 horas)
    rl_gamma: float = 0.99
    rl_learning_rate: float = 3e-4
    ppo_clip_epsilon: float = 0.2
    ppo_epochs: int = 4
    value_coef: float = 0.5
    entropy_coef: float = 0.01
    batch_size: int = 64
    train_episodes: int = 30
    hidden_dim: int = 128
    
    # Risk Management & Trading
    commission_pct: float = 0.0005  # 0.05% per trade (simulating taker + slippage)
    max_daily_drawdown: float = 0.05
    take_profit_ratio: float = 2.0
    stop_loss_pct: float = 0.02
    
    # Feature Engineering Params
    rsi_period: int = 14
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    atr_period: int = 14
    bb_period: int = 20
    bb_std: float = 2.0

# ============================================================
# PARTE 2 & 3: CARGA DE DATOS E INDICADORES (MULTI-TIMEFRAME)
# ============================================================

def robust_scaler(series: pd.Series, window: int = 100) -> pd.Series:
    """Normalización usando EMA robusta para evitar NaNs y suavizar cisnes negros."""
    rolling_median = series.rolling(window=window, min_periods=1).median()
    rolling_iqr = series.rolling(window=window, min_periods=1).quantile(0.75) - series.rolling(window=window, min_periods=1).quantile(0.25)
    rolling_iqr = rolling_iqr.replace(0, 1e-6) # prevent div/0
    return ((series - rolling_median) / rolling_iqr).clip(-5, 5)

def calculate_indicators(df: pd.DataFrame, config: StrategyConfig) -> pd.DataFrame:
    """Calcula indicadores técnicos avanzados para el estado del agente"""
    df = df.copy()
    
    # 1. Indicadores Básicos
    # RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=config.rsi_period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=config.rsi_period).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # MACD
    ema_fast = df['Close'].ewm(span=config.macd_fast, adjust=False).mean()
    ema_slow = df['Close'].ewm(span=config.macd_slow, adjust=False).mean()
    df['MACD'] = ema_fast - ema_slow
    df['Signal'] = df['MACD'].ewm(span=config.macd_signal, adjust=False).mean()
    df['MACD_Hist'] = df['MACD'] - df['Signal']
    
    # ATR (Volatilidad)
    high_low = df['High'] - df['Low']
    high_close = (df['High'] - df['Close'].shift()).abs()
    low_close = (df['Low'] - df['Close'].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['ATR'] = tr.rolling(window=config.atr_period).mean()
    
    # 2. Indicadores Estacionarios Avanzados (NUEVOS en TAMC 2.0)
    # Log Returns
    df['Log_Ret'] = np.log(df['Close'] / df['Close'].shift(1))
    
    # Distancia a SMA 200 (Tendencia Macro)
    sma200 = df['Close'].rolling(window=200).mean()
    df['Dist_SMA200'] = (df['Close'] - sma200) / sma200
    
    # ATR Ratio (Volatilidad Relativa: ATR corto vs ATR largo)
    atr_long = tr.rolling(window=100).mean()
    df['ATR_Ratio'] = df['ATR'] / (atr_long + 1e-6)
    
    # Bollinger Bands Width (Squeeze detector)
    sma_bb = df['Close'].rolling(window=config.bb_period).mean()
    std_bb = df['Close'].rolling(window=config.bb_period).std()
    upper_bb = sma_bb + (config.bb_std * std_bb)
    lower_bb = sma_bb - (config.bb_std * std_bb)
    df['BB_Width'] = (upper_bb - lower_bb) / sma_bb
    
    # VWAP Proxy (High+Low+Close / 3 ponderado por volumen en rolling window de 24h)
    typ_price = (df['High'] + df['Low'] + df['Close']) / 3
    cum_pv = (typ_price * df['Volume']).rolling(window=24).sum()
    cum_v = df['Volume'].rolling(window=24).sum()
    df['VWAP'] = cum_pv / (cum_v + 1e-6)
    df['Dist_VWAP'] = (df['Close'] - df['VWAP']) / df['VWAP']
    
    # Volatilidad relativa del Volumen
    df['Vol_Rel'] = df['Volume'] / (df['Volume'].rolling(window=24).mean() + 1e-6)
    
    # 3. Indicadores de Régimen de Mercado (NUEVOS en TAMC 2.0 - v2)
    # ADX (Fuerza de Tendencia)
    df['plus_dm'] = np.where((df['High'] - df['High'].shift(1)) > (df['Low'].shift(1) - df['Low']), 
                             np.maximum(df['High'] - df['High'].shift(1), 0), 0)
    df['minus_dm'] = np.where((df['Low'].shift(1) - df['Low']) > (df['High'] - df['High'].shift(1)), 
                              np.maximum(df['Low'].shift(1) - df['Low'], 0), 0)
    
    tr_smooth = tr.rolling(window=14).mean()
    plus_dm_smooth = df['plus_dm'].rolling(window=14).mean()
    minus_dm_smooth = df['minus_dm'].rolling(window=14).mean()
    
    df['plus_di'] = 100 * (plus_dm_smooth / (tr_smooth + 1e-6))
    df['minus_di'] = 100 * (minus_dm_smooth / (tr_smooth + 1e-6))
    df['dx'] = 100 * (np.abs(df['plus_di'] - df['minus_di']) / (df['plus_di'] + df['minus_di'] + 1e-6))
    df['ADX'] = df['dx'].rolling(window=14).mean()
    
    # Choppiness Index (Lateralidad)
    lookback_chop = 14
    tr_sum = tr.rolling(window=lookback_chop).sum()
    price_range = df['High'].rolling(window=lookback_chop).max() - df['Low'].rolling(window=lookback_chop).min()
    df['Choppiness'] = 100 * np.log10(tr_sum / (price_range + 1e-6)) / np.log10(lookback_chop)
    
    # Rellenar nulos intermedios y botar el bloque inestable inicial
    df.fillna(method='bfill', inplace=True)
    df.dropna(inplace=True)
    
    # 4. Normalización Robusta
    cols_to_norm = [
        'RSI', 'MACD_Hist', 'Dist_SMA200', 'Log_Ret', 'Vol_Rel', 'ATR_Ratio', 
        'BB_Width', 'Dist_VWAP', 'ADX', 'Choppiness'
    ]
    for col in cols_to_norm:
        if col in df.columns:
            df[f'{col}_Norm'] = robust_scaler(df[col])
            
    return df

def align_daily_features(df_1h: pd.DataFrame, ticker: str, period: str) -> pd.DataFrame:
    """Descarga datos diarios y los proyecta (forward fill) al marco de 1h."""
    try:
        # Download daily data
        df_1d = yf.download(ticker, period=period, interval="1d", progress=False, auto_adjust=True)
        if isinstance(df_1d.columns, pd.MultiIndex):
            df_1d.columns = df_1d.columns.droplevel(1)
        
        # Calculate Daily RSI and Macro Trend
        delta = df_1d['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df_1d['Daily_RSI'] = 100 - (100 / (1 + rs))
        df_1d['Daily_Log_Ret'] = np.log(df_1d['Close'] / df_1d['Close'].shift(1))
        
        # Clean Daily
        df_1d = df_1d[['Daily_RSI', 'Daily_Log_Ret']].dropna()
        df_1d.index = df_1d.index.tz_localize(None).normalize() # Ensure dates are at 00:00:00 and timezone-naive
        
        # Join to 1H data
        df_1h['DateOnly'] = df_1h.index.tz_localize(None).normalize()
        df_merged = df_1h.join(df_1d, on='DateOnly', how='left')
        df_merged.drop(columns=['DateOnly'], inplace=True)
        
        # Forward fill the daily signal for intraday hours
        df_merged.fillna(method='ffill', inplace=True)
        df_merged.fillna(0, inplace=True) # Fallback if first rows are empty
        
        # Normalize Daily Features
        df_merged['Daily_RSI_Norm'] = robust_scaler(df_merged['Daily_RSI'])
        df_merged['Daily_Log_Ret_Norm'] = robust_scaler(df_merged['Daily_Log_Ret'])

        return df_merged
    except Exception as e:
        print(f"Error procesando Multi-Timeframe: {e}")
        # Return fallback zeros if it fails
        df_1h['Daily_RSI_Norm'] = 0.0
        df_1h['Daily_Log_Ret_Norm'] = 0.0
        return df_1h

def get_market_data(config: StrategyConfig) -> pd.DataFrame:
    """Descarga y prepara datos de mercado Multi-Timeframe"""
    print(f"Descargando datos 1H y 1D para {config.ticker}...")
    try:
        df = yf.download(config.ticker, period=config.period, interval=config.interval, progress=False, auto_adjust=True)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
        
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()
        df = calculate_indicators(df, config)
        
        # Integrar TF Diario
        df = align_daily_features(df, config.ticker, config.period)
        
        # Limpiar filas restantes no válidas (ventana de 200 de los cálculos)
        df = df.iloc[205:].reset_index(drop=True)
        print(f"Datos finalizados: {len(df)} velas multi-timeframe.")
        return df
    except Exception as e:
        print(f"Error descargando datos: {e}")
        return pd.DataFrame()

# ============================================================
# PARTE 4: ENTORNO DE TRADING (INSTITUCIONAL SHAPING)
# ============================================================

class TradingEnvironment:
    """Entorno simulado con Comisiones Reales y Recompensa Sharpe"""
    
    def __init__(self, df: pd.DataFrame, config: StrategyConfig):
        self.df = df
        self.config = config
        self.reset()
        
    def reset(self):
        # Empezamos después del sequence_length inicial para poder tener historia
        self.current_step = self.config.seq_length
        self.done = False
        self.balance = self.config.initial_capital
        self.position = 0.0  # +Size para Long, -Size para Short
        self.entry_price = 0.0
        self.equity_curve = [self.balance]
        self.returns_history = []
        return self._get_state_sequence()
        
    def _get_single_state(self, step) -> np.ndarray:
        """Extrae el vector de estado de un timestep específico"""
        features_cols = [
            'RSI_Norm', 'MACD_Hist_Norm', 'Dist_SMA200_Norm', 'Log_Ret_Norm', 
            'Vol_Rel_Norm', 'ATR_Ratio_Norm', 'BB_Width_Norm', 'Dist_VWAP_Norm',
            'ADX_Norm', 'Choppiness_Norm'
        ]
        
        market_features = self.df.iloc[step][features_cols].values.astype(float)
        
        unrealized_pnl = 0.0
        if abs(self.position) > 0:
            current_price = self.df.iloc[step]['Close']
            if self.position > 0:
                unrealized_pnl = (current_price - self.entry_price) / self.entry_price
            else:
                unrealized_pnl = (self.entry_price - current_price) / self.entry_price
            
        position_state = np.array([
            1.0 if self.position > 0 else 0.0,
            1.0 if self.position < 0 else 0.0,
            1.0 if self.position == 0 else 0.0,
            unrealized_pnl * 10,
            0.0, 0.0, 0.0 
        ]) 
        
        return np.concatenate([market_features, position_state])
        
    def _get_state_sequence(self) -> np.ndarray:
        """Devuelve una secuencia temporal [Seq_Len, Features] para la red LSTM"""
        if self.current_step >= len(self.df):
            return np.zeros((self.config.seq_length, self.config.n_features + 7))
            
        seq = []
        for i in range(self.current_step - self.config.seq_length, self.current_step):
            seq.append(self._get_single_state(max(0, i)))
            
        return np.array(seq)
        
    def step(self, action: int) -> Tuple[np.ndarray, float, bool, Dict]:
        """Ejecuta orden, resta comisiones y calcula recompensa Sortino"""
        current_price = self.df.iloc[self.current_step]['Close']
        reward = 0.0
        trade_cost = 0.0

        # Mapeo: 0=Flat, 1=Long50%, 2=Long100%, 3=Short50%, 4=Short100%
        target_pos_pct = [0.0, 0.5, 1.0, -0.5, -1.0][action]
        target_pos_val = self.balance * target_pos_pct

        # Si hay un cambio de posición sustancial, aplicamos fee
        if abs(target_pos_val - self.position) > (self.balance * 0.01):
            
            # 1. Cerrar posición actual
            if self.position != 0:
                if self.position > 0:
                    pnl = (current_price - self.entry_price) / self.entry_price * abs(self.position)
                else:
                    pnl = (self.entry_price - current_price) / self.entry_price * abs(self.position)
                
                # Restar comisión de cierre
                close_cost = abs(self.position) * self.config.commission_pct
                trade_cost += close_cost
                self.balance += (pnl - close_cost)

            # 2. Abrir nueva posición
            if target_pos_pct != 0:
                open_cost = abs(target_pos_val) * self.config.commission_pct
                trade_cost += open_cost
                self.balance -= open_cost
                
                self.position = self.balance * target_pos_pct
                self.entry_price = current_price
            else:
                self.position = 0.0
                self.entry_price = 0.0
                
            # Fuerte penalización en el step por hacer trading (fomenta holding)
            reward -= (trade_cost / (self.balance + 1e-6)) * 50

        # === 🛡️ STOP-LOSS DINÁMICO (ATR) ===
        if self.position != 0:
            atr = self.df.iloc[self.current_step]['ATR']
            pnl_curr = (current_price - self.entry_price) / self.entry_price if self.position > 0 else (self.entry_price - current_price) / self.entry_price
            
            # Si perdemos más de 2x ATR, cerramos forzosamente (SL Dinámico)
            sl_threshold = - (2 * atr / current_price)
            if pnl_curr < sl_threshold:
                # Liquidación forzosa
                close_pnl = pnl_curr * abs(self.position)
                liq_cost = abs(self.position) * self.config.commission_pct
                self.balance += (close_pnl - liq_cost)
                self.position = 0.0
                reward -= 10.0 # Gran penalización por tocar Stop-Loss

        # === CÁLCULO EQUITY & RETURN ===
        current_equity = self.balance
        if self.position != 0:
            if self.position > 0:
                current_equity += (current_price - self.entry_price) / self.entry_price * abs(self.position)
            else:
                current_equity += (self.entry_price - current_price) / self.entry_price * abs(self.position)

        prev_equity = self.equity_curve[-1]
        
        step_return = 0.0
        if prev_equity > 0:
            step_return = (current_equity - prev_equity) / prev_equity
            self.returns_history.append(step_return)
            
        # Recompensa base por rentabilidad
        reward += step_return * 100

        # === SHARPE/SORTINO REWARD SHAPING ===
        # Penaliza la varianza negativa en los últimos periodos
        if len(self.returns_history) > 10:
            recent_rets = np.array(self.returns_history[-20:])
            # Penalizar volatilidad pura
            volatility = np.std(recent_rets) + 1e-6
            reward -= volatility * 10
            
            # Castigo Exponencial por Drawdown (Activación temprana a 2%)
            peak = max(self.equity_curve[-200:] if len(self.equity_curve) > 200 else self.equity_curve)
            if peak > 0:
                drawdown = (peak - current_equity) / peak
                if drawdown > 0.02:
                    reward -= (drawdown ** 2) * 1000  # Penalización más severa
                if drawdown < 0.01 and self.position != 0:
                    reward += 0.1 # Bonus por mantener equity cerca del pico

        # Penalización inactividad leve
        if self.position == 0:
            reward -= 0.05

        # Avanzar
        self.current_step += 1
        done = self.current_step >= len(self.df) - 1
        self.equity_curve.append(current_equity)

        next_state = self._get_state_sequence()
        return next_state, reward, done, {}


# ============================================================
# PARTE 5: PPO ACTOR-CRITIC CON LSTM (PyTorch)
# ============================================================

class PPOActorCritic(nn.Module):
    def __init__(self, input_dim, action_dim, hidden_dim=128, lstm_layers=1):
        super(PPOActorCritic, self).__init__()
        
        # Extractor de features base
        self.fc_in = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.Tanh()
        )
        
        # LSTM Memoria
        self.lstm = nn.LSTM(hidden_dim, hidden_dim, lstm_layers, batch_first=True)
        
        # Actor Head (Probabilidad de accion)
        self.actor = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.Tanh(),
            nn.Linear(hidden_dim, action_dim),
            nn.Softmax(dim=-1)
        )
        
        # Critic Head (Valor intrinseco del estado)
        self.critic = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.Tanh(),
            nn.Linear(hidden_dim, 1)
        )
        
    def forward(self, x, hidden=None):
        """x shape: [batch, seq_len, features]"""
        batch_size, seq_len, _ = x.size()
        
        x = self.fc_in(x)
        
        # LSTM procesa la secuencia
        lstm_out, hidden_out = self.lstm(x, hidden)
        
        # Solo usamos la salida del último paso temporal de la secuencia
        last_step_out = lstm_out[:, -1, :]
        
        # Evaluamos Actor y Critic
        action_probs = self.actor(last_step_out)
        state_value = self.critic(last_step_out)
        
        return action_probs, state_value, hidden_out

class PPOAgent:
    def __init__(self, config: StrategyConfig):
        self.config = config
        self.state_dim = config.n_features + 7
        self.action_dim = 5
        
        self.policy = PPOActorCritic(self.state_dim, self.action_dim, config.hidden_dim).to(device)
        self.optimizer = optim.Adam(self.policy.parameters(), lr=config.rl_learning_rate)
        
        self.gamma = config.rl_gamma
        self.clip_eps = config.ppo_clip_epsilon
        
    def select_action(self, state_seq):
        """Selecciona accion estocásticamente para explorar o dterminísticamente si eval"""
        state_tensor = torch.FloatTensor(state_seq).unsqueeze(0).to(device)
        with torch.no_grad():
            action_probs, state_value, _ = self.policy(state_tensor)
            
        dist = Categorical(action_probs)
        action = dist.sample()
        
        return action.item(), dist.log_prob(action).item(), state_value.item()
        
    def evaluate(self, state_seq):
        state_tensor = torch.FloatTensor(state_seq).unsqueeze(0).to(device)
        with torch.no_grad():
            action_probs, _, _ = self.policy(state_tensor)
        return torch.argmax(action_probs).item()

    def update(self, memory):
        """Entrena la red usando las trayectorias recolectadas (PPO Clipped Objective)"""
        states = torch.FloatTensor(np.array(memory['states'])).to(device)
        actions = torch.LongTensor(memory['actions']).to(device)
        old_log_probs = torch.FloatTensor(memory['log_probs']).to(device)
        returns = torch.FloatTensor(memory['returns']).to(device)
        advantages = torch.FloatTensor(memory['advantages']).to(device)
        
        # Normalizar advantages
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)
        
        inds = np.arange(len(states))
        
        # PPO Multi-Epoch Update
        for _ in range(self.config.ppo_epochs):
            np.random.shuffle(inds)
            for start in range(0, len(states), self.config.batch_size):
                end = start + self.config.batch_size
                m_inds = inds[start:end]
                
                batch_states = states[m_inds]
                batch_actions = actions[m_inds]
                batch_old_log_probs = old_log_probs[m_inds]
                batch_returns = returns[m_inds]
                batch_advantages = advantages[m_inds]
                
                # Re-evaluar
                action_probs, state_values, _ = self.policy(batch_states)
                dist = Categorical(action_probs)
                new_log_probs = dist.log_prob(batch_actions)
                entropy = dist.entropy().mean()
                
                # Ratio PPO
                ratios = torch.exp(new_log_probs - batch_old_log_probs)
                
                # Clipped Surrogate Loss
                surr1 = ratios * batch_advantages
                surr2 = torch.clamp(ratios, 1.0 - self.clip_eps, 1.0 + self.clip_eps) * batch_advantages
                actor_loss = -torch.min(surr1, surr2).mean()
                
                # Critic Loss (MSE)
                critic_loss = nn.MSELoss()(state_values.squeeze(), batch_returns)
                
                # Total Loss
                loss = actor_loss + (self.config.value_coef * critic_loss) - (self.config.entropy_coef * entropy)
                
                self.optimizer.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(self.policy.parameters(), max_norm=0.5)
                self.optimizer.step()

    def save_model(self, path: str):
        torch.save(self.policy.state_dict(), path)

# ============================================================
# PARTE 6: WALK-FORWARD CONTINUOUS TRAINING (LIFELONG LEARNING)
# ============================================================

def compute_gae(rewards, values, next_value, dones, gamma=0.99, tau=0.95):
    """Generalized Advantage Estimation"""
    values = values + [next_value]
    gae = 0
    returns = []
    advantages = []
    
    for step in reversed(range(len(rewards))):
        delta = rewards[step] + gamma * values[step + 1] * (1 - int(dones[step])) - values[step]
        gae = delta + gamma * tau * (1 - int(dones[step])) * gae
        advantages.insert(0, gae)
        returns.insert(0, gae + values[step])
        
    return returns, advantages

def train_tamc_ppo(ticker=None):
    """Función de entrenamiento PPO Walk-Forward simplificado."""
    print("\n=== TAMC 2.0 (Expert PPO + LSTM) Training Start ===")
    
    config = StrategyConfig()
    if ticker: config.ticker = ticker
    
    ticker_slug = config.ticker.replace("-", "_").replace("USD", "").strip("_").lower()
    model_save_path = f"models/tamc2_{ticker_slug}_ppo.pth"
    print(f"Dataset limit: {config.period} | Model Save: {model_save_path}")
    
    df = get_market_data(config)
    if df.empty: return
        
    config.n_features = 10  # 8 locales + 2 diarias
    
    # Split
    split_idx = int(len(df) * 0.8)
    train_df = df.iloc[:split_idx].reset_index(drop=True)
    val_df = df.iloc[split_idx:].reset_index(drop=True)
    
    agent = PPOAgent(config)
    env = TradingEnvironment(train_df, config)
    
    best_val_ret = -float('inf')
    
    # Train Loop
    for episode in range(config.train_episodes):
        state_seq = env.reset()
        done = False
        
        memory = {'states': [], 'actions': [], 'log_probs': [], 'rewards': [], 'values': [], 'dones': []}
        
        while not done:
            action, log_prob, val = agent.select_action(state_seq)
            next_state_seq, reward, done, _ = env.step(action)
            
            memory['states'].append(state_seq)
            memory['actions'].append(action)
            memory['log_probs'].append(log_prob)
            memory['rewards'].append(reward)
            memory['values'].append(val)
            memory['dones'].append(bool(done))
            
            state_seq = next_state_seq
            
            # PPO actualiza por Trajectory (no requiere llenar buffer total)
            # En este setup offline, procesamos on-policy toda la serie temporal de train (puede tardar por ser secuencial)
        
        train_return = (env.equity_curve[-1] - config.initial_capital) / config.initial_capital * 100
        
        # Calculate returns and advantages
        _, _, next_val = agent.select_action(state_seq)
        returns, advantages = compute_gae(memory['rewards'], memory['values'], next_val, memory['dones'])
        
        memory['returns'] = returns
        memory['advantages'] = advantages
        
        print(f"Ep {episode+1}/{config.train_episodes} Collecting Data... Updating PPO")
        agent.update(memory)
        
        # Eval
        val_env = TradingEnvironment(val_df, config)
        v_state = val_env.reset()
        v_done = False
        
        while not v_done:
            a = agent.evaluate(v_state)
            v_state, _, v_done, _ = val_env.step(a)
            
        val_return = (val_env.equity_curve[-1] - config.initial_capital) / config.initial_capital * 100
        
        print(f"Ep {episode+1} | Train Ret: {train_return:.1f}% | Val Ret: {val_return:.1f}%")
        
        if val_return > best_val_ret:
            best_val_ret = val_return
            if not os.path.exists("models"): os.makedirs("models")
            agent.save_model(model_save_path)
            print(f"  --> Nuevo Mejor Modelo Guardado: {best_val_ret:.1f}%")

if __name__ == "__main__":
    train_tamc_ppo()
