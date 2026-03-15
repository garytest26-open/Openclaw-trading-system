"""
test_connection.py - Test de conexión a Binance Testnet
Verifica que las API keys estén configuradas correctamente
"""

import os
import sys
import ccxt
from datetime import datetime

print("🔐 TEST DE CONEXIÓN - BINANCE TESTNET")
print("=" * 60)
print("Objetivo: Verificar configuración de API keys")
print("Estado: Conectando...")
print("=" * 60)

def test_binance_connection():
    """Testear conexión a Binance Testnet"""
    
    # Intentar cargar desde archivo .env si existe
    env_file = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_file):
        print(f"📁 Cargando configuración desde: {env_file}")
        try:
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip().strip('"').strip("'")
        except Exception as e:
            print(f"⚠️  Error cargando .env: {e}")
    
    # Obtener API keys de variables de entorno
    api_key = os.environ.get('BINANCE_TESTNET_API_KEY', '')
    secret_key = os.environ.get('BINANCE_TESTNET_SECRET_KEY', '')
    
    print(f"\n🔍 VERIFICANDO CONFIGURACIÓN:")
    print(f"   API Key configurada: {'✅ SÍ' if api_key else '❌ NO'}")
    print(f"   Secret Key configurada: {'✅ SÍ' if secret_key else '❌ NO'}")
    
    if not api_key or api_key == 'tu_api_key_aqui':
        print(f"   ⚠️  API Key no configurada o usando valor por defecto")
    if not secret_key or secret_key == 'tu_secret_key_aqui':
        print(f"   ⚠️  Secret Key no configurada o usando valor por defecto")
    
    if not api_key or not secret_key:
        print(f"\n❌ ERROR: API keys no configuradas")
        print(f"\n📋 CÓMO CONFIGURAR:")
        print(f"1. Crear cuenta en: https://testnet.binance.vision")
        print(f"2. Generar API keys con permisos:")
        print(f"   - Enable Reading")
        print(f"   - Enable Spot & Margin Trading")
        print(f"3. Ejecutar:")
        print(f"   export BINANCE_TESTNET_API_KEY='tu_api_key'")
        print(f"   export BINANCE_TESTNET_SECRET_KEY='tu_secret_key'")
        print(f"\nO crear archivo .env en esta carpeta con:")
        print(f"BINANCE_TESTNET_API_KEY=tu_api_key")
        print(f"BINANCE_TESTNET_SECRET_KEY=tu_secret_key")
        return False
    
    try:
        print(f"\n🔗 CONECTANDO A BINANCE TESTNET...")
        
        # Crear conexión a Binance Testnet
        exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': secret_key,
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
        
        # Test 1: Cargar mercados
        print(f"   📊 Cargando mercados...")
        markets = exchange.load_markets()
        print(f"   ✅ Mercados cargados: {len(markets)} símbolos")
        
        # Test 2: Obtener ticker
        print(f"   📈 Obteniendo ticker BTC/USDT...")
        ticker = exchange.fetch_ticker('BTC/USDT')
        print(f"   ✅ Ticker obtenido: ${ticker['last']:,.2f}")
        
        # Test 3: Obtener balance
        print(f"   💰 Obteniendo balance...")
        balance = exchange.fetch_balance()
        
        # Mostrar balance USDT
        usdt_balance = balance.get('total', {}).get('USDT', 0)
        print(f"   ✅ Balance obtenido: ${usdt_balance:,.2f} USDT")
        
        # Test 4: Verificar permisos
        print(f"   🔐 Verificando permisos...")
        
        # Intentar obtener órdenes abiertas (requiere permisos de trading)
        try:
            open_orders = exchange.fetch_open_orders('BTC/USDT', limit=1)
            print(f"   ✅ Permisos de trading verificados")
        except Exception as e:
            if "insufficient permission" in str(e).lower():
                print(f"   ⚠️  Permisos insuficientes para trading")
                print(f"   💡 Consejo: Habilitar 'Enable Spot & Margin Trading' en API Management")
            else:
                print(f"   ⚠️  Error verificando permisos: {e}")
        
        print(f"\n{'='*60}")
        print("✅ CONEXIÓN EXITOSA A BINANCE TESTNET")
        print(f"{'='*60}")
        
        print(f"\n📊 RESUMEN DE CONEXIÓN:")
        print(f"   Exchange: {exchange.name}")
        print(f"   Modo: Testnet (sandbox)")
        print(f"   Símbolos disponibles: {len(markets)}")
        print(f"   Precio BTC/USDT: ${ticker['last']:,.2f}")
        print(f"   Balance USDT: ${usdt_balance:,.2f}")
        print(f"   Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        print(f"\n🎯 RECOMENDACIONES:")
        if usdt_balance < 100:
            print(f"   💰 Depositar más USDT virtual (recomendado: $100)")
            print(f"   📍 En Testnet: Wallet → USDT → Deposit")
        
        print(f"\n🚀 LISTO PARA TRADING REAL:")
        print(f"   Ejecutar: python3 real_trading_system.py")
        
        return True
        
    except ccxt.AuthenticationError as e:
        print(f"\n❌ ERROR DE AUTENTICACIÓN: {e}")
        print(f"\n🔧 SOLUCIÓN:")
        print(f"1. Verificar que API keys sean correctas")
        print(f"2. Verificar permisos en Binance Testnet")
        print(f"3. Regenerar API keys si es necesario")
        return False
        
    except ccxt.NetworkError as e:
        print(f"\n❌ ERROR DE RED: {e}")
        print(f"\n🔧 SOLUCIÓN:")
        print(f"1. Verificar conexión a internet")
        print(f"2. Verificar que Binance Testnet esté disponible")
        return False
        
    except Exception as e:
        print(f"\n❌ ERROR INESPERADO: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Función principal"""
    
    print(f"\n🚀 INICIANDO TEST DE CONEXIÓN")
    
    success = test_binance_connection()
    
    if success:
        print(f"\n✅ TEST COMPLETADO EXITOSAMENTE")
        print(f"   Sistema listo para trading real")
        return True
    else:
        print(f"\n❌ TEST FALLÓ")
        print(f"   Revisar configuración antes de continuar")
        return False

if __name__ == "__main__":
    result = main()
    
    if result:
        print(f"\n🎯 PRÓXIMOS PASOS:")
        print(f"1. Depositar $100 USDT virtuales en Binance Testnet")
        print(f"2. Ejecutar: python3 real_trading_system.py")
        print(f"3. Monitorear trades en tiempo real")
    else:
        print(f"\n🔧 ACCIONES REQUERIDAS:")
        print(f"1. Configurar API keys correctamente")
        print(f"2. Ejecutar test de conexión nuevamente")
        print(f"3. Contactar soporte si persisten los errores")