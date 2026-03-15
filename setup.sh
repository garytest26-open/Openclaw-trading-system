#!/bin/bash
# 🏦 OpenClaw Trading System - Setup Script
# Instalación completa del sistema de trading algorítmico

set -e  # Exit on error

echo "========================================================"
echo "🏦 OPENCLAW TRADING SYSTEM - INSTALACIÓN COMPLETA"
echo "========================================================"
echo "🇪🇸 Hora Madrid: $(TZ='Europe/Madrid' date '+%Y-%m-%d %H:%M CET')"
echo "💰 Sistema: Trading Algorítmico con IA Avanzada"
echo "📊 Versión: 1.0.0 (12 Marzo 2026)"
echo "========================================================"

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

print_step() {
    echo -e "\n${GREEN}✅${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠️ ${NC} $1"
}

print_error() {
    echo -e "${RED}❌${NC} $1"
}

# Verificar Python
print_step "Verificando Python 3.8+..."
python3 --version || { print_error "Python3 no encontrado"; exit 1; }

# Verificar pip
print_step "Verificando pip..."
pip3 --version || { print_error "pip3 no encontrado"; exit 1; }

# Crear estructura de directorios
print_step "Creando estructura de directorios..."
mkdir -p {dashboard,swarm_ai_advanced,real_trading,strategies,docs,scripts,configs,backups,logs}

# 1. INSTALAR DASHBOARD
print_step "Instalando Dashboard..."
cd dashboard
python3 -m venv venv || { print_error "Error creando venv"; exit 1; }
source venv/bin/activate

# Instalar dependencias dashboard
pip install --upgrade pip
pip install Flask==3.0.0 Flask-CORS==4.0.0 Werkzeug==3.0.1 Jinja2==3.1.2
pip install requests==2.31.0 python-dotenv==1.0.0

print_step "Dashboard instalado correctamente"
deactivate
cd ..

# 2. INSTALAR SWARM AI AVANZADO
print_step "Instalando Swarm AI Avanzado..."
cd swarm_ai_advanced
python3 -m venv venv || { print_error "Error creando venv"; exit 1; }
source venv/bin/activate

# Instalar PyTorch (CPU version - más ligero)
pip install torch==2.1.0 torchvision==0.16.0 --index-url https://download.pytorch.org/whl/cpu
pip install transformers==4.36.0 numpy==1.24.3 pandas==2.1.4 scikit-learn==1.3.2

print_step "Swarm AI instalado correctamente"
deactivate
cd ..

# 3. INSTALAR DEPENDENCIAS GENERALES
print_step "Instalando dependencias generales..."
pip3 install ccxt==4.1.0 schedule==1.2.0 python-telegram-bot==20.6
pip3 install yfinance==0.2.33 pandas-ta==0.3.14b0 plotly==5.18.0

# 4. CONFIGURAR ARCHIVOS DE EJEMPLO
print_step "Configurando archivos de ejemplo..."
if [ ! -f ".env" ]; then
    if [ -f "configs/.env.example" ]; then
        cp configs/.env.example .env
        print_warning "Archivo .env creado desde ejemplo. Edítalo con tus configuraciones."
    else
        print_warning "Creando .env básico..."
        cat > .env << EOF
# 🔒 OPENCLAW TRADING SYSTEM - CONFIGURACIÓN
# ⚠️  NUNCA SUBIR ESTE ARCHIVO A GITHUB

# bingX Demo API (testing)
BINGX_API_KEY="your_demo_api_key"
BINGX_SECRET_KEY="your_demo_secret_key"
BINGX_TESTNET=true

# Telegram Bot (opcional)
TELEGRAM_BOT_TOKEN="your_bot_token"
TELEGRAM_CHAT_ID="your_chat_id"

# Trading Parameters
INITIAL_CAPITAL=15.39
RISK_PER_TRADE=0.02  # 2%
STOP_LOSS_PCT=0.05   # 5%
TAKE_PROFIT_PCT=0.10 # 10%

