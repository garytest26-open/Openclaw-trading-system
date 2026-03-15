@echo off
title Quantum Edge - Hyperliquid MAINNET (SOL)
color 0C
echo ==================================================
echo   ¡PELIGRO! MODO LIVE - DINERO REAL
echo   Activo: SOL-USD
echo   INICIANDO QUANTUM EDGE EN HYPERLIQUID MAINNET
echo ==================================================
echo.
cd /d "%~dp0"
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo [ADVERTENCIA] Entorno virtual no encontrado. Usando Python global.
)

python quantum_edge_live.py --ticker SOL-USD --network mainnet

echo.
echo El bot se ha detenido.
pause
