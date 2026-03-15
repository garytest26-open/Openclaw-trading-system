#!/bin/bash
# Script de verificación de integridad del backup

BACKUP_DIR="/home/ubuntu/openclaw-trading-system"
LOG_FILE="/var/log/trading_backup_verify.log"

echo "==========================================" > "$LOG_FILE"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Verificación de backup" >> "$LOG_FILE"

# Verificar existencia del directorio
if [ ! -d "$BACKUP_DIR" ]; then
    echo "❌ ERROR: Directorio de backup no encontrado" >> "$LOG_FILE"
    echo "❌ ERROR: Directorio de backup no encontrado"
    exit 1
fi

cd "$BACKUP_DIR"

# Verificar estructura básica
echo "[$(date '+%H:%M:%S')] Verificando estructura..." >> "$LOG_FILE"
REQUIRED_DIRS=("strategies" "scripts" "configs" "docs" "backups")
for dir in "${REQUIRED_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo "✅ $dir: OK" >> "$LOG_FILE"
    else
        echo "❌ $dir: FALTANTE" >> "$LOG_FILE"
    fi
done

# Verificar archivos críticos
echo "[$(date '+%H:%M:%S')] Verificando archivos críticos..." >> "$LOG_FILE"
CRITICAL_FILES=(
    "strategies/signal_generator.py"
    "strategies/signal_monitor.py"
    "strategies/real_price_generator.py"
    "backups/backup_daily.sh"
    "backups/restore_system.sh"
)

for file in "${CRITICAL_FILES[@]}"; do
    if [ -f "$file" ]; then
        SIZE=$(stat -c%s "$file" 2>/dev/null || echo "0")
        echo "✅ $file: OK ($SIZE bytes)" >> "$LOG_FILE"
    else
        echo "❌ $file: FALTANTE" >> "$LOG_FILE"
    fi
done

# Estadísticas
TOTAL_FILES=$(find . -type f | wc -l)
TOTAL_SIZE=$(du -sh . | cut -f1)
GIT_STATUS=$(git status --short 2>/dev/null | wc -l)

echo "[$(date '+%H:%M:%S')] Estadísticas finales:" >> "$LOG_FILE"
echo "📁 Archivos totales: $TOTAL_FILES" >> "$LOG_FILE"
echo "💾 Tamaño total: $TOTAL_SIZE" >> "$LOG_FILE"
echo "🔄 Cambios pendientes Git: $GIT_STATUS" >> "$LOG_FILE"

if [ "$GIT_STATUS" -gt 0 ]; then
    echo "⚠️  ALERTA: Hay $GIT_STATUS cambios sin commit" >> "$LOG_FILE"
fi

echo "==========================================" >> "$LOG_FILE"

# Mostrar resumen
echo ""
echo "📊 VERIFICACIÓN COMPLETADA:"
echo "📁 Archivos: $TOTAL_FILES"
echo "💾 Tamaño: $TOTAL_SIZE"
echo "🔄 Cambios pendientes: $GIT_STATUS"
echo ""
echo "📋 Log completo en: $LOG_FILE"
