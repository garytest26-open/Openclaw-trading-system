import pandas as pd
import numpy as np
from typing import Tuple, Optional

class MovingAverageStrategy:
    """
    A simple Moving Average Crossover strategy.
    
    Attributes
    ----------
    short_window : int
        The lookback period for the short moving average.
    long_window : int
        The lookback period for the long moving average.
    """

    def __init__(self, short_window: int = 20, long_window: int = 50):
        self.short_window = short_window
        self.long_window = long_window

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Generates trading signals from price data using vectorized operations.

        Parameters
        ----------
        data : pd.DataFrame
            DataFrame with 'close' price column. Index should be DatetimeIndex.

        Returns
        -------
        pd.DataFrame
            DataFrame with added 'signal', 'short_mavg', 'long_mavg', and 'positions' columns.
        """
        signals = pd.DataFrame(index=data.index)
        signals['signal'] = 0.0

        # Vectorized calculation of Moving Averages
        signals['short_mavg'] = data['close'].rolling(window=self.short_window, min_periods=1, center=False).mean()
        signals['long_mavg'] = data['close'].rolling(window=self.long_window, min_periods=1, center=False).mean()

        # Signal generation: 1.0 when Short > Long, else 0.0
        signals['signal'] = np.where(signals['short_mavg'] > signals['long_mavg'], 1.0, 0.0)
        
        # Generates trading positions (1.0 = Buy, -1.0 = Sell)
        signals['positions'] = signals['signal'].diff()
        
        return signals
