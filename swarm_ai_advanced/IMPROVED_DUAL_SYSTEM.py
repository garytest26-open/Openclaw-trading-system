"""
IMPROVED_DUAL_SYSTEM.py - Sistema dual MEJORADO basado en backtesting
Ajustes para mejorar performance y rentabilidad
"""

import torch
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

print("🚀 SISTEMA DUAL MEJORADO - BASADO EN BACKTESTING")
print("=" * 60)
print("Ajustes: Más señales BUY, mejor rentabilidad")
print("Objetivo: Retorno positivo en backtesting")
print("=" * 60)

class ImprovedDualTradingSystem:
    """Sistema dual MEJORADO con ajustes basados en backtesting"""
    
    def __init__(self):
        # Parámetros MEJORADOS basados en backtesting
        self.capital_allocation = {
            'SAFE_MODE': 0.60,      # 60% del capital (antes 70%)
            'GROWTH_MODE': 0.40     # 40% del capital (antes 30%)
        }
        
        # Estados actuales
        self.current_mode_distribution = self.capital_allocation.copy()
        self.market_regime = "UNKNOWN"
        self.overall_risk_level = 0.5
        
        # Sistemas individuales MEJORADOS
        self.safe_system = ImprovedSafeTradingSystem()
        self.growth_system = ImprovedGrowthTradingSystem()
        
        print(f"✅ Sistema Dual MEJORADO inicializado")
        print(f"   Distribución MEJORADA: {self.capital_allocation}")
        print(f"   Modo Seguro MEJORADO: {self.safe_system.get_info()}")
        print(f"   Modo Crecimiento MEJORADO: {self.growth_system.get_info()}")
        
        # Insights del backtesting
        print(f"\n📊 INSIGHTS DEL BACKTESTING:")
        print(f"   Problema identificado: 78% HOLD, trades no rentables")
        print(f"   Solución: Más señales BUY, mejores umbrales")
        print(f"   Objetivo: >50% trades rentables, retorno positivo")
    
    def analyze_market_for_allocation(self):
        """Analizar mercado con parámetros MEJORADOS"""
        try:
            # Analizar BTC como proxy del mercado
            ticker = yf.Ticker('BTC-USD')
            df = ticker.history(period='20d', interval='1d')  # Período más corto
            
            if df.empty or len(df) < 15:
                return "UNKNOWN", 0.5
            
            # Calcular métricas MEJORADAS
            returns = df['Close'].pct_change().dropna()
            avg_return = returns.mean() * 252
            
            # EMA para tendencia más sensible
            ema_10 = df['Close'].ewm(span=10, adjust=False).mean()
            ema_20 = df['Close'].ewm(span=20, adjust=False).mean()
            
            # Determinar régimen (umbrales MEJORADOS)
            if avg_return > 0.08 and ema_10.iloc[-1] > ema_20.iloc[-1]:  # >8% y tendencia alcista
                regime = "BULL"
                risk_level = 0.7
                
            elif avg_return < -0.06 or ema_10.iloc[-1] < ema_20.iloc[-1] * 0.95:  # < -6% o tendencia bajista
                regime = "BEAR"
                risk_level = 0.3
                
            else:
                regime = "SIDEWAYS"
                risk_level = 0.6  # Más riesgo en lateral (antes 0.5)
            
            # Ajustar distribución MEJORADA
            if regime == "BULL":
                # MUCHO más crecimiento en alcista
                self.current_mode_distribution = {
                    'SAFE_MODE': 0.30,      # 30% seguro (antes 40%)
                    'GROWTH_MODE': 0.70     # 70% crecimiento (antes 60%)
                }
                
            elif regime == "BEAR":
                # Menos seguro en bajista (más oportunidades)
                self.current_mode_distribution = {
                    'SAFE_MODE': 0.70,      # 70% seguro (antes 75%)
                    'GROWTH_MODE': 0.30     # 30% crecimiento (antes 25%)
                }
                
            else:  # SIDEWAYS
                # Más crecimiento en lateral (nuevo enfoque)
                self.current_mode_distribution = {
                    'SAFE_MODE': 0.50,      # 50% seguro (antes 60%)
                    'GROWTH_MODE': 0.50     # 50% crecimiento (antes 40%)
                }
            
            self.market_regime = regime
            self.overall_risk_level = risk_level
            
            return regime, risk_level
            
        except Exception as e:
            print(f"⚠️  Error analizando mercado: {e}")
            return "UNKNOWN", 0.5
    
    def generate_improved_signals(self, symbol='BTC-USD'):
        """Generar señales MEJORADAS"""
        
        print(f"\n🎯 GENERANDO SEÑALES MEJORADAS: {symbol}")
        print("-" * 50)
        
        # 1. Analizar mercado para distribución MEJORADA
        regime, risk_level = self.analyze_market_for_allocation()
        print(f"📊 Régimen de mercado: {regime}")
        print(f"   Nivel de riesgo: {risk_level:.2f}")
        print(f"   Distribución MEJORADA:")
        print(f"     🛡️  Modo Seguro: {self.current_mode_distribution['SAFE_MODE']*100:.0f}%")
        print(f"     ⚡  Modo Crecimiento: {self.current_mode_distribution['GROWTH_MODE']*100:.0f}%")
        
        # 2. Generar señal modo seguro MEJORADO
        print(f"\n🛡️  MODO SEGURO MEJORADO:")
        safe_signal = self.safe_system.generate_signal(symbol)
        print(f"   Señal: {safe_signal['signal']}")
        print(f"   Confianza: {safe_signal['confidence']:.2f}")
        print(f"   Posición: {safe_signal['position_size']*100:.1f}% del modo")
        
        # 3. Generar señal modo crecimiento MEJORADO
        print(f"\n⚡  MODO CRECIMIENTO MEJORADO:")
        growth_signal = self.growth_system.generate_signal(symbol)
        print(f"   Señal: {growth_signal['signal']}")
        print(f"   Confianza: {growth_signal['confidence']:.2f}")
        print(f"   Posición: {growth_signal['position_size']*100:.1f}% del modo")
        
        # 4. Combinar señales MEJORADO (más peso a crecimiento)
        final_signal = self.combine_improved_signals(safe_signal, growth_signal)
        
        # 5. Calcular posición total MEJORADA
        total_position = self.calculate_improved_position(safe_signal, growth_signal)
        
        print(f"\n🎯 SEÑAL FINAL MEJORADA: {final_signal}")
        print(f"   Posición total: {total_position*100:.1f}% del capital")
        print(f"   Distribución: {self.get_position_breakdown(safe_signal, growth_signal)}")
        
        return {
            'symbol': symbol,
            'final_signal': final_signal,
            'total_position': total_position,
            'market_regime': regime,
            'risk_level': risk_level,
            'distribution': self.current_mode_distribution.copy(),
            'safe_signal': safe_signal,
            'growth_signal': growth_signal
        }
    
    def combine_improved_signals(self, safe_signal, growth_signal):
        """Combinar señales con enfoque MEJORADO"""
        
        safe_action = safe_signal['signal']
        safe_conf = safe_signal['confidence']
        growth_action = growth_signal['signal']
        growth_conf = growth_signal['confidence']
        
        # Ponderar MEJORADO (más crecimiento, menos seguro)
        safe_weight = self.current_mode_distribution['SAFE_MODE'] * 0.6  # Reducido
        growth_weight = self.current_mode_distribution['GROWTH_MODE'] * 1.4  # Aumentado
        
        # Normalizar
        total_weight = safe_weight + growth_weight
        safe_weight = safe_weight / total_weight
        growth_weight = growth_weight / total_weight
        
        # Convertir a valores (MEJORADO para más BUY)
        def action_to_value_improved(action, confidence):
            if action == "BUY":
                return 1.2 * confidence  # Más peso a BUY
            elif action == "SELL":
                return -0.8 * confidence  # Menos peso a SELL
            else:  # HOLD
                return 0
        
        safe_value = action_to_value_improved(safe_action, safe_conf)
        growth_value = action_to_value_improved(growth_action, growth_conf)
        
        # Combinar (MEJORADO)
        combined = (safe_value * safe_weight + growth_value * growth_weight)
        
        # Determinar señal (umbrales MEJORADOS para más BUY)
        if combined > 0.10:  # 0.10 (antes 0.15) → Más fácil BUY
            return "BUY"
        elif combined < -0.12:  # -0.12 (antes -0.15) → Más difícil SELL
            return "SELL"
        else:
            return "HOLD"
    
    def calculate_improved_position(self, safe_signal, growth_signal):
        """Calcular posición MEJORADA"""
        
        safe_position = safe_signal['position_size'] * self.current_mode_distribution['SAFE_MODE']
        growth_position = growth_signal['position_size'] * self.current_mode_distribution['GROWTH_MODE']
        
        total = safe_position + growth_position
        
        # Limitar MEJORADO (más agresivo en BUY, menos en SELL)
        if safe_signal['signal'] == "BUY" or growth_signal['signal'] == "BUY":
            return min(total, 0.35)  # 35% máximo en BUY
        else:
            return min(total, 0.20)  # 20% máximo en SELL/HOLD
    
    def get_position_breakdown(self, safe_signal, growth_signal):
        """Obtener desglose de posición"""
        
        safe_portion = safe_signal['position_size'] * self.current_mode_distribution['SAFE_MODE'] * 100
        growth_portion = growth_signal['position_size'] * self.current_mode_distribution['GROWTH_MODE'] * 100
        
        return f"🛡️ {safe_portion:.1f}% + ⚡ {growth_portion:.1f}%"

