@echo off
title 🧪 HIVE-MIND ALLOCATOR - TESTNET RUNNER 🧪
color 0E

:loop
cls
echo ====================================================
echo   INICIANDO ENSAMBLE HIVE-MIND (SOL-USD) EN TESTNET
echo   Fecha: %date% Hora: %time%
echo   Entorno: HYPERLIQUID TESTNET 🧪
echo ====================================================
echo.
echo Presiona CTRL+C para detener el bucle (sino se reinicia solo)
echo.

cd /d "%~dp0"

echo [SISTEMA] Verificando conexion a base de datos Redis...
echo (Asegurate de tener tu servidor Redis encendido)
echo.

set PYTHONPATH=%~dp0
python Sindicato_Alpha_Nexus\hive_master_bot_testnet.py

echo.
echo !!!!!!! EL ENJAMBRE HA COLAPSADO !!!!!!!
echo Reiniciando Cerebro Central en 10 segundos...
timeout /t 10
goto loop
