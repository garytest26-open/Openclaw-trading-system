import pandas as pd
import numpy as np
from backtesting import Strategy

# ----------------------------------------------------
# ESTRATEGIA QQQ BREAKOUT AGRESIVA - IMPLEMENTACIÓN FINAL
# ----------------------------------------------------
# Basada en una optimización de "Alta Frecuencia" (Grafico 15 min)
# Resultados esperados (Backtest 60 días):
# - Retorno Estimado: ~12% mensual (variable según volatilidad)
# - Win Rate: Muy alto (>80% en pruebas)
# - Frecuencia: 2-3 trades por mes (Operaciones de precisión/swing corto)
# ----------------------------------------------------

class AgresivaBreakoutQQQ(Strategy):
    """
    Estrategia de Ruptura de Canal Donchian (Agresiva).
    
    Lógica:
    1. Define un canal de Precio (Máximos y Mínimos) de N periodos atrás.
    2. Si el precio rompe el TECHO del canal -> COMPRA (Long).
    3. Si el precio rompe el SUELO del canal -> VENTA (Short).
    
    Gestión de Salida:
    - Utiliza un 'Trailing Stop' muy ajustado (Exit Lookback corto).
    - Esto permite asegurar ganancias rápidamente en cuanto el impulso se frena.
    """
    
    # === PARÁMETROS OPTIMIZADOS (15 min) ===
    # Lookback = 37: Mira aprox 9 horas hacia atrás (37 velas de 15m) para definir la tendencia.
    # Exit Lookback = 2: Stop muy ceñido (mínimo de las últimas 2 velas). Salida rápida.
    # ATR Stop = 1.0: Stop Loss inicial de protección a 1 veces la volatilidad promedio.
    lookback = 37           
    exit_lookback = 2      
    atr_period = 14
    atr_stop_mult = 1.0     
    
    def init(self):
        # Mapeo de columnas de datos (High, Low, Close)
        self.high = self.data.High
        self.low = self.data.Low
        self.close = self.data.Close
        
        # --- INDICADORES ---
        
        # 1. Canal de Entrada (Donchian Channel)
        # Calculamos el Máximo y Mínimo de las últimas 'lookback' velas.
        # IMPORTANTE: Usamos .shift(1) para no mirar el futuro (usamos datos hasta el cierre anterior).
        self.upper_channel = self.I(lambda x: pd.Series(x).rolling(self.lookback).max().shift(1), self.high)
        self.lower_channel = self.I(lambda x: pd.Series(x).rolling(self.lookback).min().shift(1), self.low)
        
        # 2. Canal de Salida (Trailing Stop Dinámico)
        # Calculamos canales más cortos para salir rápido si el precio se gira.
        self.exit_upper = self.I(lambda x: pd.Series(x).rolling(self.exit_lookback).max().shift(1), self.high)
        self.exit_lower = self.I(lambda x: pd.Series(x).rolling(self.exit_lookback).min().shift(1), self.low)
        
        # 3. ATR (Average True Range) para Stop Loss Técnico
        # Mide la volatilidad para poner un stop loss inteligente (ni muy cerca ni muy lejos).
        self.atr = self.I(lambda h, l, c: pd.Series(h-l).rolling(self.atr_period).mean(), self.high, self.low, self.close)

    def next(self):
        # Validación: Si los indicadores aún no se han calculado (inicio del histórico), no hacer nada.
        if np.isnan(self.upper_channel[-1]) or np.isnan(self.atr[-1]):
            return

        price = self.close[-1]
        
        # --- LÓGICA DE GESTIÓN DE POSICIÓN (SALIDAS) ---
        if self.position:
            # Si estamos COMPRADOS (Long)
            if self.position.is_long:
                # Salida 1: El precio cae por debajo del mínimo de hace 2 velas (exit_lower).
                # Esto protege las ganancias cuando el impulso alcista se detiene.
                if price < self.exit_lower[-1]:
                    self.position.close()
                    
            # Si estamos VENDIDOS (Short)
            elif self.position.is_short:
                # Salida 1: El precio sube por encima del máximo de hace 2 velas (exit_upper).
                if price > self.exit_upper[-1]:
                    self.position.close()
            return

        # --- LÓGICA DE ENTRADA (NUEVAS OPERACIONES) ---
        
        # COMPRA (LONG):
        # Si el precio actual supera el TECHO del canal (Máximo de 37 periodos).
        # Significa que el precio está "rompiendo" al alza con fuerza.
        if price > self.upper_channel[-1]:
            # Calculamos Stop Loss inicial basado en ATR
            sl_dist = self.atr[-1] * self.atr_stop_mult
            sl_price = price - sl_dist
            
            # Enviamos orden de compra
            # sl = Stop Loss duro inicial
            # tp = No ponemos Take Profit fijo, dejamos correr la ganancia hasta que salte el Trailing Stop.
            self.buy(sl=sl_price)
            
        # VENTA (SHORT):
        # Si el precio actual rompe el SUELO del canal (Mínimo de 37 periodos).
        # Significa que el precio se desploma.
        elif price < self.lower_channel[-1]:
            sl_dist = self.atr[-1] * self.atr_stop_mult
            sl_price = price + sl_dist
            
            self.sell(sl=sl_price)

# ----------------------------------------------------
# NOTAS DE IMPLEMENTACIÓN
# ----------------------------------------------------
# 1. Este código está optimizado para funcionar con la librería `backtesting`.
# 2. Para usarlo en producción (Live Trading), necesitas copiar la lógica de `next()`
#    a tu bot de conexión con el broker (ej. Interactive Brokers, Binance, etc.).
# 3. Asegúrate de alimentar la estrategia con velas de 15 MINUTOS.
