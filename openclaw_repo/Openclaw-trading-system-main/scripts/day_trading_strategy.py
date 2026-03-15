#!/usr/bin/env python3
"""
Day Trading Strategy for Hyperliquid
Basic mean reversion + breakout strategy for FRAN
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)


class DayTradingStrategy:
    """
    Day trading strategy combining:
    1. Mean reversion (RSI-based)
    2. Breakout (Bollinger Bands)
    3. Momentum (MACD)
    """
    
    def __init__(self, config: Dict = None):
        """
        Initialize strategy with configuration
        
        Args:
            config: Strategy configuration dictionary
        """
        self.config = config or {
            "rsi_period": 14,
            "rsi_overbought": 70,
            "rsi_oversold": 30,
            "bb_period": 20,
            "bb_std": 2.0,
            "macd_fast": 12,
            "macd_slow": 26,
            "macd_signal": 9,
            "volume_threshold": 1.5,  # 1.5x average volume
            "min_candles": 50,
            "position_size_usd": 100,
            "stop_loss_pct": 0.01,  # 1%
            "take_profit_pct": 0.02,  # 2%
            "max_positions": 3
        }
        
        # State tracking
        self.open_positions = []
        self.trade_history = []
        self.last_signal = None
        self.last_analysis = {}
        
        logger.info("Day trading strategy initialized")
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate technical indicators on OHLCV data
        
        Args:
            df: DataFrame with columns ['timestamp', 'open', 'high', 'low', 'close', 'volume']
            
        Returns:
            DataFrame with added indicator columns
        """
        # Ensure numeric columns
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.config['rsi_period']).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.config['rsi_period']).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Bollinger Bands
        df['bb_middle'] = df['close'].rolling(window=self.config['bb_period']).mean()
        bb_std = df['close'].rolling(window=self.config['bb_period']).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * self.config['bb_std'])
        df['bb_lower'] = df['bb_middle'] - (bb_std * self.config['bb_std'])
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        # MACD
        exp1 = df['close'].ewm(span=self.config['macd_fast'], adjust=False).mean()
        exp2 = df['close'].ewm(span=self.config['macd_slow'], adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=self.config['macd_signal'], adjust=False).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']
        
        # Volume indicators
        df['volume_sma'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        
        # Price changes
        df['returns'] = df['close'].pct_change()
        df['volatility'] = df['returns'].rolling(window=20).std()
        
        # Support/Resistance (simplified)
        df['resistance'] = df['high'].rolling(window=20).max()
        df['support'] = df['low'].rolling(window=20).min()
        
        return df
    
    def generate_signals(self, df: pd.DataFrame, symbol: str) -> Dict:
        """
        Generate trading signals based on indicators
        
        Args:
            df: DataFrame with calculated indicators
            symbol: Trading symbol
            
        Returns:
            Dictionary with signal information
        """
        if len(df) < self.config['min_candles']:
            return {"signal": "NO_SIGNAL", "reason": "Insufficient data"}
        
        # Get latest values
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        signal_strength = 0
        reasons = []
        
        # 1. RSI Mean Reversion Signal
        if latest['rsi'] < self.config['rsi_oversold']:
            signal_strength += 2
            reasons.append(f"RSI oversold: {latest['rsi']:.1f}")
        elif latest['rsi'] > self.config['rsi_overbought']:
            signal_strength -= 2
            reasons.append(f"RSI overbought: {latest['rsi']:.1f}")
        
        # 2. Bollinger Bands Breakout
        if latest['close'] > latest['bb_upper']:
            signal_strength += 1.5
            reasons.append(f"Price above BB upper: {latest['close']:.2f} > {latest['bb_upper']:.2f}")
        elif latest['close'] < latest['bb_lower']:
            signal_strength -= 1.5
            reasons.append(f"Price below BB lower: {latest['close']:.2f} < {latest['bb_lower']:.2f}")
        
        # 3. MACD Momentum
        if latest['macd_histogram'] > 0 and prev['macd_histogram'] <= 0:
            signal_strength += 1
            reasons.append("MACD turned bullish")
        elif latest['macd_histogram'] < 0 and prev['macd_histogram'] >= 0:
            signal_strength -= 1
            reasons.append("MACD turned bearish")
        
        # 4. Volume confirmation
        if latest['volume_ratio'] > self.config['volume_threshold']:
            if signal_strength > 0:
                signal_strength += 0.5
                reasons.append(f"High volume confirmation: {latest['volume_ratio']:.1f}x")
            elif signal_strength < 0:
                signal_strength -= 0.5
                reasons.append(f"High volume confirmation: {latest['volume_ratio']:.1f}x")
        
        # 5. Support/Resistance
        if abs(latest['close'] - latest['resistance']) / latest['resistance'] < 0.005:
            signal_strength -= 0.5
            reasons.append(f"Near resistance: {latest['resistance']:.2f}")
        elif abs(latest['close'] - latest['support']) / latest['support'] < 0.005:
            signal_strength += 0.5
            reasons.append(f"Near support: {latest['support']:.2f}")
        
        # Determine final signal
        if signal_strength >= 2:
            signal = "BUY"
            confidence = min(signal_strength / 5, 1.0)
        elif signal_strength <= -2:
            signal = "SELL"
            confidence = min(abs(signal_strength) / 5, 1.0)
        else:
            signal = "HOLD"
            confidence = 0
        
        # Prepare order details if signal is generated
        order_details = None
        if signal in ["BUY", "SELL"]:
            order_details = {
                "symbol": symbol,
                "side": "BUY" if signal == "BUY" else "SELL",
                "order_type": "LIMIT",
                "size_usd": self.config['position_size_usd'],
                "limit_price": latest['close'],
                "stop_loss": latest['close'] * (1 - self.config['stop_loss_pct']) if signal == "BUY" 
                            else latest['close'] * (1 + self.config['stop_loss_pct']),
                "take_profit": latest['close'] * (1 + self.config['take_profit_pct']) if signal == "BUY" 
                              else latest['close'] * (1 - self.config['take_profit_pct']),
                "confidence": confidence,
                "timestamp": datetime.now().isoformat()
            }
        
        result = {
            "signal": signal,
            "confidence": confidence,
            "strength": signal_strength,
            "reasons": reasons,
            "price": float(latest['close']),
            "timestamp": datetime.now().isoformat(),
            "indicators": {
                "rsi": float(latest['rsi']),
                "bb_position": float(latest['bb_position']),
                "macd_histogram": float(latest['macd_histogram']),
                "volume_ratio": float(latest['volume_ratio'])
            }
        }
        
        if order_details:
            result["order_details"] = order_details
        
        # Store for reference
        self.last_signal = result
        self.last_analysis = {
            "symbol": symbol,
            "analysis": result,
            "df_tail": df.tail(3).to_dict('records')
        }
        
        return result
    
    def should_close_position(self, position: Dict, current_price: float, df: pd.DataFrame) -> bool:
        """
        Check if a position should be closed
        
        Args:
            position: Position dictionary
            current_price: Current market price
            df: Latest market data
            
        Returns:
            Boolean indicating if position should be closed
        """
        if not position:
            return False
        
        entry_price = position.get('entry_price', 0)
        position_type = position.get('type', 'LONG')
        
        if entry_price == 0:
            return False
        
        # Calculate P&L
        if position_type == 'LONG':
            pnl_pct = (current_price - entry_price) / entry_price
            stop_loss = entry_price * (1 - self.config['stop_loss_pct'])
            take_profit = entry_price * (1 + self.config['take_profit_pct'])
        else:  # SHORT
            pnl_pct = (entry_price - current_price) / entry_price
            stop_loss = entry_price * (1 + self.config['stop_loss_pct'])
            take_profit = entry_price * (1 - self.config['take_profit_pct'])
        
        # Check stop loss
        if (position_type == 'LONG' and current_price <= stop_loss) or \
           (position_type == 'SHORT' and current_price >= stop_loss):
            return True, "STOP_LOSS", pnl_pct
        
        # Check take profit
        if (position_type == 'LONG' and current_price >= take_profit) or \
           (position_type == 'SHORT' and current_price <= take_profit):
            return True, "TAKE_PROFIT", pnl_pct
        
        # Check signal reversal
        latest_signal = self.last_signal
        if latest_signal:
            current_signal = latest_signal.get('signal', 'HOLD')
            if position_type == 'LONG' and current_signal == 'SELL':
                return True, "SIGNAL_REVERSAL", pnl_pct
            elif position_type == 'SHORT' and current_signal == 'BUY':
                return True, "SIGNAL_REVERSAL", pnl_pct
        
        # Check time-based exit (e.g., end of day)
        position_age = datetime.now() - datetime.fromisoformat(position.get('entry_time', datetime.now().isoformat()))
        if position_age > timedelta(hours=4):  # Close after 4 hours max
            return True, "TIME_EXIT", pnl_pct
        
        return False, None, pnl_pct
    
    def risk_management_check(self, symbol: str, signal: Dict, current_positions: List) -> Tuple[bool, str]:
        """
        Perform risk management checks before executing trade
        
        Args:
            symbol: Trading symbol
            signal: Signal dictionary
            current_positions: List of current positions
            
        Returns:
            Tuple of (allowed, reason)
        """
        # Check max positions
        if len(current_positions) >= self.config['max_positions']:
            return False, f"Max positions reached ({self.config['max_positions']})"
        
        # Check if already in position for this symbol
        for pos in current_positions:
            if pos.get('symbol') == symbol:
                return False, f"Already in position for {symbol}"
        
        # Check signal confidence
        if signal.get('confidence', 0) < 0.4:
            return False, f"Signal confidence too low: {signal.get('confidence'):.2f}"
        
        # Check market volatility
        if 'indicators' in signal and 'volatility' in signal['indicators']:
            if signal['indicators']['volatility'] > 0.05:  # 5% volatility threshold
                return False, f"Market too volatile: {signal['indicators']['volatility']:.3f}"
        
        return True, "Risk checks passed"


# Example usage
if __name__ == "__main__":
    print("=== Day Trading Strategy Test ===")
    
    # Create sample data
    np.random.seed(42)
    dates = pd.date_range(end=datetime.now(), periods=100, freq='5min')
    prices = 100 + np.cumsum(np.random.randn(100) * 0.5)
    volumes = np.random.randint(1000, 10000, 100)
    
    df = pd.DataFrame({
        'timestamp': dates,
        'open': prices - np.random.rand(100) * 0.5,
        'high': prices + np.random.rand(100) * 0.5,
        'low': prices - np.random.rand(100) * 0.5,
        'close': prices,
        'volume': volumes
    })
    
    # Initialize strategy
    strategy = DayTradingStrategy()
    
    # Calculate indicators
    df_with_indicators = strategy.calculate_indicators(df.copy())
    
    # Generate signal
    signal = strategy.generate_signals(df_with_indicators, "BTC")
    
    print(f"\nSignal generated: {signal['signal']}")
    print(f"Confidence: {signal['confidence']:.2f}")
    print(f"Strength: {signal['strength']:.2f}")
    print(f"Price: ${signal['price']:.2f}")
    print(f"\nReasons:")
    for reason in signal['reasons']:
        print(f"  - {reason}")
    
    if 'order_details' in signal:
        print(f"\nOrder Details:")
        for key, value in signal['order_details'].items():
            print(f"  {key}: {value}")
    
    print("\n✅ Strategy test completed!")