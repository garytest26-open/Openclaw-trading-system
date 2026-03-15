#!/usr/bin/env python3
"""
Advanced Data Preprocessor for Swarm Trading AI
Feature engineering and preparation for neural networks
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime, timedelta
from scipy import stats
import talib
from sklearn.preprocessing import StandardScaler, RobustScaler, QuantileTransformer
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)


class SwarmDataPreprocessor:
    """
    Advanced data preprocessor for swarm trading AI
    Creates features for all specialized agents
    """
    
    def __init__(self, config: Dict = None):
        """
        Initialize preprocessor with configuration
        
        Args:
            config: Preprocessor configuration
        """
        self.config = config or {}
        self.scalers = {}
        self.feature_stats = {}
        
        # Technical indicator parameters
        self.ta_config = {
            'rsi_period': 14,
            'macd_fast': 12,
            'macd_slow': 26,
            'macd_signal': 9,
            'bb_period': 20,
            'bb_std': 2.0,
            'atr_period': 14,
            'stochastic_period': 14,
            'williams_period': 14,
            'cci_period': 20,
            'adx_period': 14
        }
        
        logger.info("Swarm Data Preprocessor initialized")
    
    def load_and_clean_data(self, data_path: str, symbol: str) -> pd.DataFrame:
        """
        Load and clean market data
        
        Args:
            data_path: Path to data file or directory
            symbol: Trading symbol
            
        Returns:
            Cleaned DataFrame
        """
        # For now, create synthetic data. In production, load from API/database
        np.random.seed(42)
        n_samples = 10000
        
        dates = pd.date_range(end=datetime.now(), periods=n_samples, freq='5min')
        
        # Generate realistic price series with trends and volatility clusters
        returns = np.random.normal(0.0001, 0.01, n_samples)
        # Add volatility clustering
        for i in range(1, n_samples):
            if abs(returns[i-1]) > 0.02:
                returns[i] *= 1.5
        
        prices = 100 * np.exp(np.cumsum(returns))
        
        # Generate OHLCV
        df = pd.DataFrame({
            'timestamp': dates,
            'open': prices * (1 + np.random.uniform(-0.001, 0.001, n_samples)),
            'high': prices * (1 + np.random.uniform(0, 0.002, n_samples)),
            'low': prices * (1 - np.random.uniform(0, 0.002, n_samples)),
            'close': prices,
            'volume': np.random.lognormal(10, 1, n_samples)
        })
        
        df.set_index('timestamp', inplace=True)
        logger.info(f"Generated {len(df)} samples for {symbol}")
        return df
    
    def calculate_technical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate comprehensive technical indicators
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            DataFrame with technical features
        """
        # Ensure numeric
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        close = df['close'].values
        high = df['high'].values
        low = df['low'].values
        volume = df['volume'].values
        
        # Trend indicators
        df['returns'] = df['close'].pct_change()
        df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
        
        # RSI
        df['rsi'] = talib.RSI(close, timeperiod=self.ta_config['rsi_period'])
        
        # MACD
        df['macd'], df['macd_signal'], df['macd_hist'] = talib.MACD(
            close, 
            fastperiod=self.ta_config['macd_fast'],
            slowperiod=self.ta_config['macd_slow'],
            signalperiod=self.ta_config['macd_signal']
        )
        
        # Bollinger Bands
        df['bb_upper'], df['bb_middle'], df['bb_lower'] = talib.BBANDS(
            close,
            timeperiod=self.ta_config['bb_period'],
            nbdevup=self.ta_config['bb_std'],
            nbdevdn=self.ta_config['bb_std']
        )
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
        df['bb_position'] = (close - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        # ATR
        df['atr'] = talib.ATR(high, low, close, timeperiod=self.ta_config['atr_period'])
        
        # Stochastic
        df['stochastic_k'], df['stochastic_d'] = talib.STOCH(
            high, low, close,
            fastk_period=self.ta_config['stochastic_period'],
            slowk_period=3,
            slowd_period=3
        )
        
        # Williams %R
        df['williams_r'] = talib.WILLR(
            high, low, close, 
            timeperiod=self.ta_config['williams_period']
        )
        
        # CCI
        df['cci'] = talib.CCI(
            high, low, close,
            timeperiod=self.ta_config['cci_period']
        )
        
        # ADX
        df['adx'] = talib.ADX(
            high, low, close,
            timeperiod=self.ta_config['adx_period']
        )
        
        # Volume indicators
        df['volume_sma'] = talib.SMA(volume, timeperiod=20)
        df['volume_ratio'] = volume / df['volume_sma']
        df['obv'] = talib.OBV(close, volume)
        
        # VWAP (simplified)
        df['typical_price'] = (high + low + close) / 3
        df['vwap'] = (df['typical_price'] * volume).cumsum() / volume.cumsum()
        
        # Money Flow Index
        df['mfi'] = talib.MFI(high, low, close, volume, timeperiod=14)
        
        # Price patterns
        df['hammer'] = talib.CDLHAMMER(df['open'], high, low, close)
        df['engulfing'] = talib.CDLENGULFING(df['open'], high, low, close)
        df['doji'] = talib.CDLDOJI(df['open'], high, low, close)
        
        # Volatility measures
        df['historical_vol'] = df['returns'].rolling(20).std() * np.sqrt(365*24*12)  # Annualized
        df['parkinson_vol'] = np.sqrt(1/(4*np.log(2)) * ((np.log(high/low))**2).rolling(20).mean()) * np.sqrt(365*24*12)
        
        # Momentum
        df['roc'] = talib.ROC(close, timeperiod=10)
        df['momentum'] = talib.MOM(close, timeperiod=10)
        
        # Support/Resistance
        df['resistance'] = high.rolling(20).max()
        df['support'] = low.rolling(20).min()
        df['price_to_resistance'] = close / df['resistance']
        df['price_to_support'] = close / df['support']
        
        # Statistical features
        df['skewness'] = df['returns'].rolling(50).skew()
        df['kurtosis'] = df['returns'].rolling(50).kurt()
        
        # Market microstructure (simplified)
        df['spread_estimate'] = (high - low) / close  # Proxy for spread
        df['efficiency_ratio'] = abs(df['returns'].rolling(20).sum()) / df['returns'].abs().rolling(20).sum()
        
        logger.info(f"Calculated {len(df.columns)} technical features")
        return df
    
    def calculate_advanced_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate advanced features for neural networks
        
        Args:
            df: DataFrame with basic features
            
        Returns:
            DataFrame with advanced features
        """
        # Fourier transforms for frequency analysis
        close_fft = np.fft.fft(df['close'].values)
        df['fft_magnitude'] = np.abs(close_fft)
        df['fft_phase'] = np.angle(close_fft)
        
        # Wavelet-like features (simplified)
        df['high_pass'] = df['close'] - df['close'].rolling(5).mean()
        df['low_pass'] = df['close'].rolling(20).mean()
        
        # Entropy (measure of randomness)
        def calculate_entropy(series, window=20):
            entropy = []
            for i in range(len(series)):
                if i < window:
                    entropy.append(np.nan)
                else:
                    hist, _ = np.histogram(series[i-window:i], bins=10)
                    prob = hist / hist.sum()
                    prob = prob[prob > 0]
                    entropy.append(-np.sum(prob * np.log2(prob)))
            return entropy
        
        df['price_entropy'] = calculate_entropy(df['close'].values)
        df['volume_entropy'] = calculate_entropy(df['volume'].values)
        
        # Fractal dimension (approximate)
        def hurst_exponent(series, max_lag=20):
            lags = range(2, max_lag)
            tau = [np.std(np.subtract(series[lag:], series[:-lag])) for lag in lags]
            poly = np.polyfit(np.log(lags), np.log(tau), 1)
            return poly[0]
        
        hurst_values = []
        for i in range(len(df)):
            if i < 100:
                hurst_values.append(np.nan)
            else:
                hurst_values.append(hurst_exponent(df['close'].values[i-100:i]))
        
        df['hurst_exponent'] = hurst_values
        df['fractal_dimension'] = 2 - df['hurst_exponent']
        
        # Regime detection features
        df['volatility_regime'] = (df['atr'] > df['atr'].rolling(50).mean()).astype(int)
        df['trend_regime'] = (df['adx'] > 25).astype(int)
        
        # Correlation features
        df['autocorrelation_1'] = df['returns'].autocorr(lag=1)
        df['autocorrelation_5'] = df['returns'].autocorr(lag=5)
        
        # Option-implied features (simplified proxies)
        df['risk_neutral_skew'] = df['skewness'] * -1  # Proxy for risk-neutral skew
        df['volatility_smile'] = df['parkinson_vol'] / df['historical_vol']  # Proxy for smile
        
        logger.info(f"Calculated {sum(['fft' in col or 'entropy' in col or 'hurst' in col for col in df.columns])} advanced features")
        return df
    
    def create_agent_specific_features(self, df: pd.DataFrame) -> Dict[str, np.ndarray]:
        """
        Create feature sets for each specialized agent
        
        Args:
            df: DataFrame with all features
            
        Returns:
            Dictionary with feature arrays for each agent
        """
        # Clean NaN values
        df_clean = df.fillna(method='ffill').fillna(method='bfill').fillna(0)
        
        agent_features = {}
        
        # 1. Trend Agent Features (LSTM)
        trend_features = [
            'close', 'returns', 'log_returns', 'volatility', 'momentum',
            'macd', 'macd_hist', 'adx', 'roc'
        ]
        agent_features['trend_agent'] = df_clean[trend_features].values
        
        # 2. Reversal Agent Features (CNN)
        reversal_features = [
            'rsi', 'stochastic_k', 'stochastic_d', 'williams_r', 'cci',
            'bb_position', 'price_to_resistance', 'price_to_support',
            'hammer', 'engulfing', 'doji'
        ]
        agent_features['reversal_agent'] = df_clean[reversal_features].values
        
        # 3. Volatility Agent Features (VAE)
        volatility_features = [
            'atr', 'bb_width', 'historical_vol', 'parkinson_vol',
            'volatility_regime', 'hurst_exponent', 'fractal_dimension',
            'skewness', 'kurtosis', 'volatility_smile'
        ]
        agent_features['volatility_agent'] = df_clean[volatility_features].values
        
        # 4. Volume Agent Features (Transformer)
        volume_features = [
            'volume', 'volume_ratio', 'obv', 'vwap', 'mfi',
            'volume_entropy', 'spread_estimate', 'efficiency_ratio',
            'autocorrelation_1', 'autocorrelation_5'
        ]
        agent_features['volume_agent'] = df_clean[volume_features].values
        
        # 5. Sentiment Agent Features (placeholder - would come from NLP pipeline)
        sentiment_features = [
            'returns', 'volume_ratio', 'rsi', 'bb_position',
            'risk_neutral_skew', 'fft_magnitude', 'price_entropy'
        ]
        agent_features['sentiment_agent'] = df_clean[sentiment_features].values
        
        # Store feature names for reference
        self.feature_names = {
            'trend_agent': trend_features,
            'reversal_agent': reversal_features,
            'volatility_agent': volatility_features,
            'volume_agent': volume_features,
            'sentiment_agent': sentiment_features
        }
        
        logger.info(f"Created features for {len(agent_features)} agents")
        return agent_features
    
    def normalize_features(self, agent_features: Dict[str, np.ndarray], 
                          fit: bool = True) -> Dict[str, np.ndarray]:
        """
        Normalize features for neural networks
        
        Args:
            agent_features: Dictionary of agent features
            fit: Whether to fit new scalers
            
        Returns:
            Dictionary of normalized features
        """
        normalized_features = {}
        
        for agent_name, features in agent_features.items():
            if fit:
                # Use RobustScaler for outlier resistance
                scaler = RobustScaler(quantile_range=(5, 95))
                scaled_features = scaler.fit_transform(features)
                self.scalers[agent_name] = scaler
            else:
                scaler = self.scalers.get(agent_name)
                if scaler is None:
                    raise ValueError(f"No scaler found for {agent_name}")
                scaled_features = scaler.transform(features)
            
            normalized_features[agent_name] = scaled_features
        
        logger.info("Features normalized")
        return normalized_features
    
    def create_sequences(self, features: np.ndarray, sequence_length: int = 50) -> np.ndarray:
        """
        Create sequences for time series models
        
        Args:
            features: Feature array
            sequence_length: Length of each sequence
            
        Returns:
            Array of sequences
        """
        sequences = []
        for i in range(len(features) - sequence_length):
            sequences.append(features[i:i+sequence_length])
        
        return np.array(sequences)
    
    def prepare_training_data(self, agent_features: Dict[str, np.ndarray], 
                             target_returns: np.ndarray, sequence_length: int = 50) -> Dict:
        """
        Prepare complete training dataset
        
        Args:
            agent_features: Dictionary of normalized agent features
            target_returns: Target returns for prediction
            sequence_length: Sequence length for time series models
            
        Returns:
            Dictionary with prepared datasets for each agent
        """
        training_data = {}
        
        # Align targets with features (skip first sequence_length for sequence models)
        aligned_targets = target_returns[sequence_length:]
        
        for agent_name, features in agent_features.items():
            if agent_name in ['trend_agent', 'volume_agent', 'sentiment_agent']:
                # Sequence models
                sequences = self.create_sequences(features, sequence_length)
                # Align sequences with targets
                training_data[agent_name] = {
                    'X': sequences,
                    'y': aligned_targets[:len(sequences)],
                    'sequence_length': sequence_length
                }
            else:
                # Non-sequence models (use current features)
                training_data[agent_name] = {
                    'X': features[sequence_length:],
                    'y': aligned_targets[:len(features[sequence_length:])],
                    'sequence_length': 1
                }
        
        # Also prepare data for fusion network
        # Combine all agent predictions (would be filled during training)
        training_data['fusion_network'] = {
            'X': None,  # Will be agent predictions
            'y': aligned_targets,
            'agent_names': list(agent_features.keys())
        }
        
        logger.info(f"Prepared training data for {len(training_data)} models")
        return training_data
    
    def create_labels(self, df: pd.DataFrame, horizon: int = 10) -> np.ndarray:
        """
        Create trading labels based on future returns
        
        Args:
            df: DataFrame with price data
            horizon: Prediction horizon in periods
            
        Returns:
            Array of labels (1 for buy, 0 for sell, 0.5 for hold)
        """
        future_returns = df['close'].pct_change(horizon).shift(-horizon)
        
        # Create ternary labels
        labels = np.zeros(len(f