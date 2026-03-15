#!/bin/bash
# Backup automático diario a GitHub

cd /home/ubuntu/openclaw-trading-system

echo "[$(date)] Iniciando backup automático..." >> /home/ubuntu/backup.log

# Añadir todos los cambios
git add .

# Commit con fecha
git commit -m "Backup automático $(date '+%Y-%m-%d %H:%M:%S')" > /dev/null 2>&1

# Push a GitHub
if git push origin main > /dev/null 2>&1; then
    echo "[$(date)] Backup exitoso" >> /home/ubuntu/backup.log
    echo "✅ Backup completado: $(date)"
else
    echo "[$(date)] Error en backup" >> /home/ubuntu/backup.log
    echo "❌ Error en backup"
fi
