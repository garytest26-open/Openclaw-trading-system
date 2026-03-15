#!/bin/bash

# ============================================
# Script de Instalación Automática para VPS
# Bot de Trading - Turtle Breakout Strategy
# ============================================

set -e  # Salir si hay error

echo "=========================================="
echo "  Instalación del Bot de Trading"
echo "=========================================="
echo ""

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # Sin color

# Función para imprimir mensajes
print_message() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[ADVERTENCIA]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Detectar sistema operativo
print_message "Detectando sistema operativo..."
if [ -f /etc/debian_version ]; then
    OS="debian"
    print_message "Sistema detectado: Debian/Ubuntu"
elif [ -f /etc/redhat-release ]; then
    OS="redhat"
    print_message "Sistema detectado: RedHat/CentOS"
else
    print_warning "Sistema operativo no reconocido. Continuando de todas formas..."
    OS="unknown"
fi

# Actualizar sistema
print_message "Actualizando sistema..."
if [ "$OS" = "debian" ]; then
    sudo apt-get update
    sudo apt-get upgrade -y
elif [ "$OS" = "redhat" ]; then
    sudo yum update -y
fi

# Instalar Python 3 y pip
print_message "Verificando instalación de Python 3..."
if ! command -v python3 &> /dev/null; then
    print_message "Instalando Python 3..."
    if [ "$OS" = "debian" ]; then
        sudo apt-get install -y python3 python3-pip python3-venv
    elif [ "$OS" = "redhat" ]; then
        sudo yum install -y python3 python3-pip
    fi
else
    PYTHON_VERSION=$(python3 --version)
    print_message "Python ya instalado: $PYTHON_VERSION"
fi

# Instalar pip si no está disponible
if ! command -v pip3 &> /dev/null; then
    print_message "Instalando pip..."
    if [ "$OS" = "debian" ]; then
        sudo apt-get install -y python3-pip
    elif [ "$OS" = "redhat" ]; then
        sudo yum install -y python3-pip
    fi
fi

# Crear entorno virtual
print_message "Creando entorno virtual..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    print_message "Entorno virtual creado exitosamente"
else
    print_warning "El entorno virtual ya existe. Saltando creación..."
fi

# Activar entorno virtual
print_message "Activando entorno virtual..."
source venv/bin/activate

# Actualizar pip
print_message "Actualizando pip..."
pip install --upgrade pip

# Instalar dependencias
print_message "Instalando dependencias desde requirements.txt..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    print_message "Dependencias instaladas exitosamente"
else
    print_error "No se encontró requirements.txt"
    exit 1
fi

# Verificar archivo .env
print_message "Verificando configuración..."
if [ ! -f ".env" ]; then
    print_warning "No se encontró archivo .env"
    if [ -f ".env.example" ]; then
        print_message "Copiando .env.example a .env..."
        cp .env.example .env
        print_warning "IMPORTANTE: Edita el archivo .env con tus credenciales:"
        print_warning "  nano .env"
        print_warning "  o"
        print_warning "  vim .env"
    else
        print_error "No se encontró .env.example. Debes crear .env manualmente."
    fi
else
    print_message "Archivo .env encontrado"
fi

# Configurar permisos del archivo .env
if [ -f ".env" ]; then
    print_message "Configurando permisos de .env..."
    chmod 600 .env
    print_message "Permisos configurados (600 - solo lectura/escritura para el propietario)"
fi

# Hacer ejecutables los scripts
print_message "Configurando permisos de scripts..."
chmod +x iniciar_bot.sh
chmod +x setup_vps.sh

# Verificar instalación
print_message "Verificando instalación..."
python3 -c "import ccxt, pandas; print('Librerías principales importadas exitosamente')"

echo ""
echo "=========================================="
echo -e "${GREEN}  ✓ Instalación completada${NC}"
echo "=========================================="
echo ""
print_message "Próximos pasos:"
echo "  1. Edita el archivo .env con tus credenciales:"
echo "     nano .env"
echo ""
echo "  2. Ejecuta el bot manualmente para probar:"
echo "     ./iniciar_bot.sh"
echo ""
echo "  3. O instala como servicio systemd (ver GUIA_VPS.md):"
echo "     sudo cp trading-bot.service /etc/systemd/system/"
echo "     sudo systemctl enable trading-bot"
echo "     sudo systemctl start trading-bot"
echo ""
