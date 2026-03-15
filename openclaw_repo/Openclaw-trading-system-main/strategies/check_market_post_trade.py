#!/usr/bin/env python3
"""
Check market conditions after first trade execution
"""

from real_price_generator import RealisticPriceGenerator
from datetime import datetime

def main():
    print("🔍 ANÁLISIS DE MERCADO - POST EJECUCIÓN TRADE #1")
    print("=" * 60)
    
    generator = RealisticPriceGenerator()
    
    # Obtener precios actuales
    assets = ['BTC', 'ETH', 'SOL']
    
    for asset in assets:
        data = generator.get_price_with_context(asset)
        print(f"{asset}:")
        print(f"  Precio: ${data['price']:,.2f}")
        print(f"  Condición: {data['condition_emoji']} {data['market_condition']}")
        print(f"  Cambio: {data['price_change_percent']:+.2f}%")
        print(f"  Volatilidad: {data['volatility_percent']}%")
        print()
    
    # Análisis para posible señal #2
    print("📊 EVALUACIÓN PARA SEÑAL #2:")
    print("-" * 40)
    
    current_hour = datetime.utcnow().hour
    madrid_hour = current_hour + 1
    
    print(f"Hora UTC: {current_hour}:00")
    print(f"Hora Madrid: {madrid_hour}:00")
    
    # Obtener datos ETH específicos
    eth_data = generator.get_price_with_context('ETH')
    market_condition = eth_data['market_condition']
    volatility = eth_data['volatility_percent']
    
    print(f"\nCondición ETH: {market_condition}")
    print(f"Volatilidad ETH: {volatility}%")
    
    # Evaluar si condiciones son óptimas para nueva señal
    optimal_for_signal = (
        volatility < 4.0 and  # Volatilidad controlada
        current_hour >= 9 and current_hour <= 20 and  # Horario trading UTC
        market_condition in ['BULLISH', 'NEUTRAL']  # Condición favorable
    )
    
    if optimal_for_signal:
        print("✅ Condiciones ACTUALES: ÓPTIMAS para posible señal")
        print("   Próximo chequeo: ~12:30 UTC (13:30 Madrid)")
    else:
        reason = ''
        if volatility >= 4.0:
            reason = 'Volatilidad alta'
        elif current_hour < 9 or current_hour > 20:
            reason = 'Horario no óptimo'
        else:
            reason = 'Condición de mercado no favorable'
        
        print(f"⚠️ Condiciones ACTUALES: Esperar mejor momento")
        print(f"   Razón: {reason}")
    
    print("\n" + "=" * 60)
    print("🎯 TRADE #1 EN CURSO:")
    print(f"   Activo: ETH")
    print(f"   Entrada: ~$2,003")
    print(f"   Stop Loss: $1,879.95")
    print(f"   Take Profits: $2,029.95 / $2,069.95 / $2,139.95")
    print("=" * 60)
    
    # Guardar análisis en archivo
    with open("signal_results/market_analysis_post_trade1.txt", "w") as f:
        f.write("ANÁLISIS DE MERCADO POST-EJECUCIÓN\n")
        f.write("=" * 50 + "\n")
        f.write(f"Hora análisis: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}\n")
        f.write(f"Hora Madrid: {madrid_hour}:00\n")
        f.write(f"Condición ETH: {market_condition}\n")
        f.write(f"Volatilidad ETH: {volatility}%\n")
        f.write(f"Óptimo para señal: {'SÍ' if optimal_for_signal else 'NO'}\n")
        f.write("=" * 50 + "\n")
    
    print("\n💾 Análisis guardado en: signal_results/market_analysis_post_trade1.txt")

if __name__ == "__main__":
    main()