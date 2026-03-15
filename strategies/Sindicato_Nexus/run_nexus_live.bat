@echo off
title NEXUS SINDICATO ALPHA - LIVE MAINNET (DINERO REAL)
color 0C

echo ====================================================
echo   PELIGRO: INICIANDO SIMULACION DEL SINDICATO ALPHA
echo   EN MAINNET (DINERO REAL).
echo   IA Allocation + 4 Edge PMs Independientes
echo ====================================================
echo.

echo [INFO] Asegurate de que el servidor REDIS este instalado y corriendo en Windows.
timeout /t 5 >nul

echo [1/5] Iniciando CEO... (Reinforcement Learning Allocator)
start "CEO EN VIVO - Nexus" cmd /k "python nexus_ceo.py --live"
timeout /t 4 >nul

echo [2/5] Iniciando Viper Strike PM (BTC)...
start "Viper EN VIVO - Nexus" cmd /k "python viper_strike_testnet.py --asset BTC --nexus --live"
timeout /t 2 >nul

echo [3/5] Iniciando Hive Mind PM (SOL)...
start "Hive EN VIVO - Nexus" cmd /k "python hive_master_bot_testnet.py --nexus --live"
timeout /t 2 >nul

echo [4/5] Iniciando Sniper PM (ETH)...
start "Sniper EN VIVO - Nexus" cmd /k "python nexus_mean_reversion.py --asset ETH --live"
timeout /t 2 >nul

echo [5/5] Iniciando Quant Stat-Arb PM (BTC/ETH)...
start "Arb EN VIVO - Nexus" cmd /k "python nexus_stat_arb.py --live"
timeout /t 1 >nul

echo.
echo ====================================================
echo   SINDICATO COMPLETO DESPLEGADO EN MAINNET (LIVE)
echo ====================================================
echo PELIGRO: ESTAS OPERANDO CON FONDOS REALES DE HYPERLIQUID.
echo Las 5 consolas operan como hilos paralelos.
echo Para apagar el Hedge Fund de emergencia, cierra el CEO primero.
echo.
pause
