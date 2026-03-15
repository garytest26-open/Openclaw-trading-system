"""
RSI Simple Strategy Integration para Dashboard
Estrategia probada con backtest excelente en BTC/ETH
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf
import warnings
warnings.filterwarnings('ignore')

class RSISimpleIntegration:
    """
    Integración de estrategia RSI Simple para dashboard en tiempo real
    """
    
    def __init__(self):
        self.rsi_period = 14
        self.volume_sma_period = 20
        self.stop_loss_pct = 0.02  # 2%
        self.take_profit_pct = 0.04  # 4%
        self.max_hold_hours = 24
        
        # Estado de posiciones activas
        self.active_positions = {}  # {symbol: {position, entry_price, entry_time, stop_loss, take_profit}}
        
        # Historial de señales
        self.signal_history = []
        
        # Configuración de activos (BTC y ETH solamente - SOL no funciona)
        self.supported_symbols = ['BTC-USD', 'ETH-USD']
        
        # Cache de datos
        self.data_cache = {}
        self.cache_duration = timedelta(minutes=5)
        
        print("✅ RSI Simple Integration inicializada")
        print(f"   Símbolos soportados: {self.supported_symbols}")
        print(f"   Parámetros: RSI={self.rsi_period}, SL={self.stop_loss_pct*100}%, TP={self.take_profit_pct*100}%")
    
    def calculate_rsi(self, prices):
        """Calcula RSI usando método estándar"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(self.rsi_period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def fetch_latest_data(self, symbol, hours=48):
        """
        Obtiene datos más recientes de yfinance
        Returns: DataFrame con OHLCV
        """
        cache_key = f"{symbol}_{hours}h"
        current_time = datetime.now()
        
        # Verificar cache
        if cache_key in self.data_cache:
            cached_data, cache_time = self.data_cache[cache_key]
            if current_time - cache_time < self.cache_duration:
                return cached_data.copy()
        
        # Descargar nuevos datos
        try:
            # Para datos recientes, usar período corto
            if hours <= 24:
                period = "1d"
                interval = "1h"
            elif hours <= 168:  # 1 semana
                period = "7d"
                interval = "1h"
            else:
                period = "30d"
                interval = "1h"
            
            df = yf.download(symbol, period=period, interval=interval, progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel(1)
            df.dropna(inplace=True)
            
            # Cachear
            self.data_cache[cache_key] = (df.copy(), current_time)
            
            return df
        except Exception as e:
            print(f"❌ Error fetching data for {symbol}: {e}")
            # Retornar DataFrame vacío en caso de error
            return pd.DataFrame()
    
    def analyze_symbol(self, symbol):
        """
        Analiza símbolo y genera señales si corresponde
        Returns: dict con análisis y señales
        """
        if symbol not in self.supported_symbols:
            return {
                'symbol': symbol,
                'error': 'Symbol not supported',
                'timestamp': datetime.now().isoformat()
            }
        
        # Obtener datos
        df = self.fetch_latest_data(symbol, hours=72)  # 3 días de datos
        if df.empty:
            return {
                'symbol': symbol,
                'error': 'No data available',
                'timestamp': datetime.now().isoformat()
            }
        
        # Calcular indicadores
        df['RSI'] = self.calculate_rsi(df['Close'])
        df['Volume_SMA'] = df['Volume'].rolling(self.volume_sma_period).mean()
        df['Volume_Ratio'] = df['Volume'] / df['Volume_SMA']
        df['SMA_50'] = df['Close'].rolling(50).mean()
        
        # Últimos valores
        last_row = df.iloc[-1]
        prev_row = df.iloc[-2] if len(df) > 1 else last_row
        
        current_price = float(last_row['Close'])
        current_rsi = float(last_row['RSI'])
        volume_ratio = float(last_row['Volume_Ratio'])
        above_sma_50 = current_price > float(last_row['SMA_50'])
        
        # Verificar posición activa
        position_info = self.active_positions.get(symbol)
        
        # Generar señal si no hay posición activa
        signal = None
        signal_type = None
        signal_strength = 0
        
        if position_info is None:
            # No hay posición activa, verificar señales de entrada
            
            # Señal de COMPRA (RSI oversold + volumen alto + por encima SMA 50)
            if current_rsi < 30 and volume_ratio > 1.5 and above_sma_50:
                signal = 'BUY'
                signal_type = 'RSI_OVERSOLD'
                signal_strength = (30 - current_rsi) * volume_ratio
                
                # Crear posición
                self.active_positions[symbol] = {
                    'position': 'LONG',
                    'entry_price': current_price,
                    'entry_time': datetime.now(),
                    'stop_loss': current_price * (1 - self.stop_loss_pct),
                    'take_profit': current_price * (1 + self.take_profit_pct),
                    'signal_strength': signal_strength
                }
            
            # Señal de VENTA (RSI overbought + volumen alto + por debajo SMA 50)
            elif current_rsi > 70 and volume_ratio > 1.5 and not above_sma_50:
                signal = 'SELL'
                signal_type = 'RSI_OVERBOUGHT'
                signal_strength = (current_rsi - 70) * volume_ratio
                
                # Crear posición (short)
                self.active_positions[symbol] = {
                    'position': 'SHORT',
                    'entry_price': current_price,
                    'entry_time': datetime.now(),
                    'stop_loss': current_price * (1 + self.stop_loss_pct),
                    'take_profit': current_price * (1 - self.take_profit_pct),
                    'signal_strength': signal_strength
                }
        
        else:
            # Hay posición activa, verificar salida
            position = position_info['position']
            entry_price = position_info['entry_price']
            entry_time = position_info['entry_time']
            stop_loss = position_info['stop_loss']
            take_profit = position_info['take_profit']
            
            hours_in_trade = (datetime.now() - entry_time).total_seconds() / 3600
            exit_trade = False
            exit_reason = ''
            exit_price = current_price
            pnl_pct = 0
            
            # Calcular PnL
            if position == 'LONG':
                pnl_pct = (current_price - entry_price) / entry_price * 100
                # Check stop loss
                if current_price <= stop_loss:
                    exit_trade = True
                    exit_reason = 'STOP_LOSS'
                # Check take profit
                elif current_price >= take_profit:
                    exit_trade = True
                    exit_reason = 'TAKE_PROFIT'
            else:  # SHORT
                pnl_pct = (entry_price - current_price) / entry_price * 100
                # Check stop loss
                if current_price >= stop_loss:
                    exit_trade = True
                    exit_reason = 'STOP_LOSS'
                # Check take profit
                elif current_price <= take_profit:
                    exit_trade = True
                    exit_reason = 'TAKE_PROFIT'
            
            # Check tiempo máximo
            if hours_in_trade >= self.max_hold_hours:
                exit_trade = True
                exit_reason = 'MAX_TIME_EXCEEDED'
            
            # Salir de la posición si es necesario
            if exit_trade:
                # Registrar señal de salida
                signal = 'EXIT'
                signal_type = exit_reason
                signal_strength = abs(pnl_pct)
                
                # Registrar trade en historial
                trade_record = {
                    'symbol': symbol,
                    'position': position,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'entry_time': entry_time.isoformat(),
                    'exit_time': datetime.now().isoformat(),
                    'pnl_pct': pnl_pct,
                    'exit_reason': exit_reason,
                    'duration_hours': hours_in_trade
                }
                self.signal_history.append(trade_record)
                
                # Eliminar posición activa
                del self.active_positions[symbol]
        
        # Preparar respuesta
        analysis = {
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            'price': current_price,
            'rsi': current_rsi,
            'volume_ratio': volume_ratio,
            'above_sma_50': above_sma_50,
            'has_active_position': position_info is not None,
            'signal': signal,
            'signal_type': signal_type,
            'signal_strength': signal_strength
        }
        
        # Añadir info de posición si existe
        if position_info:
            analysis['position'] = position_info['position']
            analysis['entry_price'] = position_info['entry_price']
            analysis['entry_time'] = position_info['entry_time'].isoformat()
            analysis['stop_loss'] = position_info['stop_loss']
            analysis['take_profit'] = position_info['take_profit']
            analysis['hours_in_trade'] = (datetime.now() - position_info['entry_time']).total_seconds() / 3600
            
            # Calcular PnL actual
            if position_info['position'] == 'LONG':
                analysis['current_pnl_pct'] = (current_price - position_info['entry_price']) / position_info['entry_price'] * 100
            else:
                analysis['current_pnl_pct'] = (position_info['entry_price'] - current_price) / position_info['entry_price'] * 100
        
        # Registrar señal de entrada si existe
        if signal in ['BUY', 'SELL']:
            signal_record = {
                'symbol': symbol,
                'signal': signal,
                'signal_type': signal_type,
                'price': current_price,
                'rsi': current_rsi,
                'volume_ratio': volume_ratio,
                'timestamp': datetime.now().isoformat(),
                'strength': signal_strength
            }
            self.signal_history.append(signal_record)
        
        return analysis
    
    def analyze_all_symbols(self):
        """Analiza todos los símbolos soportados"""
        results = []
        
        for symbol in self.supported_symbols:
            try:
                result = self.analyze_symbol(symbol)
                results.append(result)
            except Exception as e:
                results.append({
                    'symbol': symbol,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })
        
        return results
    
    def get_signal_history(self, limit=20):
        """Obtiene historial de señales recientes"""
        return self.signal_history[-limit:] if self.signal_history else []
    
    def get_active_positions(self):
        """Obtiene posiciones activas"""
        positions = []
        
        for symbol, info in self.active_positions.items():
            position_data = {
                'symbol': symbol,
                'position': info['position'],
                'entry_price': info['entry_price'],
                'entry_time': info['entry_time'].isoformat(),
                'stop_loss': info['stop_loss'],
                'take_profit': info['take_profit'],
                'signal_strength': info['signal_strength']
            }
            positions.append(position_data)
        
        return positions
    
    def get_performance_summary(self):
        """Resumen de performance basado en historial de trades"""
        if not self.signal_history:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'total_pnl_pct': 0,
                'avg_pnl_per_trade': 0,
                'best_trade': 0,
                'worst_trade': 0
            }
        
        # Filtrar solo trades completados (con PnL)
        completed_trades = [t for t in self.signal_history if 'pnl_pct' in t]
        
        if not completed_trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'total_pnl_pct': 0,
                'avg_pnl_per_trade': 0,
                'best_trade': 0,
                'worst_trade': 0
            }
        
        winning_trades = [t for t in completed_trades if t['pnl_pct'] > 0]
        losing_trades = [t for t in completed_trades if t['pnl_pct'] <= 0]
        
        total_pnl = sum(t['pnl_pct'] for t in completed_trades)
        avg_pnl = total_pnl / len(completed_trades)
        best_trade = max(t['pnl_pct'] for t in completed_trades) if completed_trades else 0
        worst_trade = min(t['pnl_pct'] for t in completed_trades) if completed_trades else 0
        
        return {
            'total_trades': len(completed_trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': len(winning_trades) / len(completed_trades) * 100 if completed_trades else 0,
            'total_pnl_pct': total_pnl,
            'avg_pnl_per_trade': avg_pnl,
            'best_trade': best_trade,
            'worst_trade': worst_trade,
            'timestamp': datetime.now().isoformat()
        }

# Instancia global para el dashboard
rsi_integration = RSISimpleIntegration()

def get_rsi_analysis():
    """Función para el dashboard - analiza todos los símbolos"""
    return rsi_integration.analyze_all_symbols()

def get_rsi_signals():
    """Obtiene señales recientes"""
    return rsi_integration.get_signal_history(limit=10)

def get_rsi_positions():
    """Obtiene posiciones activas"""
    return rsi_integration.get_active_positions()

def get_rsi_performance():
    """Obtiene resumen de performance"""
    return rsi_integration.get_performance_summary()

if __name__ == "__main__":
    # Test de la integración
    print("🧪 Testing RSI Simple Integration...")
    
    results = rsi_integration.analyze_all_symbols()
    for result in results:
        print(f"\n📊 {result['symbol']}:")
        print(f"  Price: ${result['price']:.2f}")
        print(f"  RSI: {result['rsi']:.1f}")
        print(f"  Volume Ratio: {result['volume_ratio']:.2f}")
        print(f"  Signal: {result.get('signal', 'NONE')}")
        
        if result.get('has_active_position'):
            print(f"  Active Position: {result['position']}")
            print(f"  PnL: {result['current_pnl_pct']:.2f}%")
    
    print(f"\n✅ RSI Integration test completado")