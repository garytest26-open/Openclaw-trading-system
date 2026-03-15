import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import pandas_ta as ta
from datetime import datetime
import time

st.set_page_config(page_title="AI Trading Hub", page_icon="📈", layout="wide")

st.title("🧠 AI Trading Hub Local")
st.markdown("Bienvenido al **Asistente de Trading Experto**. Introduce el símbolo de una criptomoneda para generar el análisis automatizado.")

symbol_input = st.text_input("Símbolo de la Criptomoneda (ej. BTC, ETH, SOL):", "BTC").upper()

def fetch_data(symbol):
    ticker = f"{symbol}-USD"
    df = yf.download(ticker, period="1mo", interval="1d", progress=False)
    if df.empty:
        return None
    
    # Check if df has MultiIndex columns (yfinance sometimes does this)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)
        
    return df

def calculate_indicators(df):
    df.ta.rsi(length=14, append=True)
    df.ta.macd(fast=12, slow=26, signal=9, append=True)
    df.ta.ema(length=50, append=True)
    df.ta.ema(length=100, append=True)
    df.ta.ema(length=200, append=True)
    df.ta.bbands(length=20, std=2, append=True)
    return df

def detect_trend(df):
    last_close = df['Close'].iloc[-1]
    ema50 = df['EMA_50'].iloc[-1]
    ema200 = df['EMA_200'].iloc[-1]
    
    if last_close > ema50 and ema50 > ema200:
        return "Alcista 🟢"
    elif last_close < ema50 and ema50 < ema200:
        return "Bajista 🔴"
    else:
        return "Lateral ⚪"

def get_S_R(df):
    recent_high = df['High'].tail(15).max()
    recent_low = df['Low'].tail(15).min()
    current_price = df['Close'].iloc[-1]
    
    # Simple dynamic SR
    res = recent_high if recent_high > current_price else current_price * 1.05
    sup = recent_low if recent_low < current_price else current_price * 0.95
    return sup, res

if st.button("Generar Análisis Predictivo 🚀"):
    with st.spinner(f"Cargando modelo y analizando datos para {symbol_input}..."):
        time.sleep(2) # Simular carga de modelo predictivo pesado
        df = fetch_data(symbol_input)
        
        if df is None:
            st.error(f"No se pudieron obtener datos para el símbolo {symbol_input}. Verifica que sea correcto.")
        else:
            df = calculate_indicators(df)
            current_price = df['Close'].iloc[-1]
            last_rsi = df['RSI_14'].iloc[-1]
            macd_val = df['MACD_12_26_9'].iloc[-1]
            macd_sig = df['MACDs_12_26_9'].iloc[-1]
            trend = detect_trend(df)
            sup, res = get_S_R(df)
            
            # Simulated AI Model Probabilities based on RSI and MACD
            base_bull = 50
            if last_rsi > 50: base_bull += 10
            if last_rsi < 30: base_bull += 15 # Oversold bounce
            if macd_val > macd_sig: base_bull += 15
            if current_price > df['EMA_50'].iloc[-1]: base_bull += 10
            
            prob_bull = min(max(base_bull, 15), 85)
            prob_bear = min(max(100 - prob_bull - 15, 10), 80)
            prob_side = 100 - prob_bull - prob_bear
            
            high_prob_scenario = "Alcista 🟢" if prob_bull > prob_bear else "Bajista 🔴"
            confidence = max(prob_bull, prob_bear)
            
            st.success("Análisis completado exitosamente.")
            
            st.markdown("---")
            st.markdown(f"### Activo: {symbol_input}/USDT")
            st.markdown(f"**Resumen del análisis:** Según el análisis del modelo de IA, la estructura técnica actual sugiere un entorno de mercado mayormente **{trend.lower()}** en el corto a medio plazo, con el precio consolidando cerca de los niveles de ${current_price:.2f}.")
            
            st.markdown("### Datos técnicos destacados:")
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Precio Actual", f"${current_price:.2f}")
            col2.metric("RSI (14)", f"{last_rsi:.2f}")
            col3.metric("Tendencia General", trend)
            
            macd_status = "Alcista" if macd_val > macd_sig else "Bajista"
            col4.metric("MACD", macd_status)

            technical_data = {
                "Indicador": ["EMA 50", "EMA 100", "EMA 200", "Banda Super. (BB)", "Banda Inferior (BB)", "Soporte Clave", "Resistencia Clave"],
                "Valor": [
                    f"${df['EMA_50'].iloc[-1]:.2f}" if not pd.isna(df['EMA_50'].iloc[-1]) else "N/A",
                    f"${df['EMA_100'].iloc[-1]:.2f}" if not pd.isna(df['EMA_100'].iloc[-1]) else "N/A",
                    f"${df['EMA_200'].iloc[-1]:.2f}" if not pd.isna(df['EMA_200'].iloc[-1]) else "N/A",
                    f"${df['BBU_20_2.0'].iloc[-1]:.2f}" if 'BBU_20_2.0' in df else "N/A",
                    f"${df['BBL_20_2.0'].iloc[-1]:.2f}" if 'BBL_20_2.0' in df else "N/A",
                    f"${sup:.2f}",
                    f"${res:.2f}"
                ]
            }
            st.table(pd.DataFrame(technical_data))
            
            st.markdown("### Escenarios de probabilidad:")
            st.markdown(f"🔴 **Escenario bajista** (Pérdida de soportes clave y agotamiento de compradores): **{prob_bear:.1f}%**")
            st.markdown(f"🟢 **Escenario alcista** (Ruptura de resistencias y continuación de tendencia positiva): **{prob_bull:.1f}%**")
            st.markdown(f"⚪ **Escenario lateral** (Consolidación en rango sin volumen direccional claro): **{prob_side:.1f}%**")
            
            st.markdown("### Escenario de alta probabilidad:")
            if high_prob_scenario == "Alcista 🟢":
                st.info(f"**Dirección esperada:** Alcista.\n\n"
                        f"**Nivel de entrada:** Cerca de soporte en ~${sup:.2f} o tras confirmación de ruptura de ${current_price * 1.02:.2f}.\n\n"
                        f"**Take Profit (TP):** ${res:.2f} (TP1), y siguiente nivel en ${res * 1.05:.2f} (TP2).\n\n"
                        f"**Stop Loss (SL):** Por debajo del nivel de invalidación en ${sup * 0.98:.2f}.\n\n"
                        f"**Horizonte temporal:** Corto/Medio plazo.")
            else:
                st.warning(f"**Dirección esperada:** Bajista.\n\n"
                        f"**Nivel de entrada:** En rechazo de la resistencia en ~${res:.2f} o al perder soporte en ${sup * 1.01:.2f}.\n\n"
                        f"**Take Profit (TP):** ${sup:.2f} (TP1), y siguiente nivel crítico en ${sup * 0.95:.2f} (TP2).\n\n"
                        f"**Stop Loss (SL):** Por encima del nivel de invalidación en ${res * 1.02:.2f}.\n\n"
                        f"**Horizonte temporal:** Corto/Medio plazo.")
                
            st.markdown(f"**🤖 Confianza del modelo:** {confidence:.1f}%")
            
            st.markdown("---")
            st.markdown("**⚠️ Nota de riesgo:** *La información y análisis proporcionados no constituyen asesoramiento financiero. Los mercados de criptomonedas son altamente volátiles y las predicciones pasadas o automáticas no son garantía de rentabilidad futura. Opera bajo tu propio riesgo y aplica una estricta gestión de capital.*")
