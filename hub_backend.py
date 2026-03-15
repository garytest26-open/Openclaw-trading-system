import fastapi
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.distributions import Categorical
import yfinance as yf
import gc

# ---------------------------------------------------------
# 1. Configuración Básica FastAPI
# ---------------------------------------------------------
app = fastapi.FastAPI(title="AI Trading Hub Backend (PyTorch LSTM)")

# Permitir CORS para que el HTML local pueda consultar la API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ---------------------------------------------------------
# 2. Re-Declarar Arquitectura PPO LSTM de TAMC 
# ---------------------------------------------------------
class PPOActorCritic(nn.Module):
    def __init__(self, input_dim, action_dim=5, hidden_dim=128, lstm_layers=1):
        super(PPOActorCritic, self).__init__()
        
        self.fc_in = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.Tanh()
        )
        
        self.lstm = nn.LSTM(hidden_dim, hidden_dim, lstm_layers, batch_first=True)
        
        self.actor = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.Tanh(),
            nn.Linear(hidden_dim, action_dim),
            nn.Softmax(dim=-1)
        )
        
        self.critic = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.Tanh(),
            nn.Linear(hidden_dim, 1)
        )
        
    def forward(self, x, hidden=None):
        x = self.fc_in(x)
        lstm_out, hidden_out = self.lstm(x, hidden)
        last_step_out = lstm_out[:, -1, :]
        action_probs = self.actor(last_step_out)
        state_value = self.critic(last_step_out)
        return action_probs, state_value, hidden_out

# Diccionario Global para mantener modelos cacheados en memoria
MODEL_CACHE = {}

def get_model(symbol: str):
    """Carga el modelo LSTM del disco según el símbolo, priorizando tamc2, luego tamc_best"""
    global MODEL_CACHE
    symbol_base = symbol.replace("USDT", "").replace("-USD", "").lower()
    
    if symbol_base in MODEL_CACHE:
        return MODEL_CACHE[symbol_base]
        
    import os
    model_paths = [
        f"models/tamc2_{symbol_base}_ppo.pth",
        f"models/tamc_{symbol_base}_best.pth"
    ]
    
    model_file = None
    for path in model_paths:
        if os.path.exists(path):
            model_file = path
            break
            
    if not model_file:
        print(f"No se encontró modelo LSTM para {symbol_base}. Usando fallback random (se avisa en la UI).")
        return None
        
    print(f"Cargando pesos de Inteligencia Artificial para {symbol_base} desde {model_file}...")
    
    # Tamc 1 (Best) tiene n_features dependientes. Tamc 2 usaba 10 features + 7 position states.
    # Asumimos TAMC standard format con 10 features de mercado (dist_sma, etc) + 7 de position
    input_dim = 17 
    model = PPOActorCritic(input_dim=input_dim, action_dim=5, hidden_dim=128)
    try:
        model.load_state_dict(torch.load(model_file, map_location=device))
    except Exception as e:
        # Fallback para arquitecturas mixtas
        try:
             # Typical format for TAMC v1 best models
             input_dim = 15 # 8 features locales + 7 pos
             model = PPOActorCritic(input_dim=input_dim, action_dim=5, hidden_dim=128)
             model.load_state_dict(torch.load(model_file, map_location=device))
        except Exception as e2:
             print(f"Error parseando tensores del modelo: {e2}")
             return None

    model.to(device)
    model.eval() # Modo inferencia
    MODEL_CACHE[symbol_base] = model
    return model

# ---------------------------------------------------------
# 3. Feature Engineering (Exacto a tamc_strategy.py)
# ---------------------------------------------------------
def robust_scaler(series: pd.Series, window: int = 100) -> pd.Series:
    rolling_median = series.rolling(window=window, min_periods=1).median()
    rolling_iqr = series.rolling(window=window, min_periods=1).quantile(0.75) - series.rolling(window=window, min_periods=1).quantile(0.25)
    rolling_iqr = rolling_iqr.replace(0, 1e-6)
    return ((series - rolling_median) / rolling_iqr).clip(-5, 5)

