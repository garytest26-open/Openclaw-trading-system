"""
Sistema de Backtesting Avanzado para Estrategias de Day Trading
Soporta múltiples timeframes, comisiones realistas y métricas detalladas.
"""
import ccxt
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import argparse
import sys
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')

# Importar estrategias
from strategies.ema_rsi_volume import EMARSIVolumeStrategy
from strategies.vwap_momentum import VWAPMomentumStrategy
from strategies.bollinger_scalping import BollingerScalpingStrategy
from strategies.breakout_atr import BreakoutATRStrategy

class DayTradingBacktest:
    """Motor de backtesting para estrategias de day trading."""
    
    def __init__(self, strategy, symbol: str, timeframe: str, 
                 initial_capital: float = 10000, commission: float = 0.0006, 
                 slippage: float = 0.0005):
        """
        Inicializa el backtester.
        
        Args:
            strategy: Instancia de la estrategia a testear
            symbol: Par de trading (ej. 'BTC/USDC:USDC')
            timeframe: Timeframe (5m, 15m, 1h, etc.)
            initial_capital: Capital inicial en USD
            commission: Comisión por trade (0.06% = 0.0006 para Hyperliquid)
            slippage: Slippage estimado (0.05% = 0.0005)
        """
        self.strategy = strategy
        self.symbol = symbol
        self.timeframe = timeframe
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        
        self.capital = initial_capital
        self.positions = []
        self.trades = []
        self.equity_curve = []
        
    def fetch_data(self, days: int = 30):
        """Descarga datos históricos."""
        print(f"Descargando datos de {self.symbol} ({self.timeframe}) - {days} días...")
        
        try:
            exchange = ccxt.hyperliquid({
                'enableRateLimit': True,
            })
            
            # Calcular cuántas velas necesitamos
            timeframe_minutes = {
                '1m': 1, '5m': 5, '15m': 15, '30m': 30,
                '1h': 60, '4h': 240, '1d': 1440
            }
            minutes_per_candle = timeframe_minutes.get(self.timeframe, 15)
            candles_needed = (days * 24 * 60) // minutes_per_candle
            
            # Límite de ccxt
            limit = min(candles_needed, 1500)
            
            ohlcv = exchange.fetch_ohlcv(self.symbol, self.timeframe, limit=limit)
            
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            print(f"✓ Descargados {len(df)} velas desde {df['timestamp'].iloc[0]} hasta {df['timestamp'].iloc[-1]}")
            return df
            
        except Exception as e:
            print(f"Error descargando datos: {e}")
            print("Generando datos sintéticos para demostración...")
            return self._generate_synthetic_data(days)
    
    def _generate_synthetic_data(self, days: int) -> pd.DataFrame:
        """Genera datos sintéticos para testing (si no hay conexión real)."""
        timeframe_minutes = {'1m': 1, '5m': 5, '15m': 15, '30m': 30, '1h': 60, '4h': 240, '1d': 1440}
        minutes = timeframe_minutes.get(self.timeframe, 15)
        num_candles = (days * 24 * 60) // minutes
        
        dates = pd.date_range(end=datetime.now(), periods=num_candles, freq=f'{minutes}min')
        
        # Simular movimiento de precio con tendencia y volatilidad
        base_price = 45000
        price = base_price
        data = []
        
        for date in dates:
            change = np.random.randn() * 100 + np.random.choice([-1, 1]) * 50
            price = max(price + change, base_price * 0.8)  # No caer más del 20%
            
            high = price * (1 + abs(np.random.randn() * 0.002))
            low = price * (1 - abs(np.random.randn() * 0.002))
            open_price = low + (high - low) * np.random.random()
            close_price = low + (high - low) * np.random.random()
            volume = np.random.uniform(100, 1000)
            
            data.append({
                'timestamp': date,
                'open': open_price,
                'high': high,
                'low': low,
                'close': close_price,
                'volume': volume
            })
        
        return pd.DataFrame(data)
    
    def run(self, df: pd.DataFrame) -> Dict:
        """
        Ejecuta el backtest.
        
        Returns:
            Dict con resultados y métricas
        """
        print(f"\nEjecutando backtest de {self.strategy.get_strategy_name()}...")
        
        # Calcular indicadores
        df = self.strategy.calculate_indicators(df)
        
        # Necesitamos suficiente historia
        required_history = self.strategy.get_required_history()
        start_index = required_history
        
        for i in range(start_index, len(df)):
            signal = self.strategy.generate_signal(df, i)
            current_price = df.iloc[i]['close']
            timestamp = df.iloc[i]['timestamp']
            
            # Procesar señal
            if signal == 'buy' and not self.strategy.in_position:
                self._open_position('long', current_price, timestamp)
                
            elif signal == 'sell' and not self.strategy.in_position:
                self._open_position('short', current_price, timestamp)
                
            elif signal in ['close_long', 'close_short'] and self.strategy.in_position:
                self._close_position(current_price, timestamp)
            
            # Guardar equity curve
            current_equity = self.calculate_current_equity(current_price)
            self.equity_curve.append({
                'timestamp': timestamp,
                'equity': current_equity,
                'capital': self.capital
            })
        
        # Cerrar posición abierta al final si existe
        if self.strategy.in_position:
            self._close_position(df.iloc[-1]['close'], df.iloc[-1]['timestamp'])
        
        # Calcular métricas
        metrics = self.calculate_metrics()
        return metrics
    
    def _open_position(self, position_type: str, price: float, timestamp):
        """Abre una posición."""
        # Aplicar slippage
        if position_type == 'long':
            execution_price = price * (1 + self.slippage)
        else:
            execution_price = price * (1 - self.slippage)
        
        # Calcular cantidad (usar todo el capital disponible)
        amount = self.capital / execution_price
        cost = self.capital
        commission_cost = cost * self.commission
        
        self.strategy.enter_position(position_type, execution_price)
        
        self.positions.append({
            'type': position_type,
            'entry_price': execution_price,
            'entry_time': timestamp,
            'amount': amount,
            'commission': commission_cost
        })
        
        # Reducir capital por comisión
        self.capital -= commission_cost
        
    def _close_position(self, price: float, timestamp):
        """Cierra la posición actual."""
        if not self.positions:
            return
            
        pos = self.positions[-1]
        
        # Aplicar slippage
        if pos['type'] == 'long':
            execution_price = price * (1 - self.slippage)
        else:
            execution_price = price * (1 + self.slippage)
        
        # Calcular P&L
        if pos['type'] == 'long':
            pnl = (execution_price - pos['entry_price']) * pos['amount']
        else:  # short
            pnl = (pos['entry_price'] - execution_price) * pos['amount']
        
        # Comisión de salida
        exit_value = execution_price * pos['amount']
        commission_cost = exit_value * self.commission
        
        net_pnl = pnl - commission_cost - pos['commission']
        pnl_pct = (net_pnl / self.initial_capital) * 100
        
        # Actualizar capital
        self.capital += net_pnl
        
        # Registrar trade
        self.trades.append({
            'entry_time': pos['entry_time'],
            'exit_time': timestamp,
            'type': pos['type'],
            'entry_price': pos['entry_price'],
            'exit_price': execution_price,
            'amount': pos['amount'],
            'pnl': net_pnl,
            'pnl_pct': pnl_pct,
            'duration': timestamp - pos['entry_time']
        })
        
        self.strategy.exit_position()
    
    def calculate_current_equity(self, current_price: float) -> float:
        """Calcula equity actual (incluyendo posiciones abiertas)."""
        equity = self.capital
        
        if self.positions and self.strategy.in_position:
            pos = self.positions[-1]
            if pos['type'] == 'long':
                unrealized_pnl = (current_price - pos['entry_price']) * pos['amount']
            else:
                unrealized_pnl = (pos['entry_price'] - current_price) * pos['amount']
            equity += unrealized_pnl
        
        return equity
    
    def calculate_metrics(self) -> Dict:
        """Calcula métricas de rendimiento."""
        if not self.trades:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'total_return': 0,
                'sharpe_ratio': 0,
                'max_drawdown': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'profit_factor': 0
            }
        
        trades_df = pd.DataFrame(self.trades)
        equity_df = pd.DataFrame(self.equity_curve)
        
        # Estadísticas básicas
        total_trades = len(trades_df)
        winning_trades = trades_df[trades_df['pnl'] > 0]
        losing_trades = trades_df[trades_df['pnl'] < 0]
        
        win_rate = (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0
        
        total_return = ((self.capital - self.initial_capital) / self.initial_capital) * 100
        
        # Sharpe Ratio (simplificado)
        if len(equity_df) > 1:
            equity_df['returns'] = equity_df['equity'].pct_change()
            sharpe_ratio = (equity_df['returns'].mean() / equity_df['returns'].std()) * np.sqrt(252) if equity_df['returns'].std() > 0 else 0
        else:
            sharpe_ratio = 0
        
        # Max Drawdown
        equity_df['cummax'] = equity_df['equity'].cummax()
        equity_df['drawdown'] = (equity_df['equity'] - equity_df['cummax']) / equity_df['cummax'] * 100
        max_drawdown = abs(equity_df['drawdown'].min())
        
        # Promedio de ganancias/pérdidas
        avg_win = winning_trades['pnl'].mean() if len(winning_trades) > 0 else 0
        avg_loss = abs(losing_trades['pnl'].mean()) if len(losing_trades) > 0 else 0
        
        # Profit Factor
        total_wins = winning_trades['pnl'].sum() if len(winning_trades) > 0 else 0
        total_losses = abs(losing_trades['pnl'].sum()) if len(losing_trades) > 0 else 1
        profit_factor = total_wins / total_losses if total_losses > 0 else 0
        
        return {
            'strategy': self.strategy.get_strategy_name(),
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'total_trades': total_trades,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'total_return': total_return,
            'final_capital': self.capital,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'avg_trade_duration': trades_df['duration'].mean() if total_trades > 0 else timedelta(0)
        }
    
    def plot_results(self, filename: str = None):
        """Genera gráfica de resultados."""
        if not self.equity_curve:
            print("No hay datos para graficar.")
            return
        
        equity_df = pd.DataFrame(self.equity_curve)
        trades_df = pd.DataFrame(self.trades) if self.trades else None
        
        fig, axes = plt.subplots(2, 1, figsize=(14, 10))
        fig.suptitle(f'{self.strategy.get_strategy_name()} - {self.symbol} ({self.timeframe})', 
                     fontsize=16, fontweight='bold')
        
        # Equity Curve
        axes[0].plot(equity_df['timestamp'], equity_df['equity'], linewidth=2, color='#2E86DE')
        axes[0].axhline(y=self.initial_capital, color='gray', linestyle='--', alpha=0.5, label='Capital Inicial')
        axes[0].fill_between(equity_df['timestamp'], self.initial_capital, equity_df['equity'], 
                             alpha=0.3, color='#2E86DE')
        axes[0].set_ylabel('Equity (USD)', fontsize=12)
        axes[0].set_title('Curva de Equity', fontsize=14)
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)
        
        # Trade PnL
        if trades_df is not None and len(trades_df) > 0:
            colors = ['green' if pnl > 0 else 'red' for pnl in trades_df['pnl']]
            axes[1].bar(range(len(trades_df)), trades_df['pnl'], color=colors, alpha=0.7)
            axes[1].axhline(y=0, color='black', linestyle='-', linewidth=0.8)
            axes[1].set_xlabel('Número de Trade', fontsize=12)
            axes[1].set_ylabel('P&L (USD)', fontsize=12)
            axes[1].set_title('P&L por Trade', fontsize=14)
            axes[1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if filename:
            plt.savefig(filename, dpi=150, bbox_inches='tight')
            print(f"\n✓ Gráfica guardada: {filename}")
        else:
            plt.savefig(f'backtest_{self.strategy.get_strategy_name()}_results.png', dpi=150, bbox_inches='tight')
            print(f"\n✓ Gráfica guardada: backtest_{self.strategy.get_strategy_name()}_results.png")
        
        plt.close()

def print_metrics(metrics: Dict):
    """Imprime métricas de forma formateada."""
    print("\n" + "="*60)
    print(f"  RESULTADOS: {metrics['strategy']}")
    print("="*60)
    print(f"Símbolo: {metrics['symbol']} | Timeframe: {metrics['timeframe']}")
    print(f"Total de Trades: {metrics['total_trades']}")
    print(f"  ├─ Ganadores: {metrics['winning_trades']} ({metrics['win_rate']:.1f}%)")
    print(f"  └─ Perdedores: {metrics['losing_trades']}")
    print(f"\nRetorno Total: {metrics['total_return']:.2f}%")
    print(f"Capital Final: ${metrics['final_capital']:.2f}")
    print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
    print(f"Max Drawdown: {metrics['max_drawdown']:.2f}%")
    print(f"\nPromedio Ganancia: ${metrics['avg_win']:.2f}")
    print(f"Promedio Pérdida: ${metrics['avg_loss']:.2f}")
    print(f"Profit Factor: {metrics['profit_factor']:.2f}")
    print(f"Duración Promedio: {metrics['avg_trade_duration']}")
    print("="*60 + "\n")

def main():
    parser = argparse.ArgumentParser(description='Backtest de estrategias de day trading')
    parser.add_argument('--strategy', type=str, required=True,
                       choices=['ema_rsi_volume', 'vwap_momentum', 'bollinger_scalping', 'breakout_atr', 'all'],
                       help='Estrategia a testear')
    parser.add_argument('--symbol', type=str, default='BTC/USDC:USDC',
                       help='Par de trading')
    parser.add_argument('--timeframe', type=str, default='15m',
                       help='Timeframe (5m, 15m, 1h, etc.)')
    parser.add_argument('--days', type=int, default=30,
                       help='Días de historico')
    parser.add_argument('--capital', type=float, default=10000,
                       help='Capital inicial')
    
    args = parser.parse_args()
    
    # Mapeo de estrategias
    strategies_map = {
        'ema_rsi_volume': EMARSIVolumeStrategy,
        'vwap_momentum': VWAPMomentumStrategy,
        'bollinger_scalping': BollingerScalpingStrategy,
        'breakout_atr': BreakoutATRStrategy
    }
    
    if args.strategy == 'all':
        strategies_to_test = list(strategies_map.keys())
    else:
        strategies_to_test = [args.strategy]
    
    all_results = []
    
    for strategy_name in strategies_to_test:
        strategy_class = strategies_map[strategy_name]
        strategy = strategy_class()
        
        backtester = DayTradingBacktest(
            strategy=strategy,
            symbol=args.symbol,
            timeframe=args.timeframe,
            initial_capital=args.capital
        )
        
        # Descargar datos (se comparte entre estrategias si se testean varias)
        if not all_results:  # Solo descargar una vez
            df = backtester.fetch_data(days=args.days)
        
        # Ejecutar backtest
        metrics = backtester.run(df)
        all_results.append(metrics)
        
        # Imprimir resultados
        print_metrics(metrics)
        
        # Generar gráfica
        backtester.plot_results()
    
    # Si se testearon múltiples estrategias, mostrar comparación
    if len(all_results) > 1:
        print("\n" + "="*80)
        print("  COMPARACIÓN DE ESTRATEGIAS")
        print("="*80)
        comparison_df = pd.DataFrame(all_results)
        print(comparison_df[['strategy', 'total_trades', 'win_rate', 'total_return', 
                             'sharpe_ratio', 'max_drawdown', 'profit_factor']].to_string(index=False))
        print("="*80)

if __name__ == '__main__':
    main()
