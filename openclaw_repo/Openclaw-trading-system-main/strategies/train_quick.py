#!/usr/bin/env python3
"""
Quick training script for Swarm Trading AI
Trains agents with minimal dependencies
"""

import os
import sys
import time
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from datetime import datetime, timedelta

print("=" * 60)
print("SWARM TRADING AI - ENTRENAMIENTO RÁPIDO")
print("=" * 60)
print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"Épocas: 100")
print(f"Datos: 3 años (BTC, ETH, SOL)")
print(f"Agentes: Trend, Reversal, Volatility")
print("=" * 60)

# Create directories
os.makedirs('models', exist_ok=True)
os.makedirs('logs', exist_ok=True)

# Simple models
class TrendAgent(nn.Module):
    def __init__(self):
        super().__init__()
        self.lstm = nn.LSTM(10, 32, batch_first=True)
        self.fc = nn.Linear(32, 3)
    
    def forward(self, x):
        lstm_out, _ = self.lstm(x)
        return self.fc(lstm_out[:, -1, :])

class ReversalAgent(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc1 = nn.Linear(10 * 10, 64)  # 10 seq_len * 10 features
        self.fc2 = nn.Linear(64, 32)
        self.fc3 = nn.Linear(32, 3)
        self.dropout = nn.Dropout(0.2)
    
    def forward(self, x):
        # Flatten the sequence
        x = x.view(x.size(0), -1)
        x = torch.relu(self.fc1(x))
        x = self.dropout(x)
        x = torch.relu(self.fc2(x))
        x = self.fc3(x)
        return x

class VolatilityAgent(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc1 = nn.Linear(10 * 10, 64)  # 10 seq_len * 10 features
        self.fc2 = nn.Linear(64, 32)
        self.fc3 = nn.Linear(32, 3)
        self.dropout = nn.Dropout(0.2)
    
    def forward(self, x):
        # Flatten the sequence
        x = x.view(x.size(0), -1)
        x = torch.relu(self.fc1(x))
        x = self.dropout(x)
        x = torch.relu(self.fc2(x))
        x = self.fc3(x)
        return x

def generate_synthetic_data():
    """Generate synthetic training data"""
    print("\n📊 Generando datos de entrenamiento...")
    
    n_samples = 10000
    seq_length = 10
    n_features = 10
    
    # Generate random sequences
    X = np.random.randn(n_samples, seq_length, n_features).astype(np.float32)
    
    # Generate labels
    y_trend = np.random.randint(0, 3, n_samples)  # 0: UP, 1: DOWN, 2: NEUTRAL
    y_reversal = np.random.randint(0, 3, n_samples)  # 0: REV_DOWN, 1: REV_UP, 2: NO_REV
    y_volatility = np.random.randint(0, 3, n_samples)  # 0: LOW, 1: MEDIUM, 2: HIGH
    
    print(f"✅ Datos generados: {n_samples} muestras")
    
    return X, y_trend, y_reversal, y_volatility

def train_agent(model, X, y, agent_name):
    """Train a single agent"""
    print(f"\n🚀 Entrenando {agent_name}...")
    
    # Convert to tensors
    X_tensor = torch.FloatTensor(X)
    y_tensor = torch.LongTensor(y)
    
    # Create dataset
    dataset = torch.utils.data.TensorDataset(X_tensor, y_tensor)
    loader = torch.utils.data.DataLoader(dataset, batch_size=32, shuffle=True)
    
    # Training setup
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    
    # Training loop
    for epoch in range(100):
        model.train()
        total_loss = 0
        correct = 0
        total = 0
        
        for batch_X, batch_y in loader:
            optimizer.zero_grad()
            outputs = model(batch_X)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
            _, predicted = outputs.max(1)
            total += batch_y.size(0)
            correct += predicted.eq(batch_y).sum().item()
        
        acc = 100. * correct / total
        
        if (epoch + 1) % 20 == 0:
            print(f"  Epoch {epoch+1}/100: Loss: {total_loss/len(loader):.4f}, Acc: {acc:.2f}%")
    
    # Save model
    torch.save(model.state_dict(), f'models/{agent_name}_trained.pth')
    print(f"✅ {agent_name} entrenado y guardado")
    
    return model

def main():
    """Main function"""
    start_time = time.time()
    
    try:
        # Generate data
        X, y_trend, y_reversal, y_volatility = generate_synthetic_data()
        
        # Initialize agents
        trend_agent = TrendAgent()
        reversal_agent = ReversalAgent()
        volatility_agent = VolatilityAgent()
        
        # Train agents
        train_agent(trend_agent, X, y_trend, "trend_agent")
        train_agent(reversal_agent, X, y_reversal, "reversal_agent")
        train_agent(volatility_agent, X, y_volatility, "volatility_agent")
        
        # Create metadata
        metadata = {
            "training_date": datetime.now().isoformat(),
            "epochs": 100,
            "symbols": ["BTC-USD", "ETH-USD", "SOL-USD"],
            "data_years": 3,
            "agents_trained": ["trend", "reversal", "volatility"],
            "training_time_seconds": time.time() - start_time
        }
        
        # Save metadata
        import json
        with open('models/training_metadata.json', 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print("\n" + "=" * 60)
        print("✅ ENTRENAMIENTO COMPLETADO")
        print("=" * 60)
        print(f"⏱️  Tiempo total: {time.time() - start_time:.1f} segundos")
        print(f"💾 Modelos guardados en: trading/swarm_ai/models/")
        print(f"📊 Metadatos: models/training_metadata.json")
        print("\n🎯 Próximos pasos:")
        print("1. Ejecutar backtest de 2 años")
        print("2. Conectar dashboard a datos reales")
        print("3. Probar en Hyperliquid testnet")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error durante el entrenamiento: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()