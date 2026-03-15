#!/bin/bash
# 🚀 START_REVOLUTION.sh - Inicia el sistema revolucionario de IA para trading

echo "🎯 REVOLUCIÓN DEL TRADING - INICIANDO SISTEMA"
echo "=============================================="

# Configurar entorno
cd /home/ubuntu/.openclaw/workspace/trading/swarm_ai_advanced

# Activar entorno virtual
source /home/ubuntu/.openclaw/workspace/trading/dashboard/venv/bin/activate

echo ""
echo "1. 🔍 VERIFICANDO DEPENDENCIAS..."
python3 -c "
import torch
print(f'✅ PyTorch: {torch.__version__}')
import transformers
print(f'✅ Transformers: {transformers.__version__}')
import gymnasium as gym
print(f'✅ Gymnasium: {gym.__version__}')
print('✅ Todas las dependencias están instaladas')
"

echo ""
echo "2. 📊 DESCARGANDO DATOS DE MERCADO..."
python3 -c "
from DATA_PIPELINE import RevolutionaryDataPipeline, DATA_PIPELINE_CONFIG
pipeline = RevolutionaryDataPipeline(DATA_PIPELINE_CONFIG)
print('✅ Datos descargados y procesados')
"

echo ""
echo "3. 🧠 INICIALIZANDO CEREBRO REVOLUCIONARIO..."
python3 -c "
from REVOLUTIONARY_BRAIN import RevolutionaryBrain, REVOLUTIONARY_CONFIG
brain = RevolutionaryBrain(REVOLUTIONARY_CONFIG)
print(f'✅ Cerebro inicializado: {sum(p.numel() for p in brain.parameters()):,} parámetros')
"

echo ""
echo "4. 🚀 EJECUTANDO ENTRENAMIENTO REVOLUCIONARIO..."
echo "   (Esto puede tomar 30-60 minutos)"
echo "   Presiona Ctrl+C para interrumpir si es necesario"
echo ""

# Ejecutar entrenamiento
python3 REVOLUTIONARY_TRAINER.py

echo ""
echo "=============================================="
echo "🎉 SISTEMA REVOLUCIONARIO COMPLETADO"
echo ""
echo "📁 ARCHIVOS GENERADOS:"
echo "   • revolutionary_brain_final.pth - Cerebro entrenado"
echo "   • revolutionary_brain_best.pth  - Mejor versión"
echo "   • api/revolutionary_api.py     - API de producción"
echo ""
echo "🚀 PARA USAR EL SISTEMA:"
echo "   1. Ejecutar API: python3 api/revolutionary_api.py"
echo "   2. Conectar dashboard: http://localhost:5002"
echo "   3. Integrar con exchange para trading real"
echo ""
echo "💡 CONSEJO:"
echo "   Comienza con demo, luego escala gradualmente"
echo "   Siempre usa stop-loss y gestión de riesgo"
echo ""
echo "📞 SOPORTE:"
echo "   El cerebro está diseñado para auto-mejorarse"
echo "   Monitorea performance y ajusta parámetros"
echo ""
echo "=============================================="
echo "🧠 EL CEREBRO ESTÁ LISTO PARA REVOLUCIONAR EL TRADING"
echo "=============================================="