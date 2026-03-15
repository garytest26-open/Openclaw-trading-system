import yfinance as yf
import pandas as pd
import numpy as np

try:
    print("Testing yfinance download...")
    df = yf.download("SOL-USD", period="2y", interval="1h", progress=False)
    print(f"Downloaded columns: {df.columns}")
    
    # Manejar MultiIndex si se usa yfinance nuevo
    if isinstance(df.columns, pd.MultiIndex):
        print("Detected MultiIndex! Flattening...")
        df.columns = df.columns.droplevel('Ticker')
        
    df.dropna(inplace=True)
    print(f"Length after dropna: {len(df)}")
    
    df['LogRet'] = np.log(df['Close'] / df['Close'].shift(1))
    df['IntraVol'] = (df['High'] - df['Low']) / df['Close']
    df['LogVol'] = np.log(df['Volume'] + 1)
    df['VolChange'] = df['LogVol'].diff()
    
    df.dropna(inplace=True)
    print(f"Final length: {len(df)}")
    print(df[['LogRet', 'IntraVol', 'VolChange']].head())
    
except Exception as e:
    print(f"Exception caught: {e}")
    import traceback
    traceback.print_exc()