def prep_market_data(symbol: str) -> pd.DataFrame:
    # 1. Fetch 1H data
    ticker = f"{symbol.replace('USDT', '')}-USD"
    df = yf.download(ticker, period="60d", interval="1h", progress=False, auto_adjust=True)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)
    
    if len(df) < 50:
        raise ValueError("Data insuficiente de Yahoo Finance (menos de 50 velas 1h)")
        
    df = df[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()
    
    # RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # MACD
    ema_fast = df['Close'].ewm(span=12, adjust=False).mean()
    ema_slow = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema_fast - ema_slow
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['MACD'] - df['Signal']
    
    # Dist SMA
    sma200 = df['Close'].rolling(window=200).mean()
    df['Dist_SMA200'] = (df['Close'] - sma200) / sma200
    df['Log_Ret'] = np.log(df['Close'] / df['Close'].shift(1))
    
    # ATR & BB Width
    tr = pd.concat([df['High']-df['Low'], (df['High']-df['Close'].shift()).abs(), (df['Low']-df['Close'].shift()).abs()], axis=1).max(axis=1)
    df['ATR'] = tr.rolling(window=14).mean()
    atr_long = tr.rolling(window=100).mean()
    df['ATR_Ratio'] = df['ATR'] / (atr_long + 1e-6)
    
    sma_bb = df['Close'].rolling(window=20).mean()
    std_bb = df['Close'].rolling(window=20).std()
    df['Upper_BB'] = sma_bb + (2.0 * std_bb)
    df['Lower_BB'] = sma_bb - (2.0 * std_bb)
    df['BB_Width'] = (df['Upper_BB'] - df['Lower_BB']) / sma_bb
    
    # VWAP Proxy
    typ_price = (df['High'] + df['Low'] + df['Close']) / 3
    cum_pv = (typ_price * df['Volume']).rolling(window=24).sum()
    cum_v = df['Volume'].rolling(window=24).sum()
    df['VWAP'] = cum_pv / (cum_v + 1e-6)
    df['Dist_VWAP'] = (df['Close'] - df['VWAP']) / df['VWAP']
    df['Vol_Rel'] = df['Volume'] / (df['Volume'].rolling(window=24).mean() + 1e-6)
    
    df.fillna(method='bfill', inplace=True)
    
    # Robust Norms
    for col in ['RSI', 'MACD_Hist', 'Dist_SMA200', 'Log_Ret', 'Vol_Rel', 'ATR_Ratio', 'BB_Width', 'Dist_VWAP']:
        df[f'{col}_Norm'] = robust_scaler(df[col])
        
    return df

# ---------------------------------------------------------
# 4. API Endpoint Principal
# ---------------------------------------------------------

@app.get("/api/analyze/{symbol}")
def analyze_crypto(symbol: str):
    try:
        # 1. Preparar features
        df = prep_market_data(symbol)
        
        # Extraccion de la UI
        current_price = df['Close'].iloc[-1]
        prev_price = df['Close'].iloc[-2]
        ema50 = df['Close'].ewm(span=50, adjust=False).mean().iloc[-1]
        ema200 = df['Close'].ewm(span=200, adjust=False).mean().iloc[-1]
        rsi = df['RSI'].iloc[-1]
        macd = df['MACD'].iloc[-1]
        macd_sig = df['Signal'].iloc[-1]
        supLevel = df['Low'].tail(14).min()
        resLevel = df['High'].tail(14).max()
        bbUp = df['Upper_BB'].iloc[-1]
        bbDown = df['Lower_BB'].iloc[-1]

        # 2. IA INFERENCIA LSTM
        model = get_model(symbol)
        is_ai_real = False
        
        probBull = 0.0
        probSide = 0.0
        probBear = 0.0
        
        if model is not None:
            # Reconstruir estado secuencial LSTM de 24 horas (seq_length=24)
            seq_len = 24
            features_cols = [c for c in df.columns if '_Norm' in c]
            
            # Limitar las features al input de la red segun arquitectura
            input_dim_net = model.fc_in[0].in_features
            needed_market_features = input_dim_net - 7
            
            # Pad with zeros if needed, or truncate
            state_seq = []
            for i in range(len(df) - seq_len, len(df)):
                m_feat = df.iloc[i][features_cols].values.astype(float)
                
                if len(m_feat) > needed_market_features:
                    m_feat = m_feat[:needed_market_features]
                elif len(m_feat) < needed_market_features:
                    pads = np.zeros(needed_market_features - len(m_feat))
                    m_feat = np.concatenate([m_feat, pads])
                
                # Position state neutro (flat target evaluation)
                p_feat = np.array([0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0])
                state_seq.append(np.concatenate([m_feat, p_feat]))
                
            state_tensor = torch.FloatTensor(np.array(state_seq)).unsqueeze(0).to(device)
            
            with torch.no_grad():
                action_probs, state_value, _ = model(state_tensor)
                
            probs = action_probs.squeeze().cpu().numpy()
            
            # TAMC Multi-Layer Actions: 
            # 0=Flat(Side), 1=Long50%(Bull), 2=Long100%(Bull), 3=Short50%(Bear), 4=Short100%(Bear)
            probSide = probs[0] * 100
            probBull = (probs[1] + probs[2]) * 100
            probBear = (probs[3] + probs[4]) * 100
            is_ai_real = True

        else:
            # Fallback (algoritmo heurisitico si no hay modelo .pth en disco)
            baseBull = 50
            if current_price > ema50: baseBull += 10
            if rsi > 40 and rsi < 70: baseBull += 5
            if macd > macd_sig: baseBull += 10
            
            probBull = min(max(baseBull, 15), 85)
            probBear = min(max(100 - probBull - 15, 10), 80)
            probSide = 100 - probBull - probBear

        response_payload = {
            "symbol": symbol.replace('USDT', ''),
            "price": float(current_price),
            "prevPrice": float(prev_price),
            "ema50": float(ema50),
            "ema200": float(ema200),
            "rsi": float(rsi),
            "macdLine": float(macd),
            "macdSignal": float(macd_sig),
            "supLevel": float(supLevel),
            "resLevel": float(resLevel),
            "bbUp": float(bbUp),
            "bbDown": float(bbDown),
            # Nuevas features internas para la UI
            "vwap": float(df['VWAP'].iloc[-1]),
            "distVwap": float(df['Dist_VWAP'].iloc[-1] * 100), # En porcentaje
            "distSma200": float(df['Dist_SMA200'].iloc[-1] * 100),
            "bbWidth": float(df['BB_Width'].iloc[-1]),
            "atrRatio": float(df['ATR_Ratio'].iloc[-1]),
            "volRel": float(df['Vol_Rel'].iloc[-1]),
            # Probabilidades
            "probBull": float(probBull),
            "probBear": float(probBear),
            "probSide": float(probSide),
            "ai_source": "Neural_LSTM" if is_ai_real else "Heuristic_Fallback"
        }
        
        # Liberar memoria VRAM si usa GPU
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            
        return response_payload

    except Exception as e:
        import traceback
        traceback.print_exc()
        return fastapi.responses.JSONResponse(status_code=500, content={"error": str(e)})

if __name__ == "__main__":
    import uvicorn
    # Inicia el backend en el puerto 8000
    uvicorn.run("hub_backend:app", host="0.0.0.0", port=8000, reload=True)
