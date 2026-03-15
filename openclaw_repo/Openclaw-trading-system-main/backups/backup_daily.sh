#!/bin/bash
# Script de backup diario del sistema de trading

BACKUP_DIR="/home/ubuntu/openclaw-trading-system"
SOURCE_DIR="/home/ubuntu/.openclaw/workspace/trading"
LOG_FILE="/var/log/trading_backup.log"

echo "==========================================" >> "$LOG_FILE"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Iniciando backup diario" >> "$LOG_FILE"

# Cambiar al directorio de backup
cd "$BACKUP_DIR"

# Sincronizar todos los archivos
echo "[$(date '+%H:%M:%S')] Sincronizando archivos..." >> "$LOG_FILE"
rsync -av --delete "$SOURCE_DIR/" ./current/ 2>> "$LOG_FILE"

# Actualizar repositorio Git
echo "[$(date '+%H:%M:%S')] Actualizando repositorio Git..." >> "$LOG_FILE"
git add . >> "$LOG_FILE" 2>&1
git commit -m "Backup diario $(date '+%Y-%m-%d')" >> "$LOG_FILE" 2>&1

# Intentar push (solo si hay repositorio remoto configurado)
if git remote | grep -q origin; then
    echo "[$(date '+%H:%M:%S')] Enviando a repositorio remoto..." >> "$LOG_FILE"
    git push origin main >> "$LOG_FILE" 2>&1
fi

# Estadísticas
BACKUP_SIZE=$(du -sh . | cut -f1)
FILE_COUNT=$(find . -type f | wc -l)
echo "[$(date '+%H:%M:%S')] Backup completado: $FILE_COUNT archivos ($BACKUP_SIZE)" >> "$LOG_FILE"
echo "==========================================" >> "$LOG_FILE"

# Notificación simple
echo "✅ Backup diario completado: $FILE_COUNT archivos ($BACKUP_SIZE)"
