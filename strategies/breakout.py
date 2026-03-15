from .day_trading_base import DayTradingStrategy
import pandas as pd
import numpy as np
from typing import Dict

class BreakoutStrategy(DayTradingStrategy):
    """
    Estrategia de Ruptura de Canal (Turtle Trading / Donchian Breakout).
    Adaptada para heredar de DayTradingStrategy.
    """

    def __init__(self, config: Dict):
        super().__init__(config)
        self.entry_window = config.get('entry_window', 20)
        self.exit_window = config.get('exit_window', 10)

    def get_strategy_name(self) -> str:
        return "Donchian Breakout"
    
    def get_required_history(self) -> int:
        return max(self.entry_window, self.exit_window) + 5

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        # Donchian Channels (shifted by 1 because we trade based on PAST N days extremes)
        # We look at the Max/Min of the PRIOR window, excluding today, to determine the breakout level.
        # Shift(1) is critical so we don't look-ahead if using closed candles, 
        # but if using live candle updating, we want the max of previous N.
        
        # En live trading, df entra con la ultima vela 'viva' o cerrada. 
        # Calculamos sobre todo el historico.
        
        df['donchian_high'] = df['high'].rolling(window=self.entry_window).max().shift(1)
        df['donchian_low'] = df['low'].rolling(window=self.exit_window).min().shift(1)
        return df

    def generate_signal(self, df: pd.DataFrame, index: int) -> str:
        """
        Retorna 'buy', 'sell' o 'hold'.
        """
        # Validar limites
        if index < self.get_required_history():
            return 'hold'

        current_close = df['close'].iloc[index]
        donchian_high = df['donchian_high'].iloc[index]
        donchian_low = df['donchian_low'].iloc[index]
        
        if pd.isna(donchian_high) or pd.isna(donchian_low):
            return 'hold'

        # Signal Logic
        if current_close > donchian_high:
            return 'buy'
        elif current_close < donchian_low:
             # Nota: Esta estrategia original era reversa o salida. 
             # Si es solo Long-Only, esto sería un exit.
             # Asumiremos Long/Short simétrico para el ejemplo, o salida si es long.
             # Para simplificar como estrategia direccional:
            return 'sell' 
            
        return 'hold'

    def check_exit_conditions(self, current_price: float) -> bool:
        # Override parent method to include "Donchian Exit" logic
        # Turtle exits when price hits the opposing N-day extreme
        
        # Check basic TP/SL first from parent
        if super().check_exit_conditions(current_price):
            return True
            
        # Donchian Exit logic requires access to the lows/highs. 
        # This is a limitation of the simple interface which passes only price to check_exit.
        # To fix this properly, we should calculate exit signals in generate_signal as 'close_long' etc.
        # For now, we rely on Generate Signal sending 'sell' to reverse or close.
        return False