class ImprovedSafeTradingSystem:
    """Sistema seguro MEJORADO (menos conservador)"""
    
    def __init__(self):
        self.name = "🛡️ Modo Seguro MEJORADO"
        self.description = "Conservador pero con más oportunidades"
        self.max_position_size = 0.15  # 15% (antes 10%)
        self.min_confidence = 0.7      # 70% (antes 80%)
        
    def get_info(self):
        return f"{self.name}: {self.description}"
    
    def generate_signal(self, symbol):
        """Generar señal MEJORADA (menos conservadora)"""
        
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period='7d', interval='1h')  # Más datos
            
            if df.empty:
                return self._default_safe_signal()
            
            # Indicadores MEJORADOS
            current_price = df['Close'].iloc[-1]
            ema_12 = df['Close'].ewm(span=12, adjust=False).mean().iloc[-1]
            ema_26 = df['Close'].ewm(span=26, adjust=False).mean().iloc[-1]
            
            price_vs_ema12 = current_price / ema_12
            ema_cross = ema_12 / ema_26
            
            # Señal MEJORADA (más BUY opportunities)
            if price_vs_ema12 < 0.96 and ema_cross > 0.98:  # Precio 4% debajo EMA12, EMAs cercanas
                signal = "BUY"
                confidence = 0.75
                position_size = 0.08  # 8%
                
            elif price_vs_ema12 > 1.04 and ema_cross < 1.02:  # Precio 4% arriba EMA12
                signal = "SELL"
                confidence = 0.70
                position_size = 0.06  # 6%
                
            elif 0.98 <= price_vs_ema12 <= 1.02:  # Precio cerca de EMA12
                signal = "BUY"  # ¡NUEVO! BUY en consolidación
                confidence = 0.65
                position_size = 0.05  # 5%
                
            else:
                signal = "HOLD"
                confidence = 0.85  # Menos confianza en HOLD
                position_size = 0.0
            
            return {
                'signal': signal,
                'confidence': confidence,
                'position_size': min(position_size, self.max_position_size),
                'reason': f"Precio/EMA12: {price_vs_ema12:.3f}, EMA12/26: {ema_cross:.3f}"
            }
            
        except Exception as e:
            print(f"⚠️  Error modo seguro mejorado: {e}")
            return self._default_safe_signal()
    
    def _default_safe_signal(self):
        return {
            'signal': "HOLD",
            'confidence': 0.8,  # Menos confianza por defecto
            'position_size': 0.0,
            'reason': "Modo seguro mejorado por defecto"
        }

