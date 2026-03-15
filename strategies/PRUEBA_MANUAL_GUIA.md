# 🧪 GUÍA DE PRUEBA MANUAL - SEÑALES POR TELEGRAM

## 📋 **OBJETIVO**
Probar el sistema Swarm AI optimizado mediante señales enviadas por Telegram que FRAN ejecuta manualmente, antes de implementar en testnet.

## 🎯 **METAS DE LA PRUEBA**
1. **Validar calidad de señales** en condiciones reales
2. **Confirmar performance** vs simulación (97.94% anual)
3. **Ajustar parámetros** basado en resultados reales
4. **Ganar confianza** antes de implementación automática

## ⏰ **DURACIÓN RECOMENDADA**
- **Mínimo:** 7 días (20-30 trades)
- **Óptimo:** 14 días (40-60 trades)
- **Horario:** 08:00-20:00 UTC (horario activo de trading)

## 📊 **MÉTRICAS A EVALUAR**
- **Win rate objetivo:** >55%
- **Profit factor objetivo:** >1.8
- **Average win/loss ratio:** >1.5
- **Consistencia:** Señales diarias estables

## 🚀 **SISTEMA IMPLEMENTADO**

### **1. Generador de Señales (`signal_generator.py`)**
- Analiza condiciones de mercado en tiempo real
- Aplica filtros inteligentes (volatilidad, volumen, tendencia)
- Genera señales con confianza >70%
- Calcula stops dinámicos basados en ATR
- Define take-profits escalonados

### **2. Monitor de Señales (`signal_monitor.py`)**
- Chequea mercado cada 30 minutos
- Envía máximo 3 señales diarias
- Respeta horario de trading (08:00-20:00 UTC)
- Mantiene historial completo
- Genera reportes diarios

### **3. Configuración Optimizada**
- **Estrategia híbrida:** Trend 40% + Mean Reversion 30% + Breakout 30%
- **Gestión de riesgo:** Stops dinámicos, posición escalonada
- **Filtros:** Volatilidad <4%, volumen >100% promedio
- **Capital base:** $10,000 (ajustable)

## 📱 **PROCESO DE PRUEBA**

### **Paso 1: Generación de Señal**
```
1. Sistema analiza mercado
2. Si condiciones son óptimas → genera señal
3. Formatea mensaje para Telegram
4. Yo te envío el mensaje completo
```

### **Paso 2: Ejecución Manual (FRAN)**
```
1. Recibes mensaje en Telegram
2. Verificas condiciones actuales
3. Ejecutas trade según señal
4. Configuras stop-loss y take-profits
5. Confirmas ejecución
```

### **Paso 3: Seguimiento y Reporte**
```
1. Monitoreas trade en tiempo real
2. Cuando se cierra (stop o take-profit)
3. Reportas resultado (ganancia/pérdida %)
4. Registramos en historial
```

### **Paso 4: Análisis y Ajuste**
```
1. Diario: Revisamos performance
2. Semanal: Ajustamos parámetros si es necesario
3. Final: Decidimos implementación en testnet
```

## 💬 **FORMATO DE MENSAJE (Ejemplo)**

```
🟢 *SEÑAL DE TRADING* 📈

*ID:* `SIG-20260309-1002-001`
*Hora:* 10:02 UTC

*🎯 ACTIVO:* BTC
*📊 TIPO:* Trend Following
*🧭 DIRECCIÓN:* LONG (COMPRA)

*💰 PRECIOS:*
• Entrada: $51,250.75
• Stop Loss: $49,850.25
• Take Profits: $52,015.01 / $53,044.53 / $54,838.30

*📈 POSICIÓN:*
• Tamaño: $615.00 (6.15% del capital)
• Confianza: 82%
• Risk/Reward: 1:1.8

*⚠️ RIESGO:*
• Pérdida máxima: $184.50 (1.85%)
• Límite diario: 3%
• Límite semanal: 8%

*✅ ACCIÓN REQUERIDA:*
1. Ejecutar LONG en BTC a $51,250.75
2. Colocar Stop Loss en $49,850.25
3. Colocar Take Profits en niveles indicados
4. Reportar resultado cuando cierre
```

## ⚙️ **CONFIGURACIÓN PERSONALIZABLE**

### **Parámetros Ajustables:**
```json
{
  "capital": 10000,               // Capital base para cálculo
  "max_signals_per_day": 3,       // Máximo señales diarias
  "trading_hours": {              // Horario activo
    "start": 8,                   // 08:00 UTC
    "end": 20                     // 20:00 UTC
  },
  "min_confidence": 0.70,         // Confianza mínima
  "min_volume_ratio": 1.0,        // Volumen mínimo
  "max_volatility_pct": 4.0       // Volatilidad máxima
}
```

### **Estrategias Disponibles:**
1. **Trend Following** (40%): Captura tendencias sostenidas
2. **Mean Reversion** (30%): Opera en rangos laterales
3. **Breakout Trading** (30%): Captura movimientos explosivos

## 📈 **REGISTRO DE RESULTADOS**

### **Archivos Generados:**
```
signal_results/
├── SIG-20260309-1002-001.txt     # Mensaje Telegram
├── SIG-20260309-1002-001.json    # Datos completos
├── daily_report_2026-03-09.json  # Reporte diario
└── signal_history.json           # Historial completo
```

