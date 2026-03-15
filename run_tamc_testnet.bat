@echo off
title TAMC 2.0 (PPO-LSTM) - TESTNET RUNNER
color 0E

:loop
cls
echo ====================================================
echo   INICIANDO BOT TAMC 2.0 (SOL-USD) EN TESTNET
echo   Fecha: %date% Hora: %time%
echo   Entorno: HYPERLIQUID TESTNET
echo ====================================================
echo.
echo Presiona CTRL+C para detener el bucle (sino se reinicia solo)
echo.

cd /d "%~dp0"

python tamc_sol_testnet.py

echo.
echo !!!!!!! EL BOT SE HA CERRADO INESPERADAMENTE !!!!!!!
echo Reiniciando en 10 segundos...
timeout /t 10
goto loop
