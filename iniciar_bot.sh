#!/bin/bash

# ============================================
# Script de Inicio del Bot de Trading
# Equivalente Linux de iniciar_bot.bat
# ============================================

echo "Iniciando el Bot de Trading..."
echo "=============================="
echo ""

# Obtener el directorio del script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
cd "$SCRIPT_DIR"

# Intentar activar entorno virtual
if [ -f "venv/bin/activate" ]; then
    echo "[INFO] Activando entorno virtual..."
    source venv/bin/activate
elif [ -f ".venv/bin/activate" ]; then
    echo "[INFO] Activando entorno virtual (.venv)..."
    source .venv/bin/activate
else
    echo "[ADVERTENCIA] No se encontró entorno virtual. Usando Python del sistema..."
fi

# Verificar que existe live_bot.py
if [ ! -f "live_bot.py" ]; then
    echo "[ERROR] No se encontró live_bot.py en el directorio actual"
    exit 1
fi

# Ejecutar el bot
echo "[INFO] Ejecutando live_bot.py..."
echo ""
python3 live_bot.py

# Capturar código de salida
EXIT_CODE=$?

echo ""
echo "=============================="
if [ $EXIT_CODE -eq 0 ]; then
    echo "El bot se ha detenido correctamente."
else
    echo "El bot se detuvo con errores (código: $EXIT_CODE)"
fi
echo "=============================="

exit $EXIT_CODE
