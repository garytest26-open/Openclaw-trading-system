"""
DATA_PIPELINE.py - Pipeline de datos revolucionario para entrenamiento del cerebro
Sistema profesional de preparación de datos para IA de trading
"""

import yfinance as yf
import pandas as pd
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

print("📊 INICIALIZANDO PIPELINE DE DATOS REVOLUCIONARIO...")
print("=" * 60)

class RevolutionaryDataset(Dataset):
    """
    Dataset revolucionario para entrenamiento de IA de trading
    """
    
    def __init__(self, symbols: List[str] = None, 
                 period: str = '2y',
                 interval: str = '1h',
                 seq_length: int = 100):
        
        self.symbols = symbols or ['BTC-USD', 'ETH-USD', 'SOL-USD']
        self.period = period
        self.interval = interval
        self.seq_length = seq_length
        
        # Download and prepare data
        self.data = self.download_and_prepare_data()
        
        # Create sequences
        self.sequences, self.targets, self.returns = self.create_sequences()
        
        print(f"✅ Dataset revolucionario creado")
        print(f"   Símbolos: {self.symbols}")
        print(f"   Período: {self.period}, Intervalo: {self.interval}")
        print(f"   Secuencias: {len(self.sequences)}")
        print(f"   Longitud secuencia: {self.seq_length}")
    
    def download_and_prepare_data(self) -> Dict[str, pd.DataFrame]:
        """
        Download and prepare market data
        """
        data_dict = {}
        
        for symbol in self.symbols:
            print(f"📥 Descargando {symbol}...")
            
            try:
                # Download data
                ticker = yf.Ticker(symbol)
                df = ticker.history(period=self.period, interval=self.interval)
                
                if df.empty:
                    print(f"⚠️  No data for {symbol}")
                    continue
                
                # Calculate features
                df = self.calculate_features(df)
                
                # Store
                data_dict[symbol] = df
                print(f"   ✅ {len(df)} filas, {len(df.columns)} features")
                
            except Exception as e:
                print(f"❌ Error downloading {symbol}: {e}")
        
        return data_dict
    
    def calculate_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate advanced technical features
        """
        if df.empty:
            return df
        
        # Price features
        df['returns'] = df['Close'].pct_change()
        df['log_returns'] = np.log(df['Close'] / df['Close'].shift(1))
        
        # Volatility
        df['volatility_20'] = df['returns'].rolling(20).std() * np.sqrt(252)
        df['volatility_50'] = df['returns'].rolling(50).std() * np.sqrt(252)
        
        # Volume indicators
        df['volume_sma_20'] = df['Volume'].rolling(20).mean()
        df['volume_ratio'] = df['Volume'] / df['volume_sma_20']
        
        # Moving averages
        for window in [5, 10, 20, 50, 100, 200]:
            df[f'sma_{window}'] = df['Close'].rolling(window).mean()
            df[f'ema_{window}'] = df['Close'].ewm(span=window).mean()
        
        # Price position relative to MAs
        df['price_vs_sma_20'] = df['Close'] / df['sma_20']
        df['price_vs_sma_50'] = df['Close'] / df['sma_50']
        df['price_vs_sma_200'] = df['Close'] / df['sma_200']
        
        # RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        df['macd'] = df['ema_12'] - df['ema_26']
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']
        
        # Bollinger Bands
        df['bb_middle'] = df['Close'].rolling(20).mean()
        bb_std = df['Close'].rolling(20).std()
        df['bb_upper'] = df['bb_middle'] + 2 * bb_std
        df['bb_lower'] = df['bb_middle'] - 2 * bb_std
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
        df['bb_position'] = (df['Close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        # ATR
        high_low = df['High'] - df['Low']
        high_close = np.abs(df['High'] - df['Close'].shift())
        low_close = np.abs(df['Low'] - df['Close'].shift())
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr'] = true_range.rolling(14).mean()
        df['atr_percent'] = df['atr'] / df['Close']
        
        # Stochastic
        low_14 = df['Low'].rolling(14).min()
        high_14 = df['High'].rolling(14).max()
        df['stochastic_k'] = 100 * (df['Close'] - low_14) / (high_14 - low_14)
        df['stochastic_d'] = df['stochastic_k'].rolling(3).mean()
        
        # Williams %R
        df['williams_r'] = 100 * (high_14 - df['Close']) / (high_14 - low_14)
        
        # CCI
        typical_price = (df['High'] + df['Low'] + df['Close']) / 3
        sma_typical = typical_price.rolling(20).mean()
        mad = typical_price.rolling(20).apply(lambda x: np.abs(x - x.mean()).mean())
        df['cci'] = (typical_price - sma_typical) / (0.015 * mad)
        
        # OBV
        df['obv'] = 0
        for i in range(1, len(df)):
            if df['Close'].iloc[i] > df['Close'].iloc[i-1]:
                df['obv'].iloc[i] = df['obv'].iloc[i-1] + df['Volume'].iloc[i]
            elif df['Close'].iloc[i] < df['Close'].iloc[i-1]:
                df['obv'].iloc[i] = df['obv'].iloc[i-1] - df['Volume'].iloc[i]
            else:
                df['obv'].iloc[i] = df['obv'].iloc[i-1]
        
        # Trend strength
        df['trend_strength'] = np.abs(df['Close'].rolling(50).apply(
            lambda x: np.polyfit(range(len(x)), x, 1)[0]
        ))
        
        # Market regime features
        df['volatility_regime'] = pd.qcut(df['volatility_20'], q=4, labels=False)
        df['trend_regime'] = pd.qcut(df['trend_strength'], q=3, labels=False)
        
        # Momentum indicators
        df['momentum_10'] = df['Close'] / df['Close'].shift(10) - 1
        df['momentum_20'] = df['Close'] / df['Close'].shift(20) - 1
        df['roc_10'] = df['Close'].pct_change(10)
        df['roc_20'] = df['Close'].pct_change(20)
        
        # Fill NaN values
        df = df.fillna(method='ffill').fillna(method='bfill')
        
        # Select final features
        feature_columns = [
            'returns', 'log_returns',
            'volatility_20', 'volatility_50',
            'volume_ratio',
            'sma_5', 'sma_10', 'sma_20', 'sma_50', 'sma_100', 'sma_200',
            'ema_5', 'ema_10', 'ema_20', 'ema_50', 'ema_100', 'ema_200',
            'price_vs_sma_20', 'price_vs_sma_50', 'price_vs_sma_200',
            'rsi', 'macd', 'macd_signal', 'macd_histogram',
            'bb_width', 'bb_position',
            'atr_percent',
            'stochastic_k', 'stochastic_d',
            'williams_r', 'cci', 'obv',
            'trend_strength',
            'volatility_regime', 'trend_regime',
            'momentum_10', 'momentum_20',
            'roc_10', 'roc_20'
        ]
        
        # Keep only columns that exist
        available_features = [col for col in feature_columns if col in df.columns]
        
        return df[available_features]
    
    def create_sequences(self) -> Tuple[List[np.ndarray], List[int], List[float]]:
        """
        Create sequences for training
        """
        all_sequences = []
        all_targets = []
        all_returns = []
        
        for symbol, df in self.data.items():
            if df.empty:
                continue
            
            # Convert to numpy
            data_array = df.values.astype(np.float32)
            
            # Create sequences
            for i in range(self.seq_length, len(data_array) - 1):
                # Input sequence
                sequence = data_array[i-self.seq_length:i]
                
                # Target: next period return
                next_return = df['returns'].iloc[i] if 'returns' in df.columns else 0
                
                # Create target class
                if next_return > 0.005:  # > 0.5%
                    target = 0  # Buy
                elif next_return < -0.005:  # < -0.5%
                    target = 2  # Sell
                else:
                    target = 1  # Hold
                
                all_sequences.append(sequence)
                all_targets.append(target)
                all_returns.append(next_return)
        
        return all_sequences, all_targets, all_returns
    
    def __len__(self) -> int:
        return len(self.sequences)
    
    def __getitem__(self, idx: int) -> Dict:
        """
        Get item for training
        """
        sequence = self.sequences[idx]
        target = self.targets[idx]
        returns = self.returns[idx]
        
        # Create multi-scale features
        seq_len = len(sequence)
        
        # Short term (last 20%)
        short_term = sequence[-int(seq_len * 0.2):]
        
        # Medium term (last 50%)
        medium_term = sequence[-int(seq_len * 0.5):]
        
        # Long term (full sequence)
        long_term = sequence
        
        # Convert to tensors
        market_data = {
            'short_term': torch.FloatTensor(short_term),
            'medium_term': torch.FloatTensor(medium_term),
            'long_term': torch.FloatTensor(long_term)
        }
        
        targets = {
            'action': torch.LongTensor([target]),
            'returns': torch.FloatTensor([returns])
        }
        
        return {
            'market_data': market_data,
            'targets': targets,
            'returns': torch.FloatTensor([returns])
        }

class RevolutionaryDataPipeline:
    """
    Pipeline completo de datos para entrenamiento revolucionario
    """
    
    def __init__(self, config: Dict):
        self.config = config
        
        # Create datasets
        print("📊 Creando datasets revolucionarios...")
        self.full_dataset = RevolutionaryDataset(
            symbols=config.get('symbols', ['BTC-USD', 'ETH-USD', 'SOL-USD']),
            period=config.get('period', '2y'),
            interval=config.get('interval', '1h'),
            seq_length=config.get('seq_length', 100)
        )
        
        # Split into train/val
        train_size = int(len(self.full_dataset) * 0.8)
        val_size = len(self.full_dataset) - train_size
        
        self.train_dataset, self.val_dataset = torch.utils.data.random_split(
            self.full_dataset, [train_size, val_size]
        )
        
        # Create dataloaders
        self.train_loader = DataLoader(
            self.train_dataset,
            batch_size=config.get('batch_size', 32),
            shuffle=True,
            num_workers=0
        )
        
        self.val_loader = DataLoader(
            self.val_dataset,
            batch_size=config.get('batch_size', 32),
            shuffle=False,
            num_workers=0
        )
        
        print(f"✅ Pipeline de datos creado")
        print(f"   Dataset completo: {len(self.full_dataset)} secuencias")
        print(f"   Train: {len(self.train_dataset)} secuencias")
        print(f"   Val: {len(self.val_dataset)} secuencias")
        print(f"   Batch size: {config.get('batch_size', 32)}")
    
    def get_data_loaders(self) -> Tuple[DataLoader, DataLoader]:
        """
        Get train and validation dataloaders
        """
        return self.train_loader, self.val_loader
    
    def analyze_dataset(self):
        """
        Analyze dataset statistics
        """
        print("\n📈 ANÁLISIS DEL DATASET:")
        print("=" * 40)
        
        # Get all targets
        all_targets = self.full_dataset.targets
        
        # Distribution
        target_counts = {
            'Buy': all_targets.count(0),
            'Hold': all_targets.count(1),
            'Sell': all_targets.count(2)
        }
        
        print(f"Distribución de targets:")
        for action, count in target_counts.items():
            percentage = count / len(all_targets) * 100
            print(f"  {action}: {count} ({percentage:.1f}%)")
        
        # Returns statistics
        all_returns = self.full_dataset.returns
        positive_returns = [r for r in all_returns if r > 0]
        negative_returns = [r for r in all_returns if r < 0]
        
        print(f"\nEstadísticas de returns:")
        print(f"  Total: {len(all_returns)}")
        print(f"  Positivos: {len(positive_returns)} ({len(positive_returns)/len(all_returns)*100:.1f}%)")
        print(f"  Negativos: {len(negative_returns)} ({len(negative_returns)/len(all_returns)*100:.1f}%)")
        print(f"  Media: {np.mean(all_returns):.6f}")
        print(f"  Std: {np.std(all_returns):.6f}")
        print(f"  Min: {np.min(all_returns):.6f}")
        print(f"  Max: {np.max(all_returns):.6f}")
        
        # Feature dimensions
        if self.full_dataset.sequences:
            sample_seq = self.full_dataset.sequences[0]
            print(f"\nDimensiones de features:")
            print(f"  Secuencia shape: {sample_seq.shape}")
            print(f"  Features por timestep: {sample_seq.shape[1]}")
        
        return {
            'target_distribution': target_counts,
            'returns_stats': {
                'mean': np.mean(all_returns),
                'std': np.std(all_returns),
                'min': np.min(all_returns),
                'max': np.max(all_returns)
            }
        }

# Default configuration
DATA_PIPELINE_CONFIG = {
    'symbols': ['BTC-USD', 'ETH-USD', 'SOL-USD'],
    'period': '2y',
    'interval': '1h',
    'seq_length': 100,
    'batch_size': 32
}

def test_data_pipeline():
    """
    Test the data pipeline
    """
    print("\n🧪 TESTEANDO PIPELINE DE DATOS...")
    print("=" * 60)
    
    # Create pipeline
    pipeline = RevolutionaryDataPipeline(DATA_PIPELINE_CONFIG)
    
    # Analyze dataset
    stats = pipeline.analyze_dataset()
    
    # Test dataloaders
    train_loader, val_loader = pipeline.get_data_loaders()
    
    # Get a batch
    for batch in train_loader:
        market_data = batch['market_data']
        targets = batch['targets']
        returns = batch['returns']
        
        print(f"\n✅ Batch de ejemplo:")
        print(f"   Short term shape: {market_data['short_term'].shape}")
        print(f"   Medium term shape: {market_data['medium_term'].shape}")
        print(f"   Long term shape: {market_data['long_term'].shape}")
        print(f"   Targets shape: {targets['action'].shape}")
        print(f"   Returns shape: {returns.shape}")
        
        # Check data ranges
        print(f"\n📊 Ranges de datos:")
        for key, tensor in market_data.items():
            print(f"   {key}: {tensor.shape}, min={tensor.min():.3f}, max={tensor.max():.3f}")
        
        break
    
    print(f"\n🎉 PIPELINE DE DATOS REVOLUCIONARIO LISTO!")
    print("=" * 60)

def calculate_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate advanced technical features
    """
    if df.empty:
        return df
    
    # Price features
    df['returns'] = df['Close'].pct_change()
    df['log_returns'] = np.log(df['Close'] / df['Close'].shift(1))
    
    # Volatility
    df['volatility_20'] = df['returns'].rolling(20).std() * np.sqrt(252)
    df['volatility_50'] = df['returns'].rolling(50).std() * np.sqrt(252)
    
    # Volume indicators
    df['volume_sma_20'] = df['Volume'].rolling(20).mean()
    df['volume_ratio'] = df['Volume'] / df['volume_sma_20']
    
    # Moving averages
    for window in [5, 10, 20, 50, 100, 200]:
        df[f'sma_{window}'] = df['Close'].rolling(window).mean()
        df[f'ema_{window}'] = df['Close'].ewm(span=window).mean()
    
    # Price position relative to MAs
    df['price_vs_sma_20'] = df['Close'] / df['sma_20']
    df['price_vs_sma_50'] = df['Close'] / df['sma_50']
    df['price_vs_sma_200'] = df['Close'] / df['sma_200']
    
    # RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # MACD (need to create EMA 12 and 26 first)
    if 'ema_12' not in df.columns:
        df['ema_12'] = df['Close'].ewm(span=12).mean()
    if 'ema_26' not in df.columns:
        df['ema_26'] = df['Close'].ewm(span=26).mean()
    
    df['macd'] = df['ema_12'] - df['ema_26']
    df['macd_signal'] = df['macd'].ewm(span=9).mean()
    df['macd_histogram'] = df['macd'] - df['macd_signal']
    
    # Bollinger Bands
    df['bb_middle'] = df['Close'].rolling(20).mean()
    bb_std = df['Close'].rolling(20).std()
    df['bb_upper'] = df['bb_middle'] + 2 * bb_std
    df['bb_lower'] = df['bb_middle'] - 2 * bb_std
    df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
    df['bb_position'] = (df['Close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
    
    # ATR
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['atr'] = true_range.rolling(14).mean()
    df['atr_percent'] = df['atr'] / df['Close']
    
    # Stochastic
    low_14 = df['Low'].rolling(14).min()
    high_14 = df['High'].rolling(14).max()
    df['stochastic_k'] = 100 * (df['Close'] - low_14) / (high_14 - low_14)
    df['stochastic_d'] = df['stochastic_k'].rolling(3).mean()
    
    # Williams %R
    df['williams_r'] = 100 * (high_14 - df['Close']) / (high_14 - low_14)
    
    # CCI
    typical_price = (df['High'] + df['Low'] + df['Close']) / 3
    sma_typical = typical_price.rolling(20).mean()
    mad = typical_price.rolling(20).apply(lambda x: np.abs(x - x.mean()).mean())
    df['cci'] = (typical_price - sma_typical) / (0.015 * mad)
    
    # OBV
    df['obv'] = 0
    for i in range(1, len(df)):
        if df['Close'].iloc[i] > df['Close'].iloc[i-1]:
            df['obv'].iloc[i] = df['obv'].iloc[i-1] + df['Volume'].iloc[i]
        elif df['Close'].iloc[i] < df['Close'].iloc[i-1]:
            df['obv'].iloc[i] = df['obv'].iloc[i-1] - df['Volume'].iloc[i]
        else:
            df['obv'].iloc[i] = df['obv'].iloc[i-1]
    
    # Trend strength
    df['trend_strength'] = np.abs(df['Close'].rolling(50).apply(
        lambda x: np.polyfit(range(len(x)), x, 1)[0]
    ))
    
    # Market regime features
    df['volatility_regime'] = pd.qcut(df['volatility_20'], q=4, labels=False)
    df['trend_regime'] = pd.qcut(df['trend_strength'], q=3, labels=False)
    
    # Momentum indicators
    df['momentum_10'] = df['Close'] / df['Close'].shift(10) - 1
    df['momentum_20'] = df['Close'] / df['Close'].shift(20) - 1
    df['roc_10'] = df['Close'].pct_change(10)
    df['roc_20'] = df['Close'].pct_change(20)
    
    # Fill NaN values
    df = df.fillna(method='ffill').fillna(method='bfill')
    
    return df

if __name__ == "__main__":
    test_data_pipeline()