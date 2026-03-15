@echo off
title Bitcoin SuperTrend Bot (TESTNET) - 24/7 Runner
color 0E

:loop
cls
echo ====================================================
echo   INICIANDO BOT BITCOIN TESTNET (Hyperliquid)
echo   Fecha: %date% Hora: %time%
echo ====================================================
echo.
echo Presiona CTRL+C para detener el bucle (sino se reinicia solo)
echo.

cd /d "%~dp0"

python btc_supertrend_testnet.py

echo.
echo !!!!!!! EL BOT SE HA CERRADO !!!!!!!
echo Reiniciando en 10 segundos...
timeout /t 10
goto loop
