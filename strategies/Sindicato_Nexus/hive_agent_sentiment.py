import time
import random
import threading
from hive_base_agent import HiveBaseAgent
from transformers import pipeline

class SentimentAgent(HiveBaseAgent):
    """
    Agente de Analisis de Sentimiento (NLP).
    En un entorno real de produccion, se conectaria a la API de Twitter/X 
    o un feed de noticias (ej. Bloomberg/NewsCrypto) via WebSockets.
    
    Aqui utilizamos un modelo Transformer (FinBERT) corriendo localmente 
    sobre titulares financieros simulados/descargados para generar la señal.
    """
    def __init__(self, asset: str = "SOL-USD"):
        super().__init__(agent_id=f"NLP_Sentiment_{asset}")
        self.asset = asset
        
        self.logger.info("Cargando modelo NLP (FinBERT)... Esto puede tardar unos segundos.")
        try:
            # Usamos un modelo liviano pre-entrenado para finanzas
            self.nlp_pipeline = pipeline("sentiment-analysis", model="ProsusAI/finbert")
            self.logger.info("✅ FinBERT cargado y listo en memoria.")
        except Exception as e:
            self.logger.error(f"Falla al cargar FinBERT. Usando fallback algoritmico: {e}")
            self.nlp_pipeline = None

    def _fetch_latest_headlines(self):
        """
        [MOCK] En produccion, esto debe ser reemplazado por la API de X
        o websockets de noticias financieras reales para el activo.
        """
        # Simulamos un stream de titulares
        mock_headlines = [
            f"Institutional money is flowing into {self.asset} at record volumes.",
            f"SEC files new lawsuit against major crypto exchanges regarding {self.asset}.",
            f"{self.asset} protocol upgrade successfully deployed on mainnet, network speeds double.",
            f"Major hack reported on a DeFi protocol heavily relying on {self.asset}.",
            f"Fidelity announces new spot ETF filing for {self.asset}.",
            f"{self.asset} shows consolidation pattern as volume drops significantly.",
            f"Rumors of massive VC sell-off hitting {self.asset} next week.",
            f"Overall market sentiment remains cautious but {self.asset} looks strong."
        ]
        return random.choice(mock_headlines)

    def _analyze_text(self, text: str):
        """Pasa el texto por FinBERT y lo convierte en una señal [-1.0 a 1.0]"""
        if not self.nlp_pipeline:
            # Fallback simulado
            return random.uniform(-1.0, 1.0), 0.5
            
        result = self.nlp_pipeline(text)[0]
        label = result['label'] # 'positive', 'negative', 'neutral'
        score = result['score'] # Confidence: 0.0 to 1.0
        
        # Mapeo a señal continua RL
        if label == 'positive':
            signal = 1.0
        elif label == 'negative':
            signal = -1.0
        else:
            signal = 0.0
            
        return signal, score

    def _run_loop(self):
        """Bucle infinito del agente, ejecutado en el daemon thread."""
        self.logger.info("Agent_Sentiment iniciado y monitoreando feeds...")
        
        while self.running:
            try:
                # 1. Obtener texto crudo (MOCK API)
                headline = self._fetch_latest_headlines()
                
                # 2. Análisis NLP con Transformer
                signal, confidence = self._analyze_text(headline)
                
                # 3. Publicar en Redis para el Master Node
                self.publish_signal(
                    asset=self.asset,
                    signal_value=signal,
                    confidence=confidence,
                    meta={"headline": headline, "model": "FinBERT"}
                )
                
                # Los sentimientos no cambian milisegundo a milisegundo,
                # iterar cada X segundos es suficiente.
                time.sleep(10)
                
            except Exception as e:
                self.logger.error(f"Error procesando NLP: {e}")
                time.sleep(5)

if __name__ == "__main__":
    # Test individual del Agente Sentimiento
    agent = SentimentAgent("SOL-USD")
    agent.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        agent.stop()
        print("Fin de prueba NLP.")
