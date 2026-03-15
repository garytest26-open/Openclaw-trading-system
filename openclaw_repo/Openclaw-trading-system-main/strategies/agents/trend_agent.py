#!/usr/bin/env python3
"""
Trend Agent for Swarm Trading AI
Bidirectional LSTM with Attention for trend detection
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Tuple, Optional, Dict
import logging

logger = logging.getLogger(__name__)


class AttentionLayer(nn.Module):
    """Attention mechanism for focusing on important timesteps"""
    
    def __init__(self, hidden_size: int):
        super().__init__()
        self.attention = nn.Sequential(
            nn.Linear(hidden_size * 2, hidden_size),
            nn.Tanh(),
            nn.Linear(hidden_size, 1)
        )
    
    def forward(self, lstm_output: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Apply attention to LSTM outputs
        
        Args:
            lstm_output: LSTM outputs [batch_size, seq_len, hidden_size*2]
            
        Returns:
            context_vector: Weighted sum of LSTM outputs
            attention_weights: Attention weights
        """
        # Calculate attention scores
        attention_scores = self.attention(lstm_output)  # [batch_size, seq_len, 1]
        attention_weights = F.softmax(attention_scores, dim=1)
        
        # Calculate context vector
        context_vector = torch.sum(attention_weights * lstm_output, dim=1)
        
        return context_vector, attention_weights.squeeze(-1)


