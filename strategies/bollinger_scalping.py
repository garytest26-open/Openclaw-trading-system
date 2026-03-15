"""
Estrategia #3: Scalping con Bollinger Bands + MACD
Scalping rápido usando bandas de volatilidad y divergencias.
Perfil: Ultra Agresivo
"""
import pandas as pd
import numpy as np
from .day_trading_base import DayTradingStrategy

class BollingerScalpingStrategy(DayTradingStrategy):
    """
    Estrategia de scalping con Bollinger Bands y MACD.
    
    Señales LONG:
    - Precio toca banda inferior de Bollinger
    - MACD histograma cambia a positivo
    - Stochastic RSI < 20 (sobreventa)
    """
    
    def __init__(self, config: dict = None):
        default_config = {
            'stop_loss_pct': 1.2,       # Muy ajustado para scalping
            'take_profit_pct': 2.4,     # R:R 1:2
            'timeframe': '5m',
            'bb_period': 20,
            'bb_std': 2,
            'macd_fast': 12,
            'macd_slow': 26,
            'macd_signal': 9,
            'stoch_rsi_period': 14,
            'stoch_rsi_smooth': 3,
            'stoch_oversold': 20,
            'stoch_overbought': 80
        }
        if config:
            default_config.update(config)
        super().__init__(default_config)
        
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcula Bollinger Bands, MACD y Stochastic RSI."""
        df = df.copy()
        
        # Bollinger Bands
        df['bb_middle'] = df['close'].rolling(window=self.config['bb_period']).mean()
        bb_std = df['close'].rolling(window=self.config['bb_period']).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * self.config['bb_std'])
        df['bb_lower'] = df['bb_middle'] - (bb_std * self.config['bb_std'])
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
        
        # MACD
        ema_fast = df['close'].ewm(span=self.config['macd_fast'], adjust=False).mean()
        ema_slow = df['close'].ewm(span=self.config['macd_slow'], adjust=False).mean()
        df['macd'] = ema_fast - ema_slow
        df['macd_signal'] = df['macd'].ewm(span=self.config['macd_signal'], adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # Stochastic RSI
        # Primero calculamos RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.config['stoch_rsi_period']).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.config['stoch_rsi_period']).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        # Luego aplicamos estocástico al RSI
        rsi_min = rsi.rolling(window=self.config['stoch_rsi_period']).min()
        rsi_max = rsi.rolling(window=self.config['stoch_rsi_period']).max()
        stoch_rsi = 100 * (rsi - rsi_min) / (rsi_max - rsi_min)
        df['stoch_rsi'] = stoch_rsi.rolling(window=self.config['stoch_rsi_smooth']).mean()
        
        return df
    
    def generate_signal(self, df: pd.DataFrame, index: int) -> str:
        """
        Genera señal basada en Bollinger Bands, MACD y Stochastic RSI.
        """
        if index < 1:
            return 'hold'
            
        current = df.iloc[index]
        previous = df.iloc[index - 1]
        
        # Verificar datos válidos
        if pd.isna(current['bb_lower']) or pd.isna(current['macd_hist']) or pd.isna(current['stoch_rsi']):
            return 'hold'
        
        # Verificar condiciones de salida
        if self.in_position:
            if self.check_exit_conditions(current['close']):
                return 'close_long' if self.position_type == 'long' else 'close_short'
            
            # Salida rápida: precio vuelve a banda media
            if self.position_type == 'long':
                if current['close'] >= current['bb_middle']:
                    return 'close_long'
            elif self.position_type == 'short':
                if current['close'] <= current['bb_middle']:
                    return 'close_short'
                    
            return 'hold'
        
        # Señal LONG: toca banda inferior con reversión
        touching_lower = current['close'] <= current['bb_lower'] * 1.005  # Dentro del 0.5%
        macd_turning_up = (previous['macd_hist'] <= 0) and (current['macd_hist'] > 0)
        oversold = current['stoch_rsi'] < self.config['stoch_oversold']
        
        if touching_lower and macd_turning_up and oversold:
            return 'buy'
        
        # Señal SHORT: toca banda superior con reversión
        touching_upper = current['close'] >= current['bb_upper'] * 0.995  # Dentro del 0.5%
        macd_turning_down = (previous['macd_hist'] >= 0) and (current['macd_hist'] < 0)
        overbought = current['stoch_rsi'] > self.config['stoch_overbought']
        
        if touching_upper and macd_turning_down and overbought:
            return 'sell'
            
        return 'hold'
    
    def get_strategy_name(self) -> str:
        return "Bollinger_Scalping"
    
    def get_required_history(self) -> int:
        return max(self.config['bb_period'], self.config['macd_slow'], self.config['stoch_rsi_period']) + 20
