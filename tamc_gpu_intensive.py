import os
import sys
import subprocess

# 1. INSTALACIÓN DE DEPENDENCIAS
def install_dependencies():
    try:
        import pandas as pd
        import torch
        import yfinance as yf
    except ImportError:
        print("Instalando librerías necesarias...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "yfinance", "torch", "pandas", "numpy", "plotly"])

install_dependencies()

import numpy as np
import pandas as pd
import yfinance as yf
import torch
import torch.nn as nn
import torch.optim as optim
from torch.distributions import Categorical
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Any
import random
import time

# CONFIGURACIÓN DE DISPOSITIVO Y OPTIMIZACIÓN
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"\n>>> USANDO DISPOSITIVO: {device}")
if torch.cuda.is_available():
    print(f">>> GPU: {torch.cuda.get_device_name(0)}")
    torch.backends.cudnn.benchmark = True
    torch.set_float32_matmul_precision('high')

SEED = 42
np.random.seed(SEED)
random.seed(SEED)
torch.manual_seed(SEED)

@dataclass
class StrategyConfig:
    ticker: str = "SOL-USD"
    period: str = "2y"      
    interval: str = "1h"    
    initial_capital: float = 10000.0
    n_features: int = 10    # Features de mercado (ADX, Chop, etc)
    seq_length: int = 32    
    rl_gamma: float = 0.99
    rl_lambda: float = 0.95 # GAE parameter
    rl_learning_rate: float = 1e-4 
    ppo_clip_epsilon: float = 0.2
    ppo_epochs: int = 15    
    batch_size: int = 4096  
    train_episodes: int = 200 
    hidden_dim: int = 256   
    commission_pct: float = 0.0005
    num_envs: int = 32      # Reducido un poco para estabilidad de memoria con seq_len 32

# ============================================================
# PARTE 2: PROCESAMIENTO VECTORIZADO
# ============================================================

def robust_scaler_vec(series, window=100):
    rolling = series.rolling(window=window, min_periods=1)
    median = rolling.median()
    iqr = rolling.quantile(0.75) - rolling.quantile(0.25)
    return ((series - median) / (iqr + 1e-6)).clip(-5, 5)

def calculate_indicators(df, config):
    df = df.copy()
    close = df['Close']
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['RSI'] = 100 - (100 / (1 + gain/(loss+1e-6)))
    df['MACD_Hist'] = close.ewm(span=12).mean() - close.ewm(span=26).mean()
    df['Log_Ret'] = np.log(close / close.shift(1))
    df['SMA200'] = close.rolling(200).mean()
    df['Dist_SMA200'] = (close - df['SMA200']) / (df['SMA200'] + 1e-6)
    tr = pd.concat([close.diff().abs(), (df['High']-df['Low'])], axis=1).max(axis=1)
    df['ATR'] = tr.rolling(14).mean()
    df['ATR_Ratio'] = df['ATR'] / (tr.rolling(100).mean() + 1e-6)
    df['BB_Width'] = (close.rolling(20).std() * 4) / (close.rolling(20).mean() + 1e-6)
    df['VWAP'] = (close * df['Volume']).rolling(24).sum() / (df['Volume'].rolling(24).sum() + 1e-6)
    df['Dist_VWAP'] = (close - df['VWAP']) / (df['VWAP'] + 1e-6)
    
    # ADX & Choppiness
    df['plus_dm'] = np.where((df['High']-df['High'].shift(1)) > (df['Low'].shift(1)-df['Low']), np.maximum(df['High']-df['High'].shift(1), 0), 0)
    df['minus_dm'] = np.where((df['Low'].shift(1)-df['Low']) > (df['High']-df['High'].shift(1)), np.maximum(df['Low'].shift(1)-df['Low'], 0), 0)
    tr_s = tr.rolling(14).mean()
    plus_di = 100 * (df['plus_dm'].rolling(14).mean() / (tr_s + 1e-6))
    minus_di = 100 * (df['minus_dm'].rolling(14).mean() / (tr_s + 1e-6))
    df['ADX'] = (100 * (np.abs(plus_di - minus_di)/(plus_di + minus_di + 1e-6))).rolling(14).mean()
    df['Choppiness'] = 100 * np.log10(tr.rolling(14).sum() / (df['High'].rolling(14).max() - df['Low'].rolling(14).min() + 1e-6)) / np.log10(14)

    cols = ['RSI', 'MACD_Hist', 'Dist_SMA200', 'Log_Ret', 'ATR_Ratio', 'BB_Width', 'Dist_VWAP', 'ADX', 'Choppiness']
    for col in cols: df[f'{col}_Norm'] = robust_scaler_vec(df[col])
    return df.fillna(0)

