from .day_trading_base import DayTradingStrategy
import pandas as pd
import numpy as np
from typing import Dict

class MeanReversionStrategy(DayTradingStrategy):
    """
    Estrategia de Reversión a la Media usando Bandas de Bollinger y RSI.
    """

    def __init__(self, config: Dict):
        super().__init__(config)
        self.bb_length = config.get('bb_length', 20)
        self.bb_std = config.get('bb_std', 2.0)
        self.rsi_length = config.get('rsi_length', 14)
        self.rsi_lower = config.get('rsi_lower', 30)
        self.rsi_upper = config.get('rsi_upper', 70)

    def get_strategy_name(self) -> str:
        return "Mean Reversion (BB+RSI)"

    def get_required_history(self) -> int:
        return max(self.bb_length, self.rsi_length) + 5

    def _calculate_rsi(self, data: pd.DataFrame, column='close') -> pd.Series:
        delta = data[column].diff()
        gain = (delta.where(delta > 0, 0)).fillna(0)
        loss = (-delta.where(delta < 0, 0)).fillna(0)

        # Exponential Moving Average for RSI
        avg_gain = gain.ewm(span=self.rsi_length, adjust=False).mean()
        avg_loss = loss.ewm(span=self.rsi_length, adjust=False).mean()

        rs = avg_gain / avg_loss.replace(0, np.finfo(float).eps) 
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        # Bandas de Bollinger
        rolling_mean = df['close'].rolling(window=self.bb_length).mean()
        rolling_std = df['close'].rolling(window=self.bb_length).std()
        
        df['upper_band'] = rolling_mean + (rolling_std * self.bb_std)
        df['lower_band'] = rolling_mean - (rolling_std * self.bb_std)

        # RSI
        df['rsi'] = self._calculate_rsi(df)
        return df

    def generate_signal(self, df: pd.DataFrame, index: int) -> str:
        if index < self.get_required_history():
            return 'hold'
            
        current_close = df['close'].iloc[index]
        lower_band = df['lower_band'].iloc[index]
        upper_band = df['upper_band'].iloc[index]
        rsi = df['rsi'].iloc[index]
        
        # Validaciones de integridad
        if pd.isna(lower_band) or pd.isna(rsi):
            return 'hold'

        # Buy: Precio bajo la banda inferior y RSI sobrevendido (rebote probable)
        if current_close < lower_band and rsi < self.rsi_lower:
            return 'buy'
            
        # Sell: Precio sobre la banda superior y RSI sobrecomprado (caida probable)
        if current_close > upper_band and rsi > self.rsi_upper:
            return 'sell'
            
        return 'hold'

