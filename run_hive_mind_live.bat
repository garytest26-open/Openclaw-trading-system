@echo off
title 🧠 HIVE-MIND ALLOCATOR (PPO + LLM + L2) - LIVE RUNNER 🚨
color 5F

:loop
cls
echo ====================================================
echo   INICIANDO ENSAMBLE HIVE-MIND (SOL-USD) EN REAL
echo   Fecha: %date% Hora: %time%
echo   Entorno: HYPERLIQUID MAINNET 🚨 DINERO REAL 🚨
echo ====================================================
echo.
echo Presiona CTRL+C para detener el bucle (sino se reinicia solo)
echo.

cd /d "%~dp0"

echo [SISTEMA] Verificando conexion a base de datos Redis...
echo (Asegurate de que Instalador Redis ya fue ejecutado previamente en tu PC)
echo.

python hive_master_bot.py

echo.
echo !!!!!!! EL ENJAMBRE HA COLAPSADO !!!!!!!
echo Reiniciando Cerebro Central en 10 segundos...
timeout /t 10
goto loop
