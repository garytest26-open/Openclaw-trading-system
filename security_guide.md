# 🔒 GUÍA DE SEGURIDAD PARA TRADING ALGORÍTMICO

## 🚨 LECCIÓN APRENDIDA (COSTOSA)
**10 de Marzo 2026:** Robo de fondos por exposición de credenciales en GitHub.
- **Causa:** Archivo `.env` con claves reales subido a repositorio público
- **Mecanismo:** Bots automatizados escanean GitHub y roban en minutos
- **Consecuencia:** Pérdida financiera + compromiso de seguridad

## 📋 PROTOCOLOS DE SEGURIDAD OBLIGATORIOS

### 1. GESTIÓN DE CREDENCIALES

#### ✅ HACER:
- Usar **`.env.example`** con placeholders: `TU_API_KEY_AQUI`
- **NUNCA** commitear archivos `.env` reales
- Agregar a **`.gitignore`**: `.env`, `*.env`, `*.key`, `*.secret`
- Usar **variables de entorno del sistema** para producción
- Considerar **Hashicorp Vault** o **AWS Secrets Manager** para entornos profesionales

#### ❌ NO HACER:
- Hardcodear credenciales en código
- Usar credenciales reales en desarrollo
- Subir archivos sensibles a repositorios públicos
- Reutilizar credenciales entre entornos

### 2. ESTRUCTURA DE ARCHIVOS SEGURA

```
openclaw-trading-system/
├── .gitignore              # ✅ Obligatorio
├── .env.example           # ✅ Plantilla segura
├── strategies/
│   └── Sindicato_Nexus/
│       ├── config/        # ✅ Configuraciones sin credenciales
│       └── .gitkeep      # ✅ Mantener estructura
└── README_SECURITY.md    # ✅ Esta guía
```

### 3. WORKFLOW DE DESARROLLO SEGURO

#### Desarrollo Local:
```bash
# 1. Clonar repositorio
git clone <repo>

# 2. Copiar plantilla
cp .env.example .env

# 3. Editar .env LOCALMENTE (NO commit)
#    Usar credenciales de PRUEBA/SANDBOX

# 4. Agregar .env a .gitignore (si no está)
echo ".env" >> .gitignore
```

#### Producción:
```bash
# 1. Variables de entorno del sistema
export PRIVATE_KEY="0x..."
export API_KEY="tu_key"

# 2. O usar archivo .env FUERA del repositorio
#    Ej: /etc/trading/.env (solo lectura para app)
```

### 4. VERIFICACIONES PRE-COMMIT

#### Script de verificación (`pre-commit-hook.sh`):
```bash
#!/bin/bash
# Buscar credenciales hardcodeadas
if grep -r "0x[0-9a-fA-F]\{64\}" . --include="*.py" --include="*.js"; then
    echo "❌ ERROR: Claves privadas hardcodeadas encontradas"
    exit 1
fi

# Verificar que .env no está en staging
if git diff --cached --name-only | grep "\.env$"; then
    echo "❌ ERROR: No se puede commitear archivos .env"
    exit 1
fi
```

### 5. MONITOREO Y ALERTAS

#### Configurar alertas para:
- Commits que contengan patrones de credenciales
- Acceso no autorizado a repositorios
- Actividad sospechosa en cuentas de exchange
- Transacciones inusuales en wallets

## 🛡️ MEJORES PRÁCTICAS ESPECÍFICAS PARA CRYPTO

### Wallets de Desarrollo vs Producción:
- **Dev Wallet:** Fondos mínimos, solo para testing
- **Prod Wallet:** Fondos reales, hardware wallet preferible
- **Separación estricta:** Nunca mezclar

### APIs de Exchanges:
- **API Keys con permisos mínimos** (solo lectura si es posible)
- **IP Whitelisting** donde esté disponible
- **Rotación periódica** de claves
- **Monitoreo de uso** de API keys

### Backup de Frases Semilla:
- **NUNCA digital** (no fotos, no cloud, no texto)
- **Solo físico** (metal plates, papel en caja de seguridad)
- **Múltiples copias** en ubicaciones separadas
- **Sin conexión a Internet** nunca

## 🔧 HERRAMIENTAS RECOMENDADAS

### Para Desarrollo:
- **git-secrets** (AWS) - Prevenir commit de credenciales
- **truffleHog** - Escanear repositorios para secrets
- **pre-commit hooks** - Verificaciones automáticas

### Para Producción:
- **Hashicorp Vault** - Gestión centralizada de secrets
- **AWS Secrets Manager** / **GCP Secret Manager**
- **1Password Teams** / **LastPass Enterprise**

### Para Wallets:
- **Ledger Nano** / **Trezor** - Hardware wallets
- **MetaMask** (solo con prácticas seguras)
- **WalletConnect** para DApps

## 🚀 CHECKLIST DE IMPLEMENTACIÓN

### Inmediato:
- [ ] Verificar que `.gitignore` incluye `.env`
- [ ] Crear `.env.example` con placeholders
- [ ] Eliminar cualquier `.env` real del repositorio
- [ ] Escanear historial Git para credenciales residuales
- [ ] Educar a todo el equipo sobre esta guía

### Corto Plazo:
- [ ] Implementar pre-commit hooks
- [ ] Configurar alertas de seguridad
- [ ] Establecer wallets separadas (dev/prod)
- [ ] Documentar procedimientos de emergencia

### Largo Plazo:
- [ ] Migrar a sistema de gestión de secrets profesional
- [ ] Implementar autenticación multi-factor en todo
- [ ] Auditorías de seguridad periódicas
- [ ] Plan de respuesta a incidentes

## 📞 CONTACTO DE EMERGENCIA

### Si detectas credenciales expuestas:
1. **ROTAR inmediatamente** todas las credenciales afectadas
2. **REVOCAR permisos** en exchanges/wallets
3. **ESCANEAR** todos los sistemas relacionados
4. **DOCUMENTAR** el incidente para aprendizaje

### Soporte Técnico:
- Asistente OpenClaw: Disponible para auditorías de seguridad
- Comunidad: Discord/Telegram para mejores prácticas
- Profesionales: Considerar auditorías de seguridad pagas para sistemas críticos

---

**Recordatorio:** En crypto, **tú eres tu propio banco**. La seguridad es tu responsabilidad. Una sola brecha puede costar todo. Sé paranoico, sé meticuloso, sé seguro.

*Última actualización: 10 de Marzo 2026 - Después del incidente de seguridad*