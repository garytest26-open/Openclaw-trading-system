"""
Estrategia #2: VWAP Bounce + Momentum
Opera rebotes del VWAP con confirmación de MACD y ADX.
Perfil: Ultra Agresivo
"""
import pandas as pd
import numpy as np
from .day_trading_base import DayTradingStrategy

class VWAPMomentumStrategy(DayTradingStrategy):
    """
    Estrategia basada en rebotes del VWAP con MACD y ADX.
    
    Señales LONG:
    - Precio rebota desde VWAP hacia arriba
    - MACD línea de señal positiva
    - ADX > 25 (tendencia fuerte)
    """
    
    def __init__(self, config: dict = None):
        default_config = {
            'stop_loss_pct': 1.5,       # Muy ajustado
            'take_profit_pct': 3.0,     # R:R 1:2
            'timeframe': '5m',          # Timeframe más agresivo
            'macd_fast': 12,
            'macd_slow': 26,
            'macd_signal': 9,
            'adx_period': 14,
            'adx_threshold': 25,
            'vwap_touch_threshold': 0.002,  # 0.2% cerca del VWAP
            'trailing_stop_activation': 1.5  # Activar trailing después de 1.5% ganancia
        }
        if config:
            default_config.update(config)
        super().__init__(default_config)
        self.trailing_stop_active = False
        self.highest_price = 0.0
        
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcula VWAP, MACD y ADX."""
        df = df.copy()
        
        # VWAP (reinicia diariamente si tenemos timestamp)
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        df['vwap'] = (typical_price * df['volume']).cumsum() / df['volume'].cumsum()
        
        # MACD
        ema_fast = df['close'].ewm(span=self.config['macd_fast'], adjust=False).mean()
        ema_slow = df['close'].ewm(span=self.config['macd_slow'], adjust=False).mean()
        df['macd'] = ema_fast - ema_slow
        df['macd_signal'] = df['macd'].ewm(span=self.config['macd_signal'], adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # ADX (Average Directional Index)
        high_diff = df['high'].diff()
        low_diff = -df['low'].diff()
        
        plus_dm = high_diff.where((high_diff > low_diff) & (high_diff > 0), 0)
        minus_dm = low_diff.where((low_diff > high_diff) & (low_diff > 0), 0)
        
        tr1 = df['high'] - df['low']
        tr2 = abs(df['high'] - df['close'].shift())
        tr3 = abs(df['low'] - df['close'].shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        atr = tr.rolling(window=self.config['adx_period']).mean()
        plus_di = 100 * (plus_dm.rolling(window=self.config['adx_period']).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window=self.config['adx_period']).mean() / atr)
        
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        df['adx'] = dx.rolling(window=self.config['adx_period']).mean()
        
        # Distancia del precio al VWAP
        df['vwap_distance'] = (df['close'] - df['vwap']) / df['vwap']
        
        return df
    
    def generate_signal(self, df: pd.DataFrame, index: int) -> str:
        """
        Genera señal basada en rebotes del VWAP con MACD y ADX.
        """
        if index < 2:
            return 'hold'
            
        current = df.iloc[index]
        previous = df.iloc[index - 1]
        
        # Verificar datos válidos
        if pd.isna(current['vwap']) or pd.isna(current['macd']) or pd.isna(current['adx']):
            return 'hold'
        
        # Verificar condiciones de salida
        if self.in_position:
            # Actualizar trailing stop para LONG
            if self.position_type == 'long' and self.trailing_stop_active:
                if current['close'] > self.highest_price:
                    self.highest_price = current['close']
                # Trailing stop: cierra si cae 1% desde el máximo
                if current['close'] < self.highest_price * 0.99:
                    return 'close_long'
            
            if self.check_exit_conditions(current['close']):
                return 'close_long' if self.position_type == 'long' else 'close_short'
            
            # Activar trailing stop si hay suficiente ganancia
            if self.position_type == 'long' and not self.trailing_stop_active:
                pnl_pct = ((current['close'] - self.entry_price) / self.entry_price) * 100
                if pnl_pct >= self.config['trailing_stop_activation']:
                    self.trailing_stop_active = True
                    self.highest_price = current['close']
                    
            return 'hold'
        
        # Condiciones generales
        strong_trend = current['adx'] > self.config['adx_threshold']
        macd_bullish = current['macd'] > current['macd_signal']
        macd_bearish = current['macd'] < current['macd_signal']
        
        # Señal LONG: rebote desde VWAP hacia arriba
        near_vwap_from_above = (-self.config['vwap_touch_threshold'] <= current['vwap_distance'] <= 0)
        bouncing_up = current['close'] > previous['close']
        
        if near_vwap_from_above and bouncing_up and macd_bullish and strong_trend:
            self.trailing_stop_active = False
            return 'buy'
        
        # Señal SHORT: rebote desde VWAP hacia abajo
        near_vwap_from_below = (0 <= current['vwap_distance'] <= self.config['vwap_touch_threshold'])
        bouncing_down = current['close'] < previous['close']
        
        if near_vwap_from_below and bouncing_down and macd_bearish and strong_trend:
            return 'sell'
            
        return 'hold'
    
    def get_strategy_name(self) -> str:
        return "VWAP_Momentum"
    
    def get_required_history(self) -> int:
        return max(self.config['macd_slow'], self.config['adx_period']) + 20
