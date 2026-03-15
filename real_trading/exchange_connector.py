"""
exchange_connector.py - Conexión segura a exchanges para trading real
Usa Binance Testnet (sandbox) para validación
"""

import os
import ccxt
import json
from datetime import datetime
import time
import hmac
import hashlib
import base64
from typing import Dict, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

print("🔐 CONECTOR DE EXCHANGE - TRADING REAL")
print("=" * 60)
print("Exchange: Binance Testnet (sandbox)")
print("Modo: Validación con capital virtual")
print("Objetivo: Testing seguro del sistema mejorado")
print("=" * 60)

class ExchangeConnector:
    """Conector seguro para Binance Testnet"""
    
    def __init__(self, use_sandbox=True):
        self.use_sandbox = use_sandbox
        self.exchange = None
        self.connected = False
        self.balance = {}
        self.symbols = ['BTC/USDT', 'ETH/USDT']
        
        # Configuración por defecto (sandbox)
        self.config = {
            'apiKey': '',
            'secret': '',
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot',
                'adjustForTimeDifference': True,
            }
        }
        
        if use_sandbox:
            self.setup_sandbox()
        else:
            self.setup_production()
    
    def setup_sandbox(self):
        """Configurar Binance Testnet (sandbox)"""
        print("🔧 Configurando Binance Testnet (sandbox)...")
        
        # Binance Testnet credentials (públicas para testing)
        # EN PRODUCCIÓN: Usar variables de entorno
        self.config.update({
            'apiKey': 'YOUR_TESTNET_API_KEY',  # Reemplazar con API key real
            'secret': 'YOUR_TESTNET_SECRET',   # Reemplazar con secret real
        })
        
        # URLs de testnet
        self.exchange = ccxt.binance({
            'apiKey': self.config['apiKey'],
            'secret': self.config['secret'],
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot',
                'adjustForTimeDifference': True,
            },
            'urls': {
                'api': {
                    'public': 'https://testnet.binance.vision/api/v3',
                    'private': 'https://testnet.binance.vision/api/v3',
                }
            }
        })
        
        print("✅ Binance Testnet configurado")
        print("   📍 URL: https://testnet.binance.vision")
        print("   💰 Capital: Virtual (sandbox)")
        print("   ⚠️  ADVERTENCIA: Usar solo para testing")
    
    def setup_production(self):
        """Configurar Binance producción (NO USAR PARA VALIDACIÓN)"""
        print("🚨 CONFIGURACIÓN PRODUCCIÓN - SOLO PARA DEPLOYMENT FINAL")
        
        # En producción, usar variables de entorno
        api_key = os.environ.get('BINANCE_API_KEY', '')
        secret = os.environ.get('BINANCE_SECRET', '')
        
        if not api_key or not secret:
            raise ValueError("❌ API keys no configuradas en variables de entorno")
        
        self.config.update({
            'apiKey': api_key,
            'secret': secret,
        })
        
        self.exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': secret,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot',
                'adjustForTimeDifference': True,
            }
        })
        
        print("✅ Binance producción configurado")
        print("   ⚠️  ADVERTENCIA: CAPITAL REAL EN RIESGO")
    
    def connect(self):
        """Conectar al exchange y verificar credenciales"""
        print("\n🔗 Conectando al exchange...")
        
        try:
            # Verificar conexión
            self.exchange.load_markets()
            
            # Verificar balance (sandbox tendrá balance virtual)
            self.update_balance()
            
            self.connected = True
            
            print("✅ Conexión exitosa")
            print(f"   Exchange: {self.exchange.name}")
            print(f"   Símbolos disponibles: {len(self.exchange.symbols)}")
            print(f"   Balance inicial: {self.get_balance_summary()}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error de conexión: {e}")
            self.connected = False
            return False
    
    def update_balance(self):
        """Actualizar balance desde exchange"""
        try:
            self.balance = self.exchange.fetch_balance()
            return self.balance
        except Exception as e:
            print(f"⚠️  Error actualizando balance: {e}")
            return {}
    
    def get_balance_summary(self):
        """Obtener resumen de balance"""
        if not self.balance:
            return "No disponible"
        
        summary = []
        for currency in ['USDT', 'BTC', 'ETH']:
            if currency in self.balance.get('total', {}):
                amount = self.balance['total'][currency]
                if amount > 0:
                    summary.append(f"{amount:.4f} {currency}")
        
        return ", ".join(summary) if summary else "0.0000 USDT"
    
    def get_ticker(self, symbol='BTC/USDT'):
        """Obtener precio actual"""
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return {
                'symbol': symbol,
                'bid': ticker['bid'],
                'ask': ticker['ask'],
                'last': ticker['last'],
                'volume': ticker['quoteVolume'],
                'timestamp': ticker['timestamp']
            }
        except Exception as e:
            print(f"⚠️  Error obteniendo ticker {symbol}: {e}")
            return None
    
    def place_order(self, symbol, side, amount, order_type='market', price=None):
        """Colocar orden en exchange"""
        
        print(f"\n📊 COLOCANDO ORDEN:")
        print(f"   Símbolo: {symbol}")
        print(f"   Lado: {side}")
        print(f"   Cantidad: {amount}")
        print(f"   Tipo: {order_type}")
        if price:
            print(f"   Precio: {price}")
        
        try:
            # Validar parámetros
            if amount <= 0:
                print("❌ Cantidad inválida")
                return None
            
            # Preparar parámetros de orden
            params = {}
            
            if order_type == 'market':
                order = self.exchange.create_market_order(symbol, side, amount, params)
            elif order_type == 'limit':
                if not price:
                    print("❌ Precio requerido para orden limit")
                    return None
                order = self.exchange.create_limit_order(symbol, side, amount, price, params)
            else:
                print(f"❌ Tipo de orden no soportado: {order_type}")
                return None
            
            print(f"✅ Orden colocada exitosamente")
            print(f"   ID: {order['id']}")
            print(f"   Estado: {order['status']}")
            print(f"   Precio ejecutado: {order.get('price', 'N/A')}")
            print(f"   Cantidad ejecutada: {order.get('filled', 0)}")
            
            # Actualizar balance
            self.update_balance()
            
            return order
            
        except Exception as e:
            print(f"❌ Error colocando orden: {e}")
            return None
    
    def get_order_status(self, order_id, symbol='BTC/USDT'):
        """Obtener estado de una orden"""
        try:
            order = self.exchange.fetch_order(order_id, symbol)
            return order
        except Exception as e:
            print(f"⚠️  Error obteniendo estado de orden: {e}")
            return None
    
    def cancel_order(self, order_id, symbol='BTC/USDT'):
        """Cancelar orden"""
        try:
            result = self.exchange.cancel_order(order_id, symbol)
            print(f"✅ Orden {order_id} cancelada")
            return result
        except Exception as e:
            print(f"❌ Error cancelando orden: {e}")
            return None
    
    def get_open_orders(self, symbol=None):
        """Obtener órdenes abiertas"""
        try:
            if symbol:
                orders = self.exchange.fetch_open_orders(symbol)
            else:
                orders = self.exchange.fetch_open_orders()
            
            return orders
        except Exception as e:
            print(f"⚠️  Error obteniendo órdenes abiertas: {e}")
            return []
    
    def get_trade_history(self, symbol=None, limit=10):
        """Obtener historial de trades"""
        try:
            if symbol:
                trades = self.exchange.fetch_my_trades(symbol, limit=limit)
            else:
                trades = self.exchange.fetch_my_trades(limit=limit)
            
            return trades
        except Exception as e:
            print(f"⚠️  Error obteniendo historial de trades: {e}")
            return []
    
    def test_connection(self):
        """Probar conexión completa"""
        print("\n🧪 TEST DE CONEXIÓN COMPLETO")
        print("-" * 40)
        
        tests = []
        
        # Test 1: Mercados
        try:
            markets = self.exchange.load_markets()
            tests.append(("✅ Mercados cargados", f"{len(markets)} símbolos"))
        except Exception as e:
            tests.append(("❌ Mercados", str(e)))
        
        # Test 2: Ticker
        try:
            ticker = self.get_ticker('BTC/USDT')
            if ticker:
                tests.append(("✅ Ticker BTC/USDT", f"${ticker['last']:,.2f}"))
            else:
                tests.append(("❌ Ticker", "No disponible"))
        except Exception as e:
            tests.append(("❌ Ticker", str(e)))
        
        # Test 3: Balance
        try:
            balance = self.update_balance()
            if balance:
                tests.append(("✅ Balance", self.get_balance_summary()))
            else:
                tests.append(("❌ Balance", "No disponible"))
        except Exception as e:
            tests.append(("❌ Balance", str(e)))
        
        # Mostrar resultados
        print("\n📊 RESULTADOS DEL TEST:")
        for test_name, result in tests:
            print(f"   {test_name}: {result}")
        
        # Evaluación
        success_count = sum(1 for t, _ in tests if t.startswith("✅"))
        total_tests = len(tests)
        
        print(f"\n🎯 EVALUACIÓN: {success_count}/{total_tests} tests exitosos")
        
        if success_count == total_tests:
            print("✅ CONEXIÓN COMPLETAMENTE OPERATIVA")
            return True
        elif success_count >= 2:
            print("⚠️  CONEXIÓN PARCIAL - Algunas funciones pueden no estar disponibles")
            return True
        else:
            print("❌ CONEXIÓN FALLIDA - Revisar configuración")
            return False

def main():
    """Función principal para testing"""
    print("\n🚀 INICIANDO CONECTOR DE EXCHANGE")
    print("=" * 60)
    
    try:
        # Crear conector (sandbox por defecto)
        connector = ExchangeConnector(use_sandbox=True)
        
        # Conectar
        if not connector.connect():
            print("❌ No se pudo conectar al exchange")
            return
        
        # Ejecutar test completo
        connector.test_connection()
        
        print("\n" + "=" * 60)
        print("🔐 CONECTOR LISTO PARA TRADING REAL")
        print("=" * 60)
        
        print("\n📋 PRÓXIMOS PASOS:")
        print("1. Configurar API keys reales en variables de entorno")
        print("2. Crear cuenta en Binance Testnet: https://testnet.binance.vision")
        print("3. Generar API keys con permisos limitados")
        print("4. Actualizar exchange_connector.py con tus keys")
        print("5. Ejecutar sistema de trading real")
        
        return connector
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    connector = main()
    
    if connector:
        print(f"\n✅ Sistema de conexión listo para validación real")
    else:
        print(f"\n❌ Configuración falló")