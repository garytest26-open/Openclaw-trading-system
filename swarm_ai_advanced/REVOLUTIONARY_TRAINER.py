"""
REVOLUTIONARY_TRAINER.py - Sistema completo de entrenamiento revolucionario
Entrena el cerebro de IA para revolucionar el trading
"""

import torch
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')

# Import our modules
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from REVOLUTIONARY_BRAIN import RevolutionaryBrain, REVOLUTIONARY_CONFIG
from DATA_PIPELINE import RevolutionaryDataPipeline, DATA_PIPELINE_CONFIG

print("🚀 INICIALIZANDO ENTRENADOR REVOLUCIONARIO...")
print("=" * 60)

class RevolutionaryTrainer:
    """
    Entrenador completo para el cerebro revolucionario
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        
        # Merge configurations
        self.brain_config = {**REVOLUTIONARY_CONFIG, **self.config.get('brain', {})}
        self.data_config = {**DATA_PIPELINE_CONFIG, **self.config.get('data', {})}
        self.train_config = {
            'num_epochs': self.config.get('num_epochs', 50),
            'early_stopping_patience': self.config.get('early_stopping_patience', 10),
            'save_every': self.config.get('save_every', 5),
            'log_every': self.config.get('log_every', 10)
        }
        
        # Initialize components
        print("🧠 Creando cerebro revolucionario...")
        self.brain = RevolutionaryBrain(self.brain_config)
        
        print("📊 Creando pipeline de datos...")
        self.data_pipeline = RevolutionaryDataPipeline(self.data_config)
        
        print("⚡ Creando sistema de entrenamiento...")
        from REVOLUTIONARY_BRAIN import RevolutionaryTraining
        self.trainer = RevolutionaryTraining(self.brain, self.brain_config)
        
        # Training state
        self.epoch = 0
        self.best_sharpe = -float('inf')
        self.patience_counter = 0
        
        print(f"\n✅ ENTRENADOR REVOLUCIONARIO INICIALIZADO")
        print(f"   Brain parameters: {sum(p.numel() for p in self.brain.parameters()):,}")
        print(f"   Training epochs: {self.train_config['num_epochs']}")
        print(f"   Early stopping: {self.train_config['early_stopping_patience']} epochs")
    
    def train(self) -> Dict[str, List]:
        """
        Entrenamiento completo del cerebro revolucionario
        """
        print("\n" + "=" * 60)
        print("🚀 INICIANDO ENTRENAMIENTO REVOLUCIONARIO")
        print("=" * 60)
        
        # Get data loaders
        train_loader, val_loader = self.data_pipeline.get_data_loaders()
        
        # Training loop
        for epoch in range(self.train_config['num_epochs']):
            self.epoch = epoch + 1
            
            print(f"\n📈 EPOCH {self.epoch}/{self.train_config['num_epochs']}")
            print("-" * 40)
            
            # Train for one epoch
            train_metrics = self.train_epoch(train_loader)
            
            # Validate
            val_metrics = self.validate(val_loader)
            
            # Print progress
            self.print_epoch_summary(train_metrics, val_metrics)
            
            # Check for improvement
            if val_metrics['sharpe'] > self.best_sharpe:
                self.best_sharpe = val_metrics['sharpe']
                self.patience_counter = 0
                
                # Save best model
                self.save_model(f"revolutionary_brain_best.pth")
                print(f"   💾 Nuevo mejor modelo (Sharpe: {self.best_sharpe:.4f})")
            else:
                self.patience_counter += 1
            
            # Save checkpoint periodically
            if self.epoch % self.train_config['save_every'] == 0:
                self.save_model(f"revolutionary_brain_epoch_{self.epoch}.pth")
            
            # Early stopping
            if self.patience_counter >= self.train_config['early_stopping_patience']:
                print(f"\n⚠️  Early stopping triggered")
                print(f"   No improvement for {self.patience_counter} epochs")
                break
        
        # Load best model
        self.load_model("revolutionary_brain_best.pth")
        
        # Final evaluation
        print("\n" + "=" * 60)
        print("🎉 ENTRENAMIENTO COMPLETADO")
        print("=" * 60)
        
        final_metrics = self.final_evaluation(val_loader)
        
        # Save final model
        self.save_model("revolutionary_brain_final.pth")
        
        return final_metrics
    
    def train_epoch(self, train_loader) -> Dict[str, float]:
        """
        Train for one epoch
        """
        self.brain.train()
        
        epoch_metrics = {
            'loss': 0,
            'accuracy': 0,
            'sharpe': 0,
            'profit_factor': 0,
            'drawdown': 0
        }
        
        num_batches = len(train_loader)
        
        for batch_idx, batch in enumerate(train_loader):
            # Train step
            step_metrics = self.trainer.train_step(batch)
            
            # Accumulate metrics
            for key in epoch_metrics:
                epoch_metrics[key] += step_metrics[key]
            
            # Log progress
            if batch_idx % self.train_config['log_every'] == 0:
                print(f"   Batch {batch_idx}/{num_batches}: "
                      f"Loss={step_metrics['total_loss']:.4f}, "
                      f"Acc={step_metrics['accuracy']:.3f}")
        
        # Average metrics
        for key in epoch_metrics:
            epoch_metrics[key] /= num_batches
        
        return epoch_metrics
    
    def validate(self, val_loader) -> Dict[str, float]:
        """
        Validation phase
        """
        return self.trainer.validate(val_loader)
    
    def print_epoch_summary(self, train_metrics: Dict, val_metrics: Dict):
        """
        Print epoch summary
        """
        print(f"   Train - Loss: {train_metrics['loss']:.4f}, Acc: {train_metrics['accuracy']:.3f}")
        print(f"   Val   - Sharpe: {val_metrics['sharpe']:.4f}, PF: {val_metrics['profit_factor']:.3f}")
        print(f"          DD: {val_metrics['max_drawdown']:.4f}, Acc: {val_metrics['accuracy']:.3f}")
        
        # Signal distribution
        if 'signal_counts' in val_metrics:
            signals = val_metrics['signal_counts']
            total = sum(signals.values())
            print(f"   Signals - ", end="")
            for signal, count in signals.items():
                percentage = count / total * 100
                print(f"{signal}: {percentage:.1f}% ", end="")
            print()
    
    def final_evaluation(self, val_loader) -> Dict[str, float]:
        """
        Final evaluation after training
        """
        print("\n📊 EVALUACIÓN FINAL DEL CEREBRO REVOLUCIONARIO")
        print("-" * 40)
        
        val_metrics = self.validate(val_loader)
        
        # Detailed analysis
        print(f"\n🎯 PERFORMANCE FINAL:")
        print(f"   Sharpe Ratio: {val_metrics['sharpe']:.4f}")
        print(f"   Profit Factor: {val_metrics['profit_factor']:.3f}")
        print(f"   Max Drawdown: {val_metrics['max_drawdown']:.4f}")
        print(f"   Accuracy: {val_metrics['accuracy']:.3f}")
        
        # Performance interpretation
        sharpe = val_metrics['sharpe']
        if sharpe > 2.0:
            rating = "🎖️ EXCELENTE (Hedge Fund Grade)"
        elif sharpe > 1.0:
            rating = "✅ BUENO (Profesional)"
        elif sharpe > 0.5:
            rating = "⚠️  ACEPTABLE"
        else:
            rating = "❌ NECESITA MEJORAS"
        
        print(f"\n📈 INTERPRETACIÓN:")
        print(f"   Rating: {rating}")
        print(f"   Sharpe > 1.0: {'✅' if sharpe > 1.0 else '❌'}")
        print(f"   Sharpe > 2.0: {'✅' if sharpe > 2.0 else '❌'}")
        
        return val_metrics
    
    def save_model(self, filename: str):
        """
        Save model
        """
        path = os.path.join(os.path.dirname(__file__), "models", filename)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.trainer.save(path)
    
    def load_model(self, filename: str):
        """
        Load model
        """
        path = os.path.join(os.path.dirname(__file__), "models", filename)
        if os.path.exists(path):
            self.trainer.load(path)
        else:
            print(f"⚠️  Model file not found: {path}")
    
    def predict_live(self, market_data: Dict) -> Dict:
        """
        Make live prediction
        """
        return self.brain.predict_single(market_data)
    
    def get_trading_signal(self, prediction: Dict) -> Tuple[str, float]:
        """
        Get trading signal from prediction
        """
        return self.brain.get_trading_signal(prediction)

class RevolutionaryDeployment:
    """
    Sistema de deployment para el cerebro revolucionario
    """
    
    def __init__(self, trainer: RevolutionaryTrainer):
        self.trainer = trainer
        self.live_predictions = []
        
        print("🚀 INICIALIZANDO DEPLOYMENT REVOLUCIONARIO")
        print("   Sistema listo para trading en tiempo real")
    
    def run_live_demo(self, num_predictions: int = 10):
        """
        Run live demo with simulated data
        """
        print(f"\n🎮 DEMO EN VIVO - {num_predictions} predicciones")
        print("=" * 40)
        
        for i in range(num_predictions):
            # Generate simulated market data
            market_data = self.generate_simulated_data()
            
            # Make prediction
            prediction = self.trainer.predict_live(market_data)
            
            # Get trading signal
            signal, strength = self.trainer.get_trading_signal(prediction)
            
            # Store prediction
            self.live_predictions.append({
                'prediction': prediction,
                'signal': signal,
                'strength': strength,
                'timestamp': pd.Timestamp.now()
            })
            
            # Print result
            print(f"\n📈 Predicción {i+1}:")
            print(f"   Señal: {signal}")
            print(f"   Fuerza: {strength:.3f}")
            print(f"   Confianza: {prediction['confidence']:.3f}")
            print(f"   Posición: {prediction['position_size']:.3f}")
            print(f"   Stop Loss: {prediction['stop_loss']:.3%}")
            print(f"   Take Profit: {prediction['take_profit']:.3%}")
            
            # Simulate delay
            import time
            time.sleep(1)
        
        # Summary
        print(f"\n📊 RESUMEN DEMO:")
        signals = [p['signal'] for p in self.live_predictions]
        for signal_type in set(signals):
            count = signals.count(signal_type)
            print(f"   {signal_type}: {count} ({count/len(signals)*100:.1f}%)")
    
    def generate_simulated_data(self) -> Dict[str, np.ndarray]:
        """
        Generate simulated market data for demo
        """
        seq_len = 100
        
        # Simulate price patterns
        time_points = np.arange(seq_len)
        
        # Short term: recent volatility
        short_term = np.random.randn(int(seq_len * 0.2), 50) * 0.1 + 0.02
        
        # Medium term: trend + noise
        medium_len = int(seq_len * 0.5)
        trend = np.linspace(0, 0.1, medium_len)
        medium_term = np.random.randn(medium_len, 50) * 0.05 + trend[:, np.newaxis]
        
        # Long term: cyclical pattern
        long_term = np.random.randn(seq_len, 50) * 0.03
        cycle = np.sin(np.linspace(0, 4*np.pi, seq_len)) * 0.05
        long_term += cycle[:, np.newaxis]
        
        return {
            'short_term': short_term.astype(np.float32),
            'medium_term': medium_term.astype(np.float32),
            'long_term': long_term.astype(np.float32)
        }
    
    def create_production_api(self):
        """
        Create production API for the brain
        """
        print("\n🌐 CREANDO API DE PRODUCCIÓN...")
        
        api_code = """