# Dashboard
FLASK_SECRET_KEY="change_this_to_random_string"
FLASK_DEBUG=false
FLASK_PORT=5001

# Logging
LOG_LEVEL="INFO"
LOG_TO_FILE=true
EOF
    fi
else
    print_step "Archivo .env ya existe (preservado)"
fi

# 5. CONFIGURAR CRON AUTOMÁTICO
print_step "Configurando sistema automático..."
cd real_trading
chmod +x CRON_AUTOMATICO_BINGX.sh 2>/dev/null || print_warning "Script CRON no encontrado, se creará manualmente"

# Crear script CRON si no existe
if [ ! -f "CRON_AUTOMATICO_BINGX.sh" ]; then
    print_warning "Creando script CRON automático..."
    cat > CRON_AUTOMATICO_BINGX.sh << 'EOF'
#!/bin/bash
# SISTEMA AUTOMÁTICO BINGX - Genera señales cada hora
cd "$(dirname "$0")"
echo "========================================================"
echo "🏦 SISTEMA AUTOMÁTICO BINGX - $(date '+%Y-%m-%d %H:%M CET')"
echo "========================================================"
python3 -c "
import sys
sys.path.append('../swarm_ai_advanced')
try:
    from AGGRESSIVE_DUAL_SYSTEM import AggressiveDualTradingSystem
    import datetime
    import json
    
    system = AggressiveDualTradingSystem()
    signals = {}
    
    for symbol in ['BTC/USDT', 'ETH/USDT']:
        signal = system.generate_aggressive_signals(symbol)
        if signal:
            signals[symbol.replace('/', '_')] = {
                'signal': signal['final_signal'],
                'confidence': max(signal['safe_signal']['confidence'], signal['growth_signal']['confidence']),
                'position_pct': signal['total_position'] * 100,
                'regime': signal['market_regime'],
                'timestamp': datetime.datetime.utcnow().isoformat()
            }
    
    # Guardar en log
    with open('bingx_auto_signals.log', 'a') as f:
        for sym, data in signals.items():
            f.write(f\"{data['timestamp']} | {sym} | {data['signal']} | {data['position_pct']:.1f}% | {data['confidence']:.2f}\\n\")
    
    print(f\"✅ Señales generadas: {len(signals)}\")
    
except Exception as e:
    print(f\"❌ Error: {e}\")
    with open('bingx_auto_errors.log', 'a') as f:
        f.write(f\"{datetime.datetime.utcnow().isoformat()} | ERROR: {str(e)}\\n\")
"
echo "========================================================"
echo "✅ SISTEMA AUTOMÁTICO COMPLETADO"
echo "========================================================"
EOF
    chmod +x CRON_AUTOMATICO_BINGX.sh
fi
cd ..

# 6. CONFIGURAR GIT IGNORE
print_step "Configurando .gitignore..."
if [ ! -f ".gitignore" ]; then
    print_warning "Creando .gitignore básico..."
    cat > .gitignore << 'EOF'
# 🔒 SECURITY: NEVER commit sensitive files
.env
*.env
*.key
*.secret
*.pem

# Virtual environments
venv/
env/
.venv/

# Python
__pycache__/
*.py[cod]
*.so
*.egg-info/

# Logs
*.log
logs/
cron.log

# Trading system
*.pth
*.pkl
*.h5
*.model
checkpoints/

# IDE
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db
EOF
else
    print_step ".gitignore ya existe (preservado)"
fi

# 7. CREAR SCRIPT DE INICIO
print_step "Creando scripts de inicio..."
cat > start_dashboard.sh << 'EOF'
#!/bin/bash
# Iniciar Dashboard OpenClaw
cd dashboard
source venv/bin/activate
echo "========================================================"
echo "🏦 OPENCLAW DASHBOARD - INICIANDO"
echo "========================================================"
echo "🌐 URL: http://localhost:5001"
echo "📊 Sistema: Trading Algorítmico con IA"
echo "🇪🇸 Hora: $(TZ='Europe/Madrid' date '+%H:%M CET')"
echo "========================================================"
python app.py
EOF
chmod +x start_dashboard.sh

cat > start_trading.sh << 'EOF'
#!/bin/bash
# Iniciar sistema de trading
cd real_trading
echo "========================================================"
echo "🏦 SISTEMA DE TRADING - INICIANDO"
echo "========================================================"
echo "💰 Capital: ~\$15.39 (bingX Demo)"
echo "⏰ Señales: Automáticas cada hora"
echo "🎯 Objetivo: Aprendizaje colaborativo"
echo "========================================================"
python3 -c "
import sys
sys.path.append('../swarm_ai_advanced')
from AGGRESSIVE_DUAL_SYSTEM import AggressiveDualTradingSystem
import datetime

print('🤖 Sistema Dual Agresivo inicializado...')
system = AggressiveDualTradingSystem()

print('\\n📊 GENERANDO SEÑAL INICIAL...')
for symbol in ['BTC/USDT', 'ETH/USDT']:
    signal = system.generate_aggressive_signals(symbol)
    if signal:
        print(f'   {symbol}: {signal[\"final_signal\"]} ({signal[\"total_position\"]*100:.1f}%)')
"
echo "========================================================"
echo "✅ Sistema listo. Configura CRON para automatización."
echo "📋 Comando CRON: crontab -e"
echo "   Añadir: 0 * * * * $(pwd)/real_trading/CRON_AUTOMATICO_BINGX.sh >> cron.log 2>&1"
echo "========================================================"
EOF
chmod +x start_trading.sh

# 8. MENSAJE FINAL
echo -e "\n${GREEN}========================================================${NC}"
echo -e "${GREEN}✅ INSTALACIÓN COMPLETADA EXITOSAMENTE${NC}"
echo -e "${GREEN}========================================================${NC}"
echo ""
echo -e "${YELLOW}📋 PRÓXIMOS PASOS:${NC}"
echo "1. ${GREEN}Editar archivo .env${NC} con tus configuraciones"
echo "2. ${GREEN}Iniciar Dashboard:${NC} ./start_dashboard.sh"
echo "3. ${GREEN}Iniciar Trading:${NC} ./start_trading.sh"
echo "4. ${GREEN}Configurar CRON:${NC} crontab -e"
echo "   Añadir: 0 * * * * $(pwd)/real_trading/CRON_AUTOMATICO_BINGX.sh >> cron.log 2>&1"
echo ""
echo -e "${YELLOW}🔧 SISTEMAS INSTALADOS:${NC}"
echo "• ${GREEN}Dashboard Web${NC} (Flask, puerto 5001)"
echo "• ${GREEN}Swarm AI Avanzado${NC} (PyTorch, Transformers)"
echo "• ${GREEN}Sistema Trading Automático${NC} (bingX Demo)"
echo "• ${GREEN}CRON jobs${NC} (señales horarias automáticas)"
echo ""
echo -e "${YELLOW}⚠️  IMPORTANTE:${NC}"
echo "• ${RED}NUNCA subir .env a GitHub${NC}"
echo "• Usar ${YELLOW}bingX Demo${NC} para aprendizaje"
echo "• ${YELLOW}Capital real solo después de testing extensivo${NC}"
echo ""
echo -e "${GREEN}🎯 ¡Sistema listo para trading educativo colaborativo!${NC}"
echo -e "${GREEN}🤝 IA genera señales, tú ejecutas (sin riesgo real)${NC}"
echo ""
echo -e "${GREEN}========================================================${NC}"
echo -e "${GREEN}🏦 OPENCLAW TRADING SYSTEM v1.0.0${NC}"
echo -e "${GREEN}📅 $(date '+%d/%m/%Y') - Hora Madrid: $(TZ='Europe/Madrid' date '+%H:%M CET')${NC}"
echo -e "${GREEN}========================================================${NC}"