class ImprovedGrowthTradingSystem:
    """Sistema crecimiento MEJORADO (más BUY, mejor rentabilidad)"""
    
    def __init__(self):
        self.name = "⚡ Modo Crecimiento MEJORADO"
        self.description = "Más activo, enfoque en BUY opportunities"
        self.max_position_size = 0.40  # 40% (antes 35%)
        self.min_confidence = 0.55     # 55% (antes 50%)
        
        print(f"   ⚡ Enfoque: Más señales BUY, mejor rentabilidad")
        
    def get_info(self):
        return f"{self.name}: {self.description}"
    
    def generate_signal(self, symbol):
        """Generar señal MEJORADA (más BUY, mejor filtrado)"""
        
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period='15d', interval='1h')  # Más datos
            
            if df.empty or len(df) < 100:
                return self._default_growth_signal()
            
            # Calcular indicadores MEJORADOS
            signals = {
                'rsi': self._calculate_rsi_improved(df),
                'macd': self._calculate_macd_improved(df),
                'trend': self._calculate_trend_improved(df),
                'volume': self._calculate_volume_improved(df),
                'momentum': self._calculate_momentum_improved(df),
                'support': self._calculate_support_improved(df),
                'volatility': self._calculate_volatility_signal(df)  # Nuevo
            }
            
            # Contar señales (MEJORADO para más BUY)
            buy_signals = sum(1 for s in signals.values() if s == "BUY")
            sell_signals = sum(1 for s in signals.values() if s == "SELL")
            total_signals = len(signals)
            
            print(f"   Señales MEJORADAS: BUY={buy_signals}, SELL={sell_signals}, TOTAL={total_signals}")
            
            # Lógica MEJORADA (más BUY, menos SELL)
            if buy_signals >= 3:  # 3 de 7 (42%)
                signal = "BUY"
                confidence = 0.75 + (buy_signals / total_signals * 0.2)
                position_size = 0.25 + (buy_signals / total_signals * 0.15)
                
            elif buy_signals >= 2 and sell_signals <= 1:  # 2+ BUY, 0-1 SELL
                signal = "BUY"
                confidence = 0.65
                position_size = 0.18
                
            elif sell_signals >= 4:  # 4+ SELL (alto)
                signal = "SELL"
                confidence = 0.70 + (sell_signals / total_signals * 0.2)
                position_size = 0.15 + (sell_signals / total_signals * 0.1)
                
            elif sell_signals >= 3 and buy_signals <= 1:  # 3+ SELL, 0-1 BUY
                signal = "SELL"
                confidence = 0.60
                position_size = 0.12
                
            else:
                signal = "HOLD"
                confidence = 0.4  # Baja confianza en HOLD
                position_size = 0.0
            
            # Limitar posición
            position_size = min(position_size, self.max_position_size)
            
            return {
                'signal': signal,
                'confidence': confidence,
                'position_size': position_size,
                'signals_breakdown': signals,
                'reason': f"BUY:{buy_signals}/SELL:{sell_signals} de {total_signals} señales"
            }
            
        except Exception as e:
            print(f"⚠️  Error modo crecimiento mejorado: {e}")
            return self._default_growth_signal()
    
    def _calculate_rsi_improved(self, df):
        """RSI MEJORADO (más BUY signals)"""
        try:
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            current_rsi = rsi.iloc[-1]
            
            # Umbrales MEJORADOS para más BUY
            if current_rsi < 40:  # 40 (antes 35) → Más BUY
                return "BUY"
            elif current_rsi > 70:  # 70 (antes 65) → Menos SELL
                return "SELL"
            else:
                return "HOLD"
        except:
            return "HOLD"
    
    def _calculate_macd_improved(self, df):
        """MACD MEJORADO (más sensible a BUY)"""
        try:
            ema_12 = df['Close'].ewm(span=12, adjust=False).mean()
            ema_26 = df['Close'].ewm(span=26, adjust=False).mean()
            macd = ema_12 - ema_26
            signal_line = macd.ewm(span=9, adjust=False).mean()
            histogram = macd - signal_line
            
            # Lógica MEJORADA
            if macd.iloc[-1] > signal_line.iloc[-1] and histogram.iloc[-1] > 0:
                return "BUY"
            elif macd.iloc[-1] < signal_line.iloc[-1] and histogram.iloc[-1] < 0:
                return "SELL"
            else:
                return "HOLD"
        except:
            return "HOLD"
    
    def _calculate_trend_improved(self, df):
        """Tendencia MEJORADA"""
        try:
            # Múltiples EMAs para mejor detección
            ema_9 = df['Close'].ewm(span=9, adjust=False).mean()
            ema_21 = df['Close'].ewm(span=21, adjust=False).mean()
            ema_50 = df['Close'].ewm(span=50, adjust=False).mean()
            
            # Tendencia alcista fuerte
            if ema_9.iloc[-1] > ema_21.iloc[-1] > ema_50.iloc[-1]:
                return "BUY"
            # Tendencia bajista fuerte
            elif ema_9.iloc[-1] < ema_21.iloc[-1] < ema_50.iloc[-1]:
                return "SELL"
            else:
                return "HOLD"
        except:
            return "HOLD"
    
    def _calculate_volume_improved(self, df):
        """Volumen MEJORADO"""
        try:
            volume_sma = df['Volume'].rolling(20).mean()
            current_volume = df['Volume'].iloc[-1]
            volume_ratio = current_volume / volume_sma.iloc[-1]
            
            price_change_1h = (df['Close'].iloc[-1] / df['Close'].iloc[-2] - 1) * 100
            price_change_4h = (df['Close'].iloc[-1] / df['Close'].iloc[-5] - 1) * 100
            
            # Lógica MEJORADA
            if volume_ratio > 1.4 and price_change_1h > 0.3 and price_change_4h > 1:
                return "BUY"
            elif volume_ratio > 1.4 and price_change_1h < -0.3 and price_change_4h < -1:
                return "SELL"
            else:
                return "HOLD"
        except:
            return "HOLD"
    
    def _calculate_momentum_improved(self, df):
        """Momentum MEJORADO"""
        try:
            # Momentum múltiple
            mom_5 = (df['Close'].iloc[-1] / df['Close'].iloc[-6] - 1) * 100
            mom_10 = (df['Close'].iloc[-1] / df['Close'].iloc[-11] - 1) * 100
            
            if mom_5 > 1.5 and mom_10 > 2.5:  # Momentum positivo fuerte
                return "BUY"
            elif mom_5 < -1.5 and mom_10 < -2.5:  # Momentum negativo fuerte
                return "SELL"
            else:
                return "HOLD"
        except:
            return "HOLD"
    
    def _calculate_support_improved(self, df):
        """Soporte/Resistencia MEJORADO"""
        try:
            current_price = df['Close'].iloc[-1]
            
            # Soporte dinámico
            support_20 = df['Low'].rolling(20).min().iloc[-1]
            resistance_20 = df['High'].rolling(20).max().iloc[-1]
            
            # Distancias porcentuales
            dist_to_support = (current_price - support_20) / current_price * 100
            dist_to_resistance = (resistance_20 - current_price) / current_price * 100
            
            if dist_to_support < 3:  # Cerca del soporte
                return "BUY"
            elif dist_to_resistance < 3:  # Cerca de la resistencia
                return "SELL"
            else:
                return "HOLD"
        except:
            return "HOLD"
    
    def _calculate_volatility_signal(self, df):
        """Señal de volatilidad (nuevo)"""
        try:
            # Volatilidad reciente
            returns = df['Close'].pct_change().dropna()
            recent_volatility = returns.tail(20).std() * np.sqrt(252)  # Anualizada
            
            # Volatilidad histórica
            historical_volatility = returns.std() * np.sqrt(252)
            
            # Ratio de volatilidad
            vol_ratio = recent_volatility / historical_volatility
            
            if vol_ratio < 0.7:  # Baja volatilidad (oportunidad)
                return "BUY"
            elif vol_ratio > 1.3:  # Alta volatilidad (riesgo)
                return "SELL"
            else:
                return "HOLD"
        except:
            return "HOLD"
    
    def _default_growth_signal(self):
        return {
            'signal': "HOLD",
            'confidence': 0.4,
            'position_size': 0.0,
            'reason': "Modo crecimiento mejorado por defecto"
        }

