#!/usr/bin/env python3
"""
Reversal Agent for Swarm Trading AI
CNN-based agent for detecting market reversals and overbought/oversold conditions
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class ReversalAgent(nn.Module):
    """
    Reversal detection agent using 1D CNN
    Specialized for identifying overbought/oversold conditions and reversal points
    """
    
    def __init__(self, config: Dict):
        """
        Initialize reversal agent
        
        Args:
            config: Agent configuration dictionary
        """
        super().__init__()
        
        self.config = config
        self.input_channels = config.get('input_channels', 11)
        self.sequence_length = config.get('sequence_length', 20)
        
        # CNN layers for pattern detection
        self.conv_layers = nn.Sequential(
            # First conv block
            nn.Conv1d(self.input_channels, 32, kernel_size=3, padding=1),
            nn.BatchNorm1d(32),
            nn.LeakyReLU(0.1),
            nn.MaxPool1d(2),
            
            # Second conv block
            nn.Conv1d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm1d(64),
            nn.LeakyReLU(0.1),
            nn.MaxPool1d(2),
            
            # Third conv block
            nn.Conv1d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm1d(128),
            nn.LeakyReLU(0.1),
            nn.AdaptiveAvgPool1d(4)
        )
        
        # Calculate flattened size
        with torch.no_grad():
            dummy_input = torch.randn(1, self.input_channels, self.sequence_length)
            conv_out = self.conv_layers(dummy_input)
            self.flattened_size = conv_out.numel()
        
        # Fully connected layers
        self.fc_layers = nn.Sequential(
            nn.Linear(self.flattened_size, 256),
            nn.BatchNorm1d(256),
            nn.LeakyReLU(0.1),
            nn.Dropout(0.3),
            
            nn.Linear(256, 128),
            nn.BatchNorm1d(128),
            nn.LeakyReLU(0.1),
            nn.Dropout(0.3),
            
            nn.Linear(128, 64),
            nn.BatchNorm1d(64),
            nn.LeakyReLU(0.1)
        )
        
        # Output heads
        self.reversal_head = nn.Sequential(
            nn.Linear(64, 32),
            nn.LeakyReLU(0.1),
            nn.Linear(32, 3)  # Overbought, Oversold, Neutral
        )
        
        self.confidence_head = nn.Sequential(
            nn.Linear(64, 16),
            nn.LeakyReLU(0.1),
            nn.Linear(16, 1),
            nn.Sigmoid()
        )
        
        self.timing_head = nn.Sequential(
            nn.Linear(64, 32),
            nn.LeakyReLU(0.1),
            nn.Linear(32, 1),
            nn.Sigmoid()  # Probability of imminent reversal
        )
        
        self.magnitude_head = nn.Sequential(
            nn.Linear(64, 32),
            nn.LeakyReLU(0.1),
            nn.Linear(32, 1)  # Expected reversal magnitude
        )
        
        # Initialize weights
        self._initialize_weights()
        
        logger.info(f"Reversal Agent initialized: {self.input_channels} channels, "
                   f"sequence length {self.sequence_length}")
    
    def _initialize_weights(self):
        """Initialize network weights"""
        for name, param in self.named_parameters():
            if 'weight' in name:
                if 'conv' in name:
                    nn.init.kaiming_normal_(param, nonlinearity='leaky_relu')
                else:
                    nn.init.kaiming_normal_(param, nonlinearity='leaky_relu')
            elif 'bias' in name:
                nn.init.constant_(param, 0)
    
    def forward(self, x: torch.Tensor) -> Dict:
        """
        Forward pass through the network
        
        Args:
            x: Input tensor [batch_size, sequence_length, input_channels]
            
        Returns:
            Dictionary with predictions
        """
        # Reshape for CNN: [batch_size, channels, sequence_length]
        x = x.transpose(1, 2)
        
        # CNN layers
        conv_features = self.conv_layers(x)
        
        # Flatten
        batch_size = conv_features.size(0)
        flattened = conv_features.view(batch_size, -1)
        
        # Fully connected layers
        fc_features = self.fc_layers(flattened)
        
        # Get predictions from all heads
        reversal_logits = self.reversal_head(fc_features)
        reversal_probs = F.softmax(reversal_logits, dim=-1)
        
        confidence = self.confidence_head(fc_features)
        timing = self.timing_head(fc_features)
        magnitude = self.magnitude_head(fc_features)
        
        # Determine reversal state
        reversal_state = torch.argmax(reversal_probs, dim=-1)
        
        # Calculate reversal strength
        oversold_strength = reversal_probs[:, 0]  # Oversold probability
        overbought_strength = reversal_probs[:, 1]  # Overbought probability
        
        result = {
            'reversal_probs': reversal_probs,
            'reversal_state': reversal_state,
            'oversold_strength': oversold_strength,
            'overbought_strength': overbought_strength,
            'confidence': confidence,
            'timing_probability': timing,
            'expected_magnitude': magnitude,
            'conv_features': conv_features
        }
        
        return result
    
    def predict(self, x: np.ndarray, device: str = 'cpu') -> Dict:
        """
        Make prediction on numpy array
        
        Args:
            x: Input array [sequence_length, input_channels] or [batch_size, sequence_length, input_channels]
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
            'reversal_probs': predictions['reversal_probs'].cpu().numpy(),
            'reversal_state': predictions['reversal_state'].cpu().numpy(),
            'oversold_strength': predictions['oversold_strength'].cpu().numpy(),
            'overbought_strength': predictions['overbought_strength'].cpu().numpy(),
            'confidence': predictions['confidence'].cpu().numpy(),
            'timing_probability': predictions['timing_probability'].cpu().numpy(),
            'expected_magnitude': predictions['expected_magnitude'].cpu().numpy()
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
        reversal_state = predictions['reversal_state'][0]
        oversold_strength = predictions['oversold_strength'][0]
        overbought_strength = predictions['overbought_strength'][0]
        confidence = predictions['confidence'][0][0]
        timing_prob = predictions['timing_probability'][0][0]
        expected_mag = predictions['expected_magnitude'][0][0]
        
        # Determine signal based on reversal state and timing
        if reversal_state == 0 and oversold_strength > 0.7 and timing_prob > 0.6 and confidence > 0.65:
            # Oversold condition with high timing probability
            signal = 'BUY'
            signal_strength = float(oversold_strength * timing_prob * confidence)
            
        elif reversal_state == 1 and overbought_strength > 0.7 and timing_prob > 0.6 and confidence > 0.65:
            # Overbought condition with high timing probability
            signal = 'SELL'
            signal_strength = float(overbought_strength * timing_prob * confidence)
            
        else:
            signal = 'HOLD'
            signal_strength = 0.0
        
        # Calculate position sizing and risk parameters
        if signal != 'HOLD':
            # More aggressive for strong reversals
            base_size = min(1.0, signal_strength)
            
            # Adjust for expected magnitude
            magnitude_boost = min(2.0, 1.0 + expected_mag * 5)  # Scale magnitude
            position_size = base_size * magnitude_boost * 0.5  # Conservative
            
            # Tight stop loss for reversal trades
            stop_loss_pct = 0.005 * (2.0 - signal_strength)  # 0.5% to 1%
            take_profit_pct = stop_loss_pct * 3.0  # 3:1 risk-reward for reversals
            
            # Entry timing adjustment
            if timing_prob > 0.8:
                # Very high timing confidence - can be more aggressive
                take_profit_pct *= 1.2
        else:
            position_size = stop_loss_pct = take_profit_pct = 0.0
        
        return {
            'signal': signal,
            'signal_strength': signal_strength,
            'confidence': float(confidence),
            'reversal_state': int(reversal_state),
            'oversold_strength': float(oversold_strength),
            'overbought_strength': float(overbought_strength),
            'timing_probability': float(timing_prob),
            'expected_magnitude': float(expected_mag),
            'stop_loss_pct': float(stop_loss_pct),
            'take_profit_pct': float(take_profit_pct),
            'position_size': float(position_size),
            'agent_type': 'reversal'
        }
    
    def detect_reversal_patterns(self, x: np.ndarray, device: str = 'cpu') -> Dict:
        """
        Detect specific reversal patterns
        
        Args:
            x: Input features
            device: Device to run on
            
        Returns:
            Pattern detection results
        """
        predictions = self.predict(x, device)
        
        # Analyze convolution features for patterns
        conv_features = predictions.get('conv_features')
        if conv_features is not None:
            # Calculate feature activations
            feature_activations = np.mean(conv_features, axis=(0, 2))  # Average over batch and time
            
            # Pattern scores (simplified)
            pattern_scores = {
                'double_bottom': float(feature_activations[0] if len(feature_activations) > 0 else 0),
                'double_top': float(feature_activations[1] if len(feature_activations) > 1 else 0),
                'head_shoulders': float(feature_activations[2] if len(feature_activations) > 2 else 0),
                'inverse_head_shoulders': float(feature_activations[3] if len(feature_activations) > 3 else 0)
            }
        else:
            pattern_scores = {}
        
        return {
            'pattern_scores': pattern_scores,
            **{k: v for k, v in predictions.items() if k != 'conv_features'}
        }
    
    def compute_loss(self, predictions: Dict, targets: Dict) -> torch.Tensor:
        """
        Compute multi-task loss
        
        Args:
            predictions: Dictionary of predictions
            targets: Dictionary of targets
            
        Returns:
            Combined loss tensor
        """
        # Reversal classification loss
        reversal_targets = targets.get('reversal_state')
        if reversal_targets is not None:
            cls_loss = F.cross_entropy(predictions['reversal_logits'], reversal_targets.long())
        else:
            cls_loss = torch.tensor(0.0).to(predictions['reversal_probs'].device)
        
        # Timing regression loss
        timing_targets = targets.get('timing')
        if timing_targets is not None:
            timing_loss = F.mse_loss(predictions['timing_probability'], timing_targets)
        else:
            timing_loss = torch.tensor(0.0).to(predictions['timing_probability'].device)
        
        # Magnitude regression loss
        magnitude_targets = targets.get('magnitude')
        if magnitude_targets is not None:
            magnitude_loss = F.mse_loss(predictions['expected_magnitude'], magnitude_targets)
        else:
            magnitude_loss = torch.tensor(0.0).to(predictions['expected_magnitude'].device)
        
        # Confidence regularization
        confidence = predictions['confidence']
        conf_reg = torch.mean((confidence - 0.5) ** 2)
        
        # Feature sparsity regularization (encourage selective pattern detection)
        conv_features = predictions.get('conv_features')
        if conv_features is not None:
            # L1 regularization on features
            feature_reg = torch.mean(torch.abs(conv_features))
        else:
            feature_reg = torch.tensor(0.0).to(confidence.device)
        
        # Combine losses
        total_loss = (
            cls_loss * 1.0 +
            timing_loss * 0.8 +
            magnitude_loss * 0.5 +
            conf_reg * 0.1 +
            feature_reg * 0.05
        )
        
        return total_loss


