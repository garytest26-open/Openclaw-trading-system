#!/usr/bin/env python3
"""
Training script for Swarm Trading AI
Trains all neural agents with 3 years of historical data for BTC, ETH, SOL
"""

import os
import sys
import json
import time
import logging
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import yfinance as yf
from typing import Dict, List, Tuple
import torch
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset

# Add paths
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import agents
from agents.trend_agent import TrendAgent
from agents.reversal_agent import ReversalAgent
from agents.volatility_agent import VolatilityAgent
from training.data_preprocessor import SwarmDataPreprocessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading/logs/training.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class SwarmTrainer:
    """
    Trainer for Swarm Trading AI agents
    """
    
    def __init__(self, config_path: str = "trading/swarm_ai/config/swarm_config.json"):
        """
        Initialize trainer
        
        Args:
            config_path: Path to configuration file
        """
        # Load configuration
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        # Training parameters
        self.epochs = 100
        self.batch_size = 32
        self.learning_rate = 0.001
        self.validation_split = 0.2
        
        # Data parameters
        self.symbols = ['BTC-USD', 'ETH-USD', 'SOL-USD']
        self.years = 3
        self.interval = '1d'  # Daily data for long-term training
        
        # Initialize components
        self.preprocessor = SwarmDataPreprocessor(self.config)
        
        # Initialize agents
        self.agents = {}
        self._initialize_agents()
        
        # Training history
        self.training_history = {
            'trend_agent': [],
            'reversal_agent': [],
            'volatility_agent': []
        }
        
        # Device configuration
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        logger.info(f"Using device: {self.device}")
        
        # Create models directory
        os.makedirs('trading/swarm_ai/models', exist_ok=True)
        
        logger.info(f"Swarm Trainer initialized for {self.symbols}")
    
    def _initialize_agents(self):
        """Initialize all agents for training"""
        agent_configs = self.config.get('agent_configs', {})
        
        # Trend Agent
        trend_config = agent_configs.get('trend_agent', {})
        self.agents['trend_agent'] = TrendAgent(trend_config)
        
        # Reversal Agent
        reversal_config = agent_configs.get('reversal_agent', {})
        self.agents['reversal_agent'] = ReversalAgent(reversal_config)
        
        # Volatility Agent
        volatility_config = agent_configs.get('volatility_agent', {})
        self.agents['volatility_agent'] = VolatilityAgent(volatility_config)
        
        logger.info(f"Initialized {len(self.agents)} agents for training")
    
    def fetch_historical_data(self) -> Dict[str, pd.DataFrame]:
        """
        Fetch 3 years of historical data for all symbols
        
        Returns:
            Dictionary of symbol -> DataFrame
        """
        logger.info(f"Fetching {self.years} years of historical data...")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=self.years * 365)
        
        data = {}
        
        for symbol in self.symbols:
            try:
                logger.info(f"Downloading {symbol} data...")
                
                # Download from yfinance
                ticker = yf.Ticker(symbol.replace('-USD', ''))
                df = ticker.history(
                    start=start_date.strftime('%Y-%m-%d'),
                    end=end_date.strftime('%Y-%m-%d'),
                    interval=self.interval
                )
                
                if df.empty:
                    logger.warning(f"No data for {symbol}, trying alternative...")
                    # Try alternative symbol format
                    alt_symbol = symbol
                    if 'BTC' in symbol:
                        alt_symbol = 'BTC-USD'
                    elif 'ETH' in symbol:
                        alt_symbol = 'ETH-USD'
                    elif 'SOL' in symbol:
                        alt_symbol = 'SOL-USD'
                    
                    df = yf.download(
                        alt_symbol,
                        start=start_date.strftime('%Y-%m-%d'),
                        end=end_date.strftime('%Y-%m-%d'),
                        progress=False
                    )
                
                if df.empty:
                    logger.error(f"Failed to fetch data for {symbol}")
                    continue
                
                # Ensure proper column names
                df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]
                
                # Add symbol column
                df['symbol'] = symbol
                
                data[symbol] = df
                logger.info(f"  {symbol}: {len(df)} rows, {df.index[0]} to {df.index[-1]}")
                
            except Exception as e:
                logger.error(f"Error fetching {symbol}: {e}")
                continue
        
        # Create synthetic data if real data fails
        if not data:
            logger.warning("Creating synthetic data for training...")
            data = self._create_synthetic_data()
        
        total_rows = sum(len(df) for df in data.values())
        logger.info(f"Total data points: {total_rows}")
        
        return data
    
    def _create_synthetic_data(self) -> Dict[str, pd.DataFrame]:
        """Create synthetic data for training"""
        data = {}
        dates = pd.date_range(end=datetime.now(), periods=self.years * 365, freq='D')
        
        for symbol in self.symbols:
            # Generate realistic price series
            np.random.seed(hash(symbol) % 10000)
            
            # Different volatility for each symbol
            if 'BTC' in symbol:
                vol = 0.02
                drift = 0.0003
            elif 'ETH' in symbol:
                vol = 0.03
                drift = 0.0004
            else:  # SOL
                vol = 0.04
                drift = 0.0005
            
            returns = np.random.normal(drift, vol, len(dates))
            prices = 100 * np.exp(np.cumsum(returns))
            
            df = pd.DataFrame({
                'Open': prices * (1 + np.random.uniform(-0.001, 0.001, len(dates))),
                'High': prices * (1 + np.random.uniform(0, 0.002, len(dates))),
                'Low': prices * (1 - np.random.uniform(0, 0.002, len(dates))),
                'Close': prices,
                'Volume': np.random.lognormal(14, 1, len(dates)),
                'symbol': symbol
            }, index=dates)
            
            data[symbol] = df
            logger.info(f"Created synthetic data for {symbol}: {len(df)} rows")
        
        return data
    
    def prepare_training_data(self, data: Dict[str, pd.DataFrame]) -> Dict[str, Dict]:
        """
        Prepare training data for all agents
        
        Args:
            data: Dictionary of symbol -> DataFrame
            
        Returns:
            Dictionary of agent_name -> training data
        """
        logger.info("Preparing training data...")
        
        all_features = {}
        
        for symbol, df in data.items():
            logger.info(f"Processing {symbol}...")
            
            # Calculate features
            df_with_features = self.preprocessor.calculate_technical_features(df.copy())
            df_with_features = self.preprocessor.calculate_advanced_features(df_with_features)
            
            # Create agent-specific features
            agent_features = self.preprocessor.create_agent_specific_features(df_with_features)
            
            # Normalize features
            normalized_features = self.preprocessor.normalize_features(agent_features, fit=True)
            
            # Store
            all_features[symbol] = normalized_features
        
        # Combine data from all symbols
        combined_data = {}
        
        for agent_name in self.agents.keys():
            agent_data = []
            labels = []
            
            for symbol, features_dict in all_features.items():
                if agent_name in features_dict:
                    features = features_dict[agent_name]
                    
                    # Create labels (simplified: 1 if next day return > 0, else 0)
                    if len(features) > 1:
                        # For sequence models
                        if agent_name in ['trend_agent']:
                            sequence_length = 50
                            for i in range(len(features) - sequence_length - 1):
                                sequence = features[i:i+sequence_length]
                                # Simple label: price increased in next period
                                next_price = features[i+sequence_length, 0]  # Assuming price is first feature
                                current_price = features[i+sequence_length-1, 0]
                                label = 1 if next_price > current_price else 0
                                
                                agent_data.append(sequence)
                                labels.append(label)
                        else:
                            # For non-sequence models
                            for i in range(len(features) - 1):
                                agent_data.append(features[i])
                                # Simple label
                                label = 1 if features[i+1, 0] > features[i, 0] else 0
                                labels.append(label)
            
            if agent_data:
                combined_data[agent_name] = {
                    'features': np.array(agent_data),
                    'labels': np.array(labels)
                }
                logger.info(f"  {agent_name}: {len(agent_data)} samples")
            else:
                logger.warning(f"No data for {agent_name}")
        
        return combined_data
    
    def train_agent(self, agent_name: str, training_data: Dict, epochs: int = 100):
        """
        Train a specific agent
        
        Args:
            agent_name: Name of agent to train
            training_data: Training data dictionary
            epochs: Number of training epochs
        """
        if agent_name not in self.agents:
            logger.error(f"Agent {agent_name} not found")
            return
        
        if agent_name not in training_data:
            logger.error(f"No training data for {agent_name}")
            return
        
        agent = self.agents[agent_name]
        data = training_data[agent_name]
        
        features = data['features']
        labels = data['labels']
        
        logger.info(f"Training {agent_name} with {len(features)} samples...")
        
        # Convert to PyTorch tensors
        X = torch.FloatTensor(features).to(self.device)
        y = torch.LongTensor(labels).to(self.device)
        
        # Create dataset and dataloader
        dataset = TensorDataset(X, y)
        dataloader = DataLoader(dataset, batch_size=self.batch_size, shuffle=True)
        
        # Setup optimizer and loss function
        optimizer = optim.Adam(agent.model.parameters(), lr=self.learning_rate)
        criterion = torch.nn.CrossEntropyLoss()
        
        # Training loop
        agent.model.train()
        agent.model.to(self.device)
        
        history = []
        
        for epoch in range(epochs):
            epoch_loss = 0.0
            correct = 0
            total = 0
            
            for batch_X, batch_y in dataloader:
                optimizer.zero_grad()
                
                # Forward pass
                outputs = agent.model(batch_X)
                loss = criterion(outputs, batch_y)
                
                # Backward pass
                loss.backward()
                optimizer.step()
                
                # Statistics
                epoch_loss += loss.item()
                _, predicted = torch.max(outputs.data, 1)
                total += batch_y.size(0)
                correct += (predicted == batch_y).sum().item()
            
            # Calculate metrics
            avg_loss = epoch_loss / len(dataloader)
            accuracy = 100 * correct / total
            
            history.append({
                'epoch': epoch + 1,
                'loss': avg_loss,
                'accuracy': accuracy
            })
            
            # Log progress
            if (epoch + 1) % 10 == 0 or epoch == 0 or epoch == epochs - 1:
                logger.info(f"  Epoch {epoch+1}/{epochs}: Loss={avg_loss:.4f}, Accuracy={accuracy:.2f}%")
        
        # Save trained model
        model_path = f'trading/swarm_ai/models/{agent_name}_trained.pth'
        torch.save(agent.model.state_dict(), model_path)
        logger.info(f"Saved trained model to {model_path}")
        
        self.training_history[agent_name] = history
        
        return history
    
    def train_all_agents(self):
        """Train all agents"""
        logger.info("=" * 60)
        logger.info("STARTING SWARM AI TRAINING")
        logger.info("=" * 60)
        
        start_time = time.time()
        
        try:
            # 1. Fetch historical data
            logger.info("\n1. 📊 Fetching historical data...")
            historical_data = self.fetch_historical_data()
            
            if not historical_data:
                logger.error("No data available for training")
                return False
            
            # 2. Prepare training data
            logger.info("\n2. 🔧 Preparing training data...")
            training_data = self.prepare_training_data(historical_data)
            
            if not training_data:
                logger.error("No training data prepared")
                return False
            
            # 3. Train each agent
            logger.info("\n3. 🧠 Training agents...")
            
            for agent_name in self.agents.keys():
                logger.info(f"\nTraining {agent_name}...")
                history = self.train_agent(agent_name, training_data, self.epochs)
                
                if history:
                    # Log final metrics
                    final_epoch = history[-1]
                    logger.info(f"  ✅ {agent_name} training completed:")
                    logger.info(f"     Final Loss: {final_epoch['loss']:.4f}")
                    logger.info(f"     Final Accuracy: {final_epoch['accuracy']:.2f}%")
            
            # 4. Save training report
            logger.info("\n4. 💾 Saving training report...")
            self.save_training_report()
            
            # Calculate total time
            total_time = time.time() - start_time
            logger.info(f"\n✅ Training completed in {total_time:.2f} seconds")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Training failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def save_training_report(self):
        """Save training report to file"""
        report = {
            'training_date': datetime.now().isoformat(),
            'parameters': {
                'epochs': self.epochs,
                'symbols': self.symbols,
                'years': self.years,
                'interval': self.interval,
                'batch_size': self.batch_size,
                'learning_rate': self.learning_rate
            },
            'training_history': self.training_history,
            'device': str(self.device)
        }
        
        report_path = 'trading/swarm_ai/models/training_report.json'
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"Training report saved to {report_path}")
    
    def print_summary(self):
        """Print training summary"""
        print("\n" + "="*60)
        print("SWARM AI TRAINING SUMMARY")
        print("="*60)
        
        print(f"\n📊 Training Parameters:")
        print(f"  • Epochs: {self.epochs}")
        print(f"  • Symbols: {', '.join(self.symbols)}")
        print(f"  • Years of data: {self.years}")
        print(f"  • Interval: {self.interval}")
        print(f"  • Device: {self.device}")
        
        print(f"\n🧠 Agents Trained:")
        for agent_name, history in self.training_history.items():
            if history:
                final = history[-1]
                print(f"  • {agent_name}:")
                print(f"     Final Loss: {final['loss']:.4f}")
                print(f"     Final Accuracy: {final['accuracy']:.2f}%")
                print(f"     Epochs completed: {len(history)}")
        
        print(f"\n💾 Models saved to: trading/swarm_ai/models/")
        print(f"📋 Report saved to: trading/swarm_ai/models/training_report.json")
        
        print("\n🎯 Next Steps:")
        print("  1. Test trained models with trading/swarm_ai/main.py --test")
        print("  2. Evaluate performance on validation data")
        print("  3. Fine-tune hyperparameters if needed")
        print("  4. Deploy to Hyperliquid testnet")
        
        print("\n" + "="*60)


def main():
    """Main training function"""
    print("\n" + "="*60)
    print("SWARM TRADING AI - TRAINING SESSION")
    print("="*60)
    print("Parameters:")
    print("  • Epochs: 100")
    print("  • Data: 3 years historical")
    print("  • Symbols: BTC, ETH, SOL")
    print("  • Agents: Trend, Reversal, Volatility")
    print("="*60 + "\n")
    
    # Ask for confirmation
    confirm = input("Start training? (yes/no): ")
    if confirm.lower() != 'yes':
        print("Training cancelled")
        return
    
    # Initialize trainer
    trainer = SwarmTrainer()
    
