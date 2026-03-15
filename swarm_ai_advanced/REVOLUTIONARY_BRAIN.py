"""
🧠 REVOLUTIONARY_BRAIN.py - EL CEREBRO QUE REVOLUCIONARÁ EL TRADING
Sistema de IA de nivel PhD para trading algorítmico revolucionario
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

print("🧠 INICIALIZANDO CEREBRO REVOLUCIONARIO...")
print("=" * 60)

class QuantumAttention(nn.Module):
    """
    Mecanismo de atención inspirado en mecánica cuántica para capturar relaciones no-lineales complejas
    """
    def __init__(self, hidden_dim: int = 256, num_heads: int = 8):
        super().__init__()
        self.hidden_dim = hidden_dim
        self.num_heads = num_heads
        self.head_dim = hidden_dim // num_heads
        
        # Quantum-inspired projections
        self.q_proj = nn.Linear(hidden_dim, hidden_dim)
        self.k_proj = nn.Linear(hidden_dim, hidden_dim)
        self.v_proj = nn.Linear(hidden_dim, hidden_dim)
        
        # Phase modulation (quantum phase)
        self.phase_encoder = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, num_heads)
        )
        
        # Entanglement layer (quantum entanglement simulation)
        self.entanglement = nn.MultiheadAttention(hidden_dim, num_heads, batch_first=True)
        
        # Output projection with quantum superposition
        self.output_proj = nn.Linear(hidden_dim, hidden_dim)
        
    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        x: (batch_size, seq_len, hidden_dim)
        """
        batch_size, seq_len, _ = x.shape
        
        # Standard attention projections
        Q = self.q_proj(x)
        K = self.k_proj(x)
        V = self.v_proj(x)
        
        # Quantum phase modulation
        phase = self.phase_encoder(x.mean(dim=1))  # (batch_size, num_heads)
        phase = torch.cos(phase).unsqueeze(1).unsqueeze(2)  # (batch_size, 1, 1, num_heads)
        
        # Reshape for multi-head attention
        Q = Q.view(batch_size, seq_len, self.num_heads, self.head_dim).transpose(1, 2)
        K = K.view(batch_size, seq_len, self.num_heads, self.head_dim).transpose(1, 2)
        V = V.view(batch_size, seq_len, self.num_heads, self.head_dim).transpose(1, 2)
        
        # Apply quantum phase modulation
        Q = Q * phase
        K = K * phase
        
        # Scaled dot-product attention with quantum modulation
        scores = torch.matmul(Q, K.transpose(-2, -1)) / np.sqrt(self.head_dim)
        attn_weights = F.softmax(scores, dim=-1)
        
        # Apply attention to values
        context = torch.matmul(attn_weights, V)
        
        # Reshape back
        context = context.transpose(1, 2).contiguous().view(batch_size, seq_len, self.hidden_dim)
        
        # Quantum entanglement layer
        entangled, _ = self.entanglement(context, context, context)
        
        # Final output with superposition
        output = self.output_proj(entangled + context)  # Superposition principle
        
        return output, attn_weights

