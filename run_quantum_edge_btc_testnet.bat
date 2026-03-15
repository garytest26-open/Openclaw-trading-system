@echo off
title Quantum Edge - Hyperliquid TESTNET (BTC)
color 0E
echo ==================================================
echo   INICIANDO QUANTUM EDGE EN MODO TESTNET
echo   Activo: BTC-USD
echo   (Dinero Ficticio - Hyperliquid)
echo ==================================================
echo.
cd /d "%~dp0"
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo [ADVERTENCIA] Entorno virtual no encontrado. Usando Python global.
)

python quantum_edge_live.py --ticker BTC-USD --network testnet

echo.
echo El bot se ha detenido.
pause
