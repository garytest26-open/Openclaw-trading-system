@echo off
title TAMC Solana Testnet Bot - Hyperliquid
color 0B
echo =======================================================
echo     INICIANDO BOT TAMC SOLANA EN TESTNET HYPERLIQUID
echo =======================================================
echo.
echo Presiona Ctrl+C para detener el bot en cualquier momento.
echo.

:: Activar el entorno virtual si existe
if exist venv\Scripts\activate (
    call venv\Scripts\activate
    echo Entorno virtual activado.
) else (
    echo Usando Python del sistema general. Asegurate de tener instaladas
    echo las dependencias.
)

echo.
echo Verificando dependencias (torch, ccxt, pandas)...

python -c "import torch" 2>nul
if %errorlevel% neq 0 (
    echo Instalando torch...
    pip install torch
)

python -c "import ccxt" 2>nul
if %errorlevel% neq 0 (
    echo Instalando ccxt...
    pip install ccxt
)

python -c "import pandas" 2>nul
if %errorlevel% neq 0 (
    echo Instalando pandas y dotenv...
    pip install pandas python-dotenv
)

echo.
echo Ejecutando tamc_sol_testnet.py...
python tamc_sol_testnet.py

echo.
echo El bot se ha detenido o ha ocurrido un error.
pause
