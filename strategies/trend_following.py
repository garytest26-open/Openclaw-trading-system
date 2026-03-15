import pandas as pd
import numpy as np

class TrendFollowingStrategy:
    """
    Estrategia de Seguimiento de Tendencia usando Cruce de Medias Móviles (SMA).
    
    Reglas:
    - COMPRA (Largo): SMA Corta > SMA Larga
    - VENTA (Corto/Cerrar): SMA Corta < SMA Larga
    """

    def __init__(self, short_window=50, long_window=200):
        self.short_window = short_window
        self.long_window = long_window

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Genera señales de trading.
        """
        signals = pd.DataFrame(index=data.index)
        signals['close'] = data['close']
        
        # Calcular SMAs
        signals['short_mavg'] = data['close'].rolling(window=self.short_window, min_periods=1).mean()
        signals['long_mavg'] = data['close'].rolling(window=self.long_window, min_periods=1).mean()

        # Señal: 1 si Corta > Larga, 0 si no
        signals['signal'] = 0.0
        signals['signal'] = np.where(signals['short_mavg'] > signals['long_mavg'], 1.0, 0.0)

        # Generar posiciones (cambios en la señal para logs, pero la señal en sí es el estado posicional)
        # En Trend Following, 'signal' 1 suele significar "MANTENER LARGO".
        # 0 suele significar "CASH" o "CORTO" dependiendo de si es Long-Only o Long-Short.
        # Asumiremos Long-Only para el backtest simple (1 = Comprado, 0 = Vendido/Cash).
        
        signals['positions'] = signals['signal'].diff()
        
        return signals