def test_improved_system():
    """Probar sistema MEJORADO"""
    print("\n🧪 TESTING SISTEMA DUAL MEJORADO")
    print("=" * 60)
    
    try:
        system = ImprovedDualTradingSystem()
        
        symbols = ['BTC-USD', 'ETH-USD']
        results = []
        
        for symbol in symbols:
            print(f"\n🔍 ANALIZANDO {symbol} (MEJORADO):")
            result = system.generate_improved_signals(symbol)
            results.append(result)
            
            print(f"\n📋 RESUMEN {symbol} (MEJORADO):")
            print(f"   Señal Final: {result['final_signal']}")
            print(f"   Posición Total: {result['total_position']*100:.1f}%")
            print(f"   Régimen: {result['market_regime']}")
            print(f"   Distribución: 🛡️ {result['distribution']['SAFE_MODE']*100:.0f}% / ⚡ {result['distribution']['GROWTH_MODE']*100:.0f}%")
            
            if result['final_signal'] != "HOLD":
                print(f"   ⚡ ¡SEÑAL ACTIVA CON SISTEMA MEJORADO!")
        
        print("\n" + "=" * 60)
        print("🎯 SISTEMA DUAL MEJORADO LISTO PARA VALIDACIÓN")
        print("=" * 60)
        
        # Evaluar mejoras
        active_signals = sum(1 for r in results if r['final_signal'] != "HOLD")
        buy_signals = sum(1 for r in results if r['final_signal'] == "BUY")
        
        print(f"\n📊 EVALUACIÓN DE MEJORAS:")
        print(f"   Señales activas: {active_signals}/{len(results)}")
        print(f"   Señales BUY: {buy_signals}/{len(results)}")
        
        if buy_signals > 0:
            print(f"   ✅ MEJORA DETECTADA - Sistema ahora genera señales BUY")
        elif active_signals > 0:
            print(f"   ⚠️  MEJORA PARCIAL - Señales activas pero no BUY")
        else:
            print(f"   ❌ SIN MEJORA - Sistema aún muy conservador")
        
        return results
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Función principal"""
    print("\n🚀 IMPLEMENTANDO SISTEMA DUAL MEJORADO")
    print("=" * 60)
    
    try:
        # Probar sistema mejorado
        print("\n1. 🧪 TESTING SISTEMA MEJORADO...")
        test_results = test_improved_system()
        
        if not test_results:
            print("❌ Testing falló")
            return
        
        # Resumen de mejoras
        print("\n" + "=" * 60)
        print("🎯 SISTEMA DUAL MEJORADO IMPLEMENTADO")
        print("=" * 60)
        
        print(f"\n📋 MEJORAS APLICADAS:")
        print(f"   🛡️  MODO SEGURO MEJORADO:")
        print(f"     • Menos conservador (15% vs 10% posición)")
        print(f"     • Más señales BUY en consolidación")
        print(f"     • Menos confianza en HOLD")
        
        print(f"\n   ⚡  MODO CRECIMIENTO MEJORADO:")
        print(f"     • Enfoque en BUY opportunities")
        print(f"     • Más indicadores (7 vs 6)")
        print(f"     • Umbrales más favorables a BUY")
        print(f"     • Nueva señal de volatilidad")
        
        print(f"\n   🔄 DISTRIBUCIÓN MEJORADA:")
        print(f"     • Más crecimiento (40% vs 30% base)")
        print(f"     • 70% crecimiento en alcista (vs 60%)")
        print(f"     • 50% crecimiento en lateral (vs 40%)")
        
        print(f"\n   🎯 COMBINACIÓN MEJORADA:")
        print(f"     • Más peso a BUY (+20%)")
        print(f"     • Menos peso a SELL (-20%)")
        print(f"     • Umbrales más fáciles para BUY")
        
        print(f"\n🎯 PRÓXIMOS PASOS:")
        print(f"   1. Backtesting rápido del sistema mejorado")
        print(f"   2. Paper trading 24h para validación")
        print(f"   3. Deployment si resultados positivos")
        
        return {
            'success': True,
            'test_results': test_results
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
    result = main()
    
    if result['success']:
        print(f"\n✅ SISTEMA DUAL MEJORADO CREADO EXITOSAMENTE")
        print(f"   Listo para validación con backtesting/paper trading")
    else:
        print(f"\n❌ FALLÓ: {result.get('error', 'Unknown')}")