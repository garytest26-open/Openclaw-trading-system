import ccxt.async_support as ccxt
import pandas as pd
import pandas_ta as ta
import asyncio
import numpy as np

# Cache para evitar consumir la API por cada cliente que pida el mismo símbolo al mismo tiempo
_cache = {}
_cache_ttl = 30  # Actualizar datos del exchange solo cada 30 segundos

async def fetch_market_analysis(symbol: str, timeframe: str = '15m') -> dict:
    """Consigue OHLCV y calcula indicadores para el símbolo."""
    # Mapeo de par a formato Binance si es necesario (e.g. BTC/USD -> BTC/USDT)
    binance_symbol = symbol.replace("USD", "USDT") if "USDT" not in symbol and "USD" in symbol else symbol
    
    # Revisar cache
    if binance_symbol in _cache:
        cached_data, timestamp = _cache[binance_symbol]
        if asyncio.get_event_loop().time() - timestamp < _cache_ttl:
            return cached_data

    exchange = ccxt.binance({'enableRateLimit': True})
    
    try:
        # Traemos 250 velas para tener suficiente historial para EMA200
        ohlcv = await exchange.fetch_ohlcv(binance_symbol, timeframe, limit=250)
        
        if not ohlcv or len(ohlcv) < 200:
             return None # No hay data suficiente

        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # Calcular indicadores con pandas-ta
        df['ema50'] = ta.ema(df['close'], length=50)
        df['ema200'] = ta.ema(df['close'], length=200)
        df['rsi'] = ta.rsi(df['close'], length=14)
        
        macd = ta.macd(df['close'])
        # MACD returns columns like MACD_12_26_9, MACDh_12_26_9, MACDs_12_26_9
        macd_col = [c for c in macd.columns if c.startswith('MACD_')][0]
        macds_col = [c for c in macd.columns if c.startswith('MACDs_')][0]
        df['macd_val'] = macd[macd_col]
        df['macd_signal'] = macd[macds_col]
        
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
        
        # Volumen MA para el ratio
        df['vol_sma'] = ta.sma(df['volume'], length=20)
        
        # Obtener la última vela completa o la actual
        latest = df.iloc[-1]
        
        # Analizar MACD trend
        macd_state = "Neutral"
        if pd.notna(latest['macd_val']) and pd.notna(latest['macd_signal']):
            if latest['macd_val'] > latest['macd_signal']:
                macd_state = "Bullish Cross" if latest['macd_val'] > 0 else "Bullish"
            elif latest['macd_val'] < latest['macd_signal']:
                macd_state = "Bearish Cross" if latest['macd_val'] < 0 else "Bearish"

        # Vol ratio
        vol_ratio = latest['volume'] / latest['vol_sma'] if pd.notna(latest['vol_sma']) and latest['vol_sma'] > 0 else 1.0

        current_price = float(latest['close'])
        
        # Determinar Timeframes Multiples de forma rudimentaria (tendencia precio vs EMA50 en varios TF)
        # Esto es solo representativo basado en el current price. Un pro lo calcularía bajando los TFs reales.
        # Por ahora usaremos la relación del precio actual vs la EMA50 para estimar tendencia
        trend_tf = 1 if current_price > latest['ema50'] else -1 if current_price < latest['ema50'] else 0
        
        analysis = {
            "price": current_price,
            "indicators": {
                "rsi": round(float(latest['rsi']), 1) if pd.notna(latest['rsi']) else 50.0,
                "macd": macd_state,
                "volumeRatio": round(float(vol_ratio), 2),
                "atr": round(float(latest['atr']), 2) if pd.notna(latest['atr']) else 0.0,
                "ema50": float(latest['ema50']) if pd.notna(latest['ema50']) else current_price,
                "ema200": float(latest['ema200']) if pd.notna(latest['ema200']) else current_price
            },
            # Por ahora generamos mock de edge_score ya que IA es el paso 3
            # Los timeframes los enviamos estáticos/heurísticos por simplicidad de no hacer 6 llamadas API
            "volatility": "High" if latest['atr'] / current_price > 0.02 else "Medium" if latest['atr'] / current_price > 0.005 else "Low",
        }
        
        _cache[binance_symbol] = (analysis, asyncio.get_event_loop().time())
        return analysis

    except Exception as e:
        print(f"Error fetching data from CCXT: {e}")
        return None
    finally:
        await exchange.close()