class TrendAgent(nn.Module):
    """
    Trend detection agent using BiLSTM with Attention
    Specialized for identifying market trends
    """
    
    def __init__(self, config: Dict):
        """
        Initialize trend agent
        
        Args:
            config: Agent configuration dictionary
        """
        super().__init__()
        
        self.config = config
        self.input_size = config.get('input_size', 9)
        self.hidden_size = config.get('hidden_size', 128)
        self.num_layers = config.get('num_layers', 3)
        self.dropout = config.get('dropout', 0.2)
        self.sequence_length = config.get('sequence_length', 50)
        
        # Bidirectional LSTM
        self.lstm = nn.LSTM(
            input_size=self.input_size,
            hidden_size=self.hidden_size,
            num_layers=self.num_layers,
            batch_first=True,
            bidirectional=True,
            dropout=self.dropout if self.num_layers > 1 else 0
        )
        
        # Attention layer
        self.attention = AttentionLayer(self.hidden_size)
        
        # Fully connected layers
        self.fc_layers = nn.Sequential(
            nn.Linear(self.hidden_size * 2, 128),
            nn.BatchNorm1d(128),
            nn.LeakyReLU(0.1),
            nn.Dropout(self.dropout),
            
            nn.Linear(128, 64),
            nn.BatchNorm1d(64),
            nn.LeakyReLU(0.1),
            nn.Dropout(self.dropout),
            
            nn.Linear(64, 32),
            nn.BatchNorm1d(32),
            nn.LeakyReLU(0.1)
        )
        
        # Output heads
        self.trend_head = nn.Sequential(
            nn.Linear(32, 16),
            nn.LeakyReLU(0.1),
            nn.Linear(16, 3)  # Up, Down, Sideways
        )
        
        self.confidence_head = nn.Sequential(
            nn.Linear(32, 8),
            nn.LeakyReLU(0.1),
            nn.Linear(8, 1),
            nn.Sigmoid()
        )
        
        self.regression_head = nn.Sequential(
            nn.Linear(32, 16),
            nn.LeakyReLU(0.1),
            nn.Linear(16, 1)  # Predicted return
        )
        
        # Initialize weights
        self._initialize_weights()
        
        logger.info(f"Trend Agent initialized: {self.input_size} inputs, "
                   f"{self.hidden_size} hidden, {self.num_layers} layers")
    
    def _initialize_weights(self):
        """Initialize network weights"""
        for name, param in self.named_parameters():
            if 'weight' in name:
                if 'lstm' in name:
                    nn.init.orthogonal_(param)
                elif 'attention' in name or 'fc' in name:
                    nn.init.kaiming_normal_(param, nonlinearity='leaky_relu')
            elif 'bias' in name:
                nn.init.constant_(param, 0)
    
    def forward(self, x: torch.Tensor, return_attention: bool = False) -> Dict:
        """
        Forward pass through the network
        
        Args:
            x: Input tensor [batch_size, seq_len, input_size]
            return_attention: Whether to return attention weights
            
        Returns:
            Dictionary with predictions
        """
        batch_size = x.size(0)
        
        # LSTM forward pass
        lstm_out, (hidden, cell) = self.lstm(x)
        # lstm_out: [batch_size, seq_len, hidden_size*2]
        
        # Apply attention
        context_vector, attention_weights = self.attention(lstm_out)
        
        # Fully connected layers
        fc_features = self.fc_layers(context_vector)
        
        # Get predictions from all heads
        trend_logits = self.trend_head(fc_features)
        trend_probs = F.softmax(trend_logits, dim=-1)
        
        confidence = self.confidence_head(fc_features)
        regression = self.regression_head(fc_features)
        
        # Calculate trend strength
        trend_strength = torch.max(trend_probs, dim=-1)[0]
        
        # Determine trend direction (1 for up, -1 for down, 0 for sideways)
        trend_direction = torch.argmax(trend_probs, dim=-1) - 1  # Convert to -1, 0, 1
        
        result = {
            'trend_probs': trend_probs,
            'trend_direction': trend_direction,
            'trend_strength': trend_strength,
            'confidence': confidence,
            'predicted_return': regression,
            'context_vector': context_vector
        }
        
        if return_attention:
            result['attention_weights'] = attention_weights
        
        return result
    
    def predict(self, x: np.ndarray, device: str = 'cpu') -> Dict:
        """
        Make prediction on numpy array
        
        Args:
            x: Input array [seq_len, input_size] or [batch_size, seq_len, input_size]
            device: Device to run on
            
        Returns:
            Prediction dictionary
        """
        self.eval()
        
        # Handle single sequence
        if len(x.shape) == 2:
            x = x[np.newaxis, ...]
        
        # Convert to tensor
        x_tensor = torch.FloatTensor(x).to(device)
        
        with torch.no_grad():
            predictions = self.forward(x_tensor)
        
        # Convert to numpy
        result = {
            'trend_probs': predictions['trend_probs'].cpu().numpy(),
            'trend_direction': predictions['trend_direction'].cpu().numpy(),
            'trend_strength': predictions['trend_strength'].cpu().numpy(),
            'confidence': predictions['confidence'].cpu().numpy(),
            'predicted_return': predictions['predicted_return'].cpu().numpy()
        }
        
        return result
    
    def get_trading_signal(self, x: np.ndarray, device: str = 'cpu') -> Dict:
        """
        Generate trading signal from input
        
        Args:
            x: Input features
            device: Device to run on
            
        Returns:
            Trading signal dictionary
        """
        predictions = self.predict(x, device)
        
        # Extract values from batch
        trend_dir = predictions['trend_direction'][0]
        trend_str = predictions['trend_strength'][0]
        confidence = predictions['confidence'][0][0]
        pred_return = predictions['predicted_return'][0][0]
        
        # Determine signal
        if trend_dir == 1 and trend_str > 0.6 and confidence > 0.7:
            signal = 'BUY'
            signal_strength = float(trend_str * confidence)
        elif trend_dir == -1 and trend_str > 0.6 and confidence > 0.7:
            signal = 'SELL'
            signal_strength = float(trend_str * confidence)
        else:
            signal = 'HOLD'
            signal_strength = 0.0
        
        # Calculate stop loss and take profit levels
        if signal != 'HOLD':
            # Dynamic levels based on volatility and trend strength
            stop_loss_pct = 0.01 / (trend_str * confidence)  # 1% base, adjusted
            take_profit_pct = stop_loss_pct * 2.0  # 2:1 risk-reward
            
            risk_adjusted_size = min(1.0, confidence * trend_str)
        else:
            stop_loss_pct = take_profit_pct = risk_adjusted_size = 0.0
        
        return {
            'signal': signal,
            'signal_strength': signal_strength,
            'confidence': float(confidence),
            'trend_direction': int(trend_dir),
            'trend_strength': float(trend_str),
            'predicted_return': float(pred_return),
            'stop_loss_pct': float(stop_loss_pct),
            'take_profit_pct': float(take_profit_pct),
            'position_size': float(risk_adjusted_size),
            'agent_type': 'trend'
        }
    
    def compute_loss(self, predictions: Dict, targets: Dict) -> torch.Tensor:
        """
        Compute combined loss for multi-task learning
        
        Args:
            predictions: Dictionary of predictions
            targets: Dictionary of targets
            
        Returns:
            Combined loss tensor
        """
        # Classification loss (trend direction)
        trend_targets = targets.get('trend_direction')
        if trend_targets is not None:
            # Convert to class indices (0, 1, 2)
            class_targets = trend_targets + 1  # Convert -1,0,1 to 0,1,2
            cls_loss = F.cross_entropy(predictions['trend_logits'], class_targets.long())
        else:
            cls_loss = torch.tensor(0.0).to(predictions['trend_probs'].device)
        
        # Regression loss (predicted returns)
        return_targets = targets.get('returns')
        if return_targets is not None:
            reg_loss = F.mse_loss(predictions['predicted_return'], return_targets)
        else:
            reg_loss = torch.tensor(0.0).to(predictions['predicted_return'].device)
        
        # Confidence regularization (encourage meaningful confidence)
        confidence = predictions['confidence']
        conf_reg = torch.mean((confidence - 0.5) ** 2)  # Penalize extreme confidence
        
        # Attention regularization (encourage diverse attention)
        if 'attention_weights' in predictions:
            attention = predictions['attention_weights']
            # Encourage attention to be not too peaked
            entropy = -torch.sum(attention * torch.log(attention + 1e-10), dim=-1)
            attn_reg = -torch.mean(entropy)  # Negative because we want higher entropy
        else:
            attn_reg = torch.tensor(0.0).to(confidence.device)
        
        # Combine losses with weights
        total_loss = (
            cls_loss * 1.0 +
            reg_loss * 0.5 +
            conf_reg * 0.1 +
            attn_reg * 0.05
        )
        
        return total_loss
    
    def get_attention_visualization(self, x: np.ndarray, device: str = 'cpu') -> np.ndarray:
        """
        Get attention weights for visualization
        
        Args:
            x: Input sequence
            device: Device to run on
            
        Returns:
            Attention weights array
        """
        self.eval()
        
        if len(x.shape) == 2:
            x = x[np.newaxis, ...]
        
        x_tensor = torch.FloatTensor(x).to(device)
        
        with torch.no_grad():
            predictions = self.forward(x_tensor, return_attention=True)
        
        return predictions['attention_weights'].cpu().numpy()