class MarketOracle(nn.Module):
    """
    Oráculo de mercado que predice movimientos con incertidumbre cuantificada
    """
    def __init__(self, input_dim: int = 50, hidden_dim: int = 512):
        super().__init__()
        
        # Feature extraction with multiple resolutions
        self.feature_extractors = nn.ModuleList([
            nn.Sequential(
                nn.Linear(input_dim, hidden_dim),
                nn.ReLU(),
                nn.Dropout(0.1),
                nn.Linear(hidden_dim, hidden_dim // 2)
            ) for _ in range(3)  # Multiple perspectives
        ])
        
        # Temporal pattern recognition
        self.temporal_encoder = nn.LSTM(
            input_size=hidden_dim // 2,
            hidden_size=hidden_dim,
            num_layers=2,
            batch_first=True,
            bidirectional=True
        )
        
        # Quantum attention for market dynamics
        self.market_attention = QuantumAttention(hidden_dim * 2, num_heads=8)
        
        # Bayesian output layers (uncertainty quantification)
        self.mean_head = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 3)  # Buy, Hold, Sell probabilities
        )
        
        self.uncertainty_head = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 3),  # Uncertainty for each action
            nn.Softplus()  # Ensure positive uncertainty
        )
        
        # Market regime classifier
        self.regime_classifier = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 4),  # Bull, Bear, Volatile, Sideways
            nn.Softmax(dim=-1)
        )
        
    def forward(self, market_features: Dict[str, torch.Tensor]) -> Dict[str, torch.Tensor]:
        """
        market_features: dict with 'short', 'medium', 'long' term features
        """
        # Extract features from multiple perspectives
        perspectives = []
        for i, extractor in enumerate(self.feature_extractors):
            # Use different feature subsets for each perspective
            feat_subset = market_features[list(market_features.keys())[i % len(market_features)]]
            perspective = extractor(feat_subset)
            perspectives.append(perspective)
        
        # Combine perspectives
        combined = torch.stack(perspectives, dim=1)  # (batch_size, num_perspectives, features)
        
        # Temporal encoding
        temporal_out, (hidden, cell) = self.temporal_encoder(combined)
        
        # Market attention
        attended, attention_weights = self.market_attention(temporal_out)
        
        # Use last timestep for prediction
        context = attended[:, -1, :]
        
        # Bayesian predictions with uncertainty
        mean_pred = self.mean_head(context)
        uncertainty = self.uncertainty_head(context)
        
        # Market regime
        regime_probs = self.regime_classifier(context)
        
        # Sample from distribution (Bayesian inference)
        std = uncertainty
        eps = torch.randn_like(std)
        sampled_pred = mean_pred + eps * std
        
        return {
            'mean_predictions': F.softmax(mean_pred, dim=-1),
            'sampled_predictions': F.softmax(sampled_pred, dim=-1),
            'uncertainty': uncertainty,
            'regime_probs': regime_probs,
            'attention_weights': attention_weights,
            'market_context': context
        }

class ProfitMaximizer(nn.Module):
    """
    Agente de maximización de profit con reinforcement learning profundo
    """
    def __init__(self, state_dim: int = 256, action_dim: int = 3):
        super().__init__()
        
        # Policy network (actor)
        self.policy_net = nn.Sequential(
            nn.Linear(state_dim, 512),
            nn.ReLU(),
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, action_dim),
            nn.Softmax(dim=-1)
        )
        
        # Value network (critic)
        self.value_net = nn.Sequential(
            nn.Linear(state_dim, 512),
            nn.ReLU(),
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, 1)
        )
        
        # Risk-aware adjustment
        self.risk_adjuster = nn.Sequential(
            nn.Linear(state_dim, 128),
            nn.ReLU(),
            nn.Linear(128, action_dim),
            nn.Sigmoid()
        )
        
    def forward(self, state: torch.Tensor, risk_tolerance: float = 0.5) -> Dict[str, torch.Tensor]:
        """
        state: market context from MarketOracle
        risk_tolerance: 0.0 (conservative) to 1.0 (aggressive)
        """
        # Base policy
        action_probs = self.policy_net(state)
        
        # State value
        state_value = self.value_net(state)
        
        # Risk adjustment
        risk_factor = self.risk_adjuster(state)
        adjusted_probs = action_probs * (1 + risk_tolerance * (risk_factor - 0.5))
        adjusted_probs = adjusted_probs / adjusted_probs.sum(dim=-1, keepdim=True)
        
        # Sample action
        action_dist = torch.distributions.Categorical(adjusted_probs)
        action = action_dist.sample()
        log_prob = action_dist.log_prob(action)
        
        return {
            'action': action,
            'action_probs': adjusted_probs,
            'log_prob': log_prob,
            'state_value': state_value,
            'entropy': action_dist.entropy()
        }

