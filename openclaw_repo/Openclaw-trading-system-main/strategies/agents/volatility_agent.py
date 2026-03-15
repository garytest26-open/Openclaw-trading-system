#!/usr/bin/env python3
"""
Volatility Agent for Swarm Trading AI
Variational Autoencoder for volatility regime detection and anomaly detection
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Dict, Tuple, Optional, List
import logging
from scipy import stats

logger = logging.getLogger(__name__)


class VariationalEncoder(nn.Module):
    """Variational encoder for volatility patterns"""
    
    def __init__(self, input_dim: int, hidden_dims: List[int], latent_dim: int):
        super().__init__()
        
        # Build encoder layers
        encoder_layers = []
        prev_dim = input_dim
        
        for hidden_dim in hidden_dims:
            encoder_layers.extend([
                nn.Linear(prev_dim, hidden_dim),
                nn.BatchNorm1d(hidden_dim),
                nn.LeakyReLU(0.1),
                nn.Dropout(0.2)
            ])
            prev_dim = hidden_dim
        
        self.encoder = nn.Sequential(*encoder_layers)
        
        # Latent space parameters
        self.fc_mu = nn.Linear(prev_dim, latent_dim)
        self.fc_logvar = nn.Linear(prev_dim, latent_dim)
        
        # Initialize weights
        self._initialize_weights()
    
    def _initialize_weights(self):
        for layer in self.encoder:
            if isinstance(layer, nn.Linear):
                nn.init.kaiming_normal_(layer.weight, nonlinearity='leaky_relu')
                nn.init.constant_(layer.bias, 0)
        
        nn.init.kaiming_normal_(self.fc_mu.weight, nonlinearity='linear')
        nn.init.constant_(self.fc_mu.bias, 0)
        
        nn.init.kaiming_normal_(self.fc_logvar.weight, nonlinearity='linear')
        nn.init.constant_(self.fc_logvar.bias, 0)
    
    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Encode input to latent distribution
        
        Args:
            x: Input tensor [batch_size, input_dim]
            
        Returns:
            Tuple of (mu, logvar)
        """
        hidden = self.encoder(x)
        mu = self.fc_mu(hidden)
        logvar = self.fc_logvar(hidden)
        
        return mu, logvar


class VariationalDecoder(nn.Module):
    """Variational decoder for reconstruction"""
    
    def __init__(self, latent_dim: int, hidden_dims: List[int], output_dim: int):
        super().__init__()
        
        # Reverse hidden dims for decoder
        hidden_dims_rev = hidden_dims[::-1]
        
        # Build decoder layers
        decoder_layers = []
        prev_dim = latent_dim
        
        for hidden_dim in hidden_dims_rev:
            decoder_layers.extend([
                nn.Linear(prev_dim, hidden_dim),
                nn.BatchNorm1d(hidden_dim),
                nn.LeakyReLU(0.1),
                nn.Dropout(0.2)
            ])
            prev_dim = hidden_dim
        
        # Output layer
        decoder_layers.append(nn.Linear(prev_dim, output_dim))
        
        self.decoder = nn.Sequential(*decoder_layers)
        
        self._initialize_weights()
    
    def _initialize_weights(self):
        for layer in self.decoder:
            if isinstance(layer, nn.Linear):
                nn.init.kaiming_normal_(layer.weight, nonlinearity='leaky_relu')
                nn.init.constant_(layer.bias, 0)
    
    def forward(self, z: torch.Tensor) -> torch.Tensor:
        """
        Decode latent vector to reconstruction
        
        Args:
            z: Latent vector [batch_size, latent_dim]
            
        Returns:
            Reconstructed tensor
        """
        return self.decoder(z)


class RegimeClassifier(nn.Module):
    """Classifier for volatility regimes"""
    
    def __init__(self, latent_dim: int, num_regimes: int = 4):
        super().__init__()
        
        self.classifier = nn.Sequential(
            nn.Linear(latent_dim, 64),
            nn.BatchNorm1d(64),
            nn.LeakyReLU(0.1),
            nn.Dropout(0.3),
            
            nn.Linear(64, 32),
            nn.BatchNorm1d(32),
            nn.LeakyReLU(0.1),
            
            nn.Linear(32, num_regimes)
        )
        
        self._initialize_weights()
    
    def _initialize_weights(self):
        for layer in self.classifier:
            if isinstance(layer, nn.Linear):
                nn.init.kaiming_normal_(layer.weight, nonlinearity='leaky_relu')
                nn.init.constant_(layer.bias, 0)
    
    def forward(self, z: torch.Tensor) -> torch.Tensor:
        """Classify regime from latent vector"""
        return self.classifier(z)


