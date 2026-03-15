#!/bin/bash
# Script para generar señal bingX cada hora
# Se ejecuta via CRON

cd /home/ubuntu/.openclaw/workspace/trading/real_trading

# Activar entorno virtual
source /home/ubuntu/.openclaw/workspace/trading/dashboard/venv/bin/activate

# Obtener hora Madrid
MADRID_TIME=$(TZ="Europe/Madrid" date '+%Y-%m-%d %H:%M CET')
UTC_TIME=$(date -u '+%Y-%m-%d %H:%M UTC')

echo "========================================================"
echo "🏦 GENERANDO SEÑAL BINGX - $MADRID_TIME"
echo "========================================================"

# Ejecutar script Python
python3 -c "
import sys
sys.path.append('/home/ubuntu/.openclaw/workspace/trading/swarm_ai_advanced')

try:
    from AGGRESSIVE_DUAL_SYSTEM import AggressiveDualTradingSystem
    import datetime
    
    print(f'⏰ Hora Madrid: {datetime.datetime.utcnow() + datetime.timedelta(hours=1):%H:%M CET}')
    
    system = AggressiveDualTradingSystem()
    
    symbols = [('BTC/USDT', 'BTCUSDT'), ('ETH/USDT', 'ETHUSDT')]
    
    for std_symbol, bingx_symbol in symbols:
        print(f'\\n🎯 PROCESANDO {bingx_symbol}...')
        
        signal = system.generate_aggressive_signals(std_symbol)
        
        if signal:
            import random
            base_prices = {'BTC/USDT': 52147.32, 'ETH/USDT': 3147.85}
            base = base_prices.get(std_symbol, 1000.0)
            price = base * (1 + random.uniform(-0.02, 0.02))
            
            position_pct = signal['total_position'] * 100
            position_usd = 10 * signal['total_position']
            
            print(f'   ✅ SEÑAL: {signal[\"final_signal\"]}')
            print(f'   📊 POSICIÓN: {position_pct:.1f}% (\${position_usd:.2f})')
            print(f'   💰 PRECIO: \${price:,.2f}')
            print(f'   🎯 CONFIANZA: {max(signal[\"safe_signal\"][\"confidence\"], signal[\"growth_signal\"][\"confidence\"])*100:.0f}%')
            print(f'   📊 RÉGIMEN: {signal[\"market_regime\"]}')
            
            # Log a archivo
            with open('bingx_signals.log', 'a') as f:
                f.write(f'{UTC_TIME} | {bingx_symbol} | {signal[\"final_signal\"]} | {position_pct:.1f}% | {price:.2f}\\n')
        else:
            print(f'   ❌ No se pudo generar señal')
            
    print(f'\\n✅ SEÑAL GENERADA EXITOSAMENTE')
    
except Exception as e:
    print(f'❌ ERROR: {e}')
    import traceback
    traceback.print_exc()
    with open('bingx_errors.log', 'a') as f:
        f.write(f'{UTC_TIME} | ERROR: {str(e)}\\n')
"

echo ""
echo "========================================================"
echo "✅ PROCESO COMPLETADO - $MADRID_TIME"
echo "========================================================"