# Swarm Trading AI - Sistema de Enjambre de Agentes Neuronales

**Arquitectura avanzada para FRAN**
*Última actualización: 2026-03-09*

## 🧠 Visión General

Sistema de trading algorítmico que utiliza un enjambre de agentes neuronales especializados que colaboran para tomar decisiones de trading óptimas. Cada agente se especializa en un aspecto diferente del mercado, y un fusionador neuronal combina sus señales.

## 🏗️ Arquitectura del Sistema

```
swarm_ai/
├── agents/                    # Agentes especializados
│   ├── trend_agent.py        # Agente de tendencia (LSTM)
│   ├── reversal_agent.py     # Agente de reversión (CNN)
│   ├── volatility_agent.py   # Agente de volatilidad (Autoencoder)
│   ├── volume_agent.py       # Agente de volumen (Transformer)
│   └── sentiment_agent.py    # Agente de sentimiento (NLP)
├── swarm/                    # Mecanismos de enjambre
│   ├── swarm_coordinator.py  # Coordinador del enjambre
│   ├── consensus_engine.py   # Motor de consenso
│   └── evolutionary_opt.py   # Optimización evolutiva
├── models/                   # Modelos entrenados
├── training/                 # Scripts de entrenamiento
│   ├── data_preprocessor.py  # Preprocesamiento de datos
│   ├── trainer.py           # Entrenamiento de agentes
│   └── meta_trainer.py      # Entrenamiento del fusionador
├── data/                    # Datos para entrenamiento
└── config/                  # Configuración
    └── swarm_config.json    # Configuración del sistema
```

## 🤖 Agentes Especializados

### 1. **Trend Agent (LSTM)**
- **Arquitectura:** LSTM bidireccional + Attention
- **Input:** Secuencias temporales de precios (50-100 timesteps)
- **Output:** Probabilidad de tendencia alcista/bajista
- **Especialización:** Identificación de patrones de tendencia a mediano/largo plazo

### 2. **Reversal Agent (CNN)**
- **Arquitectura:** CNN 1D + Pooling
- **Input:** Matrices de precios normalizadas
- **Output:** Señales de sobrecompra/sobreventa
- **Especialización:** Detección de puntos de reversión

### 3. **Volatility Agent (Autoencoder)**
- **Arquitectura:** Autoencoder variacional (VAE)
- **Input:** Distribuciones de volatilidad
- **Output:** Anomalías y regímenes de mercado
- **Especialización:** Detección de cambios en volatilidad

### 4. **Volume Agent (Transformer)**
- **Arquitectura:** Transformer con atención multi-head
- **Input:** Secuencias de volumen y flujo de órdenes
- **Output:** Intensidad de interés de mercado
- **Especialización:** Análisis de flujo de volumen

### 5. **Sentiment Agent (NLP)**
- **Arquitectura:** BERT fine-tuned + LSTM
- **Input:** Noticias, tweets, datos on-chain
- **Output:** Score de sentimiento (-1 a +1)
- **Especialización:** Análisis de sentimiento de mercado

## 🐝 Mecanismo de Enjambre

### **Consenso Ponderado**
Cada agente vota con una confianza calculada:
```
Voto_final = Σ (voto_agente_i × confianza_agente_i × peso_agente_i)
```

### **Aprendizaje por Refuerzo Multi-Agente**
- Recompensas individuales y colectivas
- Cooperación vs competencia controlada
- Actualización de políticas con PPO

### **Evolución Diferencial**
- Optimización de hiperparámetros de agentes
- Selección natural de las mejores configuraciones
- Mutación y crossover de arquitecturas

## 🧩 Fusionador Neuronal

### **Meta-Learning Network**
- **Input:** Señales de todos los agentes + contexto de mercado
- **Arquitectura:** MLP profunda con skip connections
- **Output:** Señal de trading final + confianza
- **Entrenamiento:** Meta-aprendizaje con datos de múltiples mercados

## 📊 Pipeline de Datos

1. **Recolección:**
   - Precios OHLCV en múltiples timeframes
   - Datos de orden book
   - Noticias y sentimiento
   - Datos on-chain (para cripto)

2. **Preprocesamiento:**
   - Normalización adaptativa
   - Feature engineering avanzado
   - Augmentation de datos temporales

3. **Feature Engineering:**
   - 100+ features técnicos
   - Features de mercado microstructure
   - Embeddings de texto

## 🚀 Pipeline de Trading

```
[Market Data] → [Agentes Especializados] → [Swarm Consensus] 
      ↓                                       ↓
[Feature Engineering] ← [Fusionador Neuronal] → [Trade Signal]
      ↓                                       ↓
[Risk Management] → [Order Execution] → [Performance Tracking]
```

## ⚙️ Configuración Técnica

### **Requisitos:**
- Python 3.9+
- PyTorch 2.0+ / TensorFlow 2.15+
- GPU recomendada para entrenamiento
- 16GB+ RAM para datos en tiempo real

### **Hiperparámetros:**
- Tamaño de enjambre: 5-20 agentes
- Ventana temporal: 50-200 timesteps
- Frecuencia de trading: 1m - 1h
- Batch size: 32-256

## 📈 Métricas de Performance

### **Individuales por Agente:**
- Accuracy, Precision, Recall, F1-score
- Sharpe ratio individual
- Profit factor por agente

### **Colectivas del Enjambre:**
- Sharpe ratio del sistema
- Maximum drawdown
- Win rate consolidada
- Diversity score (medida de diversidad de agentes)

## 🔬 Características Avanzadas

1. **Transfer Learning:** Agentes pre-entrenados en múltiples mercados
2. **Online Learning:** Adaptación en tiempo real
3. **Explainable AI:** Interpretabilidad de decisiones
4. **Anomaly Detection:** Detección de regímenes de mercado anómalos
5. **Risk-Aware:** Incorporación de métricas de riesgo en el aprendizaje

## 🎯 Objetivos

1. **Corto plazo (1 mes):** Sistema básico funcionando en backtest
2. **Mediano plazo (3 meses):** Forward testing en paper trading
3. **Largo plazo (6 meses):** Live trading con gestión de capital conservadora

---

*Sistema en desarrollo - Arquitectura de vanguardia para trading algorítmico*