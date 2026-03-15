@echo off
title VIPER STRIKE [BTC] - TESTNET
color 0E

:loop
cls
echo ====================================================
echo   INICIANDO VIPER STRIKE (BTC) EN TESTNET
echo   Fecha: %date% Hora: %time%
echo   Entorno: HYPERLIQUID TESTNET
echo ====================================================
echo.
echo Presiona CTRL+C para detener el bucle (sino se reinicia solo)
echo.

cd /d "%~dp0"

python viper_strike_testnet.py --asset BTC

echo.
echo !!!!!!! EL BOT SE HA CERRADO INESPERADAMENTE !!!!!!!
echo Reiniciando en 10 segundos...
timeout /t 10
goto loop
