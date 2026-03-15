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

if sys.stdout.encoding != 'utf-8':
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
        from nexus_omega_strategy import (
            NexusOmegaConfig, precompute_8_signals, detect_squeeze,
            detect_market_structure, calc_momentum_direction,
            calc_atr, calc_rsi, calc_macd, RegimeDetectorV2
        )

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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NEXUS OMEGA — Capa 8 RL")
    parser.add_argument("--train", action="store_true", help="Entrenar el modelo RL")
    parser.add_argument("--eval", action="store_true", help="Evaluar modelo entrenado")
    parser.add_argument("--ticker", type=str, default="SOL-USD", help="Ticker (SOL-USD, BTC-USD)")
    parser.add_argument("--episodes", type=int, default=100, help="Número de episodios")
    parser.add_argument("--hidden", type=int, default=256, help="Hidden dim")
    parser.add_argument("--lstm-layers", type=int, default=2, help="Capas LSTM")
    parser.add_argument("--seq-len", type=int, default=32, help="Secuencia temporal")
    parser.add_argument("--lr", type=float, default=3e-4, help="Learning rate")

    args = parser.parse_args()

    config = RLConfig(
        ticker=args.ticker,
        n_episodes=args.episodes,
        hidden_dim=args.hidden,
        lstm_layers=args.lstm_layers,
        seq_len=args.seq_len,
        lr=args.lr,
    )

    if args.train:
        train_rl_filter(config)
    elif args.eval:
        eval_rl_filter(config)
    else:
        print("NEXUS OMEGA — Capa 8 RL (PPO-LSTM)")
        print()
        print("Uso:")
        print("  Entrenar:  python nexus_omega_rl_layer.py --train --ticker SOL-USD --episodes 200")
        print("  Evaluar:   python nexus_omega_rl_layer.py --eval --ticker SOL-USD")
        print()
        print("Opciones:")
        print("  --ticker      Ticker (SOL-USD, BTC-USD)")
        print("  --episodes    Número de episodios de entrenamiento")
        print("  --hidden      Dimensión hidden del modelo (default: 256)")
        print("  --lstm-layers Capas LSTM (default: 2)")
        print("  --seq-len     Longitud de secuencia (default: 32)")
        print("  --lr          Learning rate (default: 3e-4)")
