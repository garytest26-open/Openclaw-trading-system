import yfinance as yf
print("Start download...")
try:
    df = yf.download("BTC-USD", period="5d", interval="1h", progress=False)
    print(f"Downloaded {len(df)} rows")
except Exception as e:
    print(f"Error: {e}")
print("Done")
