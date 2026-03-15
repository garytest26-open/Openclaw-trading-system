@echo off
title Quantum Edge - Hyperliquid TESTNET (SOL)
color 0E
echo ==================================================
echo   INICIANDO QUANTUM EDGE EN MODO TESTNET
echo   Activo: SOL-USD
echo   (Dinero Ficticio - Hyperliquid)
echo ==================================================
echo.
cd /d "%~dp0"
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo [ADVERTENCIA] Entorno virtual no encontrado. Usando Python global.
)

python quantum_edge_live.py --ticker SOL-USD --network testnet

echo.
echo El bot se ha detenido.
pause
