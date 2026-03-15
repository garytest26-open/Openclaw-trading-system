@echo off
title Bitcoin SuperTrend Bot - 24/7 Runner
color 0A

:loop
cls
echo ====================================================
echo   INICIANDO BOT BITCOIN SUPERTREND (Hyperliquid)
echo   Fecha: %date% Hora: %time%
echo ====================================================
echo.
echo Presiona CTRL+C para detener el bucle (sino se reinicia solo)
echo.

python btc_supertrend_live.py

echo.
echo !!!!!!! EL BOT SE HA CERRADO !!!!!!!
echo Reiniciando en 10 segundos...
timeout /t 10
goto loop
