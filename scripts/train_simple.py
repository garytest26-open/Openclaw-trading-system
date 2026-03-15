#!/usr/bin/env python3
"""
Simple training script for Swarm Trading AI
Optimized for speed and reliability
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
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import warnings
warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/training.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Training parameters
EPOCHS = 100
BATCH_SIZE = 32
LEARNING_RATE = 0.001
SYMBOLS = ['BTC-USD', 'ETH-USD', 'SOL-USD']
YEARS = 3

# Simple neural network models
class SimpleTrendAgent(nn.Module):
    def __init__(self, input_size=10, hidden_size=64):
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, batch_first=True, bidirectional=True)
        self.fc1 = nn.Linear(hidden_size * 2, 32)
        self.fc2 = nn.Linear(32, 3)  # 3 classes: UP, DOWN, NEUTRAL
        self.dropout = nn.Dropout(0.2)
        
    def forward(self, x):
        lstm_out, _ = self.lstm(x)
        lstm_out = lstm_out[:, -1, :]  # Take last time step
        x = torch.relu(self.fc1(lstm_out))
        x = self.dropout(x)
        x = self.fc2(x)
        return x

class SimpleReversalAgent(nn.Module):
    def __init__(self, input_size=10):
        super().__init__()
        self.conv1 = nn.Conv1d(1, 16, kernel_size=3, padding=1)
        self.conv2 = nn.Conv1d(16, 32, kernel_size=3, padding=1)
        self.pool = nn.MaxPool1d(2)
        self.fc1 = nn.Linear(32 * 5, 64)
        self.fc2 = nn.Linear(64, 3)  # 3 classes: REVERSAL_UP, REVERSAL_DOWN, NO_REVERSAL
        self.dropout = nn.Dropout(0.2)
        
    def forward(self, x):
        x = x.unsqueeze(1)  # Add channel dimension
        x = torch.relu(self.conv1(x))
        x = self.pool(x)
        x = torch.relu(self.conv2(x))
        x = self.pool(x)
        x = x.view(x.size(0), -1)
        x = torch.relu(self.fc1(x))
        x = self.dropout(x)
        x = self.fc2(x)
        return x

class SimpleVolatilityAgent(nn.Module):
    def __init__(self, input_size=10, latent_size=8):
        super().__init__()
        # Encoder
        self.encoder = nn.Sequential(
            nn.Linear(input_size, 32),
            nn.ReLU(),
            nn.Linear(32, 16),
            nn.ReLU(),
            nn.Linear(16, latent_size * 2)  # Mean and log variance
        )
        # Decoder
        self.decoder = nn.Sequential(
            nn.Linear(latent_size, 16),
            nn.ReLU(),
            nn.Linear(16, 32),
            nn.ReLU(),
            nn.Linear(32, input_size)
        )
        # Classifier
        self.classifier = nn.Sequential(
            nn.Linear(latent_size, 8),
            nn.ReLU(),
            nn.Linear(8, 3)  # 3 volatility regimes: LOW, MEDIUM, HIGH
        )
        
    def reparameterize(self, mu, logvar):
        std = torch.exp(0.5 * logvar)
        eps = torch.randn_like(std)
        return mu + eps * std
        
    def forward(self, x):
        # Encode
        h = self.encoder(x)
        mu, logvar = h.chunk(2, dim=1)
        z = self.reparameterize(mu, logvar)
        
        # Decode
        recon = self.decoder(z)
        
        # Classify
        regime = self.classifier(z)
        
        return recon, regime, mu, logvar

def download_data():
    """Download historical data"""
    logger.info(f"📊 Downloading {YEARS} years of data for {SYMBOLS}...")
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=YEARS * 365)
    
    all_data = []
    
    for symbol in SYMBOLS:
        try:
            clean_symbol = symbol.replace('-USD', '')
            logger.info(f"  Downloading {clean_symbol}...")
            
            df = yf.download(
                clean_symbol,
                start=start_date.strftime('%Y-%m-%d'),
                end=end_date.strftime('%Y-%m-%d'),
                progress=False
            )
            
            if df.empty:
                logger.warning(f"  ⚠️  No data for {symbol}, creating synthetic...")
                # Create synthetic data
                dates = pd.date_range(start=start_date, end=end_date, freq='D')
                if 'BTC' in symbol:
                    base_price = 50000
                elif 'ETH' in symbol:
                    base_price = 3000
                else:  # SOL
                    base_price = 100
                
                returns = np.random.normal(0, 0.02, len(dates))
                prices = base_price * np.exp(np.cumsum(returns))
                
                df = pd.DataFrame({
                    'Open': prices * 0.99,
                    'High': prices * 1.01,
                    'Low': prices * 0.98,
                    'Close': prices,
                    'Volume': np.random.lognormal(10, 1, len(dates))
                }, index=dates)
            
            df['Symbol'] = symbol
            all_data.append(df)
            logger.info(f"  ✅ {symbol}: {len(df)} days of data")
            
        except Exception as e:
            logger.error(f"  ❌ Error downloading {symbol}: {e}")
            # Create synthetic data as fallback
            dates = pd.date_range(start=start_date, end=end_date, freq='D')
            base_price = 50000 if 'BTC' in symbol else (3000 if 'ETH' in symbol else 100)
            returns = np.random.normal(0, 0.02, len(dates))
            prices = base_price * np.exp(np.cumsum(returns))
            
            df = pd.DataFrame({
                'Open': prices * 0.99,
                'High': prices * 1.01,
                'Low': prices * 0.98,
                'Close': prices,
                'Volume': np.random.lognormal(10, 1, len(dates))
            }, index=dates)
            df['Symbol'] = symbol
            all_data.append(df)
            logger.info(f"  ⚠️  Using synthetic data for {symbol}")
    
    # Combine all data
    combined_df = pd.concat(all_data)
    logger.info(f"✅ Total data points: {len(combined_df)}")
    
    return combined_df

def create_features(df):
    """Create technical features"""
    logger.info("🔧 Creating technical features...")
    
    features = []
    labels_trend = []
    labels_reversal = []
    labels_volatility = []
    
    for symbol in SYMBOLS:
        symbol_data = df[df['Symbol'] == symbol].copy()
        
        if len(symbol_data) < 20:
            continue
        
        # Basic features
        symbol_data['Returns'] = symbol_data['Close'].pct_change()
        symbol_data['Log_Returns'] = np.log(symbol_data['Close'] / symbol_data['Close'].shift(1))
        
        # Moving averages
        symbol_data['MA_5'] = symbol_data['Close'].rolling(window=5).mean()
        symbol_data['MA_20'] = symbol_data['Close'].rolling(window=20).mean()
        symbol_data['MA_50'] = symbol_data['Close'].rolling(window=50).mean()
        
        # Volatility
        symbol_data['Volatility_5'] = symbol_data['Returns'].rolling(window=5).std()
        symbol_data['Volatility_20'] = symbol_data['Returns'].rolling(window=20).std()
        
        # RSI (simplified)
        delta = symbol_data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        symbol_data['RSI'] = 100 - (100 / (1 + rs))
        
        # Volume features
        symbol_data['Volume_MA'] = symbol_data['Volume'].rolling(window=20).mean()
        symbol_data['Volume_Ratio'] = symbol_data['Volume'] / symbol_data['Volume_MA']
        
        # Price position
        symbol_data['High_Low_Ratio'] = (symbol_data['High'] - symbol_data['Low']) / symbol_data['Close']
        
        # Drop NaN values
        symbol_data = symbol_data.dropna()
        
        if len(symbol_data) < 50:
            continue
        
        # Create sequences
        feature_cols = ['Returns', 'Log_Returns', 'MA_5', 'MA_20', 'MA_50', 
                       'Volatility_5', 'Volatility_20', 'RSI', 'Volume_Ratio', 'High_Low_Ratio']
        
        # Ensure all columns exist
        for col in feature_cols:
            if col not in symbol_data.columns:
                symbol_data[col] = 0
        
        # Normalize features
        scaler = StandardScaler()
        scaled_features = scaler.fit_transform(symbol_data[feature_cols].values)
        
        # Create sequences of length 10
        seq_length = 10
        for i in range(len(scaled_features) - seq_length - 1):
            seq = scaled_features[i:i+seq_length]
            features.append(seq)
            
            # Create labels
            future_return = symbol_data['Returns'].iloc[i+seq_length]
            
            # Trend label
            if future_return > 0.005:
                labels_trend.append(0)  # UP
            elif future_return < -0.005:
                labels_trend.append(1)  # DOWN
            else:
                labels_trend.append(2)  # NEUTRAL
            
            # Reversal label (simplified)
            current_trend = np.mean(symbol_data['Returns'].iloc[i:i+5])
            future_trend = np.mean(symbol_data['Returns'].iloc[i+5:i+10])
            if current_trend > 0.01 and future_trend < -0.005:
                labels_reversal.append(0)  # REVERSAL_DOWN
            elif current_trend < -0.01 and future_trend > 0.005:
                labels_reversal.append(1)  # REVERSAL_UP
            else:
                labels_reversal.append(2)  # NO_REVERSAL
            
            # Volatility label
            current_vol = symbol_data['Volatility_20'].iloc[i+seq_length]
            if current_vol < 0.01:
                labels_volatility.append(0)  # LOW
            elif current_vol < 0.03:
                labels_volatility.append(1)  # MEDIUM
            else:
                labels_volatility.append(2)  # HIGH
    
    logger.info(f"✅ Created {len(features)} sequences with features")
    
    return np.array(features), np.array(labels_trend), np.array(labels_reversal), np.array(labels_volatility)

def train_model(model, train_loader, val_loader, criterion, optimizer, epochs, model_name):
    """Train a model"""
    logger.info(f"🚀 Training {model_name} for {epochs} epochs...")
    
    best_val_loss = float('inf')
    patience = 10
    patience_counter = 0
    
    for epoch in range(epochs):
        # Training
        model.train()
        train_loss = 0
        train_correct = 0
        train_total = 0
        
        for batch_idx, (data, target) in enumerate(train_loader):
            optimizer.zero_grad()
            output = model(data)
            loss = criterion(output, target)
            loss.backward()
            optimizer.step()
            
            train_loss += loss.item()
            _, predicted = output.max(1)
            train_total += target.size(0)
            train_correct += predicted.eq(target).sum().item()
            
            if batch_idx % 50 == 0:
                logger.info(f"  Epoch {epoch+1}/{epochs}, Batch {batch_idx}/{len(train_loader)}, "
                           f"Loss: {loss.item():.4f}")
        
        train_acc = 100. * train_correct / train_total
        
        # Validation
        model.eval()
        val_loss = 0
        val_correct = 0
        val_total = 0
        
        with torch.no_grad():
            for data, target in val_loader:
                output = model(data)
                loss = criterion(output, target)
                val_loss += loss.item()
                _, predicted = output.max(1)
                val_total += target.size(0)
                val_correct += predicted.eq(target).sum().item()
        
        val_acc = 100. * val_correct / val_total
        val_loss /= len(val_loader)
        
        logger.info(f"✅ Epoch {epoch+1}/{epochs}: "
                   f"Train Loss: {train_loss/len(train_loader):.4f}, "
                   f"Train Acc: {train_acc:.2f}%, "
                   f"Val Loss: {val_loss:.4f}, "
                   f"Val Acc: {val_acc:.2f}%")
        
        # Early stopping
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            patience_counter = 0
            # Save best model
            torch.save(model.state_dict(), f'models/{model_name}_best.pth')
            logger.info(f"  💾 Saved best {model_name} model")
        else:
            patience_counter += 1
            if patience_counter >= patience:
                logger.info(f"  ⏹️  Early stopping triggered for {model_name}")
                break
    
    return model

def train_vae(model, train_loader, val_loader, optimizer, epochs, model_name):
    """Train VAE model"""
    logger.info(f"🚀 Training {model_name} (VAE) for {epochs} epochs...")
    
    best_val_loss = float('inf')
    
    for epoch in range(epochs):
        # Training
        model.train()
        train_recon_loss = 0
        train_kl_loss = 0
        train_class_loss = 0
        
        for batch_idx, (data, target) in enumerate(train_loader):
            optimizer.zero_grad()
            recon, regime, mu, logvar = model(data)
            
            # Reconstruction loss
            recon_loss = nn.functional.mse_loss(recon, data)
            
            # KL divergence
            kl_loss = -0.5 * torch.sum(1 + logvar - mu.pow(2) - logvar.exp())
            kl_loss /= data.size(0)
            
            # Classification loss
            class_loss = nn.functional.cross_entropy(regime, target)
            
            # Total loss
            loss = recon_loss + 0.1 * kl_loss + class_loss
            
            loss.backward()
            optimizer.step()
            
            train_recon_loss += recon_loss.item()
            train_kl_loss += kl_loss.item()
            train_class_loss += class_loss.item()
            
            if batch_idx % 50 == 0:
                logger.info(f"  Epoch {epoch+1}/{epochs}, Batch {batch_idx}/{len(train_loader)}, "
                           f"Loss: {loss.item():.4f}")
        
        # Validation
        model.eval()
        val_loss = 0
        
        with torch.no_grad():
            for data, target in val_loader:
                recon, regime, mu, logvar = model(data)
                recon_loss = nn.functional.mse_loss(recon, data)
                kl_loss = -0.5 * torch.sum(1 + logvar - mu.pow(2) - logvar.exp())
                kl_loss /= data.size(0)
                class_loss = nn.functional.cross_entropy(regime, target)
                loss = recon_loss + 0.1 * kl_loss + class_loss
                val_loss += loss.item()
        
        val_loss /= len(val_loader)
        
        logger.info(f"✅ Epoch {epoch+1}/{epochs}: "
                   f"Recon Loss: {train_recon_loss/len(train_loader):.4f}, "
                   f"KL Loss: {train_kl_loss/len(train_loader):.4f}, "
                   f"Class Loss: {train_class_loss/len(train_loader):.4f}, "
                   f"Val Loss: {val_loss:.4f}")
        
        # Save best model
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            torch.save(model.state_dict(), f'models/{model_name}_best.pth')
            logger.info(f"  💾 Saved best {model_name} model")
    
    return model

def main():
    """Main training function"""
    logger.info("=" * 60)
    logger.info("SWARM TRADING AI - ENTRENAMIENTO")
    logger.info("=" * 60)
    logger.info(f"Épocas: {EPOCHS}")
    logger.info(f"D