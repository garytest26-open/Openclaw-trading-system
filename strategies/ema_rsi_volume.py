"""
Estrategia #1: EMA Crossover + RSI + Volume Surge
Captura movimientos rápidos con alineación de tendencia, momentum y volumen.
Perfil: Ultra Agresivo
"""
import pandas as pd
import numpy as np
from .day_trading_base import DayTradingStrategy

class EMARSIVolumeStrategy(DayTradingStrategy):
    """
    Estrategia basada en cruces de EMA con confirmación de RSI y volumen.
    
    Señales LONG:
    - EMA 8 cruza arriba de EMA 21
    - RSI > 50 y < 70
    - Volumen > 1.5x promedio
    """
    
    def __init__(self, config: dict = None):
        default_config = {
            'stop_loss_pct': 2.0,      # Ultra agresivo
            'take_profit_pct': 4.0,     # R:R 1:2
            'timeframe': '15m',
            'ema_fast': 8,
            'ema_slow': 21,
            'rsi_period': 14,
            'volume_ma_period': 20,
            'volume_surge_multiplier': 1.5,
            'rsi_min': 50,
            'rsi_max': 70,
            'rsi_min_short': 30,
            'rsi_max_short': 50
        }
        if config:
            default_config.update(config)
        super().__init__(default_config)
        
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcula EMA 8, EMA 21, RSI, y Volume MA."""
        df = df.copy()
        
        # EMAs
        df['ema_fast'] = df['close'].ewm(span=self.config['ema_fast'], adjust=False).mean()
        df['ema_slow'] = df['close'].ewm(span=self.config['ema_slow'], adjust=False).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.config['rsi_period']).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.config['rsi_period']).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Volume MA y surge
        df['volume_ma'] = df['volume'].rolling(window=self.config['volume_ma_period']).mean()
        df['volume_surge'] = df['volume'] > (df['volume_ma'] * self.config['volume_surge_multiplier'])
        
        # VWAP diario (simplificado, asumiendo que tenemos datos intradiarios)
        df['vwap'] = (df['volume'] * (df['high'] + df['low'] + df['close']) / 3).cumsum() / df['volume'].cumsum()
        
        return df
    
    def generate_signal(self, df: pd.DataFrame, index: int) -> str:
        """
        Genera señal basada en cruces de EMA, RSI y volumen.
        """
        if index < 1:
            return 'hold'
            
        current = df.iloc[index]
        previous = df.iloc[index - 1]
        
        # Verificar si tenemos datos válidos
        if pd.isna(current['ema_fast']) or pd.isna(current['rsi']):
            return 'hold'
        
        # Verificar condiciones de salida primero
        if self.in_position:
            if self.check_exit_conditions(current['close']):
                return 'close_long' if self.position_type == 'long' else 'close_short'
            
            # Salida anticipada: cruce contrario o RSI extremo
            if self.position_type == 'long':
                if current['ema_fast'] < current['ema_slow'] or current['rsi'] > 75:
                    return 'close_long'
            elif self.position_type == 'short':
                if current['ema_fast'] > current['ema_slow'] or current['rsi'] < 25:
                    return 'close_short'
                    
            return 'hold'
        
        # Señales de entrada LONG
        ema_cross_up = (previous['ema_fast'] <= previous['ema_slow']) and (current['ema_fast'] > current['ema_slow'])
        rsi_ok_long = self.config['rsi_min'] < current['rsi'] < self.config['rsi_max']
        volume_ok = current['volume_surge']
        above_vwap = current['close'] > current['vwap']
        
        if ema_cross_up and rsi_ok_long and volume_ok and above_vwap:
            return 'buy'
        
        # Señales de entrada SHORT (para estrategia bidireccional)
        ema_cross_down = (previous['ema_fast'] >= previous['ema_slow']) and (current['ema_fast'] < current['ema_slow'])
        rsi_ok_short = self.config['rsi_min_short'] < current['rsi'] < self.config['rsi_max_short']
        below_vwap = current['close'] < current['vwap']
        
        if ema_cross_down and rsi_ok_short and volume_ok and below_vwap:
            return 'sell'
            
        return 'hold'
    
    def get_strategy_name(self) -> str:
        return "EMA_RSI_Volume"
    
    def get_required_history(self) -> int:
        # Necesitamos al menos suficiente historia para calcular todos los indicadores
        return max(self.config['ema_slow'], self.config['rsi_period'], self.config['volume_ma_period']) + 10