from flask import Flask, request, jsonify
import numpy as np
import torch

app = Flask(__name__)

# Load revolutionary brain
brain = RevolutionaryBrain(REVOLUTIONARY_CONFIG)
brain.load_state_dict(torch.load('revolutionary_brain_final.pth'))
brain.eval()

@app.route('/predict', methods=['POST'])
def predict():
    data = request.json
    
    # Prepare market data
    market_data = {
        'short_term': np.array(data['short_term'], dtype=np.float32),
        'medium_term': np.array(data['medium_term'], dtype=np.float32),
        'long_term': np.array(data['long_term'], dtype=np.float32)
    }
    
    # Make prediction
    with torch.no_grad():
        prediction = brain.predict_single(market_data)
    
    # Get trading signal
    signal, strength = brain.get_trading_signal(prediction)
    
    return jsonify({
        'signal': signal,
        'strength': float(strength),
        'confidence': float(prediction['confidence']),
        'position_size': float(prediction['position_size']),
        'stop_loss': float(prediction['stop_loss']),
        'take_profit': float(prediction['take_profit'])
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002)
"""
        
        # Save API code
        api_path = os.path.join(os.path.dirname(__file__), "api", "revolutionary_api.py")
        os.makedirs(os.path.dirname(api_path), exist_ok=True)
        
        with open(api_path, 'w') as f:
            f.write(api_code)
        
        print(f"✅ API creada en: {api_path}")
        print(f"   Endpoint: POST /predict")
        print(f"   Puerto: 5002")
        
        return api_path

def main():
    """
    Main function to run revolutionary training
    """
    print("🎯 SISTEMA REVOLUCIONARIO DE IA PARA TRADING")
    print("=" * 60)
    
    # Configuration
    config = {
        'num_epochs': 30,  # Reduced for faster training
        'early_stopping_patience': 5,
        'save_every': 5,
        'log_every': 5,
        'data': {
            'period': '1y',  # 1 year for faster training
            'seq_length': 50  # Shorter sequences
        }
    }
    
    try:
        # Create trainer
        trainer = RevolutionaryTrainer(config)
        
        # Train the brain
        print("\n🔥 INICIANDO ENTRENAMIENTO...")
        final_metrics = trainer.train()
        
        # Create deployment system
        deployment = RevolutionaryDeployment(trainer)
        
        # Run live demo
        deployment.run_live_demo(num_predictions=5)
        
        # Create production API
        api_path = deployment.create_production_api()
        
        print("\n" + "=" * 60)
        print("🎉 SISTEMA REVOLUCIONARIO COMPLETADO!")
        print("=" * 60)
        print("\n📁 ARCHIVOS CREADOS:")
        print(f"   • Revolutionary Brain: revolutionary_brain_final.pth")
        print(f"   • Training metrics: metrics.npy")
        print(f"   • Production API: {api_path}")
        print(f"   • Data pipeline: DATA_PIPELINE.py")
        print(f"   • Brain architecture: REVOLUTIONARY_BRAIN.py")
        
        print("\n🚀 PRÓXIMOS PASOS:")
        print("   1. Ejecutar API: python revolutionary_api.py")
        print("   2. Conectar a datos en tiempo real")
        print("   3. Integrar con exchange (Binance/Coinbase)")
        print("   4. Implementar sistema de ejecución automática")
        print("   5. Monitorear performance en producción")
        
        print("\n💡 RECOMENDACIÓN:")
        print("   Comenzar con capital pequeño y escalar gradualmente")
        print("   Monitorear drawdown y ajustar risk parameters")
        print("   Mantener siempre stop-loss activado")
        
        return {
            'success': True,
            'final_sharpe': final_metrics.get('sharpe', 0),
            'final_pf': final_metrics.get('profit_factor', 0),
            'api_path': api_path
        }
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            'success': False,
            'error': str(e)
        }

if __name__ == "__main__":
    # Run the revolutionary system
    result = main()
    
    if result['success']:
        print(f"\n✅ ÉXITO: Sistema revolucionario entrenado")
        print(f"   Sharpe Ratio final: {result['final_sharpe']:.4f}")
        print(f"   Profit Factor final: {result['final_pf']:.3f}")
        print(f"   API disponible en: {result['api_path']}")
    else:
        print(f"\n❌ FALLO: {result.get('error', 'Unknown error')}")