class ReversalAgentTrainer:
    """Trainer for the reversal agent"""
    
    def __init__(self, agent: ReversalAgent, config: Dict):
        """
        Initialize trainer
        
        Args:
            agent: ReversalAgent instance
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
            patience=8,
            verbose=True
        )
        
        # Early stopping
        self.best_loss = float('inf')
        self.patience_counter = 0
        self.patience = config.get('early_stopping_patience', 15)
        
        self.device = config.get('device', 'cpu')
        self.agent.to(self.device)
        
        logger.info("Reversal Agent Trainer initialized")
    
    def create_reversal_labels(self, prices: np.ndarray, lookforward: int = 10) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Create labels for reversal detection
        
        Args:
            prices: Price array
            lookforward: Lookforward window for labeling
            
        Returns:
            Tuple of (reversal_state, timing, magnitude)
        """
        returns = np.diff(prices) / prices[:-1]
        
        reversal_state = np.zeros(len(prices) - lookforward)
        timing = np.zeros(len(prices) - lookforward)
        magnitude = np.zeros(len(prices) - lookforward)
        
        for i in range(len(prices) - lookforward):
            future_max = np.max(prices[i+1:i+lookforward+1])
            future_min = np.min(prices[i+1:i+lookforward+1])
            current = prices[i]
            
            # Calculate potential reversal
            upside_potential = (future_max - current) / current
            downside_potential = (current - future_min) / current
            
            # Determine if oversold or overbought
            rsi_like = 100 * (1 - 1/(1 + np.mean(returns[max(0, i-14):i+1] > 0)))
            
            if rsi_like < 30 and upside_potential > 0.02:
                # Oversold condition
                reversal_state[i] = 0  # Oversold
                timing[i] = min(1.0, upside_potential / 0.05)  # Normalized timing
                magnitude[i] = upside_potential
            elif rsi_like > 70 and downside_potential > 0.02:
                # Overbought condition
                reversal_state[i] = 1  # Overbought
                timing[i] = min(1.0, downside_potential / 0.05)
                magnitude[i] = downside_potential
            else:
                # Neutral
                reversal_state[i] = 2  # Neutral
                timing[i] = 0
                magnitude[i] = 0
        
        return reversal_state, timing, magnitude
    
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
        
        for batch_idx, (x_batch, price_batch) in enumerate(train_loader):
            x_batch = x_batch.to(self.device)
            
            # Create labels from prices
            reversal_state, timing, magnitude = self.create_reversal_labels(
                price_batch.numpy(), lookforward=10
            )
            
            # Convert to tensors
            reversal_tensor = torch.FloatTensor(reversal_state).to(self.device)
            timing_tensor = torch.FloatTensor(timing).to(self.device)
            magnitude_tensor = torch.FloatTensor(magnitude).to(self.device)
            
            # Prepare targets
            targets = {
                'reversal_state': reversal_tensor,
                'timing': timing_tensor,
                'magnitude': magnitude_tensor
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
        all_states = []
        
        with torch.no_grad():
            for x_batch, price_batch in val_loader:
                x_batch = x_batch.to(self.device)
                
                # Create labels
                reversal_state, timing, magnitude = self.create_reversal_labels(
                    price_batch.numpy(), lookforward=10
                )
                
                targets = {
                    'reversal_state': torch.FloatTensor(reversal_state).to(self.device),
                    'timing': torch.FloatTensor(timing).to(self.device),
                    'magnitude': torch.FloatTensor(magnitude).to(self.device)
                }
                
                predictions = self.agent(x_batch)
                loss = self.agent.compute_loss(predictions, targets)
                
                total_loss += loss.item()
                n_batches += 1
                
                # Collect predictions for metrics
                state_pred = torch.argmax(predictions['reversal_probs'], dim=-1)
                all_predictions.append(state_pred.cpu().numpy())
                all_states.append(reversal_state)
        
        avg_loss = total_loss / n_batches if n_batches > 0 else 0
        
        # Calculate metrics
        if len(all_predictions) > 0:
            preds_np = np.concatenate(all_predictions)
            states_np = np.concatenate(all_states)
            
            accuracy = np.mean(preds_np == states_np)
            
            # Calculate precision/recall for oversold/overbought
            oversold_precision = np.mean((preds_np == 0)[states_np == 0]) if np.sum(states_np == 0) > 0 else 0
            overbought_precision = np.mean((preds_np == 1)[states_np == 1]) if np.sum(states_np == 1) > 0 else 0
            
            metrics = {
                'loss': avg_loss,
                'accuracy': accuracy,
                'oversold_precision': oversold_precision,
                'overbought_precision': overbought_precision,
                'n_samples': len(preds_np)
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
                self.best_loss = val_loss
                self.patience_counter = 0
                
                # Save best model
                torch.save({
                    'epoch': epoch,
                    'model_state_dict': self.agent.state_dict(),
                    'optimizer_state_dict': self.optimizer.state_dict(),
                    'loss': val_loss,
                    'metrics': metrics
                }, f'reversal_agent_best.pth')
                
                logger.info(f"New best model saved with loss {val_loss:.4f}")
            else:
                self.patience_counter += 1
                if self.patience_counter >= self.patience:
                    logger.info(f"Early stopping triggered at epoch {epoch+1}")
                    break
        
        logger.info("Training completed")