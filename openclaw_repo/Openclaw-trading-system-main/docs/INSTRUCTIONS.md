# 📊 Swarm Trading AI Dashboard - Instrucciones de Acceso

## 🌐 **Acceso Remoto desde tu Ordenador**

El dashboard está diseñado para que puedas monitorear las estrategias en tiempo real desde cualquier navegador web.

### **1. Obtén la IP de tu VPS**

```bash
# En el VPS, ejecuta:
hostname -I
```

Ejemplo de salida:
```
172.31.91.130
```

### **2. Inicia el Dashboard**

```bash
cd /home/ubuntu/.openclaw/workspace
./trading/dashboard/start_dashboard.sh
```

El dashboard se iniciará en el puerto **5000**.

### **3. Accede desde tu Navegador**

Abre tu navegador y visita:
```
http://TU_IP_VPS:5000
```

Ejemplo:
```
http://172.31.91.130:5000
```

---

## 🔧 **Configuración del Firewall (IMPORTANTE)**

Para que funcione, el puerto 5000 debe estar abierto:

### **AWS/GCP/Azure (Security Groups)**
1. Ve a la consola de tu proveedor cloud
2. Encuentra el security group de tu VPS
3. Agrega una regla de entrada:
   - **Tipo:** HTTP (o Custom TCP)
   - **Puerto:** 5000
   - **Origen:** 0.0.0.0/0 (o tu IP específica)
   - **Descripción:** Swarm Trading Dashboard

### **Firewall del VPS (UFW)**
```bash
# Permitir puerto 5000
sudo ufw allow 5000/tcp
sudo ufw reload

# Verificar estado
sudo ufw status
```

---

## 📱 **Características del Dashboard**

### **Paneles Principales:**

1. **📈 Market Overview**
   - Precios en tiempo real de BTC, ETH, SOL
   - Cambios porcentuales
   - Volumen de trading

2. **🤖 Agent Predictions**
   - Señales de cada agente neural
   - Niveles de confianza
   - Fuerza de la señal

3. **🐝 Swarm Consensus**
   - Decisión colectiva del enjambre
   - Acuerdo entre agentes
   - Ponderación de votos

4. **📊 Charts & Analytics**
   - Gráficos de precios históricos
   - Rendimiento de agentes
   - Correlaciones entre activos

5. **💱 Trade History**
   - Historial de operaciones
   - P&L por trade
   - Estadísticas de rendimiento

---

## ⚙️ **Configuración Avanzada**

### **Modo de Datos Reales (Post-Entrenamiento)**
Una vez entrenados los agentes, el dashboard puede mostrar datos reales:

```python
# En app.py, cambiar:
mock_system = MockTradingSystem()

# Por:
real_system = SwarmTradingSystem("trading/swarm_ai/config/swarm_config.json")
```

### **Personalizar Puerto**
Si el puerto 5000 está ocupado:

```bash
# Editar app.py, línea ~210:
socketio.run(app, host='0.0.0.0', port=8080, ...)

# O usar variable de entorno:
export DASHBOARD_PORT=8080
./start_dashboard.sh
```

### **Acceso HTTPS (Recomendado para producción)**
```bash
# Usar Nginx como proxy inverso
sudo apt install nginx
sudo nano /etc/nginx/sites-available/dashboard

# Configuración Nginx:
server {
    listen 80;
    server_name TU_DOMINIO_O_IP;
    
    location / {
        proxy_pass http://localhost:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}

# Habilitar y reiniciar
sudo ln -s /etc/nginx/sites-available/dashboard /etc/nginx/sites-enabled/
sudo systemctl restart nginx
```

---

## 🚨 **Solución de Problemas**

### **Problema: No puedo acceder al dashboard**
**Solución:**
```bash
# 1. Verificar que el dashboard está corriendo
ps aux | grep app.py

# 2. Verificar puerto abierto
netstat -tulpn | grep :5000

# 3. Probar acceso localmente en el VPS
curl http://localhost:5000

# 4. Verificar firewall
sudo iptables -L -n
```

### **Problema: Conexión lenta o intermitente**
**Solución:**
- Usar puerto 80/443 con Nginx
- Habilitar compresión en Nginx
- Reducir frecuencia de actualización (editar `app.py`)

### **Problema: No veo datos reales**
**Solución:**
```bash
# 1. Entrenar los agentes primero
cd trading/swarm_ai
./start_training.sh

# 2. Iniciar sistema de trading
python main.py --trade --test

# 3. Conectar dashboard al sistema real
```

---

## 📡 **Acceso Móvil**

El dashboard es responsive y funciona en:
- **Ordenadores** (Chrome, Firefox, Safari)
- **Tablets** (iPad, Android)
- **Móviles** (iPhone, Android)

### **Acceso Rápido desde Móvil**
1. Obtén la IP pública de tu VPS
2. Abre navegador en tu móvil
3. Visita: `http://IP_VPS:5000`
4. Agrega a pantalla de inicio (como app)

---

## 🔒 **Consideraciones de Seguridad**

### **Para Desarrollo/Pruebas:**
- Usar solo en redes de confianza
- No exponer datos sensibles
- Reiniciar servicio periódicamente

### **Para Producción:**
```bash
# 1. Autenticación básica
sudo apt install apache2-utils
sudo htpasswd -c /etc/nginx/.htpasswd usuario

# 2. Añadir a configuración Nginx:
auth_basic "Swarm Trading Dashboard";
auth_basic_user_file /etc/nginx/.htpasswd;

# 3. Certificado SSL (Let's Encrypt)
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d TU_DOMINIO
```

---

## 🚀 **Inicio Rápido**

### **Paso 1 - Iniciar Dashboard:**
```bash
cd /home/ubuntu/.openclaw/workspace
./trading/dashboard/start_dashboard.sh
```

### **Paso 2 - Abrir Navegador:**
```
http://[TU_IP_VPS]:5000
```

### **Paso 3 - Monitorear:**
- Ver señales en tiempo real
- Analizar rendimiento
- Ajustar estrategias

---

## 📞 **Soporte**

Si encuentras problemas:
1. Revisa logs: `trading/dashboard/logs/`
2. Verifica conexión: `ping TU_IP_VPS`
3. Consulta este documento
4. Contacta para soporte adicional

---

**¡Listo para monitorear tus estrategias en tiempo real! 🎯**