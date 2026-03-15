@echo off
title NEXUS SINDICATO ALPHA - TESTNET
color 0E

echo ====================================================
echo   INICIANDO SIMULACION DEL SINDICATO ALPHA
echo   (Hedge Fund Architecture - Multi-Agent)
echo ====================================================
echo.

echo [INFO] Asegurate de que el servidor REDIS este instalado y corriendo.
echo (Puedes instalarlo en Windows usando memurai o wsl)
timeout /t 3 >nul

echo [1/4] Iniciando CEO... (Asignador Central de Capital)
start "CEO (Capital Allocator) - Sindicato Alpha Nexus" cmd /k "python nexus_ceo.py"
timeout /t 4 >nul

echo [2/4] Iniciando Viper Strike PM (BTC)...
start "Viper (Squeezes PM) - Nexus" cmd /k "python viper_strike_testnet.py --asset BTC --nexus"
timeout /t 2 >nul

echo [3/4] Iniciando Hive Mind PM (SOL)...
start "Hive (PPO/Enjambre PM) - Nexus" cmd /k "python hive_master_bot_testnet.py --nexus"
timeout /t 2 >nul

echo [4/4] Iniciando Sniper PM (ETH)...
start "Sniper (RSI/BB Lateral PM) - Nexus" cmd /k "python nexus_mean_reversion.py --asset ETH"
timeout /t 1 >nul

echo.
echo ====================================================
echo   SINDICATO DESPLEGADO EN MEMORIA EXCITOSAMENTE
echo ====================================================
echo Las 4 ventanas de consola operan en paralelo gestionadas por Redis.
echo.
pause
