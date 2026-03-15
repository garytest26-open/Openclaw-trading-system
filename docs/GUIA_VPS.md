# 📘 Guía Completa: Configuración del Bot en VPS

Esta guía te ayudará a configurar tu bot de trading para que funcione 24/7 en un servidor VPS (Virtual Private Server).

## 📋 Requisitos Previos

- **VPS con Linux**: Ubuntu 22.04 LTS o Debian 11/12 (recomendado)
- **Especificaciones mínimas**: 
  - 1 CPU
  - 1GB RAM
  - 10GB almacenamiento
- **Acceso SSH** al VPS
- **Credenciales del exchange** (API keys o Private Key para Hyperliquid)

## 💰 Proveedores de VPS Recomendados

| Proveedor | Precio Aprox. | Características |
|-----------|---------------|-----------------|
| **DigitalOcean** | $6/mes | Fácil de usar, buen soporte |
| **Vultr** | $5/mes | Económico, muchas ubicaciones |
| **Linode** | $5/mes | Confiable, buena documentación |
| **AWS EC2** | Variable | Profesional, capa gratuita disponible |
| **Google Cloud** | Variable | Créditos gratis para nuevos usuarios |

---

## 🚀 Paso 1: Contratar y Acceder al VPS

### 1.1 Contratar VPS

1. Ve al sitio web de tu proveedor preferido
2. Selecciona **Ubuntu 22.04 LTS** como sistema operativo
3. Elige el plan más básico (suficiente para el bot)
4. Completa el pago y espera a que se active

### 1.2 Obtener Credenciales SSH

El proveedor te enviará:
- **Dirección IP** del servidor (ej: `123.45.67.89`)
- **Usuario** (normalmente `root` o `ubuntu`)
- **Contraseña** o **clave SSH**

### 1.3 Conectar por SSH

**En Windows** (usando PowerShell o CMD):
```bash
ssh root@123.45.67.89
```

**En Windows** (usando PuTTY):
1. Descarga PuTTY desde https://www.putty.org/
2. Ingresa la IP en "Host Name"
3. Click en "Open"
4. Ingresa usuario y contraseña

**En Mac/Linux**:
```bash
ssh root@123.45.67.89
```

> **Nota**: La primera vez te pedirá confirmar la conexión, escribe `yes` y presiona Enter.

---

## 📤 Paso 2: Subir Archivos al VPS

Tienes varias opciones para transferir los archivos del bot a tu VPS:

### Opción A: FileZilla (GUI - Más fácil para principiantes)

1. **Descargar FileZilla**: https://filezilla-project.org/
2. **Conectar al VPS**:
   - Host: `sftp://123.45.67.89`
   - Usuario: `root`
   - Contraseña: tu contraseña
   - Puerto: `22`
3. **Arrastrar archivos** desde tu PC (izquierda) al VPS (derecha)

### Opción B: SCP (Línea de comandos)

**Desde Windows PowerShell**:
```bash
scp -r C:\Users\francisco\.gemini\antigravity\scratch\algo_trading_agent root@123.45.67.89:/root/
```

**Desde Mac/Linux**:
```bash
scp -r /ruta/al/proyecto root@123.45.67.89:/root/
```

### Opción C: Git (Recomendado si usas GitHub)

**En el VPS**:
```bash
cd /root
git clone https://github.com/tu-usuario/tu-repositorio.git
cd tu-repositorio
```

> ⚠️ **ADVERTENCIA**: Si usas Git, asegúrate de que el archivo `.env` esté en `.gitignore` para no subir tus credenciales a GitHub.

### Archivos que DEBES subir:
```
algo_trading_agent/
├── live_bot.py
├── config.py
├── requirements.txt
├── .env                    # ⚠️ CON TUS CREDENCIALES
├── setup_vps.sh
├── iniciar_bot.sh
└── trading-bot.service
```

---

## ⚙️ Paso 3: Ejecutar Script de Instalación

Una vez conectado al VPS y con los archivos transferidos:

```bash
# Ir al directorio del proyecto
cd /root/algo_trading_agent

# Dar permisos de ejecución al script
chmod +x setup_vps.sh

# Ejecutar instalación
./setup_vps.sh
```

Este script automáticamente:
- ✅ Detecta tu sistema operativo
- ✅ Actualiza el sistema
- ✅ Instala Python 3 y pip
- ✅ Crea el entorno virtual
- ✅ Instala todas las dependencias
- ✅ Configura permisos de seguridad

