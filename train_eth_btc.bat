@echo off
title TAMC 2.0 - ETH ^& BTC Trainer
color 0B

echo ====================================================
echo   INICIANDO ENTRENAMIENTO SECUENCIAL (TAMC 2.0)
echo   Activos: ETH-USD y BTC-USD
echo   Fecha: %date% Hora: %time%
echo ====================================================
echo.

cd /d "%~dp0"

echo [1/2] Entrenando modelo PPO-LSTM para ETH-USD...
echo.
python train_tamc_v2.py --ticker ETH-USD

echo.
echo ====================================================
echo [2/2] Finalizado ETH. Iniciando entrenamiento para BTC-USD...
echo ====================================================
echo.
python train_tamc_v2.py --ticker BTC-USD

echo.
echo ====================================================
echo   ENTRENAMIENTOS SECUENCIALES FINALIZADOS
echo ====================================================
timeout /t 30