class TrendAgentTrainer:
    """Trainer for the trend agent"""
    
    def __init__(self, agent: TrendAgent, config: Dict):
        """
        Initialize trainer
        
        Args:
            agent: TrendAgent instance
            config: Training configuration
        """
        self.agent = agent
        self.config = config
        
        # Optimizer
        self.optimizer = torch.optim.AdamW(
            agent.parameters(),
            lr=config.get('learning_rate', 0.001),
            weight_decay=config.get('weight_decay', 0.01)
        )
        
        # Learning rate scheduler
        self.scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer,
            mode='min',
            factor=0.5,
            patience=10,
            verbose=True
        )
        
        # Early stopping
        self.best_loss = float('inf')
        self.patience_counter = 0
        self.patience = config.get('early_stopping_patience', 20)
        
        self.device = config.get('device', 'cpu')
        self.agent.to(self.device)
        
        logger.info("Trend Agent Trainer initialized")
    
    def train_epoch(self, train_loader, epoch: int) -> float:
        """
        Train for one epoch
        
        Args:
            train_loader: DataLoader for training data
            epoch: Current epoch number
            
        Returns:
            Average training loss
        """
        self.agent.train()
        total_loss = 0
        n_batches = 0
        
        for batch_idx, (x_batch, y_batch) in enumerate(train_loader):
            x_batch = x_batch.to(self.device)
            y_batch = y_batch.to(self.device)
            
            # Prepare targets
            targets = {
                'returns': y_batch[:, 0],  # Future returns
                'trend_direction': torch.sign(y_batch[:, 0])  # Sign of returns
            }
            
            # Forward pass
            self.optimizer.zero_grad()
            predictions = self.agent(x_batch)
            
            # Compute loss
            loss = self.agent.compute_loss(predictions, targets)
            
            # Backward pass
            loss.backward()
            
            # Gradient clipping
            torch.nn.utils.clip_grad_norm_(self.agent.parameters(), max_norm=1.0)
            
            # Optimizer step
            self.optimizer.step()
            
            total_loss += loss.item()
            n_batches += 1
            
            if batch_idx % 100 == 0:
                logger.info(f"Epoch {epoch}, Batch {batch_idx}: Loss = {loss.item():.4f}")
        
        avg_loss = total_loss / n_batches if n_batches > 0 else 0
        return avg_loss
    
    def validate(self, val_loader) -> Tuple[float, Dict]:
        """
        Validate on validation set
        
        Args:
            val_loader: DataLoader for validation data
            
        Returns:
            Tuple of (average loss, metrics dictionary)
        """
        self.agent.eval()
        total_loss = 0
        n_batches = 0
        
        all_predictions = []
        all_targets = []
        
        with torch.no_grad():
            for x_batch, y_batch in val_loader:
                x_batch = x_batch.to(self.device)
                y_batch = y_batch.to(self.device)
                
                targets = {
                    'returns': y_batch[:, 0],
                    'trend_direction': torch.sign(y_batch[:, 0])
                }
                
                predictions = self.agent(x_batch)
                loss = self.agent.compute_loss(predictions, targets)
                
                total_loss += loss.item()
                n_batches += 1
                
                # Collect predictions for metrics
                trend_pred = torch.argmax(predictions['trend_probs'], dim=-1) - 1
                all_predictions.append(trend_pred.cpu().numpy())
                all_targets.append(targets['trend_direction'].cpu().numpy())
        
        avg_loss = total_loss / n_batches if n_batches > 0 else 0
        
        # Calculate metrics
        if len(all_predictions) > 0:
            predictions_np = np.concatenate(all_predictions)
            targets_np = np.concatenate(all_targets)
            
            accuracy = np.mean(predictions_np == targets_np)
            metrics = {
                'loss': avg_loss,
                'accuracy': accuracy,
                'n_samples': len(predictions_np)
            }
        else:
            metrics = {'loss': avg_loss}
        
        return avg_loss, metrics
    
    def train(self, train_loader, val_loader, epochs: int = 100):
        """
        Full training loop
        
        Args:
            train_loader: Training DataLoader
            val_loader: Validation DataLoader
            epochs: Number of epochs to train
        """
        logger.info(f"Starting training for {epochs} epochs")
        
        for epoch in range(epochs):
            # Training
            train_loss = self.train_epoch(train_loader, epoch)
            
            # Validation
            val_loss, metrics = self.validate(val_loader)
            
            # Learning rate scheduling
            self.scheduler.step(val_loss)
            
            # Log progress
            logger.info(f"Epoch {epoch+1}/{epochs}: "
                       f"Train Loss = {train_loss:.4f}, "
                       f"Val Loss = {val_loss:.4f}, "
                       f"Accuracy = {metrics.get('accuracy', 0):.4f}")
            
            # Early stopping check
            if val_loss < self.best_loss:
                self.best_loss = val