class AnomalyDetector(nn.Module):
    """Anomaly detection based on reconstruction error"""
    
    def __init__(self, input_dim: int):
        super().__init__()
        
        self.scorer = nn.Sequential(
            nn.Linear(input_dim * 2, 64),  # Input + reconstruction
            nn.LeakyReLU(0.1),
            nn.Linear(64, 32),
            nn.LeakyReLU(0.1),
            nn.Linear(32, 1),
            nn.Sigmoid()
        )
        
        self._initialize_weights()
    
    def _initialize_weights(self):
        for layer in self.scorer:
            if isinstance(layer, nn.Linear):
                nn.init.kaiming_normal_(layer.weight, nonlinearity='leaky_relu')
                nn.init.constant_(layer.bias, 0)
    
    def forward(self, x: torch.Tensor, x_recon: torch.Tensor) -> torch.Tensor:
        """Score anomaly likelihood"""
        combined = torch.cat([x, x_recon], dim=-1)
        return self.scorer(combined)


class VolatilityAgent(nn.Module):
    """
    Volatility regime detection agent using Variational Autoencoder
    Specialized for detecting volatility regimes, anomalies, and regime changes
    """
    
    def __init__(self, config: Dict):
        """
        Initialize volatility agent
        
        Args:
            config: Agent configuration dictionary
        """
        super().__init__()
        
        self.config = config
        self.input_dim = config.get('input_dim', 10)
        self.latent_dim = config.get('latent_dim', 16)
        self.hidden_dims = config.get('hidden_dims', [64, 32])
        self.beta = config.get('beta', 0.1)  # Beta-VAE parameter
        self.num_regimes = config.get('num_regimes', 4)
        
        # VAE components
        self.encoder = VariationalEncoder(self.input_dim, self.hidden_dims, self.latent_dim)
        self.decoder = VariationalDecoder(self.latent_dim, self.hidden_dims, self.input_dim)
        
        # Additional components
        self.regime_classifier = RegimeClassifier(self.latent_dim, self.num_regimes)
        self.anomaly_detector = AnomalyDetector(self.input_dim)
        
        # Volatility predictor
        self.volatility_predictor = nn.Sequential(
            nn.Linear(self.latent_dim, 32),
            nn.LeakyReLU(0.1),
            nn.Linear(32, 16),
            nn.LeakyReLU(0.1),
            nn.Linear(16, 1),
            nn.Softplus()  # Ensure positive output
        )
        
        # Regime transition detector
        self.transition_detector = nn.Sequential(
            nn.Linear(self.latent_dim * 2, 64),  # Current and previous latent
            nn.LeakyReLU(0.1),
            nn.Linear(64, 32),
            nn.LeakyReLU(0.1),
            nn.Linear(32, 1),
            nn.Sigmoid()
        )
        
        logger.info(f"Volatility Agent initialized: {self.input_dim} inputs, "
                   f"{self.latent_dim} latent dim, {self.num_regimes} regimes")
    
    def reparameterize(self, mu: torch.Tensor, logvar: torch.Tensor) -> torch.Tensor:
        """
        Reparameterization trick for VAE
        
        Args:
            mu: Mean of latent distribution
            logvar: Log variance of latent distribution
            
        Returns:
            Sampled latent vector
        """
        std = torch.exp(0.5 * logvar)
        eps = torch.randn_like(std)
        return mu + eps * std
    
    def encode(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Encode input to latent space
        
        Args:
            x: Input tensor
            
        Returns:
            Tuple of (z, mu, logvar)
        """
        mu, logvar = self.encoder(x)
        z = self.reparameterize(mu, logvar)
        return z, mu, logvar
    
    def decode(self, z: torch.Tensor) -> torch.Tensor:
        """Decode latent vector to reconstruction"""
        return self.decoder(z)
    
    def forward(self, x: torch.Tensor, prev_z: Optional[torch.Tensor] = None) -> Dict:
        """
        Forward pass through the network
        
        Args:
            x: Input tensor [batch_size, input_dim]
            prev_z: Previous latent vector for transition detection
            
        Returns:
            Dictionary with all outputs
        """
        # Encode
        z, mu, logvar = self.encode(x)
        
        # Decode
        x_recon = self.decode(z)
        
        # Regime classification
        regime_logits = self.regime_classifier(z)
        regime_probs = F.softmax(regime_logits, dim=-1)
        regime = torch.argmax(regime_probs, dim=-1)
        
        # Anomaly detection
        anomaly_score = self.anomaly_detector(x, x_recon)
        
        # Volatility prediction
        pred_volatility = self.volatility_predictor(z)
        
        # Regime transition detection
        transition_prob = torch.zeros(x.size(0), 1).to(x.device)
        if prev_z is not None and prev_z.size(0) == x.size(0):
            combined = torch.cat([prev_z, z], dim=-1)
            transition_prob = self.transition_detector(combined)
        
        # Calculate reconstruction error
        recon_error = F.mse_loss(x_recon, x, reduction='none').mean(dim=-1)
        
        # Calculate KL divergence
        kl_div = -0.5 * torch.sum(1 + logvar - mu.pow(2) - logvar.exp(), dim=-1)
        
        result = {
            'z': z,
            'mu': mu,
            'logvar': logvar,
            'x_recon': x_recon,
            'regime_logits': regime_logits,
            'regime_probs': regime_probs,
            'regime': regime,
            'anomaly_score': anomaly_score,
            'pred_volatility': pred_volatility,
            'transition_prob': transition_prob,
            'recon_error': recon_error,
            'kl_div': kl_div
        }
        
        return result
    
    def predict(self, x: np.ndarray, prev_z: Optional[np.ndarray] = None, 
                device: str = 'cpu') -> Dict:
        """
        Make prediction on numpy array
        
        Args:
            x: Input array [input_dim] or [batch_size, input_dim]
            prev_z: Previous latent vector
            device: Device to run on
            
        Returns:
            Prediction dictionary
        """
        self.eval()
        
        # Handle single sample
        if len(x.shape) == 1:
            x = x[np.newaxis, ...]
        
        # Convert to tensors
        x_tensor = torch.FloatTensor(x).to(device)
        prev_z_tensor = None
        if prev_z is not None:
            if len(prev_z.shape) == 1:
                prev_z = prev_z[np.newaxis, ...]
            prev_z_tensor = torch.FloatTensor(prev_z).to(device)
        
        with torch.no_grad():
            predictions = self.forward(x_tensor, prev_z_tensor)
        
        # Convert to numpy
        result = {}
        for key, value in predictions.items():
            if key != 'z' and key != 'mu' and key != 'logvar' and key != 'x_recon':
                result[key] = value.cpu().numpy()
            else:
                result[key] = value.cpu().numpy()
        
        return result
    
    def detect_regime_change(self, current_x: np.ndarray, previous_x: np.ndarray, 
                            device: str = 'cpu') -> Dict:
        """
        Detect regime change between two consecutive states
        
        Args:
            current_x: Current features
            previous_x: Previous features
            device: Device to run on
            
        Returns:
            Regime change detection results
        """
        # Encode both states
        current_tensor = torch.FloatTensor(current_x).to(device)
        previous_tensor = torch.FloatTensor(previous_x).to(device)
        
        with torch.no_grad():
            z_current, mu_current, _ = self.encode(current_tensor)
            z_previous, mu_previous, _ = self.encode(previous_tensor)
            
            # Calculate latent distance
            latent_distance = torch.norm(z_current - z_previous, dim=-1)
            
            # Get transition probability
            combined = torch.cat([z_previous, z_current], dim=-1)
            transition_prob = self.transition_detector(combined)
            
            # Get regime classifications
            current_regime = torch.argmax(F.softmax(self.regime_classifier(z_current), dim=-1), dim=-1)
            previous_regime = torch.argmax(F.softmax(self.regime_classifier(z_previous), dim=-1), dim=-1)
            
            # Check if regime changed
            regime_changed = (current_regime != previous_regime).float()
        
        return {
            'latent_distance': latent_distance.cpu().numpy(),
            'transition_probability': transition_prob.cpu().numpy(),
            'current_regime': current_regime.cpu().numpy(),
            'previous_regime': previous_regime.cpu().numpy(),
            'regime_changed': regime_changed.cpu().numpy()
        }
    
    def get_trading_signal(self, x: np.ndarray, historical_context: List[np.ndarray] = None,
                          device: str = 'cpu') -> Dict:
        """
        Generate trading signal based on volatility regime
        
        Args:
            x: Current features
            historical_context: List of previous features for context
            device: Device to run on
            
        Returns:
            Trading signal dictionary
        """
        if historical_context is not None and len(historical_context) > 0:
            # Use last historical state for transition detection
            prev_x = historical_context[-1]
            prev_predictions = self.predict(prev_x, device=device)
            prev_z = prev_predictions.get('z')
            
            # Detect regime change
            regime_change = self.detect_regime_change(x, prev_x, device)
            transition_prob = regime_change['transition_probability'][0][0]
            regime_changed = regime_change['regime_changed'][0]
        else:
            prev_z = None
            transition_prob = 0.5
            regime_changed = 0
        
        # Get current predictions
        predictions = self.predict(x, prev_z, device)
        
        # Extract values
        regime = predictions['regime'][0]
        regime_probs = predictions['regime_probs'][0]
        anomaly_score = predictions['anomaly_score'][0][0]
        pred_volatility = predictions['pred_volatility'][0][0]
        recon_error = predictions['recon_error'][0]
        
        # Define regime meanings (simplified)
        # 0: Low volatility, stable
        # 1: Rising volatility, accumulation
        # 2: High volatility, distribution
        # 3: Declining volatility, trend establishment
        
        # Determine signal based on regime
        if regime == 0:  # Low volatility, stable
            # Wait for breakout
            signal = 'HOLD'
            signal_strength = 0.0
            confidence = 0.7  # High confidence in stability
            
        elif regime == 1:  # Rising volatility, accumulation
            # Potential buying opportunity in accumulation
            if transition_prob > 0.7 and regime_changed:
                signal = 'BUY'
                signal_strength = min(1.0, transition_prob * pred_volatility * 10)
            else:
                signal = 'HOLD'
                signal_strength = 0.0
            confidence = 0.6
        
        elif regime == 2:  # High volatility, distribution
            # Caution advised, possible selling or shorting
            if anomaly_score > 0.8:  # High anomaly in high volatility
                signal = 'SELL'
                signal_strength = min(1.0, anomaly_score * pred_volatility * 8)
            else:
                signal = 'HOLD'
                signal_strength = 0.0
            confidence = 0.65
        
        elif regime == 3:  # Declining volatility, trend establishment
            # Could be trend continuation
            if transition_prob > 0.6 and not regime_changed:
                # Stable declining volatility suggests trend
                signal = 'BUY' if pred_volatility < 0.02 else 'HOLD'
                signal_strength = min(1.0, (1.0 - transition_prob) * 2)
            else:
                signal = 'HOLD'
                signal_strength = 0.0
            confidence = 0.55
        
        else:
            signal = 'HOLD'
            signal_strength = 0.0
            confidence = 0.5
        
        # Adjust for anomaly detection
        if anomaly_score > 0.9:
            # Extreme anomaly - reduce position size
            position_multiplier = 0.3
            stop_loss_wider = True
        elif anomaly_score > 0.7:
            position_multiplier = 0.6
            stop_loss_wider = True
        else:
            position_multiplier = 1.0
            stop_loss_wider = False
        
        # Calculate position sizing
        if signal != 'HOLD':
            base_size = min(1.0, signal_strength * confidence)
            
            # Adjust for volatility
            vol_adjustment = 1.0 / max(0.01, pred_volatility)  # Smaller positions in high volatility
            position_size = base_size * vol_adjustment * position_multiplier * 0.5
            
            # Calculate stop loss and take profit
            if stop_loss_wider:
                stop_loss_pct = 0.02 * (1.0 + pred_volatility * 10)
            else:
                stop_loss_pct = 0.01 * (1.0 + pred_volatility * 5)
            
            take_profit_pct = stop_loss_pct * (2.5 if regime == 1 else 2.0)  # Better R/R in accumulation
        else:
            position_size = stop_loss_pct = take_profit_pct = 0.0
        
        return {
            'signal': signal,
            'signal_strength': float(signal_strength),
            'confidence': float(confidence),
            'regime': int(regime),
            'regime_probs': regime_probs.tolist(),
            'anomaly_score': float(anomaly_score),
            'predicted_volatility': float(pred_volatility),
            'transition_probability': float(transition_prob),
            'regime_changed': bool(regime_changed),
            'reconstruction_error': float(recon_error),
            'stop_loss_pct': float(stop_loss_pct) if signal != 'HOLD' else 0.0,
            'take_profit_pct': float(take_profit_pct) if signal != 'HOLD' else 0.0,
            'position_size': float(position_size),
            'agent_type': 'volatility'
        }
    
    def compute_vae_loss(self, predictions: Dict, beta: float = None) -> torch.Tensor:
        """
        Compute VAE loss (reconstruction + KL divergence)
        
        Args:
            predictions: Dictionary from forward pass
            beta: Beta parameter for Beta-VAE
            
        Returns:
            VAE loss tensor
        """
        if beta is None:
            beta = self.beta
        
        recon_loss = predictions['recon_error'].mean()
        kl_loss = predictions['kl_div'].mean()
        
        return recon_loss + beta * kl_loss
    
    def compute_regime_loss(self, predictions: Dict, targets: Dict) -> torch.Tensor:
        """
        Compute regime classification loss
        
        Args:
            predictions: Dictionary from forward pass
            targets: Dictionary with regime targets
            
        Returns:
            Classification loss tensor
        """
        regime_targets = targets.get('regime')
        if regime_targets is not None:
            return F.cross_entropy(predictions['regime_logits'], regime_targets.long())
        return torch.tensor(0.0).to(predictions['regime_logits'].device)
    
    def compute_anomaly_loss(self, predictions: Dict, targets: Dict) -> torch.Tensor:
        """
        Compute anomaly detection loss
        
        Args:
            predictions: Dictionary from forward pass
            targets: Dictionary with anomaly labels
            
        Returns:
            Anomaly loss tensor
        """
        anomaly_targets = targets.get('anomaly')
        if anomaly_targets is not None:
            return F.binary_cross_entropy(predictions['anomaly_score'], anomaly_targets)
        return torch.tensor(0.0).to(predictions['anomaly_score'].device)
    
    def compute_total_loss(self, predictions: Dict, targets: Dict) -> torch.Tensor:
        """
        Compute total multi-task loss
        
        Args:
            predictions: Dictionary from forward pass
            targets: Dictionary with all targets
            
        Returns:
            Combined loss tensor
        """
        vae_loss = self.compute_vae_loss(predictions)
        regime_loss = self.compute_regime_loss(predictions, targets)
        anomaly_loss = self.compute_anomaly_loss(predictions, targets)
        
        # Combined with weights
        total_loss = (
            vae_loss * 1.0 +
            regime_loss * 0.8 +
            anomaly_loss * 0.5
        )
        
        return total_loss


class VolatilityAgentTrainer:
    """Trainer for the volatility agent"""
    
    def __init__(self, agent: VolatilityAgent, config: Dict):
        """
        Initialize trainer
        
        Args:
            agent: VolatilityAgent instance
            config: Training configuration
        """
        self.agent = agent
        self.config = config
        
        # Optimizer
        self.optimizer = torch.optim.AdamW(
            agent.parameters(),
            lr=config.get('learning_rate', 0.0005),
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
        
        logger.info("Volatility Agent Trainer initialized")
    
    def create_volatility_labels(self, prices: np.ndarray, window: int = 20) -> Dict:
        """
        Create labels for volatility regime training
        
        Args:
            prices: Price array
            window: Window for volatility calculation
            
        Returns:
            Dictionary of labels
        """
        returns = np.diff(prices) / prices[:-1]
        
        # Calculate rolling volatility
        volatility = np.zeros_like(prices)
        for i in range(len(prices)):
            start = max(0, i - window + 1)
            vol = np.std(returns[start:i]) if i - start > 1 else 0.01
            volatility[i] = vol
        
        # Create regime labels based on volatility
        regime = np.zeros(len(prices))
        
        # Percentile-based regime classification
        vol_25 = np.percentile(volatility, 25)
        vol_50 = np.percentile(volatility, 50)
        vol_75 = np.percentile(volatility, 75)
        
        for i in range(len(prices)):
            if volatility[i] < vol_25:
                regime[i] = 0  # Low volatility
            elif volatility[i] < vol_50:
                regime[i] = 3  # Declining/stable low
            elif volatility[i] < vol_75:
                regime[i] = 1  # Rising volatility
            else:
                regime[i] = 2  # High volatility
        
        # Create anomaly labels (spikes in volatility)
        anomaly = np.zeros(len(prices))
        vol_mean = np.mean(volatility)
        vol_std = np.std(volatility)
        
        for i in range(len(prices)):
            if volatility[i] > vol_mean + 2 * vol_std:
                anomaly[i] = 1  # Anomaly
            elif volatility[i] > vol_mean + vol_std:
                anomaly[i] = 0.5  # Mild anomaly
        
        return {
            'regime': regime,
            'anomaly': anomaly,
            'volatility': volatility
        }
    
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
            labels = self.create_volatility_labels(price_batch.numpy())
            
            # Convert to tensors
            regime_tensor = torch.FloatTensor(labels['regime']).to(self.device)
            anomaly_tensor = torch.FloatTensor(labels['anomaly']).to(self.device)
            
            # Prepare targets
            targets = {
                'regime': regime_tensor,
                'anomaly': anomaly_tensor
            }
            
            # Forward pass (without previous z for training)
            self.optimizer.zero_grad()
            predictions = self.agent(x_batch)
            
            # Compute loss
            loss = self.agent.compute_total_loss(predictions, targets)
            
            # Backward pass
            loss.backward()
            
            # Gradient clipping
            torch.nn.utils.clip_grad_norm_(self.agent.parameters(), max_norm=1.0)
            
            # Optimizer step
            self.optimizer.step()
            
            total_loss += loss.item()
            n_batches += 1
            
            if batch_idx % 100 == 0:
                recon_loss = self.agent.compute_vae_loss(predictions).item()
                regime_loss = self.agent.compute_regime_loss(predictions, targets).item()
                
                logger.info(f"Epoch {epoch}, Batch {batch_idx}: "
                           f"Total Loss = {loss.item():.4f}, "
                           f"Recon = {recon_loss:.4f}, "
                           f"Regime = {regime_loss:.4f}")
        
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
        
        all_regimes = []
        all_preds = []
        
        with torch.no_grad():
            for x_batch, price_batch in val_loader:
                x_batch = x_batch.to(self.device)
                
                # Create labels
                labels = self.create_volatility_labels(price_batch.numpy())
                
                targets = {
                    'regime': torch.FloatTensor(labels['regime']).to(self.device),
                    'anomaly': torch.FloatTensor(labels['anomaly']).to(self.device)
                }
                
                predictions = self.agent(x_batch)
                loss = self.agent.compute_total_loss(predictions, targets)
                
                total_loss += loss.item()
                n_batches += 1
                
                # Collect predictions for metrics
                regime_pred = torch.argmax(predictions['regime_probs'], dim=-1)
                all_preds.append(regime_pred.cpu().numpy())
                all_regimes.append(labels['regime'])
        
        avg_loss = total_loss / n_batches if n_batches > 0 else 0
        
        # Calculate metrics
        if len(all_preds) > 0:
            preds_np = np.concatenate(all_preds)
            regimes_np = np.concatenate(all_regimes)
            
            accuracy = np.mean(preds_np == regimes_np)
            
            # Calculate per-regime accuracy
            regime_accuracies = {}
            for reg in range(self.agent.num_regimes):
                mask = regimes_np == reg
                if np.sum(mask) > 0:
                    regime_accuracies[f'regime_{reg}_acc'] = np.mean(preds_np[mask] == reg)
            
            metrics = {
                'loss': avg_loss,
                'accuracy': accuracy,
                **regime_accuracies,
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
                }, f'volatility_agent_best.pth')
                
                logger.info(f"New best model saved with loss {val_loss:.4f}")
            else:
                self.patience_counter += 1
                if self.patience_counter >= self.patience:
                    logger.info(f"Early stopping triggered at epoch {epoch+1}")
                    break
        
        logger.info("Training completed")