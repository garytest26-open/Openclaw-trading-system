import pandas as pd
import numpy as np
import yfinance as yf
import lightgbm as lgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
import os
import joblib

print("==================================================")
print("  ENTRENANDO MODELO QUANT: VIPER STRIKE ML FILTER ")
print("  Diferenciando Breakouts Reales vs Falsos (LGBM) ")
print("==================================================")

TICKER = 'BTC-USD'
TIMEFRAME = '1h'
YEARS_BACK = 2

def calc_atr(high, low, close, period):
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def calc_bollinger(close, period, std_mult):
    sma = close.rolling(period).mean()
    std = close.rolling(period).std()
    return sma + (std * std_mult), sma, sma - (std * std_mult)

def calc_keltner(high, low, close, period, atr_mult):
    ema = close.ewm(span=period, adjust=False).mean()
    atr = calc_atr(high, low, close, period)
    return ema + (atr * atr_mult), ema, ema - (atr * atr_mult)

def detect_squeeze(high, low, close):
    bb_upper, _, bb_lower = calc_bollinger(close, 20, 1.5) # Valores default BTC de viper configs
    kc_upper, _, kc_lower = calc_keltner(high, low, close, 20, 2.0)
    in_squeeze = ((bb_lower > kc_lower) & (bb_upper < kc_upper)).astype(int)
    squeeze_release = ((in_squeeze.shift(1) == 1) & (in_squeeze == 0)).astype(int)
    return squeeze_release

def calc_momentum(close, period):
    return close - close.shift(period)

def prepare_data():
    print(f"Descargando {YEARS_BACK} años de datos 1H para {TICKER}...")
    df = yf.download(TICKER, period=f"{YEARS_BACK}y", interval=TIMEFRAME, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)
    df.columns = [c.lower() for c in df.columns]
    
    print("Calculando Indicadores y Features HFT...")
    # Base indicators
    df['squeeze_release'] = detect_squeeze(df['high'], df['low'], df['close'])
    df['momentum'] = calc_momentum(df['close'], 10)
    df['atr'] = calc_atr(df['high'], df['low'], df['close'], 10)
    
    # ML Features (Contexto de mercado en las últimas N horas antes del disparo)
    df['volatility_ratio'] = df['atr'] / df['close'] * 100
    df['momentum_slope'] = df['momentum'] - df['momentum'].shift(5) # Aceleracion
    df['volume_surge'] = df['volume'] / df['volume'].rolling(20).mean() # Spike de volumen
    
    df['close_sma20_dist'] = (df['close'] - df['close'].rolling(20).mean()) / df['close'] * 100
    df['close_sma200_dist'] = (df['close'] - df['close'].rolling(200).mean()) / df['close'] * 100
    
    df['rsi_14'] = 100 - (100 / (1 + (df['close'].diff().where(df['close'].diff() > 0, 0).rolling(14).mean() / -df['close'].diff().where(df['close'].diff() < 0, 0).rolling(14).mean())))
    
    # Target (Label): ¿Fue el squeeze rentable?
    # Regla: Compra si se liberó el Squeeze. Es EXITOSO (1) si en las próximas 12 horas subió al menos 1.5% sin caer antes un 1.0%.
    df['future_high_px'] = df['high'].rolling(12).max().shift(-12)
    df['future_low_px'] = df['low'].rolling(12).min().shift(-12)
    
    df['max_drawdown_pct'] = (df['future_low_px'] - df['close']) / df['close'] * 100
    df['max_run_pct'] = (df['future_high_px'] - df['close']) / df['close'] * 100
    
    # Target Logic: Direccion es Bullish si momentum > 0, Bearish si < 0.
    # Evaluamos solo trades LONG para simplificar la asimetria.
    df['target_long_win'] = ((df['max_run_pct'] > 1.5) & (df['max_drawdown_pct'] > -1.0)).astype(int)
    
    return df.dropna()

def train_model():
    df = prepare_data()
    
    # Solo entrenamos sobre las velas donde HUBO un Squeeze Release y el Momentum apoyaba LONG
    trigger_cases = df[(df['squeeze_release'] == 1) & (df['momentum'] > 0)].copy()
    
    print(f"Total Squeezes Analizables Históricamente (Sub-Muestra de Gatillo): {len(trigger_cases)}")
    
    features = ['volatility_ratio', 'momentum_slope', 'volume_surge', 'close_sma20_dist', 'close_sma200_dist', 'rsi_14']
    
    X = trigger_cases[features]
    y = trigger_cases['target_long_win']
    
    print(f"Distribución de Clases (0: Fake Breakout, 1: Breakout Real): \n{y.value_counts()}")
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)
    
    print("Entrenando modelo LightGBM para Filtrado de Microestructura...")
    
    params = {
        'objective': 'binary',
        'metric': 'binary_logloss',
        'boosting_type': 'gbdt',
        'learning_rate': 0.05,
        'num_leaves': 31,
        'feature_fraction': 0.8,
        'verbose': -1
    }
    
    lgb_train = lgb.Dataset(X_train, y_train)
    lgb_eval = lgb.Dataset(X_test, y_test, reference=lgb_train)
    
    model = lgb.train(
        params,
        lgb_train,
        num_boost_round=500,
        valid_sets=[lgb_train, lgb_eval]
    )
    
    preds = model.predict(X_test)
    preds_binary = (preds > 0.65).astype(int) # Umbral estricto para Sindicato
    
    print("\nReporte de Clasificación sobre Conjunto de Prueba (Futuro Nunca Visto por la IA):")
    print(classification_report(y_test, preds_binary))
    
    os.makedirs("models", exist_ok=True)
    model.save_model("models/viper_ml_filter.txt")
    print("Modelo exportado exitosamente a 'models/viper_ml_filter.txt'")

if __name__ == "__main__":
    train_model()