**Tiempo estimado**: 2-5 minutos

---

## 🔐 Paso 4: Configurar Credenciales (.env)

### 4.1 Si NO subiste tu archivo .env

El script habrá creado un `.env` desde `.env.example`. Editalo:

```bash
nano .env
```

### 4.2 Configurar para Hyperliquid

```bash
WALLET_ADDRESS=0xTuWalletAddressAqui
PRIVATE_KEY=0xTuPrivateKeyAqui
```

### 4.3 Configurar para otros exchanges (Binance, Bybit)

```bash
EXCHANGE_API_KEY=tu_api_key_aqui
EXCHANGE_SECRET=tu_secret_aqui
```

**Guardar cambios**:
- Presiona `Ctrl + O` (guardar)
- Presiona `Enter` (confirmar)
- Presiona `Ctrl + X` (salir)

### 4.4 Verificar permisos de seguridad

```bash
chmod 600 .env
ls -la .env
```

Deberías ver: `-rw-------` (solo el dueño puede leer/escribir)

---

## 🤖 Paso 5: Probar el Bot Manualmente

Antes de configurar el servicio automático, prueba que funcione:

```bash
./iniciar_bot.sh
```

**Deberías ver**:
```
Iniciando el Bot de Trading...
==============================
[INFO] Activando entorno virtual...
[INFO] Ejecutando live_bot.py...

2026-01-27 20:00:00 - INFO - Bot Inicializado. Estrategia: TURTLE_BREAKOUT
2026-01-27 20:00:00 - INFO - Símbolo: BTC/USDC:USDC, Temporalidad: 1d
2026-01-27 20:00:00 - INFO - Modo Dry Run (Simulación): True
...
```

**Para detener**: Presiona `Ctrl + C`

Si hay errores, revisa:
- Archivo `.env` correctamente configurado
- Credenciales válidas del exchange
- Conexión a internet del VPS

---

## 🔄 Paso 6: Configurar Servicio Systemd (Ejecución Automática)

Para que el bot se ejecute automáticamente y se reinicie si falla:

### 6.1 Editar archivo de servicio

Primero, edita `trading-bot.service` para ajustar las rutas:

```bash
nano trading-bot.service
```

**Cambia** `YOUR_USERNAME` por tu usuario real. Si usas `root`:
- Reemplaza `/home/YOUR_USERNAME/` con `/root/`
- Reemplaza `User=YOUR_USERNAME` con `User=root`

**Ejemplo para usuario root**:
```ini
[Service]
Type=simple
User=root
WorkingDirectory=/root/algo_trading_agent
Environment="PATH=/root/algo_trading_agent/venv/bin"
ExecStart=/root/algo_trading_agent/venv/bin/python3 /root/algo_trading_agent/live_bot.py
```

### 6.2 Instalar el servicio

```bash
# Copiar archivo a systemd
sudo cp trading-bot.service /etc/systemd/system/

# Recargar systemd para que reconozca el nuevo servicio
sudo systemctl daemon-reload

# Habilitar inicio automático
sudo systemctl enable trading-bot

# Iniciar el servicio
sudo systemctl start trading-bot
```

### 6.3 Verificar que esté funcionando

```bash
sudo systemctl status trading-bot
```

Deberías ver: `Active: active (running)`

---

## 📊 Paso 7: Comandos Útiles para Gestión del Bot

### Ver logs en tiempo real
```bash
sudo journalctl -u trading-bot -f
```

### Ver últimas 100 líneas de logs
```bash
sudo journalctl -u trading-bot -n 100
```

### Ver logs de hoy
```bash
sudo journalctl -u trading-bot --since today
```

### Reiniciar el bot
```bash
sudo systemctl restart trading-bot
```

### Detener el bot
```bash
sudo systemctl stop trading-bot
```

### Ver estado del bot
```bash
sudo systemctl status trading-bot
```

### Deshabilitar inicio automático
```bash
sudo systemctl disable trading-bot
```

### Ver archivo de log tradicional
```bash
tail -f /root/algo_trading_agent/trading_bot.log
```

---

## 🔧 Solución de Problemas

### El bot no inicia

```bash
# Ver detalles del error
sudo journalctl -u trading-bot -n 50

# Verificar sintaxis de Python
cd /root/algo_trading_agent
source venv/bin/activate
python3 -c "import live_bot"
```

### El bot se detiene inesperadamente

