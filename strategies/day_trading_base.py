"""
Clase base abstracta para estrategias de day trading.
Proporciona interfaz común para todas las estrategias.
"""
from abc import ABC, abstractmethod
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional

class DayTradingStrategy(ABC):
    """Clase base para todas las estrategias de day trading."""
    
    def __init__(self, config: Dict):
        """
        Inicializa la estrategia.
        
        Args:
            config: Diccionario con configuración de la estrategia
                - stop_loss_pct: Porcentaje de stop loss
                - take_profit_pct: Porcentaje de take profit
                - timeframe: Timeframe a usar (5m, 15m, etc.)
        """
        self.config = config
        self.stop_loss_pct = config.get('stop_loss_pct', 2.0)
        self.take_profit_pct = config.get('take_profit_pct', 4.0)
        self.timeframe = config.get('timeframe', '15m')
        self.in_position = False
        self.entry_price = 0.0
        self.position_type = None  # 'long' or 'short'
        
    @abstractmethod
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calcula todos los indicadores técnicos necesarios.
        
        Args:
            df: DataFrame con datos OHLCV
            
        Returns:
            DataFrame con indicadores añadidos
        """
        pass
    
    @abstractmethod
    def generate_signal(self, df: pd.DataFrame, index: int) -> str:
        """
        Genera señal de trading basada en indicadores.
        
        Args:
            df: DataFrame con indicadores calculados
            index: Índice de la vela actual
            
        Returns:
            'buy', 'sell', 'close_long', 'close_short', o 'hold'
        """
        pass
    
    def check_exit_conditions(self, current_price: float) -> bool:
        """
        Verifica condiciones de salida (stop-loss, take-profit).
        
        Args:
            current_price: Precio actual
            
        Returns:
            True si debe cerrar la posición
        """
        if not self.in_position:
            return False
            
        if self.position_type == 'long':
            pnl_pct = ((current_price - self.entry_price) / self.entry_price) * 100
        else:  # short
            pnl_pct = ((self.entry_price - current_price) / self.entry_price) * 100
            
        # Stop loss
        if pnl_pct <= -self.stop_loss_pct:
            return True
            
        # Take profit
        if pnl_pct >= self.take_profit_pct:
            return True
            
        return False
    
    def enter_position(self, position_type: str, price: float):
        """Registra entrada en posición."""
        self.in_position = True
        self.position_type = position_type
        self.entry_price = price
        
    def exit_position(self):
        """Registra salida de posición."""
        self.in_position = False
        self.position_type = None
        self.entry_price = 0.0
        
    def get_position_info(self) -> Dict:
        """Retorna información de la posición actual."""
        return {
            'in_position': self.in_position,
            'position_type': self.position_type,
            'entry_price': self.entry_price,
            'stop_loss_pct': self.stop_loss_pct,
            'take_profit_pct': self.take_profit_pct
        }
    
    @abstractmethod
    def get_strategy_name(self) -> str:
        """Retorna el nombre de la estrategia."""
        pass
    
    @abstractmethod
    def get_required_history(self) -> int:
        """Retorna el número mínimo de velas necesarias."""
        pass
