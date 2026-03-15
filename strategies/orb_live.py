from .day_trading_base import DayTradingStrategy
import pandas as pd
import numpy as np
from datetime import time
from typing import Dict

class ORBStrategyLive(DayTradingStrategy):
    """
    Estrategia Opening Range Breakout (ORB) adaptada para Live Trading.
    Patrón: Breakout de rango de apertura con filtro de tendencia (EMA) y volumen.
    """
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self.or_start_time = config.get('or_start_time', time(14, 30)) # 9:30 EST
        self.or_end_time = config.get('or_end_time', time(15, 0))      # 10:00 EST
        self.ema_fast_period = config.get('ema_fast', 5)
        self.ema_slow_period = config.get('ema_slow', 60)
        self.vol_mult = config.get('vol_mult', 1.0)
        
        # State variables for the day
        self.current_day = None
        self.or_high = None
        self.or_low = None
        self.or_done = False

    def get_strategy_name(self) -> str:
        return "ORB Strategy"

    def get_required_history(self) -> int:
        return 100 # Need enough for slow EMA

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df['ema_fast'] = df['close'].ewm(span=self.ema_fast_period, adjust=False).mean()
        df['ema_slow'] = df['close'].ewm(span=self.ema_slow_period, adjust=False).mean()
        df['vol_ma'] = df['volume'].rolling(window=20).mean()
        return df

    def _update_or_levels(self, df: pd.DataFrame):
        """
        Actualiza los niveles del Opening Range basándose en los datos recientes.
        Debe llamarse en cada ciclo.
        """
        # Asumimos que el último dato es el actual/reciente
        last_timestamp = df.iloc[-1]['timestamp']
        current_date = last_timestamp.date()
        current_time = last_timestamp.time()

        # Reset diario
        if self.current_day != current_date:
            self.current_day = current_date
            self.or_high = None
            self.or_low = None
            self.or_done = False
        
        # Durante el rango de apertura (acumular high/low)
        if self.or_start_time <= current_time < self.or_end_time:
            high = df.iloc[-1]['high']
            low = df.iloc[-1]['low']
            
            if self.or_high is None or high > self.or_high:
                self.or_high = high
            if self.or_low is None or low < self.or_low:
                self.or_low = low
                
        # Finalizar rango
        elif current_time >= self.or_end_time and not self.or_done:
            if self.or_high is not None and self.or_low is not None:
                self.or_done = True
                # Opcional: Log del rango establecido

    def generate_signal(self, df: pd.DataFrame, index: int) -> str:
        # 1. Actualizar estado del OR (Opening Range)
        self._update_or_levels(df)
        
        # Si no se ha definido el rango hoy, no operar en dirección de ruptura
        if not self.or_done or self.or_high is None:
            return 'hold'

        # Datos actuales
        price = df.iloc[index]['close']
        ema_fast = df.iloc[index]['ema_fast']
        ema_slow = df.iloc[index]['ema_slow']
        vol = df.iloc[index]['volume']
        vol_avg = df.iloc[index]['vol_ma']
        
        # Validaciones de integridad
        if pd.isna(ema_fast) or pd.isna(ema_slow) or pd.isna(vol_avg):
            return 'hold'

        # Lógica de Entrada
        # Long: Precio rompe OR High + EMA rápida > alenta + Volumen alto
        if price > self.or_high:
            if ema_fast > ema_slow and vol > (self.vol_mult * vol_avg):
                return 'buy'
                
        # Short: Precio rompe OR Low + EMA rápida < lenta + Volumen alto
        elif price < self.or_low:
             if ema_fast < ema_slow and vol > (self.vol_mult * vol_avg):
                 return 'sell'
                 
        return 'hold'
