import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import yfinance as yf
from strategies.breakout import BreakoutStrategy
from strategies.pullback import PullbackStrategy
import logging

# Config
INITIAL_CAPITAL = 10000.0
START_DATE = '2017-01-01'
END_DATE = '2026-01-27'
SYMBOL = 'SPY'
LEVERAGE_BREAKOUT = 1.5

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("Backtest")

def get_real_data(symbol, start, end):
    logger.info(f"Downloading data for {symbol} from Yahoo Finance...")
    data = yf.download(symbol, start=start, end=end)
    
    # yfinance returns MultiIndex columns in recent versions, we flatten/normalize them
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
        
    # Ensure lowercase standard columns
    data.columns = [c.lower() for c in data.columns]
    
    # Handle missing values if any
    data = data.ffill().dropna()
    
    return data

def calculate_drawdown(equity_curve):
    rolling_max = equity_curve.cummax()
    drawdown = (equity_curve - rolling_max) / rolling_max
    return drawdown.min() * 100

def run_strategy(data, strategy, leverage=1.0):
    signals = strategy.generate_signals(data)
    
    # Position logic: Shift 1 day to trade at next open
    positions = signals['signal'].shift(1).fillna(0)
    
    # Returns
    market_returns = data['close'].pct_change().fillna(0)
    strategy_returns = positions * market_returns * leverage
    
    equity_curve = INITIAL_CAPITAL * (1 + strategy_returns).cumprod()
    
    metrics = {}
    metrics['total_return'] = (equity_curve.iloc[-1] / INITIAL_CAPITAL) - 1
    metrics['sharpe'] = strategy_returns.mean() / strategy_returns.std() * np.sqrt(252) if strategy_returns.std() != 0 else 0
    metrics['max_dd'] = calculate_drawdown(equity_curve)
    metrics['final_value'] = equity_curve.iloc[-1]
    
    return equity_curve, metrics

def run_backtest():
    logger.info(f"--- Running REAL WORLD Backtest: {SYMBOL} ({START_DATE} to {END_DATE}) ---")
    
    # 1. Get Data
    data = get_real_data(SYMBOL, START_DATE, END_DATE)
    logger.info(f"Data downloaded: {len(data)} trading days")
    
    # Benchmark: Buy & Hold
    market_returns = data['close'].pct_change().fillna(0)
    benchmark_equity = INITIAL_CAPITAL * (1 + market_returns).cumprod()
    bh_total_return = (benchmark_equity.iloc[-1] / INITIAL_CAPITAL) - 1
    bh_max_dd = calculate_drawdown(benchmark_equity)
    
    logger.info(f"BENCHMARK (Buy & Hold) Return: {bh_total_return*100:.2f}% | Max DD: {bh_max_dd:.2f}%")
    
    # 2. Run Pullback (Conservative)
    pullback_strat = PullbackStrategy(sma_period=200, rsi_entry=40, rsi_exit=75)
    pb_equity, pb_metrics = run_strategy(data, pullback_strat, leverage=1.0)
    
    # 3. Run Breakout (Aggressive)
    breakout_strat = BreakoutStrategy(entry_window=20, exit_window=10)
    bo_equity, bo_metrics = run_strategy(data, breakout_strat, leverage=LEVERAGE_BREAKOUT)
    
    # Report
    logger.info("-" * 50)
    logger.info(f"STRATEGY 1: Smart Pullback (1x)")
    logger.info(f"Return: {pb_metrics['total_return']*100:.2f}%")
    logger.info(f"Max DD: {pb_metrics['max_dd']:.2f}%")
    
    logger.info("-" * 50)
    logger.info(f"STRATEGY 2: Turtle Breakout ({LEVERAGE_BREAKOUT}x)")
    logger.info(f"Return: {bo_metrics['total_return']*100:.2f}%")
    logger.info(f"Max DD: {bo_metrics['max_dd']:.2f}%")
    
    # Winner Check
    if bo_metrics['total_return'] > bh_total_return:
        logger.info(">>> RESULT: Aggressive Breakout BEAT Buy & Hold! <<<")
    elif pb_metrics['total_return'] > bh_total_return:
        logger.info(">>> RESULT: Conservative Pullback BEAT Buy & Hold! <<<")
    else:
        logger.info(">>> RESULT: Buy & Hold is King. (Crypto is hard to beat) <<<")
    
    # Plot Comparison
    plt.figure(figsize=(12, 6))
    plt.plot(benchmark_equity, label='Buy & Hold (BTC)', color='gray', alpha=0.5, linestyle='--')
    plt.plot(pb_equity, label='Smart Pullback (1x)', color='blue')
    plt.plot(bo_equity, label=f'Turtle Breakout ({LEVERAGE_BREAKOUT}x)', color='red')
    
    plt.title(f'Real World Backtest: {SYMBOL}')
    plt.yscale('log') # Log scale is better for Crypto
    plt.ylabel('Portfolio Value (Log Scale $)')
    plt.legend()
    plt.grid(True, which="both", ls="-", alpha=0.2)
    plt.savefig('backtest_real_results.png')
    logger.info("Chart saved to 'backtest_real_results.png'")

if __name__ == "__main__":
    run_backtest()