def get_market_data(config):
    df = yf.download(config.ticker, period=config.period, interval=config.interval, auto_adjust=True, progress=False)
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(1)
    df = calculate_indicators(df, config)
    return df.iloc[205:].reset_index(drop=True)

# ============================================================
# PARTE 3: MODELO Y ENTRENAMIENTO GAE
# ============================================================

class PPOActorCritic(nn.Module):
    def __init__(self, input_dim, action_dim, hidden_dim=256):
        super().__init__()
        self.fc_in = nn.Sequential(nn.Linear(input_dim, hidden_dim), nn.LayerNorm(hidden_dim), nn.GELU())
        self.lstm = nn.LSTM(hidden_dim, hidden_dim, batch_first=True, num_layers=2)
        self.actor = nn.Sequential(nn.Linear(hidden_dim, hidden_dim), nn.GELU(), nn.Linear(hidden_dim, action_dim), nn.Softmax(dim=-1))
        self.critic = nn.Sequential(nn.Linear(hidden_dim, hidden_dim), nn.GELU(), nn.Linear(hidden_dim, 1))
        
    def forward(self, x, hidden=None):
        x = self.fc_in(x)
        lstm_out, hidden_out = self.lstm(x, hidden)
        return self.actor(lstm_out[:, -1, :]), self.critic(lstm_out[:, -1, :]), hidden_out

def compute_gae(rewards, values, next_value, dones, gamma, lmbda):
    advantages = torch.zeros_like(rewards).to(device)
    last_gae = 0
    for t in reversed(range(len(rewards))):
        if t == len(rewards) - 1:
            next_val = next_value
        else:
            next_val = values[t + 1]
        
        delta = rewards[t] + gamma * next_val * (1 - dones[t]) - values[t]
        advantages[t] = last_gae = delta + gamma * lmbda * (1 - dones[t]) * last_gae
    return advantages, advantages + values

