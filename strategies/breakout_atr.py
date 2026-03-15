"""
Estrategia #4: Breakout Intradiario + ATR
Captura breakouts de rangos con volatilidad confirmada.
Perfil: Ultra Agresivo
"""
import pandas as pd
import numpy as np
from .day_trading_base import DayTradingStrategy

class BreakoutATRStrategy(DayTradingStrategy):
    """
    Estrategia basada en breakouts con ATR para gestión dinámica de riesgo.
    
    Señales LONG:
    - Precio rompe máximo de N horas
    - ATR > promedio (alta volatilidad)
    - Volumen > 2x promedio
    - Cierre confirma el breakout
    """
    
    def __init__(self, config: dict = None):
        default_config = {
            'stop_loss_atr_multiplier': 2.5,  # Stop loss dinámico basado en ATR
            'take_profit_atr_multiplier': 5.0,  # R:R 1:2
            'timeframe': '15m',
            'atr_period': 14,
            'atr_ma_period': 20,
            'range_lookback_periods': 16,  # 4 horas en 15m
            'volume_ma_period': 20,
            'volume_surge_multiplier': 2.0,
            'breakout_confirmation_pct': 0.001  # 0.1% arriba del nivel
        }
        if config:
            default_config.update(config)
        super().__init__(default_config)
        self.breakout_level = None
        self.current_stop_loss = None
        self.current_take_profit = None
        
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcula ATR, rangos de trading y volume."""
        df = df.copy()
        
        # ATR (Average True Range)
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        df['atr'] = true_range.rolling(window=self.config['atr_period']).mean()
        df['atr_ma'] = df['atr'].rolling(window=self.config['atr_ma_period']).mean()
        
        # Rango de trading (high/low de últimas N velas)
        df['range_high'] = df['high'].rolling(window=self.config['range_lookback_periods']).max()
        df['range_low'] = df['low'].rolling(window=self.config['range_lookback_periods']).min()
        df['range_width'] = df['range_high'] - df['range_low']
        
        # Volume
        df['volume_ma'] = df['volume'].rolling(window=self.config['volume_ma_period']).mean()
        df['volume_surge'] = df['volume'] > (df['volume_ma'] * self.config['volume_surge_multiplier'])
        
        return df
    
    def generate_signal(self, df: pd.DataFrame, index: int) -> str:
        """
        Genera señal basada en breakouts con ATR.
        """
        if index < 1:
            return 'hold'
            
        current = df.iloc[index]
        previous = df.iloc[index - 1]
        
        # Verificar datos válidos
        if pd.isna(current['atr']) or pd.isna(current['range_high']):
            return 'hold'
        
        # Verificar condiciones de salida
        if self.in_position:
            # Usar stop loss y take profit dinámicos basados en ATR
            if self.position_type == 'long':
                if current['close'] <= self.current_stop_loss:
                    return 'close_long'
                if current['close'] >= self.current_take_profit:
                    return 'close_long'
            elif self.position_type == 'short':
                if current['close'] >= self.current_stop_loss:
                    return 'close_short'
                if current['close'] <= self.current_take_profit:
                    return 'close_short'
                    
            # Salida si se forma un nuevo rango (reversión)
            if self.position_type == 'long' and current['close'] < previous['range_low']:
                return 'close_long'
            elif self.position_type == 'short' and current['close'] > previous['range_high']:
                return 'close_short'
                
            return 'hold'
        
        # Condiciones generales para breakout
        high_volatility = current['atr'] > current['atr_ma']
        volume_surge = current['volume_surge']
        
        # Señal LONG: breakout alcista
        # El precio rompe el máximo del rango anterior
        breakout_up = current['close'] > previous['range_high'] * (1 + self.config['breakout_confirmation_pct'])
        # Confirmación: la vela cierra arriba del nivel de breakout
        confirmed_close = current['close'] > previous['range_high']
        
        if breakout_up and confirmed_close and high_volatility and volume_surge:
            self.breakout_level = previous['range_high']
            # Stop loss dinámico: N x ATR debajo del precio
            self.current_stop_loss = current['close'] - (current['atr'] * self.config['stop_loss_atr_multiplier'])
            # Take profit dinámico: M x ATR arriba del precio
            self.current_take_profit = current['close'] + (current['atr'] * self.config['take_profit_atr_multiplier'])
            return 'buy'
        
        # Señal SHORT: breakout bajista
        breakout_down = current['close'] < previous['range_low'] * (1 - self.config['breakout_confirmation_pct'])
        confirmed_close_down = current['close'] < previous['range_low']
        
        if breakout_down and confirmed_close_down and high_volatility and volume_surge:
            self.breakout_level = previous['range_low']
            # Stop loss dinámico
            self.current_stop_loss = current['close'] + (current['atr'] * self.config['stop_loss_atr_multiplier'])
            # Take profit dinámico
            self.current_take_profit = current['close'] - (current['atr'] * self.config['take_profit_atr_multiplier'])
            return 'sell'
            
        return 'hold'
    
    def check_exit_conditions(self, current_price: float) -> bool:
        """Override para usar stop loss/take profit dinámicos basados en ATR."""
        # Esta estrategia usa stops dinámicos en generate_signal
        return False
    
    def get_strategy_name(self) -> str:
        return "Breakout_ATR"
    
    def get_required_history(self) -> int:
        return max(self.config['atr_period'], self.config['atr_ma_period'], 
                   self.config['range_lookback_periods'], self.config['volume_ma_period']) + 10
