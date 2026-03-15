#!/bin/bash
# Script para configurar repositorio GitHub remoto

echo "=========================================="
echo "🔗 CONFIGURACIÓN REPOSITORIO GITHUB REMOTO"
echo "=========================================="

BACKUP_DIR="/home/ubuntu/openclaw-trading-system"
GITHUB_USER="garytest26-open"
REPO_NAME="openclaw-trading-system"

cd "$BACKUP_DIR"

# Verificar conexión SSH a GitHub
echo "🔍 Verificando conexión SSH a GitHub..."
ssh -T git@github.com 2>&1 | grep -i "successfully authenticated" && echo "✅ Conexión SSH OK" || echo "⚠️  Problema con conexión SSH"

# Configurar repositorio remoto
echo "🔗 Configurando repositorio remoto..."
if git remote | grep -q origin; then
    echo "✅ Repositorio remoto ya configurado"
    git remote -v
else
    echo "⚙️  Añadiendo repositorio remoto..."
    git remote add origin git@github.com:$GITHUB_USER/$REPO_NAME.git
    echo "✅ Repositorio remoto añadido"
fi

# Intentar crear repositorio en GitHub si no existe
echo "🌐 Intentando crear repositorio en GitHub..."
curl -X POST -H "Authorization: token YOUR_TOKEN_HERE" \
     -H "Accept: application/vnd.github.v3+json" \
     https://api.github.com/user/repos \
     -d "{\"name\":\"$REPO_NAME\",\"private\":true}" 2>/dev/null && \
     echo "✅ Repositorio creado en GitHub" || \
     echo "⚠️  No se pudo crear repositorio (necesita token)"

echo ""
echo "📋 Para completar la configuración:"
echo "1. Añade la clave SSH a tu cuenta GitHub"
echo "2. Crea el repositorio en GitHub: https://github.com/new"
echo "3. Ejecuta: git push -u origin main"
echo ""
echo "🎯 Configuración local completada!"