def train():
    config = StrategyConfig()
    df_raw = get_market_data(config)
    cols = ['RSI_Norm', 'MACD_Hist_Norm', 'Dist_SMA200_Norm', 'Log_Ret_Norm', 'ATR_Ratio_Norm', 'BB_Width_Norm', 'Dist_VWAP_Norm', 'ADX_Norm', 'Choppiness_Norm']
    market_data = torch.FloatTensor(df_raw[cols].values).to(device)
    prices = torch.FloatTensor(df_raw['Close'].values).to(device)
    atrs = torch.FloatTensor(df_raw['ATR'].values).to(device)
    
    model = PPOActorCritic(config.n_features + 7, 5, config.hidden_dim).to(device)
    try: model = torch.compile(model)
    except: pass
    optimizer = optim.Adam(model.parameters(), lr=config.rl_learning_rate)
    
    print(f"\n>>> INICIANDO ENTRENAMIENTO MEJORADO (GAE + Real Rewards) - {config.num_envs} Envs")
    start_time = time.time()
    
    for ep in range(config.train_episodes):
        model.eval()
        cur_indices = torch.randint(config.seq_length, len(df_raw)-257, (config.num_envs,)).to(device)
        positions = torch.zeros(config.num_envs).to(device)
        entry_prices = torch.zeros(config.num_envs).to(device)
        balances = torch.ones(config.num_envs).to(device) * config.initial_capital
        
        mb_states, mb_actions, mb_rewards, mb_log_probs, mb_values, mb_dones = [], [], [], [], [], []
        
        for _ in range(256): # Steps per episode
            # Build States
            states_list = []
            for i in range(config.num_envs):
                idx = cur_indices[i].item()
                s = market_data[idx-config.seq_length:idx] 
                # Meta features: Pos, Unrealized PnL, etc.
                meta = torch.zeros((config.seq_length, 7)).to(device)
                p_curr = prices[idx]
                p_entry = entry_prices[i]
                unrealized = (p_curr-p_entry)/p_entry if p_entry > 0 and positions[i] > 0 else (p_entry-p_curr)/p_entry if p_entry > 0 and positions[i] < 0 else 0
                meta[:, 0] = 1.0 if positions[i] > 0 else 0.0
                meta[:, 1] = 1.0 if positions[i] < 0 else 0.0
                meta[:, 3] = unrealized * 10
                states_list.append(torch.cat([torch.zeros(config.seq_length, 1).to(device), s, meta], dim=1)) # 1+9+7 = 17
            
            states_t = torch.stack(states_list)
            with torch.no_grad():
                probs, vals, _ = model(states_t)
            
            dist = Categorical(probs)
            actions = dist.sample()
            
            # REAL REWARD CALCULATION
            rewards = torch.zeros(config.num_envs).to(device)
            for i in range(config.num_envs):
                idx = cur_indices[i].item()
                target_pct = [0.0, 0.5, 1.0, -0.5, -1.0][actions[i].item()]
                p_curr = prices[idx]
                
                # Trade PnL logic
                if target_pct != (positions[i]/balances[i] if balances[i] else 0):
                    cost = abs(target_pct*balances[i] - positions[i]) * config.commission_pct
                    balances[i] -= cost
                    positions[i] = balances[i] * target_pct
                    entry_prices[i] = p_curr
                    rewards[i] -= 0.1 # Trading penalty
                
                # Check Stop Loss (ATR based)
                pnl = (p_curr-entry_prices[i])/entry_prices[i] if positions[i] > 0 else (entry_prices[i]-p_curr)/entry_prices[i] if positions[i] < 0 else 0
                if pnl < -(2*atrs[idx]/p_curr) and positions[i] != 0:
                    balances[i] += pnl * abs(positions[i])
                    positions[i] = 0
                    rewards[i] -= 1.0 # SL penalty
                
                rewards[i] += pnl * 10 # Scaled Reward
            
            mb_states.append(states_t); mb_actions.append(actions); mb_rewards.append(rewards)
            mb_log_probs.append(dist.log_prob(actions)); mb_values.append(vals.squeeze()); mb_dones.append(torch.zeros(config.num_envs).to(device))
            cur_indices += 1
            
        # PPO UPDATE
        model.train()
        with torch.no_grad():
            _, last_v, _ = model(states_t) # Use last states
        
        advs, targets = compute_gae(torch.stack(mb_rewards), torch.stack(mb_values), last_v.squeeze(), torch.stack(mb_dones), config.rl_gamma, config.rl_lambda)
        
        # Flatten for update
        b_states = torch.cat(mb_states); b_actions = torch.cat(mb_actions)
        b_log_probs = torch.cat(mb_log_probs); b_advs = advs.view(-1); b_targets = targets.view(-1)
        
        for _ in range(config.ppo_epochs):
            inds = torch.randperm(len(b_states))
            for i in range(0, len(b_states), config.batch_size):
                sb = inds[i:i+config.batch_size]
                curr_probs, curr_vals, _ = model(b_states[sb])
                curr_dist = Categorical(curr_probs)
                
                ratio = torch.exp(curr_dist.log_prob(b_actions[sb]) - b_log_probs[sb])
                surr1 = ratio * b_advs[sb]
                surr2 = torch.clamp(ratio, 1-config.ppo_clip_epsilon, 1+config.ppo_clip_epsilon) * b_advs[sb]
                
                aloss = -torch.min(surr1, surr2).mean()
                vloss = 0.5 * (curr_vals.squeeze() - b_targets[sb]).pow(2).mean()
                entropy = curr_dist.entropy().mean()
                
                loss = aloss + 0.5 * vloss - 0.01 * entropy
                optimizer.zero_grad(); loss.backward(); optimizer.step()
        
        if (ep+1)%10 == 0:
            print(f"Ep {ep+1}/{config.train_episodes} | Avg Rew: {torch.stack(mb_rewards).mean():.4f} | Time: {time.time()-start_time:.1f}s")

    torch.save(model.state_dict(), "tamc2_improved_5090.pth")
    print(f"\n>>> FINALIZADO. Modelo guardado: 'tamc2_improved_5090.pth'")

if __name__ == "__main__":
    train()
