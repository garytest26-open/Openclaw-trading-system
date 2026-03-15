import pandas as pd
import numpy as np

class PullbackStrategy:
    """
    Estrategia de Pullback Inteligente.
    Combina filtro de tendencia a largo plazo con entradas por sobreventa a corto plazo.
    
    Reglas:
    - Filtro: Precio > SMA 200 (Tendencia Alcista)
    - ENTRADA (Largo): RSI < 40 (Corrección/Pullback)
    - SALIDA (Cerrar): RSI > 75 (Rebote completado/Sobrecompra)
    """

    def __init__(self, sma_period=200, rsi_period=14, rsi_entry=40, rsi_exit=75):
        self.sma_period = sma_period
        self.rsi_period = rsi_period
        self.rsi_entry = rsi_entry
        self.rsi_exit = rsi_exit

    def _calculate_rsi(self, data: pd.DataFrame, column='close') -> pd.Series:
        # Implementación nativa de RSI para evitar deps externas
        delta = data[column].diff()
        gain = (delta.where(delta > 0, 0)).fillna(0)
        loss = (-delta.where(delta < 0, 0)).fillna(0)

        avg_gain = gain.ewm(span=self.rsi_period, adjust=False).mean()
        avg_loss = loss.ewm(span=self.rsi_period, adjust=False).mean()

        rs = avg_gain / avg_loss.replace(0, np.finfo(float).eps) 
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        signals = pd.DataFrame(index=data.index)
        signals['close'] = data['close']
        
        # Indicadores
        signals['sma_long'] = data['close'].rolling(window=self.sma_period).mean()
        signals['rsi'] = self._calculate_rsi(data)

        # Lógica de Estado (Iterativa para manejar Hold correctamente hasta la salida)
        # Vectorizar esta lógica específica con condiciones de salida variables es complejo
        # Usaremos iteración rápida sobre arrays numpy para eficiencia y claridad
        
        close_arr = signals['close'].values
        sma_arr = signals['sma_long'].values
        rsi_arr = signals['rsi'].values
        signal_arr = np.zeros(len(data))
        
        in_position = False
        
        for i in range(self.sma_period, len(data)):
            # Condiciones
            is_uptrend = close_arr[i] > sma_arr[i]
            is_oversold = rsi_arr[i] < self.rsi_entry
            is_overbought = rsi_arr[i] > self.rsi_exit
            
            if not in_position:
                if is_uptrend and is_oversold:
                    signal_arr[i] = 1 # ENTRAR
                    in_position = True
            else:
                if is_overbought:
                    signal_arr[i] = 0 # SALIR
                    in_position = False
                else:
                    signal_arr[i] = 1 # MANTENER
        
        signals['signal'] = signal_arr
        
        # 'signal' aquí ya representa la POSICIÓN deseada (1=Dentro, 0=Fuera)
        # positions para logging de cambios
        signals['positions'] = signals['signal'].diff()
        
        return signals
