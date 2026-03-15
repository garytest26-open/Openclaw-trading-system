"""
Script para verificar símbolos disponibles en Hyperliquid
"""
import ccxt

def verificar_simbolos_hyperliquid():
    try:
        # Inicializar Hyperliquid sin credenciales (solo lectura)
        exchange = ccxt.hyperliquid({
            'enableRateLimit': True,
        })
        
        print("Cargando mercados de Hyperliquid...")
        markets = exchange.load_markets()
        
        # Filtrar símbolos relacionados con BTC
        btc_symbols = [symbol for symbol in markets.keys() if 'BTC' in symbol]
        
        print(f"\n[OK] Simbolos con BTC disponibles en Hyperliquid ({len(btc_symbols)}):")
        for symbol in sorted(btc_symbols):
            print(f"  - {symbol}")
        
        # Verificar símbolo específico
        target = 'BTC/USDC:USDC'
        if target in markets:
            print(f"\n[OK] El simbolo '{target}' esta DISPONIBLE")
            market = markets[target]
            print(f"  Tipo: {market.get('type', 'N/A')}")
            print(f"  Perpetuo: {market.get('swap', False)}")
            print(f"  Activo: {market.get('active', False)}")
        else:
            print(f"\n[ERROR] El simbolo '{target}' NO esta disponible")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    verificar_simbolos_hyperliquid()
