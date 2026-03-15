import redis
import json
import time
import threading
import logging
import pandas as pd
from collections import defaultdict

class HiveMasterNode:
    """
    El Cerebro Central del Enjambre.
    Se suscribe a Redis, escucha a todos los micro-agentes, 
    agrega sus señales por activo (Asset) y alimenta el Cerebro PPO cada 1 segundo.
    """
    def __init__(self, redis_host: str = 'localhost', redis_port: int = 6379):
        self.channel_name = "hive_mind_signals"
        
        # Estado Interno: { asset_name: { agent_id: { signal_value, confidence, timestamp } } }
        self.state = defaultdict(lambda: defaultdict(dict))
        
        self.logger = logging.getLogger("HiveMaster")
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            formatter = logging.Formatter('[%(asctime)s] [MASTER_NODE] 🧠 %(levelname)s: %(message)s')
            ch = logging.StreamHandler()
            ch.setFormatter(formatter)
            self.logger.addHandler(ch)

        try:
            self.redis_client = redis.Redis(host=redis_host, port=redis_port, db=0, decode_responses=True)
            self.pubsub = self.redis_client.pubsub()
            self.pubsub.subscribe(self.channel_name)
            self.logger.info("🟢 Master Node suscrito al bus de señales Redis.")
        except redis.ConnectionError:
            self.logger.error("🔴 ERROR CRÍTICO: El nodo maestro no pudo conectar a Redis.")
            raise

        self.running = False
        self._listener_thread = None

    def _listen_loop(self):
        """Hilo en segundo plano que ingiere señales 24/7 sin bloquear."""
        self.logger.info("Escuchando murmullo del enjambre (Pub/Sub Listener)...")
        for message in self.pubsub.listen():
            if not self.running:
                break
                
            if message['type'] == 'message':
                try:
                    payload = json.loads(message['data'])
                    agent = payload['agent_id']
                    asset = payload['asset']
                    
                    # Guardar la última señal del agente para el activo
                    self.state[asset][agent] = {
                        "signal": float(payload['signal']),
                        "confidence": float(payload['confidence']),
                        "timestamp": float(payload['timestamp'])
                    }
                    self.logger.debug(f"Input asimilado de {agent} para {asset}: {payload['signal']}")
                except Exception as e:
                    self.logger.error(f"Mensaje malformado ignorado: {e}")

    def start_listening(self):
        if self.running: return
        self.running = True
        self._listener_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._listener_thread.start()
        
    def stop_listening(self):
        self.running = False
        if self._listener_thread:
            # Emitir un mensaje tonto para despertar el pubsub iterador bloqueado
            self.redis_client.publish(self.channel_name, json.dumps({'type':'shutdown'}))
            self._listener_thread.join(timeout=2)
            
    def get_aggregated_state(self, asset: str, max_age_seconds: float = 5.0) -> dict:
        """
        Devuelve el estado "digerido" de todos los agentes para un activo.
        Ignora las señales más viejas que `max_age_seconds` (agentes muertos o retrasados).
        Retorna: { agent_id: signal_value, ... }
        """
        now = time.time()
        aggregated = {}
        
        agents_data = self.state.get(asset, {})
        for agent_id, data in agents_data.items():
            age = now - data['timestamp']
            if age <= max_age_seconds:
                # Basic aggregation logic: just pass the signal for the RL model to weigh it
                aggregated[agent_id] = data['signal'] * data['confidence']
            else:
                # Señal muerta (Stale)
                aggregated[agent_id] = 0.0 
                
        return aggregated

if __name__ == "__main__":
    # Prueba rápida del Nodo Central (Requiere Servidor Redis corriendo)
    print("Iniciando test del Master Node...")
    try:
        master = HiveMasterNode()
        master.start_listening()
        print("Master Node escuchando. Usa CTRL+C para apagar.")
        while True:
            time.sleep(1)
            estado = master.get_aggregated_state("SOL-USD")
            if estado:
                print(f"Estado de Enjambre (SOL-USD): {estado}")
    except KeyboardInterrupt:
        print("Apagando...")
        master.stop_listening()
