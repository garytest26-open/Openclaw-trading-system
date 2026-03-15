#!/usr/bin/env python3
"""
Swarm Coordinator for Swarm Trading AI
Complete implementation with weighted consensus and evolutionary optimization
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Any
import logging
from datetime import datetime, timedelta
import json
from collections import defaultdict, deque
import random

logger = logging.getLogger(__name__)


class SwarmCoordinator:
    """
    Complete swarm coordinator for neural trading agents
    Manages agent registration, prediction aggregation, and evolutionary optimization
    """
    
    def __init__(self, config: Dict):
        """
        Initialize swarm coordinator
        
        Args:
            config: Swarm configuration dictionary
        """
        self.config = config
        self.agents = {}
        self.agent_weights = config.get('voting_weights', {})
        self.consensus_method = config.get('consensus_method', 'weighted_voting')
        self.min_confidence = config.get('min_confidence', 0.6)
        self.max_disagreement = config.get('max_disagreement', 0.3)
        
        # Performance tracking
        self.agent_performance = defaultdict(lambda: deque(maxlen=100))
        self.consensus_history = deque(maxlen=1000)
        self.trade_history = deque(maxlen=1000)
        
        # Evolutionary optimization
        self.evolutionary_config = config.get('evolutionary_optimization', {})
        self.evolutionary_enabled = self.evolutionary_config.get('enabled', False)
        self.generation = 0
        self.population_size = self.evolutionary_config.get('population_size', 20)
        
        # Fusion network placeholder (would be neural network in production)
        self.fusion_network = None
        self.fusion_initialized = False
        
        # State tracking
        self.last_predictions = {}
        self.last_consensus = None
        self.market_context = {}
        
        logger.info("Swarm Coordinator initialized")
    
    def register_agent(self, agent_name: str, agent_instance, 
                      initial_weight: float = None, 
                      performance_history: List[float] = None):
        """
        Register a trading agent with the swarm
        
        Args:
            agent_name: Name of the agent
            agent_instance: Agent instance
            initial_weight: Initial voting weight
            performance_history: Initial performance history
        """
        weight = initial_weight if initial_weight is not None else self.agent_weights.get(agent_name, 0.2)
        
        self.agents[agent_name] = {
            'instance': agent_instance,
            'weight': weight,
            'performance': deque(performance_history if performance_history else [], maxlen=100),
            'confidence_history': deque(maxlen=100),
            'signal_history': deque(maxlen=100),
            'last_prediction': None,
            'active': True
        }
        
        logger.info(f"Registered agent: {agent_name} with weight {weight:.3f}")
    
    def deactivate_agent(self, agent_name: str):
        """Deactivate an agent (temporarily remove from consensus)"""
        if agent_name in self.agents:
            self.agents[agent_name]['active'] = False
            logger.info(f"Deactivated agent: {agent_name}")
    
    def activate_agent(self, agent_name: str):
        """Activate a previously deactivated agent"""
        if agent_name in self.agents:
            self.agents[agent_name]['active'] = True
            logger.info(f"Activated agent: {agent_name}")
    
    def update_agent_weight(self, agent_name: str, new_weight: float):
        """Update an agent's voting weight"""
        if agent_name in self.agents:
            old_weight = self.agents[agent_name]['weight']
            self.agents[agent_name]['weight'] = max(0.0, min(1.0, new_weight))
            logger.info(f"Updated {agent_name} weight: {old_weight:.3f} -> {new_weight:.3f}")
    
    def collect_predictions(self, market_data: Dict, symbol: str) -> Dict[str, Dict]:
        """
        Collect predictions from all active agents
        
        Args:
            market_data: Market data dictionary with agent-specific features
            symbol: Trading symbol
            
        Returns:
            Dictionary of agent predictions
        """
        predictions = {}
        
        for agent_name, agent_info in self.agents.items():
            if not agent_info['active']:
                continue
            
            try:
                agent = agent_info['instance']
                
                # Get agent-specific features
                agent_features = market_data.get(f'{agent_name}_features')
                if agent_features is None:
                    logger.warning(f"No features found for agent {agent_name}")
                    continue
                
                # Get prediction from agent
                if hasattr(agent, 'get_trading_signal'):
                    prediction = agent.get_trading_signal(agent_features)
                elif hasattr(agent, 'predict'):
                    raw_pred = agent.predict(agent_features)
                    prediction = self._convert_to_signal(raw_pred, agent_name)
                else:
                    logger.error(f"Agent {agent_name} has no prediction method")
                    continue
                
                # Add metadata
                prediction['agent_name'] = agent_name
                prediction['timestamp'] = datetime.now().isoformat()
                prediction['symbol'] = symbol
                prediction['weight'] = agent_info['weight']
                
                predictions[agent_name] = prediction
                agent_info['last_prediction'] = prediction
                
                # Update confidence history
                agent_info['confidence_history'].append(prediction.get('confidence', 0.5))
                agent_info['signal_history'].append(prediction.get('signal', 'HOLD'))
                
            except Exception as e:
                logger.error(f"Error getting prediction from agent {agent_name}: {e}")
                continue
        
        self.last_predictions = predictions
        return predictions
    
    def _convert_to_signal(self, raw_prediction: Dict, agent_name: str) -> Dict:
        """
        Convert raw prediction to standardized signal format
        
        Args:
            raw_prediction: Raw prediction from agent
            agent_name: Name of the agent
            
        Returns:
            Standardized signal dictionary
        """
        # Agent-specific conversion logic
        if agent_name == 'trend_agent':
            return self._convert_trend_signal(raw_prediction)
        elif agent_name == 'reversal_agent':
            return self._convert_reversal_signal(raw_prediction)
        elif agent_name == 'volatility_agent':
            return self._convert_volatility_signal(raw_prediction)
        elif agent_name == 'volume_agent':
            return self._convert_volume_signal(raw_prediction)
        elif agent_name == 'sentiment_agent':
            return self._convert_sentiment_signal(raw_prediction)
        else:
            return self._convert_generic_signal(raw_prediction)
    
    def _convert_trend_signal(self, prediction: Dict) -> Dict:
        """Convert trend agent prediction"""
        return {
            'signal': prediction.get('signal', 'HOLD'),
            'signal_strength': prediction.get('signal_strength', 0.0),
            'confidence': prediction.get('confidence', 0.5),
            'predicted_return': prediction.get('predicted_return', 0.0),
            'stop_loss_pct': prediction.get('stop_loss_pct', 0.01),
            'take_profit_pct': prediction.get('take_profit_pct', 0.02),
            'position_size': prediction.get('position_size', 0.5)
        }
    
    def _convert_reversal_signal(self, prediction: Dict) -> Dict:
        """Convert reversal agent prediction"""
        return {
            'signal': prediction.get('signal', 'HOLD'),
            'signal_strength': prediction.get('signal_strength', 0.0),
            'confidence': prediction.get('confidence', 0.5),
            'predicted_return': prediction.get('predicted_return', 0.0),
            'stop_loss_pct': prediction.get('stop_loss_pct', 0.005),
            'take_profit_pct': prediction.get('take_profit_pct', 0.015),
            'position_size': prediction.get('position_size', 0.3)
        }
    
    def _convert_volatility_signal(self, prediction: Dict) -> Dict:
        """Convert volatility agent prediction"""
        return {
            'signal': prediction.get('signal', 'HOLD'),
            'signal_strength': prediction.get('signal_strength', 0.0),
            'confidence': prediction.get('confidence', 0.5),
            'predicted_return': prediction.get('predicted_return', 0.0),
            'stop_loss_pct': prediction.get('stop_loss_pct', 0.02),
            'take_profit_pct': prediction.get('take_profit_pct', 0.04),
            'position_size': prediction.get('position_size', 0.2)
        }
    
    def _convert_volume_signal(self, prediction: Dict) -> Dict:
        """Convert volume agent prediction"""
        return {
            'signal': prediction.get('signal', 'HOLD'),
            'signal_strength': prediction.get('signal_strength', 0.0),
            'confidence': prediction.get('confidence', 0.5),
            'predicted_return': prediction.get('predicted_return', 0.0),
            'stop_loss_pct': prediction.get('stop_loss_pct', 0.008),
            'take_profit_pct': prediction.get('take_profit_pct', 0.016),
            'position_size': prediction.get('position_size', 0.4)
        }
    
    def _convert_sentiment_signal(self, prediction: Dict) -> Dict:
        """Convert sentiment agent prediction"""
        return {
            'signal': prediction.get('signal', 'HOLD'),
            'signal_strength': prediction.get('signal_strength', 0.0),
            'confidence': prediction.get('confidence', 0.5),
            'predicted_return': prediction.get('predicted_return', 0.0),
            'stop_loss_pct': prediction.get('stop_loss_pct', 0.015),
            'take_profit_pct': prediction.get('take_profit_pct', 0.03),
            'position_size': prediction.get('position_size', 0.25)
        }
    
    def _convert_generic_signal(self, prediction: Dict) -> Dict:
        """Generic conversion for unknown agents"""
        return {
            'signal': prediction.get('signal', 'HOLD'),
            'signal_strength': float(prediction.get('signal_strength', 0.0)),
            'confidence': float(prediction.get('confidence', 0.5)),
            'predicted_return': float(prediction.get('predicted_return', 0.0)),
            'stop_loss_pct': float(prediction.get('stop_loss_pct', 0.01)),
            'take_profit_pct': float(prediction.get('take_profit_pct', 0.02)),
            'position_size': float(prediction.get('position_size', 0.5))
        }
    
    def calculate_weighted_consensus(self, predictions: Dict[str, Dict]) -> Dict:
        """
        Calculate consensus using weighted voting
        
        Args:
            predictions: Dictionary of agent predictions
            
        Returns:
            Consensus signal dictionary
        """
        if not predictions:
            return self._create_null_consensus()
        
        # Initialize tracking
        buy_votes = []
        sell_votes = []
        hold_votes = []
        
        weighted_signals = []
        weighted_confidences = []
        weighted_returns = []
        weighted_stop_losses = []
        weighted_take_profits = []
        
        agent_details = []
        total_weight = 0.0
        
        for agent_name, prediction in predictions.items():
            agent_info = self.agents.get(agent_name, {})
            weight = agent_info.get('weight', 0.2)
            total_weight += weight
            
            signal = prediction.get('signal', 'HOLD')
            confidence = prediction.get('confidence', 0.5)
            signal_strength = prediction.get('signal_strength', 0.0)
            pred_return = prediction.get('predicted_return', 0.0)
            stop_loss = prediction.get('stop_loss_pct', 0.01)
            take_profit = prediction.get('take_profit_pct', 0.02)
            
            # Track votes
            vote_info = {
                'agent': agent_name,
                'weight': weight,
                'confidence': confidence,
                'strength': signal_strength,
                'signal': signal
            }
            
            if signal == 'BUY':
                buy_votes.append(vote_info)
                vote_value = 1.0
            elif signal == 'SELL':
                sell_votes.append(vote_info)
                vote_value = -1.0
            else:  # HOLD
                hold_votes.append(vote_info)
                vote_value = 0.0
            
            # Weighted calculations
            weighted_signal = vote_value * weight * confidence * signal_strength
            weighted_signals.append(weighted_signal)
            weighted_confidences.append(confidence * weight)
            weighted_returns.append(pred_return * weight)
            weighted_stop_losses.append(stop_loss * weight)
            weighted_take_profits.append(take_profit * weight)
            
            # Store agent details
            agent_details.append({
                'agent': agent_name,
                'signal': signal,
                'confidence': confidence,
                'strength': signal_strength,
                'weight': weight,
                'predicted_return': pred_return,
                'stop_loss': stop_loss,
                'take_profit': take_profit
            })
        
        if total_weight == 0:
            return self._create_null_consensus()
        
        # Calculate consensus metrics
        consensus_signal_value = sum(weighted_signals) / total_weight
        swarm_confidence = sum(weighted_confidences) / total_weight
        predicted_return = sum(weighted_returns) / total_weight
        avg_stop_loss = sum(weighted_stop_losses) / total_weight
        avg_take_profit = sum(weighted_take_profits) / total_weight
        
        # Determine final signal
        if consensus_signal_value > self.min_confidence:
            final_signal = 'BUY'
            signal_strength = min(1.0, consensus_signal_value)
        elif consensus_signal_value < -self.min_confidence:
            final_signal = 'SELL'
            signal_strength = min(1.0, -consensus_signal_value)
        else:
            final_signal = 'HOLD'
            signal_strength = 0.0
        
        # Calculate agreement level
        n_agents = len(predictions)
        buy_ratio = len(buy_votes) / n_agents if n_agents > 0 else 0
        sell_ratio = len(sell_votes) / n_agents if n_agents > 0 else 0
        hold_ratio = len(hold_votes) / n_agents if n_agents > 0 else 0
        
        max_ratio = max(buy_ratio, sell_ratio, hold_ratio)
        agreement = max_ratio if max_ratio > 0.5 else 0.5
        disagreement = 1.0 - agreement
        
        # Check for high disagreement
        if disagreement > self.max_disagreement:
            logger.warning(f"High disagreement detected: {disagreement:.2f}")
            # In high disagreement, be more conservative
            if final_signal != 'HOLD':
                signal_strength *= 0.5
                swarm_confidence *= 0.7
        
        # Calculate position sizing
        if final_signal != 'HOLD':
            # Base position size on signal strength and confidence
            base_size = min(1.0, signal_strength * swarm_confidence)
            
            # Adjust for agreement
            position_size = base_size * agreement
            
            # Adjust for number of agents (diversity bonus)
            diversity_factor = 1.0 - (1.0 / max(1, n_agents))
            position_size *= diversity_factor
            
            # Adjust stop loss and take profit based on consensus
            stop_loss_pct = avg_stop_loss / max(0.3, signal_strength)
            take_profit_pct = avg_take_profit * signal_strength
        else:
            position_size = 0.0
            stop_loss_pct = avg_stop_loss
            take_profit_pct = avg_take_profit
        
        consensus = {
            'signal': final_signal,
            'signal_strength': float(signal_strength),
            'swarm_confidence': float(swarm_confidence),
            'predicted_return': float(predicted_return),
            'agreement': float(agreement),
            'disagreement': float(disagreement),
            'position_size': float(position_size),
            'stop_loss_pct': float(stop_loss_pct),
            'take_profit_pct': float(take_profit_pct),
            'n_agents': n_agents,
            'buy_votes': len(buy_votes),
            'sell_votes': len(sell_votes),
            'hold_votes': len(hold_votes),
            'buy_ratio': float(buy_ratio),
            'sell_ratio': float(sell_ratio),
            'hold_ratio': float(hold_ratio),
            'agent_details': agent_details,
            'timestamp': datetime.now().isoformat(),
            'consensus_method': 'weighted_voting'
        }
        
        # Store in history
        self.consensus_history.append(consensus)
        self.last_consensus = consensus
        
        logger.info(f"Consensus: {final_signal} (Strength: {signal_strength:.2f}, "
                   f"Confidence: {swarm_confidence:.2f}, Agreement: {agreement:.2f})")
        
        return consensus
    
    def calculate_neural_consensus(self, predictions: Dict[str, Dict]) -> Dict:
        """
        Calculate consensus using neural fusion network
        
        Args:
            predictions: Dictionary of agent predictions
            
        Returns:
            Consensus signal dictionary
        """
        # This would use a neural network to combine agent predictions
        # For now, fall back to weighted consensus
        logger.warning("Neural fusion network not implemented, using weighted consensus")
        return self.calculate_weighted_