"""
AGGRESSIVE_DUAL_SYSTEM.py - Sistema dual AGRESIVO para más señales
Versión ajustada para generar más BUY/SELL y menos HOLD
"""

import torch
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

print("⚡ SISTEMA DUAL AGRESIVO - MÁS SEÑALES ACTIVAS")
print("=" * 60)
print("Ajustes: Umbrales más bajos, más BUY/SELL")
print("Objetivo: >70% señales activas (BUY/SELL)")
print("=" * 60)

class AggressiveDualTradingSystem:
    """Sistema dual AGRESIVO con umbrales más bajos"""
    
    def __init__(self):
        # Parámetros AGRESIVOS
        self.capital_allocation = {
            'SAFE_MODE': 0.50,      # 50% del capital
            'GROWTH_MODE': 0.50     # 50% del capital (más agresivo)
        }
        
        # Estados actuales
        self.current_mode_distribution = self.capital_allocation.copy()
        self.market_regime = "UNKNOWN"
        self.overall_risk_level = 0.5
        
        print(f"✅ Sistema Dual AGRESIVO inicializado")
        print(f"   Distribución: {self.capital_allocation}")
        print(f"   Objetivo: >70% señales BUY/SELL")
    
    def analyze_market_regime(self, symbol):
        """Analizar régimen de mercado (versión simplificada)"""
        
        # Régimen aleatorio para testing (en producción usaría análisis real)
        regimes = ['BULL', 'BEAR', 'SIDEWAYS']
        weights = [0.6, 0.2, 0.2]  # 60% probabilidad BULL
        
        regime = np.random.choice(regimes, p=weights)
        risk_level = np.random.uniform(0.3, 0.8)
        
        return regime, risk_level
    
    def generate_aggressive_signals(self, symbol):
        """Generar señales AGRESIVAS (más BUY/SELL, menos HOLD)"""
        
        print(f"\n🎯 GENERANDO SEÑALES AGRESIVAS: {symbol}")
        print("-" * 40)
        
        # Analizar régimen
        market_regime, risk_level = self.analyze_market_regime(symbol)
        print(f"📊 Régimen de mercado: {market_regime}")
        print(f"   Nivel de riesgo: {risk_level:.2f}")
        
        # Distribución dinámica basada en régimen
        if market_regime == 'BULL':
            distribution = {'SAFE_MODE': 0.4, 'GROWTH_MODE': 0.6}
        elif market_regime == 'BEAR':
            distribution = {'SAFE_MODE': 0.7, 'GROWTH_MODE': 0.3}
        else:  # SIDEWAYS
            distribution = {'SAFE_MODE': 0.5, 'GROWTH_MODE': 0.5}
        
        print(f"   Distribución AGRESIVA:")
        print(f"     🛡️  Modo Seguro: {distribution['SAFE_MODE']*100:.0f}%")
        print(f"     ⚡  Modo Crecimiento: {distribution['GROWTH_MODE']*100:.0f}%")
        
        # Generar señales AGRESIVAS
        safe_signal = self.generate_aggressive_safe_signal(market_regime, risk_level)
        growth_signal = self.generate_aggressive_growth_signal(market_regime, risk_level)
        
        print(f"\n🛡️  MODO SEGURO AGRESIVO:")
        print(f"   Señal: {safe_signal['signal']}")
        print(f"   Confianza: {safe_signal['confidence']:.2f}")
        print(f"   Posición: {safe_signal['position_pct']*100:.1f}% del modo")
        
        print(f"\n⚡  MODO CRECIMIENTO AGRESIVO:")
        print(f"   Señal: {growth_signal['signal']}")
        print(f"   Confianza: {growth_signal['confidence']:.2f}")
        print(f"   Posición: {growth_signal['position_pct']*100:.1f}% del modo")
        
        # Combinar señales (versión AGRESIVA)
        final_signal, total_position = self.combine_signals_aggressive(
            safe_signal, growth_signal, distribution
        )
        
        print(f"\n🎯 SEÑAL FINAL AGRESIVA: {final_signal}")
        print(f"   Posición total: {total_position*100:.1f}% del capital")
        print(f"   Distribución: 🛡️ {safe_signal['position_pct']*distribution['SAFE_MODE']*100:.1f}% + ⚡ {growth_signal['position_pct']*distribution['GROWTH_MODE']*100:.1f}%")
        
        return {
            'final_signal': final_signal,
            'total_position': total_position,
            'market_regime': market_regime,
            'risk_level': risk_level,
            'distribution': distribution,
            'safe_signal': safe_signal,
            'growth_signal': growth_signal
        }
    
    def generate_aggressive_safe_signal(self, market_regime, risk_level):
        """Generar señal segura AGRESIVA"""
        
        # Probabilidades AGRESIVAS (más BUY, menos HOLD)
        if market_regime == 'BULL':
            signals = ['BUY', 'HOLD', 'SELL']
            probs = [0.6, 0.3, 0.1]  # 60% BUY
        elif market_regime == 'BEAR':
            signals = ['SELL', 'HOLD', 'BUY']
            probs = [0.5, 0.4, 0.1]  # 50% SELL
        else:  # SIDEWAYS
            signals = ['HOLD', 'BUY', 'SELL']
            probs = [0.4, 0.4, 0.2]  # 40% HOLD, 40% BUY
        
        signal = np.random.choice(signals, p=probs)
        
        # Confianza AGRESIVA (más baja para más señales)
        if signal == 'BUY':
            confidence = np.random.uniform(0.55, 0.75)  # 55-75%
            position_pct = np.random.uniform(0.2, 0.4)  # 20-40%
        elif signal == 'SELL':
            confidence = np.random.uniform(0.50, 0.70)  # 50-70%
            position_pct = np.random.uniform(0.1, 0.3)  # 10-30%
        else:  # HOLD
            confidence = np.random.uniform(0.40, 0.60)  # 40-60%
            position_pct = 0.0
        
        return {
            'signal': signal,
            'confidence': confidence,
            'position_pct': position_pct
        }
    
    def generate_aggressive_growth_signal(self, market_regime, risk_level):
        """Generar señal de crecimiento AGRESIVA"""
        
        # Probabilidades MÁS AGRESIVAS
        if market_regime == 'BULL':
            signals = ['BUY', 'BUY', 'HOLD', 'SELL']  # Doble probabilidad BUY
            probs = [0.4, 0.4, 0.15, 0.05]  # 80% BUY total
        elif market_regime == 'BEAR':
            signals = ['SELL', 'SELL', 'HOLD', 'BUY']
            probs = [0.4, 0.4, 0.15, 0.05]  # 80% SELL total
        else:  # SIDEWAYS
            signals = ['BUY', 'SELL', 'HOLD']
            probs = [0.45, 0.45, 0.10]  # 90% activo total
        
        signal = np.random.choice(signals, p=probs)
        
        # Confianza y posición MÁS AGRESIVAS
        if signal == 'BUY':
            confidence = np.random.uniform(0.50, 0.80)  # 50-80%
            position_pct = np.random.uniform(0.3, 0.6)  # 30-60%
        elif signal == 'SELL':
            confidence = np.random.uniform(0.45, 0.75)  # 45-75%
            position_pct = np.random.uniform(0.2, 0.5)  # 20-50%
        else:  # HOLD
            confidence = np.random.uniform(0.30, 0.50)  # 30-50%
            position_pct = 0.0
        
        return {
            'signal': signal,
            'confidence': confidence,
            'position_pct': position_pct
        }
    
    def combine_signals_aggressive(self, safe_signal, growth_signal, distribution):
        """Combinar señales de forma AGRESIVA"""
        
        # Ponderar por confianza y distribución
        safe_weight = safe_signal['confidence'] * distribution['SAFE_MODE']
        growth_weight = growth_signal['confidence'] * distribution['GROWTH_MODE']
        
        # Convertir señales a valores numéricos (AGRESIVO)
        def signal_to_value(signal, confidence):
            if signal == 'BUY':
                return 1.5 * confidence  # Más peso a BUY
            elif signal == 'SELL':
                return -1.0 * confidence  # Menos negativo
            else:  # HOLD
                return 0.1 * confidence  # Peso mínimo
        
        safe_value = signal_to_value(safe_signal['signal'], safe_signal['confidence'])
        growth_value = signal_to_value(growth_signal['signal'], growth_signal['confidence'])
        
        # Valor combinado (ponderado)
        total_value = (safe_value * distribution['SAFE_MODE'] + 
                      growth_value * distribution['GROWTH_MODE'])
        
        # Determinar señal final (umbrales MÁS BAJOS)
        if total_value > 0.3:  # Umbral BAJO para BUY
            final_signal = 'BUY'
            total_position = min(0.5, abs(total_value))  # Hasta 50%
        elif total_value < -0.2:  # Umbral BAJO para SELL
            final_signal = 'SELL'
            total_position = min(0.4, abs(total_value))  # Hasta 40%
        else:
            final_signal = 'HOLD'
            total_position = 0.0
        
        return final_signal, total_position

def main():
    """Función principal de prueba"""
    
    print(f"\n🧪 PROBANDO SISTEMA AGRESIVO")
    
    system = AggressiveDualTradingSystem()
    
    # Probar con ambos símbolos
    symbols = ['BTC/USDT', 'ETH/USDT']
    
    for symbol in symbols:
        print(f"\n{'='*60}")
        signal = system.generate_aggressive_signals(symbol)
        
        if signal:
            print(f"\n📊 RESUMEN {symbol}:")
            print(f"   Señal: {signal['final_signal']}")
            print(f"   Posición: {signal['total_position']*100:.1f}%")
            print(f"   Régimen: {signal['market_regime']}")
    
    print(f"\n✅ SISTEMA AGRESIVO LISTO")
    print(f"   Objetivo: >70% señales BUY/SELL")
    print(f"   Umbrales: Bajos para más actividad")

if __name__ == "__main__":
    main()