class RevolutionaryBrain(nn.Module):
    """
    🧠 CEREBRO REVOLUCIONARIO - Sistema unificado de IA para trading
    Combina: Oráculo de Mercado + Maximizador de Profit + Gestión de Riesgo
    """
    def __init__(self, config: Dict):
        super().__init__()
        
        self.config = config
        
        # Core components
        self.market_oracle = MarketOracle(
            input_dim=config.get('feature_dim', 50),
            hidden_dim=config.get('hidden_dim', 512)
        )
        
        self.profit_maximizer = ProfitMaximizer(
            state_dim=config.get('context_dim', 1024),
            action_dim=3  # Buy, Hold, Sell
        )
        
        # Risk management system
        self.risk_manager = nn.Sequential(
            nn.Linear(config.get('context_dim', 1024), 256),
            nn.ReLU(),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, 4),  # Position size, stop loss, take profit, hedge ratio
            nn.Sigmoid()
        )
        
        # Meta-controller for strategy adaptation
        self.meta_controller = nn.Sequential(
            nn.Linear(config.get('context_dim', 1024), 512),
            nn.ReLU(),
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Linear(256, 3),  # Aggressiveness, patience, adaptability
            nn.Sigmoid()
        )
        
        # Fusion layer for final decision
        self.decision_fusion = QuantumAttention(
            hidden_dim=config.get('context_dim', 1024),
            num_heads=8
        )
        
        print(f"🧠 RevolutionaryBrain inicializado")
        print(f"   Parámetros totales: {sum(p.numel() for p in self.parameters()):,}")
        print(f"   Componentes: MarketOracle, ProfitMaximizer, RiskManager, MetaController")
        
    def forward(self, market_data: Dict[str, torch.Tensor], 
                risk_tolerance: float = 0.5) -> Dict[str, torch.Tensor]:
        """
        Procesamiento completo del cerebro revolucionario
        """
        # 1. Market analysis with uncertainty
        oracle_output = self.market_oracle(market_data)
        
        # 2. Profit maximization with RL
        profit_output = self.profit_maximizer(
            oracle_output['market_context'],
            risk_tolerance
        )
        
        # 3. Risk management
        risk_params = self.risk_manager(oracle_output['market_context'])
        
        # 4. Meta-control for strategy adaptation
        meta_params = self.meta_controller(oracle_output['market_context'])
        
        # 5. Fuse all information for final decision
        decision_components = torch.stack([
            oracle_output['market_context'],
            profit_output['state_value'],
            risk_params.mean(dim=-1, keepdim=True).expand(-1, oracle_output['market_context'].size(-1))
        ], dim=1)
        
        fused_decision, fusion_weights = self.decision_fusion(decision_components)
        
        # 6. Generate final trading signals
        final_context = fused_decision.mean(dim=1)
        
        # Final decision head
        final_decision = nn.Sequential(
            nn.Linear(final_context.size(-1), 128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 3),  # Final Buy/Hold/Sell probabilities
            nn.Softmax(dim=-1)
        )(final_context)
        
        # Confidence estimation
        confidence = torch.sqrt(1.0 / (oracle_output['uncertainty'].mean(dim=-1) + 1e-8))
        confidence = torch.clamp(confidence, 0.0, 1.0)
        
        return {
            # Core predictions
            'final_decision': final_decision,
            'confidence': confidence,
            
            # Component outputs
            'oracle_predictions': oracle_output['mean_predictions'],
            'oracle_uncertainty': oracle_output['uncertainty'],
            'rl_action': profit_output['action'],
            'rl_action_probs': profit_output['action_probs'],
            
            # Risk parameters
            'position_size': risk_params[:, 0],      # 0-1
            'stop_loss': risk_params[:, 1] * 0.1,    # 0-10%
            'take_profit': risk_params[:, 2] * 0.2,  # 0-20%
            'hedge_ratio': risk_params[:, 3],        # 0-1
            
            # Meta parameters
            'aggressiveness': meta_params[:, 0],
            'patience': meta_params[:, 1],
            'adaptability': meta_params[:, 2],
            
            # Market analysis
            'market_regime': torch.argmax(oracle_output['regime_probs'], dim=-1),
            'regime_probs': oracle_output['regime_probs'],
            
            # Attention information
            'attention_weights': oracle_output['attention_weights'],
            'fusion_weights': fusion_weights,
            
            # Context for training
            'market_context': oracle_output['market_context'],
            'final_context': final_context
        }
    
    def predict_single(self, market_features: Dict, 
                      risk_tolerance: float = 0.5) -> Dict[str, np.ndarray]:
        """
        Predicción para un solo timestep (inferencia)
        """
        self.eval()
        
        # Convert to tensors
        inputs = {}
        for key, value in market_features.items():
            if isinstance(value, np.ndarray):
                inputs[key] = torch.FloatTensor(value).unsqueeze(0)
            else:
                inputs[key] = torch.FloatTensor([value]).unsqueeze(0)
        
        with torch.no_grad():
            outputs = self.forward(inputs, risk_tolerance)
        
        # Convert to numpy
        result = {}
        for key, value in outputs.items():
            if isinstance(value, torch.Tensor):
                result[key] = value.squeeze(0).cpu().numpy()
            elif isinstance(value, dict):
                result[key] = {
                    k: v.squeeze(0).cpu().numpy() if isinstance(v, torch.Tensor) else v
                    for k, v in value.items()
                }
            else:
                result[key] = value
        
        return result
    
    def get_trading_signal(self, prediction: Dict) -> Tuple[str, float]:
        """
        Convierte predicción en señal de trading clara
        """
        final_decision = prediction['final_decision']
        confidence = prediction['confidence']
        
        # Decode probabilities
        buy_prob = final_decision[0]
        hold_prob = final_decision[1]
        sell_prob = final_decision[2]
        
        # Determine signal
        if buy_prob > 0.6 and confidence > 0.7:
            signal = "STRONG_BUY"
            strength = buy_prob * confidence
        elif buy_prob > 0.4 and confidence > 0.5:
            signal = "BUY"
            strength = buy_prob * confidence
        elif sell_prob > 0.6 and confidence > 0.7:
            signal = "STRONG_SELL"
            strength = sell_prob * confidence
        elif sell_prob > 0.4 and confidence > 0.5:
            signal = "SELL"
            strength = sell_prob * confidence
        else:
            signal = "HOLD"
            strength = hold_prob * confidence
        
        return signal, float(strength)

