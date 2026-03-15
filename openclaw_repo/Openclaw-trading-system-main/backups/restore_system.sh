#!/bin/bash
# Script de recuperación de emergencia

echo "=========================================="
echo "🔄 SISTEMA DE RECUPERACIÓN DE EMERGENCIA"
echo "=========================================="

RESTORE_DIR="/home/ubuntu/.openclaw/workspace/trading"
BACKUP_DIR="/home/ubuntu/openclaw-trading-system"

if [ ! -d "$BACKUP_DIR" ]; then
    echo "❌ ERROR: No se encuentra el directorio de backup"
    echo "Intentando clonar desde GitHub..."
    
    # Intentar clonar desde GitHub si existe
    if command -v git &> /dev/null; then
        git clone git@github.com:garytest26-open/openclaw-trading-system.git "$BACKUP_DIR"
    else
        echo "❌ Git no está instalado. No se puede recuperar."
        exit 1
    fi
fi

echo "📁 Restaurando desde: $BACKUP_DIR"
echo "📁 Destino: $RESTORE_DIR"

# Crear directorio destino si no existe
mkdir -p "$RESTORE_DIR"

# Copiar todo excepto el directorio .git
echo "📋 Copiando archivos..."
rsync -av --exclude='.git' "$BACKUP_DIR/current/" "$RESTORE_DIR/" 2>/dev/null || \
rsync -av --exclude='.git' "$BACKUP_DIR/" "$RESTORE_DIR/" 2>/dev/null

# Estadísticas
RESTORED_FILES=$(find "$RESTORE_DIR" -type f | wc -l)
echo "✅ Sistema restaurado: $RESTORED_FILES archivos recuperados"
echo ""
echo "📋 Pasos adicionales:"
echo "1. Revisar configuraciones en $RESTORE_DIR/config/"
echo "2. Verificar scripts en $RESTORE_DIR/scripts/"
echo "3. Ejecutar setup.sh si es necesario"
echo ""
echo "🎯 Recuperación completada exitosamente!"
