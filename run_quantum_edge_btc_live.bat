@echo off
title Quantum Edge - Hyperliquid MAINNET (BTC)
color 0C
echo ==================================================
echo   ¡PELIGRO! MODO LIVE - DINERO REAL
echo   Activo: BTC-USD
echo   INICIANDO QUANTUM EDGE EN HYPERLIQUID MAINNET
echo ==================================================
echo.
cd /d "%~dp0"
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo [ADVERTENCIA] Entorno virtual no encontrado. Usando Python global.
)

python quantum_edge_live.py --ticker BTC-USD --network mainnet

echo.
echo El bot se ha detenido.
pause
