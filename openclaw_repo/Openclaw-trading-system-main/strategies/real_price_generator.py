#!/usr/bin/env python3
"""
Generate REALISTIC cryptocurrency prices based on actual market conditions
Uses CoinGecko API for real prices when available, falls back to realistic simulation
"""

import requests
import json
import time
import random
from datetime import datetime, timedelta

class RealisticPriceGenerator:
    """Generate realistic cryptocurrency prices"""
    
    def __init__(self):
        self.last_prices = {}
        self.volatility_factors = {
            'BTC': 0.02,   # 2% daily volatility
            'ETH': 0.03,   # 3% daily volatility  
            'SOL': 0.05,   # 5% daily volatility
        }
        
        # Base realistic prices (updated periodically)
        self.base_prices = {
            'BTC': 51750.0,  # Realistic BTC price range
            'ETH': 3180.0,   # Realistic ETH price range
            'SOL': 115.0,    # Realistic SOL price range
        }
        
        # Try to get real prices first
        self._try_get_real_prices()
    
    def _try_get_real_prices(self):
        """Try to get real prices from public APIs"""
        try:
            # Try CoinGecko API (no API key needed for basic price)
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {
                'ids': 'bitcoin,ethereum,solana',
                'vs_currencies': 'usd'
            }
            
            response = requests.get(url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                
                # Update base prices with real data
                if 'bitcoin' in data and 'usd' in data['bitcoin']:
                    self.base_prices['BTC'] = data['bitcoin']['usd']
                    print(f"✅ Precio REAL BTC obtenido: ${self.base_prices['BTC']:,.2f}")
                
                if 'ethereum' in data and 'usd' in data['ethereum']:
                    self.base_prices['ETH'] = data['ethereum']['usd']
                    print(f"✅ Precio REAL ETH obtenido: ${self.base_prices['ETH']:,.2f}")
                
                if 'solana' in data and 'usd' in data['solana']:
                    self.base_prices['SOL'] = data['solana']['usd']
                    print(f"✅ Precio REAL SOL obtenido: ${self.base_prices['SOL']:,.2f}")
                    
                return True
                
        except Exception as e:
            print(f"⚠️ No se pudieron obtener precios reales: {e}")
            print("📊 Usando precios realistas basados en mercado actual...")
        
        return False
    
    def get_realistic_price(self, symbol, add_noise=True):
        """
        Get realistic price for a cryptocurrency
        Args:
            symbol: BTC, ETH, or SOL
            add_noise: Add realistic market noise
        Returns:
            float: Realistic price
        """
        symbol = symbol.upper().replace('USDT', '').replace('-USD', '')
        
        if symbol not in self.base_prices:
            # Default for unknown symbols
            base_price = 100.0
            volatility = 0.04
        else:
            base_price = self.base_prices[symbol]
            volatility = self.volatility_factors.get(symbol, 0.03)
        
        if add_noise:
            # Add realistic market movement
            # - Small random walk based on volatility
            # - Trending bias (60% chance of continuing trend)
            # - Time-of-day effects
            
            # Get current hour for market session effects
            current_hour = datetime.utcnow().hour
            
            # Market session multipliers
            if 13 <= current_hour < 21:  # US market hours
                session_multiplier = 1.2  # More active
            elif 0 <= current_hour < 8:   # Asia market hours
                session_multiplier = 0.8  # Less active
            else:                         # European overlap
                session_multiplier = 1.0  # Normal
            
            # Calculate price movement
            daily_volatility = volatility * session_multiplier
            hourly_volatility = daily_volatility / 24
            
            # Random walk with slight momentum
            if symbol in self.last_prices:
                last_price = self.last_prices[symbol]
                momentum = (base_price - last_price) / last_price
                momentum_bias = min(max(momentum * 0.3, -0.005), 0.005)
            else:
                momentum_bias = 0
            
            # Generate price with realistic characteristics
            random_move = random.gauss(0, hourly_volatility)
            price_move = random_move + momentum_bias
            
            final_price = base_price * (1 + price_move)
            
            # Ensure price stays in realistic range
            min_price = base_price * 0.98  # 2% minimum
            max_price = base_price * 1.02  # 2% maximum
            final_price = max(min_price, min(final_price, max_price))
            
        else:
            final_price = base_price
        
        # Store for next call (for momentum calculation)
        self.last_prices[symbol] = final_price
        
        return round(final_price, 2)
    
    def get_price_with_context(self, symbol):
        """
        Get price with market context information
        Returns dict with price and market conditions
        """
        price = self.get_realistic_price(symbol)
        
        # Determine market conditions
        symbol_clean = symbol.upper().replace('USDT', '').replace('-USD', '')
        base_price = self.base_prices.get(symbol_clean, price)
        
        price_change_pct = ((price - base_price) / base_price) * 100
        
        # Classify market condition
        if abs(price_change_pct) < 0.5:
            market_condition = "NEUTRAL"
            condition_emoji = "➡️"
        elif price_change_pct > 0:
            market_condition = "BULLISH"
            condition_emoji = "📈"
        else:
            market_condition = "BEARISH"
            condition_emoji = "📉"
        
        # Determine volatility level
        volatility = self.volatility_factors.get(symbol_clean, 0.03) * 100
        
        return {
            'symbol': symbol,
            'price': price,
            'price_formatted': f"${price:,.2f}",
            'base_price': base_price,
            'price_change_percent': round(price_change_pct, 2),
            'market_condition': market_condition,
            'condition_emoji': condition_emoji,
            'volatility_percent': round(volatility, 1),
            'timestamp': datetime.utcnow().isoformat(),
            'source': 'realistic_simulation',
            'note': 'Precio realista basado en condiciones actuales de mercado'
        }
    
    def generate_signal_prices(self, symbol, direction="LONG"):
        """
        Generate complete price set for a trading signal
        Returns entry, stop loss, and take profit levels
        """
        entry_price = self.get_realistic_price(symbol)
        
        # Get symbol-specific volatility
        symbol_clean = symbol.upper().replace('USDT', '').replace('-USD', '')
        volatility = self.volatility_factors.get(symbol_clean, 0.03)
        
        # Calculate stop loss (2x daily volatility)
        stop_distance_pct = volatility * 2
        
        if direction.upper() == "LONG":
            stop_loss = entry_price * (1 - stop_distance_pct)
            take_profits = [
                entry_price * 1.015,  # 1.5%
                entry_price * 1.035,  # 3.5%
                entry_price * 1.070,  # 7.0%
            ]
        else:  # SHORT
            stop_loss = entry_price * (1 + stop_distance_pct)
            take_profits = [
                entry_price * 0.985,  # 1.5%
                entry_price * 0.965,  # 3.5%
                entry_price * 0.930,  # 7.0%
            ]
        
        # Round all prices
        stop_loss = round(stop_loss, 2)
        take_profits = [round(tp, 2) for tp in take_profits]
        
        return {
            'entry': entry_price,
            'stop_loss': stop_loss,
            'take_profits': take_profits,
            'stop_distance_pct': round(stop_distance_pct * 100, 1),
            'volatility_used': round(volatility * 100, 1)
        }

def test_realistic_prices():
    """Test the realistic price generator"""
    print("=" * 70)
    print("🎯 GENERADOR DE PRECIOS REALISTAS")
    print("=" * 70)
    
    generator = RealisticPriceGenerator()
    
    print("\n📊 PRECIOS BASE REALISTAS:")
    for symbol, price in generator.base_prices.items():
        print(f"   {symbol}: ${price:,.2f}")
    
    print("\n🔍 GENERANDO PRECIOS REALISTAS:")
    
    symbols = ['BTC', 'ETH', 'SOL']
    for symbol in symbols:
        price_data = generator.get_price_with_context(symbol)
        
        print(f"\n{symbol}:")
        print(f"   Precio: {price_data['price_formatted']}")
        print(f"   Condición: {price_data['condition_emoji']} {price_data['market_condition']}")
        print(f"   Cambio vs base: {price_data['price_change_percent']:+.2f}%")
        print(f"   Volatilidad típica: {price_data['volatility_percent']}%")
    
    print("\n🎯 EJEMPLO DE SEÑAL COMPLETA (BTC LONG):")
    signal_prices = generator.generate_signal_prices('BTC', 'LONG')
    print(f"   Entrada: ${signal_prices['entry']:,.2f}")
    print(f"   Stop Loss: ${signal_prices['stop_loss']:,.2f} ({signal_prices['stop_distance_pct']}%)")
    print(f"   Take Profits:")
    for i, tp in enumerate(signal_prices['take_profits'], 1):
        tp_pct = ((tp - signal_prices['entry']) / signal_prices['entry']) * 100
        print(f"     TP{i}: ${tp:,.2f} ({tp_pct:+.1f}%)")
    
    print("\n" + "=" * 70)
    print("✅ SISTEMA LISTO PARA PRECIOS REALISTAS")
    print("=" * 70)

if __name__ == "__main__":
    test_realistic_prices()