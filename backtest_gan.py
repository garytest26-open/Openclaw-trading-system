import os
import torch
import numpy as np
import pandas as pd
import yfinance as yf
from future_forge_gan import ConditionalGenerator, LATENT_DIM, NUM_CLASSES, EMBEDDING_DIM, HIDDEN_DIM, SEQ_LEN, FEATURES
import matplotlib.pyplot as plt

def load_pre_trained_gan(model_path="models/cgan_future_forge.pth"):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    if not os.path.exists(model_path):
        print(f"Error: No se encontró el modelo GAN en {model_path}.")
        print("Debes ejecutar future_forge_gan.py primero hasta que termine.")
        return None, None, None, None

    # Inicializar la arquitectura
    generator = ConditionalGenerator(LATENT_DIM, NUM_CLASSES, EMBEDDING_DIM, HIDDEN_DIM, SEQ_LEN, FEATURES).to(device)
    
    # Cargar pesos y datos estadísticos de normalización
    checkpoint = torch.load(model_path, map_location=device, weights_only=False)
    generator.load_state_dict(checkpoint['generator_state_dict'])
    generator.eval()
    
    mean_stat = checkpoint['mean_stat']
    std_stat = checkpoint['std_stat']
    
    print("Creador de Mundos (GAN) cargado correctamente.")
    return generator, mean_stat, std_stat, device

def backtest_gan_strategy(ticker="SOL-USD", test_months=6, threshold=0.01):
    """
    Estrategia Teórica:
    En cada hora, le pedimos a la GAN que genere N posibles "Universos de Mercado Rango/Toro".
    Si el promedio de esos universos predice una subida neta > threshold, Compramos (Long).
    Si el promedio predice una caída > threshold, Vendemos (Short/Flat).
    """
    print("FUTURE FORGE SIMULATION BACKTEST")
    print("="*60)
    
    generator, mean_stat, std_stat, device = load_pre_trained_gan()
    
    if generator is None:
        return
        
    print(f"Descargando {test_months} meses de datos de prueba para {ticker}...")
    df = yf.download(ticker, period=f"{test_months}mo", interval="1h", progress=False)
    
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel('Ticker')
        
    df.dropna(inplace=True)
    closes = df['Close'].values
    dates = df.index.values
    
    capital = 10000.0
    initial_capital = capital
    position = 0 # 0=Flat, 1=Long
    entry_price = 0
    trade_log = []
    equity_curve = [capital]
    
    print("\nEjecutando Simulación de Trading basada en Multiversos...")
    
    # Simulamos el paso del tiempo
    for i in range(0, len(closes) - 24, 6): # Re-evaluamos cada 6 horas
        current_price = closes[i]
        
        # Le pedimos a la GAN que genere 10 universos Toro (1) y 10 universos Rango (0)
        # para promediar la "expectativa" matemática del activo
        with torch.no_grad():
            z = torch.randn(20, LATENT_DIM).to(device)
            # 10 Sideways (0) y 10 Bull (1)
            conditions = torch.LongTensor([0]*10 + [1]*10).to(device)
            fake_seqs = generator(z, conditions).cpu().numpy() # [20, 24, 3 features]
        
        # Desnormalizamos los retornos logaritmicos
        fake_returns = (fake_seqs[:, :, 0] * std_stat[0]) + mean_stat[0] # [20, 24]
        
        # Sumamos el retorno de las 24 hrs en cada uno de los 20 universos y sacamos la media
        expected_24h_return = np.mean(np.sum(fake_returns, axis=1)) 
        
        # Lógica de Trading
        if expected_24h_return > threshold and position == 0:
            # BUY
            position = 1
            entry_price = current_price
            fee = capital * 0.001
            capital -= fee
            
            trade_log.append({'date': dates[i], 'type': 'BUY', 'price': current_price, 'expected': expected_24h_return})
            
        elif expected_24h_return < -threshold and position == 1:
            # SELL
            position = 0
            profit_pct = (current_price - entry_price) / entry_price
            capital = capital * (1 + profit_pct)
            fee = capital * 0.001
            capital -= fee
            
            trade_log.append({'date': dates[i], 'type': 'SELL', 'price': current_price, 'expected': expected_24h_return, 'cap': capital})
            
    # Cerrar si quedamos abiertos
    if position == 1:
        profit_pct = (closes[-1] - entry_price) / entry_price
        capital = capital * (1 + profit_pct)
        
    roi = ((capital - initial_capital) / initial_capital) * 100
    buy_hold_roi = ((closes[-1] - closes[0]) / closes[0]) * 100
    
    print("\n" + "="*40)
    print("RESULTADOS DEL BACKTEST")
    print("="*40)
    print(f"Capital Inicial: ${initial_capital:,.2f}")
    print(f"Capital Final:   ${capital:,.2f}")
    print(f"Retorno Neto:    {roi:+.2f}%")
    print(f"Retorno Buy&Hold:{buy_hold_roi:+.2f}%")
    print(f"Total Trades:    {len(trade_log)}")
    print("=========================================\n")
    
if __name__ == "__main__":
    backtest_gan_strategy()
