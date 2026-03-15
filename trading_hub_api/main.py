import asyncio
import json
import sys
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Añadir directorio padre al sys.path para poder importar tamc_strategy
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from market_data import fetch_market_analysis
from model_inference import load_tamc2_model, get_ai_inference

app = FastAPI(title="Trading Hub API")

# Cache de modelos cargados para no instanciar PPO en cada request
_models_cache = {}

# Configure CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[WebSocket, dict] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[websocket] = {"symbol": "BTC/USDT", "price": 65000}
        print(f"Client connected. Total clients: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            del self.active_connections[websocket]
            print(f"Client disconnected. Total clients: {len(self.active_connections)}")

    async def broadcast_to_clients(self):
        for connection, state in list(self.active_connections.items()):
            try:
                data = await generate_hybrid_data(state)
                if data:
                    await connection.send_text(json.dumps(data))
            except Exception as e:
                print(f"Error broadcasting: {e}")
                self.disconnect(connection)

manager = ConnectionManager()

def get_model_for_symbol(symbol: str):
    """Obtiene el modelo de la cache o lo carga desde disco si es primera vez"""
    if symbol not in _models_cache:
        model, config = load_tamc2_model(symbol)
        _models_cache[symbol] = {"model": model, "config": config}
    return _models_cache[symbol]["model"], _models_cache[symbol]["config"]


# --- Market Data + PPO AI Combiner ---
async def generate_hybrid_data(state: dict):
    """Fetches real market data and combines it with Real PyTorch inference"""
    symbol = state.get("symbol", "BTC/USDT")
    
    # 1. Traer datos reales del exchange
    real_data = await fetch_market_analysis(symbol, '15m')
    
    if not real_data:
        # Fallback si CCXT falla
        current_price = state.get("price", 65000)
        atr_val = 50
        volatility_state = "Medium"
        indicators = {
            "rsi": 50.0, "macd": "Neutral", "volumeRatio": 1.0, 
            "atr": 50, "ema50": current_price, "ema200": current_price
        }
        real_data = {"price": current_price, "indicators": indicators, "volatility": volatility_state}
    else:
        current_price = real_data["price"]
        atr_val = real_data["indicators"]["atr"]
        volatility_state = real_data["volatility"]
        indicators = real_data["indicators"]
        
    # 2. IA Inference - Obtener el modelo preentrenado PPO TAMC2
    model, config = get_model_for_symbol(symbol)
    
    # Valores por defecto estables (nada aleatorio)
    score = 50
    win_prob = 50
    confidence = 50
    momentum_str = "Neutral"
    recommendation = "WAIT"
    
    if model is not None:
        try:
            inference = get_ai_inference(model, real_data, config)
            if inference:
                score = inference["edgeScore"]
                win_prob = inference["winProb"]
                confidence = inference["confidence"]
                recommendation = inference["recommendation_action"]
                
                # Momentum calculado determinísticamente del RSI
                momentum_val = indicators.get("rsi", 50) - 50
                sign = "+" if momentum_val > 0 else "-"
                momentum_str = f"{sign}{int(abs(momentum_val) * 2)}"
        except Exception as e:
            print(f"Falló la inferencia con el modelo: {e}")
            
    
    # 3. Setup Heurístico Basado en ATR Real (Estable, cambia solo si el precio/ATR cambian)
    sl_dist = 1.5 * atr_val if atr_val > 0 else current_price * 0.02
    position_size = 150 / sl_dist if sl_dist > 0 else 0
    rr_ratio = 2.5 # Valor fijo y estable para R/R
    
    # Timeframes multi-period calculados lógicamente con histeresis para evitar parpadeos
    dist_50 = (current_price / indicators.get("ema50", current_price)) - 1
    dist_200 = (current_price / indicators.get("ema200", current_price)) - 1
    rsi_val = indicators.get("rsi", 50)
    
    timeframes = [
        1 if dist_50 > 0.001 else -1 if dist_50 < -0.001 else 0, # M15 (sensible)
        1 if dist_50 > 0.005 else -1 if dist_50 < -0.005 else 0, # H1 (menos sensible)
        1 if dist_200 > 0.01 else -1 if dist_200 < -0.01 else 0, # H4
        1 if dist_200 > 0.02 else -1 if dist_200 < -0.02 else 0, # D1
        1 if "Bullish" in indicators.get("macd", "") else -1,     # W1 basado en MACD
        1 if rsi_val > 50 else -1                                 # MN basado en RSI
    ]
    
    return {
        "edgeScore": score,
        "winProb": win_prob,
        "confidence": confidence,
        "volatility": volatility_state,
        "momentum": momentum_str,
        "timeframes": timeframes,
        "indicators": indicators,
        "price": current_price,
        "setup": {
            "entry": current_price,
            "stopLoss": current_price - sl_dist,
            "tp1": current_price + (sl_dist * rr_ratio * 0.6),
            "tp2": current_price + (sl_dist * rr_ratio),
            "positionSize": position_size,
            "riskAmount": 150,
            "potentialProfit": round(150 * rr_ratio, 2),
            "rrRatio": rr_ratio
        }
    }


async def background_task():
    while True:
        await asyncio.sleep(5) # Envio websocket a React de datos frescos CCXT
        if manager.active_connections:
           await manager.broadcast_to_clients()

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(background_task())

@app.websocket("/ws/stream")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "subscribe" and "symbol" in msg:
                    current_state = manager.active_connections.get(websocket, {})
                    if isinstance(current_state, str):
                        current_state = {"symbol": current_state, "price": 65000}
                    current_state["symbol"] = msg["symbol"]
                    manager.active_connections[websocket] = current_state
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        manager.disconnect(websocket)


@app.get("/health")
async def health_check():
    return {"status": "ok", "app": "Trading Hub API (PyTorch Integrated - Deterministic)"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

