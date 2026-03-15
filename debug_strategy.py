import pandas as pd
import numpy as np
from breakout_strategy_qqq import DonchianBreakoutQQQ, descargar_datos_intradia_qqq
from backtesting import Backtest

class DebugStrategy(DonchianBreakoutQQQ):
    def next(self):
        # Print info for the first 20 candles
        if len(self.data) < 100:
            return
            
        if len(self.data) > 130:
            return

        date = self.data.index[-1]
        price = self.close[-1]
        exit_l = self.exit_lower[-1]
        exit_u = self.exit_upper[-1]
        
        print(f"Date: {date} | Price: {price:.2f} | ExitLower: {exit_l:.2f} | ExitUpper: {exit_u:.2f} | Pos: {self.position.size}")
        
        super().next()

def main():
    print("Running Debug Strategy...")
    # Just grab a small slice of data or use the function
    df = descargar_datos_intradia_qqq()
    if len(df) > 500:
        df = df.iloc[-500:] # Last 500 candles
        
    bt = Backtest(df, DebugStrategy, cash=10000, commission=.0005)
    
    # Run with the problematic parameters
    # Lookback 10, Exit 3
    bt.run(lookback=10, exit_lookback=3, atr_stop_mult=1.0)

if __name__ == "__main__":
    main()
