#!/usr/bin/env python3
"""
Script de verificación de configuración del bot de trading.
Verifica que todas las configuraciones sean correctas antes de ejecutar el bot.
"""
import ccxt
import config
import sys

def verificar_exchange():
    """Verifica que el exchange esté configurado correctamente."""
    print(f"🔍 Verificando configuración del exchange...")
    print(f"   Exchange: {config.EXCHANGE_ID}")
    
    try:
        exchange_class = getattr(ccxt, config.EXCHANGE_ID)
        exchange = exchange_class()
        print(f"   ✅ Exchange '{config.EXCHANGE_ID}' encontrado en CCXT")
        return exchange
    except AttributeError:
        print(f"   ❌ ERROR: Exchange '{config.EXCHANGE_ID}' no encontrado en CCXT")
        return None

def verificar_mercado(exchange):
    """Verifica que el símbolo de mercado exista en el exchange."""
    print(f"\n🔍 Verificando símbolo de mercado...")
    print(f"   Símbolo configurado: {config.SYMBOL}")
    
    try:
        markets = exchange.load_markets()
        
        if config.SYMBOL in markets:
            print(f"   ✅ Símbolo '{config.SYMBOL}' encontrado en {config.EXCHANGE_ID}")
            return True
        else:
            print(f"   ❌ ERROR: Símbolo '{config.SYMBOL}' NO encontrado en {config.EXCHANGE_ID}")
            print(f"\n   💡 Símbolos BTC disponibles:")
            btc_markets = [k for k in markets.keys() if 'BTC' in k]
            for market in btc_markets[:15]:
                print(f"      - {market}")
            return False
    except Exception as e:
        print(f"   ❌ ERROR al cargar mercados: {e}")
        return False

def verificar_credenciales():
    """Verifica que las credenciales estén configuradas si no está en modo DRY_RUN."""
    print(f"\n🔍 Verificando credenciales...")
    print(f"   Modo DRY_RUN (Simulación): {config.DRY_RUN}")
    
    if config.DRY_RUN:
        print(f"   ℹ️  Modo simulación activado - No se requieren credenciales")
        return True
    
    if config.EXCHANGE_ID == 'hyperliquid':
        if config.WALLET_ADDRESS and config.PRIVATE_KEY:
            if 'tu_direccion' not in config.WALLET_ADDRESS.lower() and 'tu_clave' not in config.PRIVATE_KEY.lower():
                print(f"   ✅ WALLET_ADDRESS y PRIVATE_KEY configurados")
                return True
            else:
                print(f"   ❌ ERROR: Credenciales tienen valores de placeholder")
                return False
        else:
            print(f"   ❌ ERROR: WALLET_ADDRESS o PRIVATE_KEY no configurados")
            return False
    else:
        if config.API_KEY and config.SECRET:
            if 'tu_api' not in config.API_KEY.lower() and 'tu_secret' not in config.SECRET.lower():
                print(f"   ✅ API_KEY y SECRET configurados")
                return True
            else:
                print(f"   ❌ ERROR: Credenciales tienen valores de placeholder")
                return False
        else:
            print(f"   ❌ ERROR: API_KEY o SECRET no configurados")
            return False

def verificar_parametros():
    """Verifica que los parámetros de trading sean razonables."""
    print(f"\n🔍 Verificando parámetros de trading...")
    print(f"   Estrategia: {config.STRATEGY_NAME}")
    print(f"   Ventana de entrada: {config.ENTRY_WINDOW} períodos")
    print(f"   Ventana de salida: {config.EXIT_WINDOW} períodos")
    print(f"   Temporalidad: {config.TIMEFRAME}")
    print(f"   Riesgo por operación: ${config.RISK_AMOUNT_USD}")
    print(f"   Apalancamiento: {config.LEVERAGE}x")
    print(f"   Intervalo de verificación: {config.CHECK_INTERVAL}s")
    
    warnings = []
    
    if config.ENTRY_WINDOW < 5:
        warnings.append("⚠️  ENTRY_WINDOW muy pequeña (< 5)")
    
    if config.EXIT_WINDOW >= config.ENTRY_WINDOW:
        warnings.append("⚠️  EXIT_WINDOW >= ENTRY_WINDOW (no recomendado para Tortuga)")
    
    if config.LEVERAGE > 1.0 and config.DRY_RUN == False:
        warnings.append("⚠️  Apalancamiento activado en modo real - ALTO RIESGO")
    
    if config.CHECK_INTERVAL < 30:
        warnings.append("⚠️  CHECK_INTERVAL muy corto, puede generar muchas solicitudes")
    
    if warnings:
        print(f"\n   Advertencias:")
        for w in warnings:
            print(f"   {w}")
    else:
        print(f"   ✅ Parámetros configurados correctamente")
    
    return len(warnings) == 0

def main():
    """Función principal de verificación."""
    print("=" * 60)
    print("🤖 VERIFICACIÓN DE CONFIGURACIÓN DEL BOT DE TRADING")
    print("=" * 60)
    
    # Verificar exchange
    exchange = verificar_exchange()
    if not exchange:
        print("\n❌ Verificación FALLIDA: Exchange no válido")
        sys.exit(1)
    
    # Verificar mercado
    if not verificar_mercado(exchange):
        print("\n❌ Verificación FALLIDA: Símbolo de mercado no válido")
        sys.exit(1)
    
    # Verificar credenciales
    if not verificar_credenciales():
        print("\n❌ Verificación FALLIDA: Credenciales no configuradas correctamente")
        print("\n💡 Para operar en modo real, configura tus credenciales en el archivo .env")
        print("   O mantén DRY_RUN=True en config.py para modo simulación")
        sys.exit(1)
    
    # Verificar parámetros
    parametros_ok = verificar_parametros()
    
    print("\n" + "=" * 60)
    if parametros_ok:
        print("✅ VERIFICACIÓN COMPLETADA: Configuración correcta")
    else:
        print("⚠️  VERIFICACIÓN COMPLETADA CON ADVERTENCIAS")
    print("=" * 60)
    print("\n💡 Puedes ejecutar el bot con: python live_bot.py")
    print("   O usando el archivo: iniciar_bot.bat\n")
    
    sys.exit(0)

if __name__ == "__main__":
    main()
