# 🚨 GUÍA DE RECUPERACIÓN DE EMERGENCIA

## 📋 SITUACIÓN: VPS FALLÓ - NECESITAS RESTAURAR EL SISTEMA

### **PASO 1: ACCEDER A GITHUB**
1. **Ve a:** https://github.com/garytest26-open/openclaw-trading-system
2. **Inicia sesión** con tu cuenta
3. **Verifica** que el repositorio existe y tiene archivos

### **PASO 2: CLONAR EN NUEVO VPS**
```bash
# En el NUEVO VPS:
git clone git@github.com:garytest26-open/openclaw-trading-system.git
cd openclaw-trading-system
```

### **PASO 3: RESTAURAR SISTEMA**
```bash
# Ejecutar script de recuperación
chmod +x backups/restore_system.sh
./backups/restore_system.sh
```

### **PASO 4: VERIFICAR INSTALACIÓN**
```bash
# Verificar estructura
ls -la /home/ubuntu/.openclaw/workspace/trading/

# Verificar scripts críticos
python3 /home/ubuntu/.openclaw/workspace/trading/swarm_ai/signal_generator.py --test
```

## 🔑 CLAVE SSH DE RESPALDO
Si necesitas la clave SSH para acceder al repositorio:

```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIM3UJd9Y7NZbUUeb00o3MoFZ3JCmsOP+w7XDzEUOPQKQ openclaw-backup@vps
```

**Guarda esta clave en un lugar seguro aparte de GitHub.**

## 📞 CONTACTOS DE EMERGENCIA
- **GitHub Support:** https://support.github.com
- **OpenClaw Docs:** https://docs.openclaw.ai
- **Backup Status:** Revisa /var/log/trading_backup.log

## 🎯 VERIFICACIÓN POST-RECUPERACIÓN
1. ✅ Todos los archivos presentes
2. ✅ Scripts ejecutables
3. ✅ Configuraciones intactas
4. ✅ Modelos de IA cargados
5. ✅ Sistema operativo nuevamente

## ⏱️ TIEMPO ESTIMADO DE RECUPERACIÓN
- **Clonar desde GitHub:** 1-2 minutos
- **Restaurar archivos:** 1 minuto
- **Verificación:** 2 minutos
- **Total:** 4-5 minutos

---

**⚠️ IMPORTANTE:** Esta guía asume que:
1. Tienes acceso a tu cuenta GitHub
2. La clave SSH está añadida a GitHub
3. El repositorio existe y tiene backups actualizados
4. Puedes acceder a un nuevo VPS con permisos similares

**Última actualización:** 2026-03-09
**Sistema:** OpenClaw Trading Swarm AI v1.0