```bash
# Ver logs del crash
sudo journalctl -u trading-bot --since "10 minutes ago"

# Verificar recursos del sistema
free -h          # Memoria
df -h           # Disco
top             # CPU y procesos
```

### Cambios en el código no se aplican

```bash
# Después de editar archivos, reinicia el servicio
sudo systemctl restart trading-bot
```

### Actualizar dependencias

```bash
cd /root/algo_trading_agent
source venv/bin/activate
pip install --upgrade -r requirements.txt
sudo systemctl restart trading-bot
```

### Errores de exchange/API

```bash
# Verificar configuración
cat .env

# Verificar conexión
cd /root/algo_trading_agent
source venv/bin/activate
python3 verificar_configuracion.py
```

---

## 🛡️ Recomendaciones de Seguridad

### 1. Configurar Firewall

```bash
# Instalar UFW
sudo apt-get install ufw

# Permitir SSH
sudo ufw allow 22/tcp

# Habilitar firewall
sudo ufw enable
```

### 2. Cambiar puerto SSH (opcional pero recomendado)

```bash
sudo nano /etc/ssh/sshd_config
# Cambiar: Port 22  →  Port 2222
sudo systemctl restart sshd

# Actualizar firewall
sudo ufw allow 2222/tcp
sudo ufw delete allow 22/tcp
```

### 3. Crear usuario no-root (recomendado)

```bash
# Crear nuevo usuario
adduser trader

# Darle privilegios sudo
usermod -aG sudo trader

# Copiar archivos
cp -r /root/algo_trading_agent /home/trader/
chown -R trader:trader /home/trader/algo_trading_agent

# Actualizar rutas en trading-bot.service
```

### 4. Configurar fail2ban (protección contra ataques)

```bash
sudo apt-get install fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

### 5. Backups automáticos del estado

```bash
# Crear script de backup
nano /root/backup_bot.sh
```

Contenido:
```bash
#!/bin/bash
cp /root/algo_trading_agent/bot_state.json /root/backups/bot_state_$(date +%Y%m%d_%H%M%S).json
```

```bash
chmod +x /root/backup_bot.sh

# Agregar a crontab (cada 6 horas)
crontab -e
# Agregar: 0 */6 * * * /root/backup_bot.sh
```

---

## 📈 Monitoreo y Mantenimiento

### Verificar que el bot está operando

```bash
# Ver logs recientes
sudo journalctl -u trading-bot -n 20

# Ver archivo de estado
cat /root/algo_trading_agent/bot_state.json
```

### Monitoreo semanal recomendado

1. **Revisar logs** para errores
2. **Verificar bot_state.json** para ver posiciones
3. **Actualizar sistema operativo**:
   ```bash
   sudo apt-get update && sudo apt-get upgrade -y
   ```

### Actualizar el bot con nuevo código

```bash
# Detener bot
sudo systemctl stop trading-bot

# Actualizar archivos (FileZilla, SCP, o Git)
cd /root/algo_trading_agent
git pull  # Si usas Git

# Actualizar dependencias si cambiaron
source venv/bin/activate
pip install --upgrade -r requirements.txt

# Reiniciar bot
sudo systemctl start trading-bot
```

---

## ✅ Checklist de Configuración Completa

- [ ] VPS contratado y accesible por SSH
- [ ] Archivos del bot transferidos al VPS
- [ ] Script `setup_vps.sh` ejecutado exitosamente
- [ ] Archivo `.env` configurado con credenciales correctas
- [ ] Bot probado manualmente con `./iniciar_bot.sh`
- [ ] Servicio systemd instalado y habilitado
- [ ] Bot ejecutándose automáticamente
- [ ] Logs verificados sin errores
- [ ] Firewall configurado (opcional)
- [ ] Backups configurados (opcional)

---

## 🆘 Soporte

Si encuentras problemas:

1. **Revisa logs**: `sudo journalctl -u trading-bot -n 100`
2. **Verifica configuración**: `cat .env`
3. **Prueba manualmente**: `./iniciar_bot.sh`
4. **Consulta documentación** del exchange que uses

---

## 📝 Notas Finales

- ✅ El bot ahora funciona 24/7
- ✅ Se reinicia automáticamente si falla
- ✅ Inicia automáticamente cuando el VPS se reinicia
- ✅ Los logs se guardan en `journalctl` y en `trading_bot.log`

**¡Tu bot está listo para operar de forma autónoma!** 🚀
