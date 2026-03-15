# 🚀 ACCESO RÁPIDO AL DASHBOARD

## ✅ **DASHBOARD INICIADO Y FUNCIONANDO**

### **URL de Acceso:**
```
http://172.31.91.130:5000
```

### **Características Disponibles:**
1. **📈 Market Overview** - Precios BTC/ETH/SOL en tiempo real
2. **🤖 Agent Predictions** - Señales de agentes neurales
3. **🐝 Swarm Consensus** - Decisión colectiva del enjambre
4. **📊 Interactive Charts** - Gráficos con Plotly
5. **💱 Trade History** - Historial de operaciones

### **Datos Actuales:**
- **Modo:** Datos mock (simulados)
- **Actualización:** Cada 5 segundos
- **Agentes:** Trend, Reversal, Volatility
- **Activos:** BTC, ETH, SOL

---

## 🔧 **Configuración Necesaria:**

### **1. Firewall/Puertos:**
El puerto **5000** debe estar abierto en tu VPS:

```bash
# Para AWS/GCP/Azure:
# 1. Ve a la consola de tu proveedor cloud
# 2. Encuentra el security group de tu VPS
# 3. Añade regla de entrada:
#    - Tipo: Custom TCP
#    - Puerto: 5000
#    - Origen: 0.0.0.0/0 (o tu IP específica)
```

### **2. Acceso desde tu Ordenador:**
1. Abre tu navegador (Chrome, Firefox, Safari)
2. Visita: `http://172.31.91.130:5000`
3. ¡Listo! Verás el dashboard en tiempo real

---

## 📱 **Acceso Móvil:**
- El dashboard es **responsive**
- Funciona en iPhone, Android, iPad
- Misma URL: `http://172.31.91.130:5000`

---

## 🚨 **Solución de Problemas:**

### **Problema: No puedo acceder**
```bash
# Verifica que el dashboard está corriendo:
ps aux | grep app.py

# Verifica puerto:
ss -tulpn | grep :5000

# Test local:
curl http://localhost:5000
```

### **Problema: Puerto bloqueado**
```bash
# Abre puerto 5000 en firewall local:
sudo ufw allow 5000/tcp
sudo ufw reload
```

### **Problema: Conexión lenta**
- Usa Chrome o Firefox
- Verifica tu conexión a internet
- El dashboard actualiza cada 5 segundos

---

## 🔄 **Próximos Pasos:**

### **1. Entrenar Agentes Reales:**
```bash
cd /home/ubuntu/.openclaw/workspace/trading/swarm_ai
./start_training.sh
```
- 100 épocas
- 3 años de datos BTC/ETH/SOL
- ~30-60 minutos de entrenamiento

### **2. Conectar Datos Reales:**
Una vez entrenados los agentes, el dashboard mostrará:
- **Señales reales** de los agentes neurales
- **Consenso ponderado** del enjambre
- **Rendimiento histórico**
- **Backtesting results**

### **3. Trading en Testnet:**
- Conectar a Hyperliquid testnet
- Ejecutar estrategias automáticas
- Monitorear P&L en tiempo real

---

## 📞 **Soporte:**

Si encuentras problemas:
1. Revisa logs: `trading/dashboard/logs/`
2. Verifica IP: `hostname -I`
3. Test local: `curl http://localhost:5000`
4. Contacta para ayuda adicional

---

**¡Tu dashboard está listo para usar! 🎯**

Accede ahora: [http://172.31.91.130:5000](http://172.31.91.130:5000)