class RevolutionaryTraining:
    """
    Sistema de entrenamiento revolucionario para el cerebro
    """
    def __init__(self, brain: RevolutionaryBrain, config: Dict):
        self.brain = brain
        self.config = config
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.brain.to(self.device)
        
        # Optimizers
        self.optimizer = torch.optim.AdamW(
            self.brain.parameters(),
            lr=config.get('learning_rate', 1e-4),
            weight_decay=config.get('weight_decay', 1e-5)
        )
        
        # Loss functions
        self.prediction_loss = nn.CrossEntropyLoss()
        self.value_loss = nn.MSELoss()
        self.uncertainty_loss = nn.GaussianNLLLoss()
        
        # Training metrics
        self.metrics = {
            'total_loss': [],
            'prediction_accuracy': [],
            'sharpe_ratio': [],
            'profit_factor': [],
            'max_drawdown': []
        }
        
        print(f"🚀 RevolutionaryTraining inicializado")
        print(f"   Device: {self.device}")
        print(f"   Learning rate: {config.get('learning_rate', 1e-4)}")
    
    def train_step(self, batch: Dict) -> Dict[str, float]:
        """
        Single training step
        """
        self.brain.train()
        
        # Move batch to device
        market_data = {k: v.to(self.device) for k, v in batch['market_data'].items()}
        targets = {k: v.to(self.device) for k, v in batch['targets'].items()}
        returns = batch['returns'].to(self.device)
        
        # Forward pass
        outputs = self.brain(market_data)
        
        # Calculate losses
        total_loss = 0
        
        # 1. Prediction loss (cross-entropy)
        pred_loss = self.prediction_loss(
            outputs['final_decision'],
            targets['action']
        )
        total_loss += pred_loss * self.config.get('pred_loss_weight', 1.0)
        
        # 2. Value loss (for RL component)
        value_loss = self.value_loss(
            outputs.get('state_value', torch.zeros_like(returns)),
            returns
        )
        total_loss += value_loss * self.config.get('value_loss_weight', 0.5)
        
        # 3. Uncertainty calibration loss
        if 'oracle_uncertainty' in outputs:
            # Encourage appropriate uncertainty (high when wrong, low when right)
            pred_correct = (torch.argmax(outputs['final_decision'], dim=-1) == targets['action']).float()
            uncertainty_target = 1.0 - pred_correct  # High uncertainty when wrong
            unc_loss = F.mse_loss(outputs['oracle_uncertainty'].mean(dim=-1), uncertainty_target)
            total_loss += unc_loss * self.config.get('unc_loss_weight', 0.3)
        
        # 4. Risk-adjusted return maximization
        action_taken = torch.argmax(outputs['final_decision'], dim=-1)
        strategy_returns = returns * (action_taken == 0).float()  # Only when buying
        
        # Sharpe ratio penalty (negative Sharpe increases loss)
        sharpe = strategy_returns.mean() / (strategy_returns.std() + 1e-8)
        sharpe_penalty = -sharpe * self.config.get('sharpe_weight', 0.1)
        total_loss += sharpe_penalty
        
        # 5. Drawdown penalty
        cumulative = torch.cumprod(1 + strategy_returns, dim=0)
        running_max = torch.cummax(cumulative, dim=0).values
        drawdown = (cumulative - running_max) / running_max
        max_dd = torch.min(drawdown)
        dd_penalty = -max_dd * self.config.get('dd_weight', 0.05)
        total_loss += dd_penalty
        
        # Backward pass
        self.optimizer.zero_grad()
        total_loss.backward()
        
        # Gradient clipping
        torch.nn.utils.clip_grad_norm_(
            self.brain.parameters(),
            self.config.get('grad_clip', 1.0)
        )
        
        self.optimizer.step()
        
        # Calculate accuracy
        pred_actions = torch.argmax(outputs['final_decision'], dim=-1)
        accuracy = (pred_actions == targets['action']).float().mean()
        
        # Calculate profit factor
        positive_returns = strategy_returns[strategy_returns > 0].sum()
        negative_returns = torch.abs(strategy_returns[strategy_returns < 0]).sum()
        profit_factor = positive_returns / (negative_returns + 1e-8)
        
        return {
            'total_loss': total_loss.item(),
            'accuracy': accuracy.item(),
            'sharpe': sharpe.item(),
            'profit_factor': profit_factor.item(),
            'max_drawdown': max_dd.item()
        }
    
    def train(self, train_loader, val_loader, num_epochs: int = 100):
        """
        Full training loop
        """
        print(f"\n🚀 INICIANDO ENTRENAMIENTO REVOLUCIONARIO")
        print(f"   Epochs: {num_epochs}")
        print(f"   Batch size: {train_loader.batch_size}")
        print(f"   Training samples: {len(train_loader.dataset)}")
        print("=" * 60)
        
        best_sharpe = -float('inf')
        best_model_state = None
        
        for epoch in range(num_epochs):
            # Training phase
            self.brain.train()
            epoch_metrics = {
                'loss': 0,
                'accuracy': 0,
                'sharpe': 0,
                'profit_factor': 0,
                'drawdown': 0
            }
            
            for batch_idx, batch in enumerate(train_loader):
                step_metrics = self.train_step(batch)
                
                # Accumulate metrics
                for key in epoch_metrics:
                    epoch_metrics[key] += step_metrics[key]
                
                # Log progress
                if batch_idx % self.config.get('log_interval', 10) == 0:
                    print(f"Epoch {epoch+1}, Batch {batch_idx}: "
                          f"Loss={step_metrics['total_loss']:.4f}, "
                          f"Acc={step_metrics['accuracy']:.3f}, "
                          f"Sharpe={step_metrics['sharpe']:.3f}")
            
            # Average metrics
            num_batches = len(train_loader)
            for key in epoch_metrics:
                epoch_metrics[key] /= num_batches
            
            # Validation phase
            val_metrics = self.validate(val_loader)
            
            # Update best model
            if val_metrics['sharpe'] > best_sharpe:
                best_sharpe = val_metrics['sharpe']
                best_model_state = self.brain.state_dict().copy()
                print(f"   💾 Nuevo mejor modelo (Sharpe: {best_sharpe:.4f})")
            
            # Store metrics
            self.metrics['total_loss'].append(epoch_metrics['loss'])
            self.metrics['prediction_accuracy'].append(epoch_metrics['accuracy'])
            self.metrics['sharpe_ratio'].append(val_metrics['sharpe'])
            self.metrics['profit_factor'].append(val_metrics['profit_factor'])
            self.metrics['max_drawdown'].append(val_metrics['max_drawdown'])
            
            # Print epoch summary
            print(f"\n📊 EPOCH {epoch+1}/{num_epochs} COMPLETADA")
            print(f"   Train - Loss: {epoch_metrics['loss']:.4f}, Acc: {epoch_metrics['accuracy']:.3f}")
            print(f"   Val   - Sharpe: {val_metrics['sharpe']:.4f}, PF: {val_metrics['profit_factor']:.3f}")
            print(f"          DD: {val_metrics['max_drawdown']:.4f}, Acc: {val_metrics['accuracy']:.3f}")
            
            # Early stopping
            if epoch > 20 and val_metrics['sharpe'] < best_sharpe * 0.8:
                print(f"   ⚠️  Early stopping (performance degradation)")
                break
        
        # Load best model
        if best_model_state is not None:
            self.brain.load_state_dict(best_model_state)
        
        print(f"\n🎉 ENTRENAMIENTO REVOLUCIONARIO COMPLETADO")
        print(f"   Mejor Sharpe ratio: {best_sharpe:.4f}")
        print(f"   Épocas entrenadas: {epoch+1}")
        
        return self.metrics
    
    def validate(self, val_loader) -> Dict[str, float]:
        """
        Validation phase
        """
        self.brain.eval()
        
        all_predictions = []
        all_targets = []
        all_returns = []
        all_signals = []
        
        with torch.no_grad():
            for batch in val_loader:
                market_data = {k: v.to(self.device) for k, v in batch['market_data'].items()}
                targets = batch['targets']['action'].to(self.device)
                returns = batch['returns'].to(self.device)
                
                outputs = self.brain(market_data)
                
                # Store predictions
                pred_actions = torch.argmax(outputs['final_decision'], dim=-1)
                all_predictions.append(pred_actions.cpu().numpy())
                all_targets.append(targets.cpu().numpy())
                all_returns.append(returns.cpu().numpy())
                
                # Get trading signals
                for i in range(len(pred_actions)):
                    signal, strength = self.brain.get_trading_signal({
                        'final_decision': outputs['final_decision'][i],
                        'confidence': outputs['confidence'][i]
                    })
                    all_signals.append((signal, float(strength)))
        
        # Calculate metrics
        all_predictions = np.concatenate(all_predictions)
        all_targets = np.concatenate(all_targets)
        all_returns = np.concatenate(all_returns)
        
        # Strategy returns (only when predicting buy)
        strategy_returns = all_returns * (all_predictions == 0).astype(float)
        
        # Sharpe ratio
        sharpe = np.mean(strategy_returns) / (np.std(strategy_returns) + 1e-8) * np.sqrt(252)
        
        # Profit factor
        positive = strategy_returns[strategy_returns > 0].sum()
        negative = np.abs(strategy_returns[strategy_returns < 0]).sum()
        profit_factor = positive / (negative + 1e-8)
        
        # Maximum drawdown
        cumulative = np.cumprod(1 + strategy_returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = np.min(drawdown)
        
        # Accuracy
        accuracy = np.mean(all_predictions == all_targets)
        
        # Signal distribution
        signals = [s[0] for s in all_signals]
        signal_counts = {s: signals.count(s) for s in set(signals)}
        
        print(f"   📈 Signal distribution: {signal_counts}")
        
        return {
            'sharpe': sharpe,
            'profit_factor': profit_factor,
            'max_drawdown': max_drawdown,
            'accuracy': accuracy,
            'signal_counts': signal_counts
        }
    
    def save(self, path: str):
        """
        Save brain and training state
        """
        torch.save({
            'brain_state_dict': self.brain.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'config': self.config,
            'metrics': self.metrics
        }, path)
        print(f"💾 Cerebro revolucionario guardado en: {path}")
    
    def load(self, path: str):
        """
        Load brain and training state
        """
        checkpoint = torch.load(path, map_location=self.device)
        self.brain.load_state_dict(checkpoint['brain_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        self.config = checkpoint['config']
        self.metrics = checkpoint['metrics']
        print(f"📂 Cerebro revolucionario cargado desde: {path}")

# Default configuration for revolutionary brain
REVOLUTIONARY_CONFIG = {
    # Architecture
    'feature_dim': 50,
    'hidden_dim': 512,
    'context_dim': 1024,
    
    # Training
    'learning_rate': 1e-4,
    'weight_decay': 1e-5,
    'grad_clip': 1.0,
    
    # Loss weights
    'pred_loss_weight': 1.0,
    'value_loss_weight': 0.5,
    'unc_loss_weight': 0.3,
    'sharpe_weight': 0.1,
    'dd_weight': 0.05,
    
    # Training schedule
    'batch_size': 32,
    'num_epochs': 100,
    'log_interval': 10
}

def test_revolutionary_brain():
    """
    Test the revolutionary brain
    """
    print("\n🧪 TESTEANDO CEREBRO REVOLUCIONARIO...")
    print("=" * 60)
    
    # Create brain
    brain = RevolutionaryBrain(REVOLUTIONARY_CONFIG)
    
    # Test forward pass
    batch_size = 4
    seq_len = 20
    
    dummy_market_data = {
        'short_term': torch.randn(batch_size, seq_len, 50),
        'medium_term': torch.randn(batch_size, seq_len * 2, 50),
        'long_term': torch.randn(batch_size, seq_len * 4, 50)
    }
    
    with torch.no_grad():
        outputs = brain(dummy_market_data)
    
    print(f"✅ Forward pass exitoso")
    print(f"   Final decision shape: {outputs['final_decision'].shape}")
    print(f"   Confidence shape: {outputs['confidence'].shape}")
    print(f"   Market regime: {outputs['market_regime'].shape}")
    print(f"   Position size: {outputs['position_size'].shape}")
    
    # Test single prediction
    single_features = {
        'short_term': np.random.randn(seq_len, 50),
        'medium_term': np.random.randn(seq_len * 2, 50),
        'long_term': np.random.randn(seq_len * 4, 50)
    }
    
    prediction = brain.predict_single(single_features)
    signal, strength = brain.get_trading_signal(prediction)
    
    print(f"\n🎯 Predicción de ejemplo:")
    print(f"   Señal: {signal}")
    print(f"   Fuerza: {strength:.3f}")
    print(f"   Confianza: {prediction['confidence']:.3f}")
    print(f"   Tamaño posición: {prediction['position_size']:.3f}")
    
    # Test training pipeline
    print(f"\n🚀 Testeando pipeline de entrenamiento...")
    trainer = RevolutionaryTraining(brain, REVOLUTIONARY_CONFIG)
    print(f"✅ Pipeline de entrenamiento listo")
    
    print(f"\n🎉 CEREBRO REVOLUCIONARIO LISTO PARA REVOLUCIONAR EL TRADING!")
    print("=" * 60)

if __name__ == "__main__":
    test_revolutionary_brain()