### **Estadísticas que Monitorearemos:**
- **Win Rate:** % de trades ganadores
- **Profit Factor:** (Ganancias totales) / (Pérdidas totales)
- **Average Win:** % promedio de trades ganadores
- **Average Loss:** % promedio de trades perdedores
- **Max Drawdown:** Máxima pérdida consecutiva
- **Sharpe Ratio:** Retorno ajustado por riesgo

## ⚠️ **CONSIDERACIONES IMPORTANTES**

### **Para FRAN:**
1. **Ejecuta solo** si el tamaño de posición es adecuado para tu capital
2. **Considera fees y slippage** en la ejecución real
3. **Respeta los stops** - no modifiques durante el trade
4. **Reporta resultados** honestamente para análisis preciso
5. **Comunica problemas** de ejecución inmediatamente

### **Limitaciones del Sistema:**
1. **Señales basadas en simulación** hasta que tengamos datos reales
2. **Mercado 24/7** pero solo operamos en horario activo
3. **Condiciones extremas** pueden generar menos señales
4. **Requiere disciplina** en la ejecución manual

## 🎮 **MODOS DE OPERACIÓN**

### **Modo 1: Prueba Controlada (Recomendado)**
- Yo envío señales cuando sistema las genera
- Tú ejecutas y reportas resultados
- Ajustamos semanalmente basado en performance

### **Modo 2: Autónomo**
- Sistema envía señales automáticamente por Telegram
- Tú ejecutas cuando recibes notificación
- Menos interacción, más similar a testnet

### **Modo 3: Hiperactivo**
- Más señales diarias (hasta 5)
- Menos filtros conservadores
- Para validación rápida pero más riesgosa

## 📋 **CHECKLIST DE IMPLEMENTACIÓN**

### **Antes de Comenzar:**
- [ ] Confirmar horario de disponibilidad de FRAN
- [ ] Ajustar capital base según realidad
- [ ] Configurar límites de pérdida personalizados
- [ ] Probar formato de mensaje en Telegram
- [ ] Establecer canal de reporte de resultados

### **Durante la Prueba:**
- [ ] Monitorear consistencia de señales
- [ ] Registrar todos los trades ejecutados
- [ ] Revisar performance diaria
- [ ] Ajustar parámetros si es necesario
- [ ] Mantener comunicación activa

### **Al Finalizar:**
- [ ] Analizar estadísticas completas
- [ ] Comparar con simulación (97.94% anual)
- [ ] Decidir implementación en testnet
- [ ] Documentar lecciones aprendidas
- [ ] Planificar fase de automatización

## 🚨 **PROTOCOLO DE SEGURIDAD**

### **Límites Estrictos:**
- **Máximo 3 señales diarias** (evita overtrading)
- **Stop loss obligatorio** en cada trade
- **Límite diario de pérdida:** 3% del capital
- **Límite semanal de pérdida:** 8% del capital
- **Revisión obligatoria** tras 3 pérdidas consecutivas

### **Condiciones de Parada:**
1. **Drawdown >15%** durante prueba → pausa y análisis
2. **5 pérdidas consecutivas** → revisión completa
3. **Win rate <40%** después de 20 trades → re-optimización
4. **Problemas de ejecución** consistentes → ajuste de parámetros

## 🎯 **CRITERIOS DE ÉXITO**

### **Para Continuar a Testnet:**
- **Win rate:** >55% después de 30 trades
- **Profit factor:** >1.8
- **Consistencia:** Señales diarias estables
- **Disciplina:** Ejecución correcta de stops/take-profits
- **Confianza:** FRAN comfortable con performance

### **Para Re-optimización:**
- **Win rate:** <50% después de 20 trades
- **Profit factor:** <1.5
- **Drawdown:** >20% durante prueba
- **Inconsistencia:** Performance muy variable

## 💡 **RECOMENDACIONES INICIALES**

1. **Comienza con capital pequeño** ($100-500) para prueba
2. **Ejecuta exactamente** como indica la señal
3. **No modifiques stops** durante el trade
4. **Reporta resultados** honestamente
5. **Comunica cualquier problema** inmediatamente
6. **Ten paciencia** - 7-14 días para datos significativos

## 📞 **COMUNICACIÓN**

### **Canal Principal:**
- **Telegram:** Señales y reportes de ejecución

### **Frecuencia:**
- **Señales:** 1-3 veces al día (cuando condiciones óptimas)
- **Reportes diarios:** Resumen de performance
- **Revisión semanal:** Análisis completo y ajustes

### **Formato de Reporte:**
```
✅ TRADE CERRADO
ID: SIG-20260309-1002-001
Resultado: +2.1% (Take Profit 1)
Tiempo: 3 horas 15 minutos
Comentarios: Ejecución correcta, slight slippage
```

## 🚀 **PRÓXIMOS PASOS**

### **Si la prueba es exitosa:**
1. Implementación en Hyperliquid testnet
2. Trading automático con capital simulado
3. Monitoreo 24/7 con dashboard
4. Escalado gradual a capital real

### **Si necesita ajustes:**
1. Re-optimización basada en datos reales
2. Ajuste de parámetros específicos
3. Segunda ronda de prueba manual
4. Validación antes de testnet

---

**✅ EL SISTEMA ESTÁ LISTO PARA PRUEBA MANUAL**

**¿Comenzamos hoy con la primera señal, FRAN?** 🎯