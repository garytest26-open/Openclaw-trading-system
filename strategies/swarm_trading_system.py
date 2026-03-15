#!/usr/bin/env python3
"""
Swarm Trading System - Main Execution System
Integrates all neural agents with Hyperliquid trading
"""

import os
import sys
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

# Add paths
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import agents
from agents.trend_agent import TrendAgent
from agents.reversal_agent import ReversalAgent
from agents.volatility_agent import VolatilityAgent
from swarm.swarm_coordinator_simple import SimpleSwarmCoordinator
from training.data_preprocessor import SwarmDataPreprocessor

# Import Hyperliquid client from basic trading system
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts', 'hyperliquid'))
try:
    from hyperliquid_client import HyperliquidClient
except ImportError:
    # Create a mock client for testing
    class HyperliquidClient:
        def __init__(self, *args, **kwargs):
            pass
        def get_candles(self, *args, **kwargs):
            return []

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading/logs/swarm_system.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class SwarmTradingSystem:
    """
    Main swarm trading system that integrates neural agents with live trading
    """
    
    def __init__(self, config_path: str = "trading/swarm_ai/config/swarm_config.json"):
        """
        Initialize the complete swarm trading system
        
        Args:
            config_path: Path to swarm configuration
        """
        # Load configuration
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        # Initialize components
        self.preprocessor = SwarmDataPreprocessor(self.config)
        self.swarm_coordinator = SimpleSwarmCoordinator(self.config.get('swarm_config', {}))
        
        # Initialize agents
        self.agents = {}
        self._initialize_agents()
        
        # Initialize Hyperliquid client
        hyperliquid_config = self.config.get('hyperliquid_config', {})
        self.hyperliquid_client = HyperliquidClient(
            testnet=hyperliquid_config.get('environment') == 'testnet'
        )
        
        # System state
        self.is_running = False
        self.market_data_cache = {}
        self.agent_predictions_cache = {}
        self.trade_history = []
        self.performance_metrics = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_pnl': 0.0,
            'sharpe_ratio': 0.0,
            'max_drawdown': 0.0
        }
        
        # Risk management
        self.risk_config = self.config.get('risk_management', {})
        self.max_position_size = self.risk_config.get('max_position_size_percent', 2)
        self.max_daily_loss = self.risk_config.get('max_portfolio_risk_percent', 15)
        
        logger.info("Swarm Trading System initialized")
    
    def _initialize_agents(self):
        """Initialize all neural agents"""
        agent_configs = self.config.get('agent_configs', {})
        
        # Trend Agent
        if agent_configs.get('trend_agent', {}).get('enabled', True):
            trend_config = agent_configs['trend_agent']
            self.agents['trend_agent'] = TrendAgent(trend_config)
            self.swarm_coordinator.register_agent('trend_agent', self.agents['trend_agent'])
            logger.info("Trend Agent initialized")
        
        # Reversal Agent
        if agent_configs.get('reversal_agent', {}).get('enabled', True):
            reversal_config = agent_configs['reversal_agent']
            self.agents['reversal_agent'] = ReversalAgent(reversal_config)
            self.swarm_coordinator.register_agent('reversal_agent', self.agents['reversal_agent'])
            logger.info("Reversal Agent initialized")
        
        # Volatility Agent
        if agent_configs.get('volatility_agent', {}).get('enabled', True):
            volatility_config = agent_configs['volatility_agent']
            self.agents['volatility_agent'] = VolatilityAgent(volatility_config)
            self.swarm_coordinator.register_agent('volatility_agent', self.agents['volatility_agent'])
            logger.info("Volatility Agent initialized")
        
        # Note: Volume and Sentiment agents would be added here
        # For now, we'll work with the three implemented agents
    
    def fetch_market_data(self, symbol: str, timeframe: str = "5m", limit: int = 100) -> pd.DataFrame:
        """
        Fetch market data from Hyperliquid
        
        Args:
            symbol: Trading symbol
            timeframe: Candle timeframe
            limit: Number of candles
            
        Returns:
            DataFrame with OHLCV data
        """
        try:
            candles = self.hyperliquid_client.get_candles(symbol, timeframe, limit)
            
            if not candles:
                logger.warning(f"No candles returned for {symbol}")
                # Create synthetic data for testing
                return self._create_synthetic_data(symbol, limit)
            
            # Convert to DataFrame
            df = pd.DataFrame(candles)
            if len(df.columns) >= 6:
                df.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.set_index('timestamp', inplace=True)
            else:
                logger.error(f"Unexpected candle format for {symbol}")
                return self._create_synthetic_data(symbol, limit)
            
            logger.info(f"Fetched {len(df)} candles for {symbol}")
            return df
            
        except Exception as e:
            logger.error(f"Error fetching market data for {symbol}: {e}")
            return self._create_synthetic_data(symbol, limit)
    
    def _create_synthetic_data(self, symbol: str, n_samples: int) -> pd.DataFrame:
        """Create synthetic market data for testing"""
        np.random.seed(42)
        dates = pd.date_range(end=datetime.now(), periods=n_samples, freq='5min')
        
        # Generate realistic price series
        returns = np.random.normal(0.0001, 0.01, n_samples)
        prices = 100 * np.exp(np.cumsum(returns))
        
        df = pd.DataFrame({
            'timestamp': dates,
            'open': prices * (1 + np.random.uniform(-0.001, 0.001, n_samples)),
            'high': prices * (1 + np.random.uniform(0, 0.002, n_samples)),
            'low': prices * (1 - np.random.uniform(0, 0.002, n_samples)),
            'close': prices,
            'volume': np.random.lognormal(10, 1, n_samples)
        })
        
        df.set_index('timestamp', inplace=True)
        logger.info(f"Created synthetic data for {symbol}")
        return df
    
    def prepare_agent_features(self, df: pd.DataFrame, symbol: str) -> Dict[str, np.ndarray]:
        """
        Prepare features for all agents
        
        Args:
            df: Market data DataFrame
            symbol: Trading symbol
            
        Returns:
            Dictionary of agent_name -> feature array
        """
        # Calculate all technical features
        df_with_features = self.preprocessor.calculate_technical_features(df.copy())
        df_with_features = self.preprocessor.calculate_advanced_features(df_with_features)
        
        # Create agent-specific features
        agent_features = self.preprocessor.create_agent_specific_features(df_with_features)
        
        # Normalize features
        normalized_features = self.preprocessor.normalize_features(agent_features, fit=False)
        
        # Store in cache
        self.market_data_cache[symbol] = {
            'raw': df,
            'with_features': df_with_features,
            'agent_features': normalized_features
        }
        
        return normalized_features
    
    def get_agent_predictions(self, symbol: str) -> Dict[str, Dict]:
        """
        Get predictions from all agents
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Dictionary of agent predictions
        """
        if symbol not in self.market_data_cache:
            logger.error(f"No market data cached for {symbol}")
            return {}
        
        agent_features = self.market_data_cache[symbol]['agent_features']
        predictions = {}
        
        for agent_name, agent in self.agents.items():
            try:
                features = agent_features.get(agent_name)
                if features is None:
                    logger.warning(f"No features for agent {agent_name}")
                    continue
                
                # Get the most recent sequence
                if agent_name in ['trend_agent', 'volume_agent', 'sentiment_agent']:
                    # Sequence models need the last sequence_length samples
                    sequence_length = getattr(agent, 'sequence_length', 50)
                    if len(features) >= sequence_length:
                        sequence = features[-sequence_length:]
                        prediction = agent.get_trading_signal(sequence)
                    else:
                        logger.warning(f"Insufficient data for {agent_name}")
                        continue
                else:
                    # Non-sequence models use the latest features
                    latest_features = features[-1:]
                    prediction = agent.get_trading_signal(latest_features)
                
                predictions[agent_name] = prediction
                
            except Exception as e:
                logger.error(f"Error getting prediction from {agent_name}: {e}")
                continue
        
        self.agent_predictions_cache[symbol] = predictions
        return predictions
    
    def execute_trading_cycle(self, symbol: str):
        """
        Execute a complete trading cycle for a symbol
        
        Args:
            symbol: Trading symbol
        """
        logger.info(f"Starting trading cycle for {symbol}")
        
        try:
            # 1. Fetch market data
            df = self.fetch_market_data(symbol)
            if df.empty:
                logger.error(f"No market data for {symbol}")
                return
            
            # 2. Prepare features
            agent_features = self.prepare_agent_features(df, symbol)
            
            # 3. Get agent predictions
            predictions = self.get_agent_predictions(symbol)
            if not predictions:
                logger.warning(f"No predictions for {symbol}")
                return
            
            # 4. Get swarm consensus
            consensus = self.swarm_coordinator.get_consensus(predictions)
            
            # 5. Risk management check
            risk_ok, risk_reason = self.risk_management_check(consensus, symbol)
            if not risk_ok:
                logger.info(f"Risk check failed: {risk_reason}")
                consensus['signal'] = 'HOLD'  # Override to HOLD
                consensus['signal_strength'] = 0.0
            
            # 6. Execute trade if signal is actionable
            if consensus['signal'] in ['BUY', 'SELL'] and consensus['signal_strength'] > 0.3:
                execution_result = self.execute_trade(consensus, symbol)
                
                if execution_result['status'] == 'EXECUTED':
                    self.trade_history.append(execution_result)
                    self.update_performance_metrics(execution_result)
                    
                    logger.info(f"Trade executed: {symbol} {consensus['signal']} "
                               f"(Strength: {consensus['signal_strength']:.2f})")
                else:
                    logger.info(f"Trade not executed: {execution_result.get('reason', 'Unknown')}")
            
            # 7. Log consensus
            logger.info(f"Consensus for {symbol}: {consensus['signal']} "
                       f"(Strength: {consensus['signal_strength']:.2f}, "
                       f"Agreement: {consensus['agreement']:.2f})")
            
            # 8. Update agent weights based on recent performance
            self.update_agent_weights()
            
        except Exception as e:
            logger.error(f"Error in trading cycle for {symbol}: {e}")
    
    def risk_management_check(self, consensus: Dict, symbol: str) -> Tuple[bool, str]:
        """
        Perform risk management checks
        
        Args:
            consensus: Consensus signal
            symbol: Trading symbol
            
        Returns:
            Tuple of (allowed, reason)
        """
        # Check signal strength
        if consensus['signal_strength'] < 0.3:
            return False, f"Signal strength too low: {consensus['signal_strength']:.2f}"
        
        # Check agreement level
        if consensus['agreement'] < 0.4:
            return False, f"Agreement too low: {consensus['agreement']:.2f}"
        
        # Check daily loss limit (simplified)
        daily_loss = self.calculate_daily_pnl()
        if daily_loss < -self.max_daily_loss:
            return False, f"Daily loss limit reached: {daily_loss:.1f}%"
        
        # Check max positions (simplified)
        open_positions = [t for t in self.trade_history[-100:] 
                         if t.get('status') == 'OPEN' and t.get('symbol') == symbol]
        if len(open_positions) >= 3:
            return False, f"Max open positions reached for {symbol}"
        
        # Check position size
        position_size = consensus.get('position_size', 0.0)
        if position_size > self.max_position_size / 100:  # Convert percent to decimal
            return False, f"Position size too large: {position_size*100:.1f}%"
        
        return True, "Risk checks passed"
    
    def execute_trade(self, consensus: Dict, symbol: str) -> Dict:
        """
        Execute a trade based on consensus
        
        Args:
            consensus: Consensus signal
            symbol: Trading symbol
            
        Returns:
            Execution result
        """
        try:
            # Prepare order
            order_side = 'BUY' if consensus['signal'] == 'BUY' else 'SELL'
            
            # Get current price (simplified)
            if symbol in self.market_data_cache:
                current_price = float(self.market_data_cache[symbol]['raw']['close'].iloc[-1])
            else:
                current_price = 100.0  # Default for testing
            
            # Calculate position size in USD
            position_size_usd = consensus.get('position_size', 0.5) * 1000  # Base $1000
            
            # Prepare Hyperliquid order (commented out for safety)
            """
            order_data = {
                "coin": symbol,
                "is_buy": order_side == 'BUY',
                "sz": position_size_usd,
                "limit_px": current_price,
                "order_type": {"limit": {"tif": "Gtc"}},
                "reduce_only": False
            }
            
            # Place order
            response = self.hyperliquid_client.place_order(order_data)
            """
            
            # For now, simulate execution
            response = {
                "status": "SIMULATED",
                "order_id": int(time.time() * 1000),
                "symbol": symbol,
                "side": order_side,
                "size_usd": position_size_usd,
                "price": current_price,
                "timestamp": datetime.now().isoformat()
            }
            
            # Create trade record
            trade_record = {
                'trade_id': response['order_id'],
                'symbol': symbol,
                'side': order_side,
                'entry_price': current_price,
                'size_usd': position_size_usd,
                'stop_loss': current_price * (1 - consensus['stop_loss_pct']),
                'take_profit': current_price * (1 + consensus['take_profit_pct']),
                'entry_time': datetime.now().isoformat(),
                'consensus_strength': consensus['signal_strength'],
                'consensus_agreement': consensus['agreement'],
                'agent_details': consensus['agent_details'],
                'status': 'OPEN',
                'pnl': 0.0,
                'pnl_percent': 0.0
            }
            
            return {
                'status': 'EXECUTED',
                'trade': trade_record,
                'response': response
            }
            
        except Exception as e:
            logger.error(f"Error executing trade: {e}")
            return {
                'status': 'ERROR',
                'error': str(e),
                'symbol': symbol
            }
    
    def calculate_daily_pnl(self) -> float:
        """Calculate today's P&L percentage (simplified)"""
        today = datetime.now().date()
        today_trades = [t for t in self.trade_history 
                       if datetime.fromisoformat(t.get('entry_time', '')).date() == today]
        
        if not today_trades:
            return 0.0
        
        total_pnl = sum(t.get('pnl', 0) for t in today_trades)
        total_invested = sum(t.get('size_usd', 0) for t in today_trades)
        
        if total_invested > 0:
            return (total_pnl / total_invested) * 100
        return 0.0
    
    def update_performance_metrics(self, execution_result: Dict):
        """Update performance metrics after trade execution"""
        trade = execution_result.get('trade', {})
        
        if trade.get('status') == 'CLOSED':
            self.performance_metrics['total_trades'] += 1
            
            pnl = trade.get('pnl', 0)
            self.performance_metrics['total_pnl'] += pnl
            
            if pnl > 0:
                self.performance_metrics['winning_trades'] += 1
            elif pnl < 0:
                self.performance_metrics['losing_trades'] += 1
            
            # Update Sharpe ratio (simplified)
            if self.performance_metrics['total_trades'] > 0:
                win_rate = self.performance_metrics['winning_trades'] / self.performance_metrics['total_trades']
                self.