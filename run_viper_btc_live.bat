@echo off
title VIPER STRIKE [BTC] - LIVE (MAINNET) !!!
color 4F

:loop
cls
echo ====================================================
echo   INICIANDO VIPER STRIKE (BTC) EN LIVE (MAINNET) !!!
echo   Fecha: %date% Hora: %time%
echo   Entorno: HYPERLIQUID MAINNET (REAL MONEY)
echo ====================================================
echo.
echo Presiona CTRL+C para detener el bucle (sino se reinicia solo)
echo.

cd /d "%~dp0"

python viper_strike_testnet.py --asset BTC --live

echo.
echo !!!!!!! EL BOT SE HA CERRADO INESPERADAMENTE !!!!!!!
echo Reiniciando en 10 segundos...
timeout /t 10
goto loop
