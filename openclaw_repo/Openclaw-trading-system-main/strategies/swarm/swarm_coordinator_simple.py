#!/usr/bin/env python3
"""
Simple Swarm Coordinator for Swarm Trading AI
Basic weighted consensus implementation
"""

import numpy as np
from typing import Dict, List, Optional
import logging
from datetime import datetime
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


class SimpleSwarmCoordinator:
    """
    Simple swarm coordinator with weighted consensus
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.agents = {}
        self.agent_weights = config.get('voting_weights', {
            'trend_agent': 0.25,
            'reversal_agent': 0.20,
            'volatility_agent': 0.15,
            'volume_agent': 0.20,
            'sentiment_agent': 0.20
        })
        self.min_confidence = 0.6
        self.consensus_history = deque(maxlen=100)
        
        logger.info("Simple Swarm Coordinator initialized")
    
    def register_agent(self, agent_name: str, agent_instance):
        """Register an agent"""
        weight = self.agent_weights.get(agent_name, 0.2)
        self.agents[agent_name] = {
            'instance': agent_instance,
            'weight': weight,
            'active': True
        }
        logger.info(f"Registered {agent_name} with weight {weight}")
    
    def get_consensus(self, predictions: Dict[str, Dict]) -> Dict:
        """
        Calculate weighted consensus from agent predictions
        
        Args:
            predictions: Dict of agent_name -> prediction dict
            
        Returns:
            Consensus signal
        """
        if not predictions:
            return self._null_consensus()
        
        buy_strength = 0
        sell_strength = 0
        total_weight = 0
        details = []
        
        for agent_name, pred in predictions.items():
            if agent_name not in self.agents:
                continue
            
            weight = self.agents[agent_name]['weight']
            signal = pred.get('signal', 'HOLD')
            confidence = pred.get('confidence', 0.5)
            strength = pred.get('signal_strength', 0.0)
            
            if signal == 'BUY':
                buy_strength += weight * confidence * strength
            elif signal == 'SELL':
                sell_strength += weight * confidence * strength
            
            total_weight += weight
            details.append({
                'agent': agent_name,
                'signal': signal,
                'confidence': confidence,
                'strength': strength,
                'weight': weight
            })
        
        if total_weight == 0:
            return self._null_consensus()
        
        # Calculate net signal
        net_signal = (buy_strength - sell_strength) / total_weight
        
        # Determine final signal
        if net_signal > self.min_confidence:
            final_signal = 'BUY'
            signal_strength = min(1.0, net_signal)
        elif net_signal < -self.min_confidence:
            final_signal = 'SELL'
            signal_strength = min(1.0, -net_signal)
        else:
            final_signal = 'HOLD'
            signal_strength = 0.0
        
        # Calculate agreement
        buy_count = sum(1 for d in details if d['signal'] == 'BUY')
        sell_count = sum(1 for d in details if d['signal'] == 'SELL')
        hold_count = sum(1 for d in details if d['signal'] == 'HOLD')
        total = len(details)
        
        agreement = max(buy_count, sell_count, hold_count) / total if total > 0 else 0.5
        
        consensus = {
            'signal': final_signal,
            'signal_strength': float(signal_strength),
            'agreement': float(agreement),
            'buy_count': buy_count,
            'sell_count': sell_count,
            'hold_count': hold_count,
            'agent_details': details,
            'timestamp': datetime.now().isoformat()
        }
        
        self.consensus_history.append(consensus)
        return consensus
    
    def _null_consensus(self) -> Dict:
        """Return null consensus when no predictions"""
        return {
            'signal': 'HOLD',
            'signal_strength': 0.0,
            'agreement': 0.5,
            'buy_count': 0,
            'sell_count': 0,
            'hold_count': 0,
            'agent_details': [],
            'timestamp': datetime.now().isoformat()
        }
    
    def update_weights_based_on_performance(self, performance_scores: Dict[str, float]):
        """
        Update agent weights based on performance
        
        Args:
            performance_scores: Dict of agent_name -> performance score (0-1)
        """
        for agent_name, score in performance_scores.items():
            if agent_name in self.agents:
                # Simple update: weight = score normalized across all agents
                self.agents[agent_name]['weight'] = score
        
        # Normalize weights to sum to 1
        total = sum(agent['weight'] for agent in self.agents.values())
        if total > 0:
            for agent in self.agents.values():
                agent['weight'] /= total
    
    def get_status(self) -> Dict:
        """Get coordinator status"""
        active_agents = [name for name, info in self.agents.items() if info['active']]
        
        return {
            'total_agents': len(self.agents),
            'active_agents': len(active_agents),
            'agent_weights': {name: info['weight'] for name, info in self.agents.items()},
            'recent_consensus_count': len(self.consensus_history)
        }