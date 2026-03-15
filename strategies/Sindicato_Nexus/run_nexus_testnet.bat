@echo off
title NEXUS SINDICATO ALPHA - TESTNET (VERSION FULL INSTITUCIONAL)
color 0E

echo ====================================================
echo   INICIANDO SIMULACION DEL SINDICATO ALPHA (X5 PROCESOS)
echo   IA Allocation + 4 Edge PMs Independientes
echo ====================================================
echo.

echo [INFO] Asegurate de que el servidor REDIS este instalado y corriendo en Windows.
timeout /t 3 >nul

echo [1/5] Iniciando CEO... (Reinforcement Learning Allocator)
start "CEO (Capital Allocator) - Nexus" cmd /k "python nexus_ceo.py"
timeout /t 4 >nul

echo [2/5] Iniciando Viper Strike PM (BTC)...
start "Viper (Squeezes + ML XGBoost Edge) - Nexus" cmd /k "python viper_strike_testnet.py --asset BTC --nexus"
timeout /t 2 >nul

echo [3/5] Iniciando Hive Mind PM (SOL)...
start "Hive (PPO Institucional Edge) - Nexus" cmd /k "python hive_master_bot_testnet.py --nexus"
timeout /t 2 >nul

echo [4/5] Iniciando Sniper PM (ETH)...
start "Sniper (Reversion + L2 Muros Ballena) - Nexus" cmd /k "python nexus_mean_reversion.py --asset ETH"
timeout /t 2 >nul

echo [5/5] Iniciando Quant Stat-Arb PM (BTC/ETH)...
start "Arb (Market Neutral Pairs Trading) - Nexus" cmd /k "python nexus_stat_arb.py"
timeout /t 1 >nul

echo.
echo ====================================================
echo   SINDICATO COMPLETO DESPLEGADO EN MEMORIA 
echo ====================================================
echo Las 5 consolas operan como hilos paralelos comunicados por Redis sub-milisegundo.
echo Para detener el ecosistema, deberas cerrar las consolas una por una.
echo.
pause
