import torch
import numpy as np
import pandas as pd
from typing import Dict, Any

# Importamos la arquitectura de red y la configuración desde el código original del usuario
from tamc_strategy import PPOActorCritic, StrategyConfig

# Instanciamos el dispositivo
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

def load_tamc2_model(symbol: str) -> tuple[PPOActorCritic, StrategyConfig]:
    """Carga el modelo TAMC2 para el símbolo especificado."""
    config = StrategyConfig()
    
    # Preparamos las dimensiones según tamc_strategy.py (10 features + 7 position states)
    config.n_features = 10
    state_dim = config.n_features + 7
    action_dim = 5
    
    model = PPOActorCritic(state_dim, action_dim, config.hidden_dim).to(device)
    
    # Mapeo de nombre de símbolo para encajar con los archivos .pth guardados
    ticker_slug = symbol.replace("USD", "").replace("USDT", "").replace("/", "").strip("_").lower()
    
    model_path = f"models/tamc2_{ticker_slug}_ppo.pth"
    
    try:
        model.load_state_dict(torch.load(model_path, map_location=device))
        model.eval() # Modo evaluación
        print(f"Modelo TAMC2 cargado exitosamente para {symbol} desde {model_path}")
        return model, config
    except FileNotFoundError:
        print(f"ATENCIÓN: Archivo {model_path} no encontrado. Se usarán predicciones fallback/heurísticas.")
        return None, config
    except Exception as e:
        print(f"Error cargando modelo {model_path}: {e}")
        return None, config


def prepare_state_sequence(real_data: dict, config: StrategyConfig) -> np.ndarray:
    """Convierte el diccionario de market_data en el tensor [seq_len, features] que requiere la LSTM."""
    
    # Debido a que el backend en tiempo real (market_data.py) no guarda el historial exacto 
    # de 24 horas y no gestiona la posición real del agente (solo visualiza), 
    # generaremos un state_sequence sintético donde el último paso es el real y los anteriores 
    # son slight variaciones, o rellenados repitiendo el actual (padding simplificado para este Hub).
    
    # Extraer variables normalizadas esperadas por el modelo (Aproximación para Dashboard)
    ind = real_data.get("indicators", {})
    rsi_norm = (ind.get("rsi", 50) - 50) / 20.0
    
    # Simularemos los _Norm que usa el robust_scaler original
    state_vector = [
        rsi_norm,                                   # RSI_Norm
        0.0 if ind.get("macd") == "Neutral" else (1.0 if "Bullish" in ind.get("macd", "") else -1.0), # MACD_Hist_Norm
        (real_data.get("price", 0) - ind.get("ema200", 0)) / (ind.get("ema200", 1) + 1e-6) * 10, # Dist_SMA200_Norm
        0.0,  # Log_Ret_Norm (requires history)
        1.0,  # Vol_Rel_Norm
        1.0,  # ATR_Ratio_Norm
        1.0,  # BB_Width_Norm
        0.0,  # Dist_VWAP_Norm
        rsi_norm, # Daily_RSI_Norm
        0.0,  # Daily_Log_Ret_Norm
        # Position states (simulamos flat para la visualización neutra del dashboard)
        0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0 
    ]
    
    # Crear secuencia de tamaño seq_length
    seq = np.array([state_vector for _ in range(config.seq_length)])
    return seq


def get_ai_inference(model: PPOActorCritic, real_data: dict, config: StrategyConfig) -> Dict[str, Any]:
    """Pasa los datos actuales de mercado por la red recurrente LSTM cargada en memoria."""
    if model is None:
        return None
        
    try:
        state_seq = prepare_state_sequence(real_data, config)
        state_tensor = torch.FloatTensor(state_seq).unsqueeze(0).to(device)
        
        with torch.no_grad():
             # action_probs shape: [1, action_dim], state_value shape: [1, 1]
            action_probs, state_value, _ = model(state_tensor)
            
        probs = action_probs.cpu().numpy()[0]
        score = float(state_value.cpu().numpy()[0][0])
        
        # Las acciones en TAMC: 0=Flat, 1=Long50, 2=Long100, 3=Short50, 4=Short100
        prob_long = probs[1] + probs[2]
        prob_short = probs[3] + probs[4]
        prob_flat = probs[0]
        
        # Mapear a Edge Score (0 a 100)
        # El critic value puede ser un número arbitrario dependiendo del entrenamiento,
        # lo normalizaremos asumiendo un rango típico de [-5, 5] -> [0, 100]
        normalized_score = max(0, min(100, (score + 5) * 10))
        
        # Inferir recomendación
        best_action = np.argmax(probs)
        action_map = {0: "WAIT", 1: "LONG (Light)", 2: "LONG (Heavy)", 3: "SHORT (Light)", 4: "SHORT (Heavy)"}
        
        return {
            "edgeScore": int(normalized_score),
            "winProb": int(max(prob_long, prob_short) * 100),
            "confidence": int(probs[best_action] * 100),
            "recommendation_action": action_map[best_action],
            "raw_probs": {
                "long": float(prob_long),
                "short": float(prob_short),
                "flat": float(prob_flat)
            }
        }
    except Exception as e:
        print(f"Error realizando inferencia IA: {e}")
        return None
