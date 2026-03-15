import logging
import sys
from strategies.mean_reversion import MeanReversionStrategy
import pandas as pd
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("AlgoAgent")

def main():
    logger.info("Starting Algorithmic Trading Agent...")
    
    # Example Data (Mocking fetching from an exchange)
    logger.info("Generating mock data...")
    dates = pd.date_range(start='2024-01-01', periods=200, freq='D')
    # Random walk with some volatility for BB/RSI triggers
    np.random.seed(42)
    prices = 100 + np.cumsum(np.random.normal(0, 2, 200))
    data = pd.DataFrame({
        'close': prices,
        'high': prices + np.random.normal(0, 0.5, 200),
        'low': prices - np.random.normal(0, 0.5, 200),
        'open': prices # Approximation
    }, index=dates)
    
    # Initialize Strategy
    logger.info("Initializing Strategy: Mean Reversion (Bollinger + RSI)")
    strategy = MeanReversionStrategy(bb_length=20, rsi_length=14)
    
    # Run Strategy
    logger.info("Running strategy analysis...")
    signals = strategy.generate_signals(data)
    
    # Output results
    latest_signal = signals.iloc[-1]
    logger.info(f"Latest Signal (as of {signals.index[-1].date()}): ")
    logger.info(f"Close Price: {data.iloc[-1]['close']:.2f}")
    logger.info(f"RSI: {latest_signal['rsi']:.2f}")
    logger.info(f"Upper Band: {latest_signal['upper_band']:.2f}")
    logger.info(f"Lower Band: {latest_signal['lower_band']:.2f}")
    
    if latest_signal['signal'] == 1.0:
        logger.info("ACTION: LONG CONDITION MET (Oversold)")
    elif latest_signal['signal'] == -1.0:
        logger.info("ACTION: SHORT CONDITION MET (Overbought)")
    else:
        logger.info("ACTION: NEUTRAL")

    logger.info("Agent run completed successfully.")

if __name__ == "__main__":
    main()
