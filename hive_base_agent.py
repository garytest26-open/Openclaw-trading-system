import redis
import json
import time
import uuid
import threading
import logging

class HiveBaseAgent:
    """
    Clase base para todos los Micro-Agentes del enjambre Hive-Mind.
    Maneja la conexion a Redis, el envio de señales y el logging unificado.
    """
    def __init__(self, agent_id: str, redis_host: str = 'localhost', redis_port: int = 6379):
        self.agent_id = agent_id
        self.channel_name ="hive_mind_signals"
        
        # Configurar Logging
        self.logger = logging.getLogger(self.agent_id)
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            formatter = logging.Formatter(f'[%(asctime)s] [{self.agent_id}] %(levelname)s: %(message)s')
            ch = logging.StreamHandler()
            ch.setFormatter(formatter)
            self.logger.addHandler(ch)

        # Conectar a Redis
        try:
            self.redis_client = redis.Redis(host=redis_host, port=redis_port, db=0, decode_responses=True)
            self.redis_client.ping()
            self.logger.info("🟢 Conectado exitosamente al Bus de Mensajes (Redis).")
        except redis.ConnectionError:
            self.logger.error("🔴 ERROR CRÍTICO: No se pudo conectar a Redis.")
            self.logger.error("Asegúrate de tener el servidor Redis corriendo localmente (ej. WSL u oficial Windows port).")
            raise
            
        self.running = False
        self._worker_thread = None

    def publish_signal(self, asset: str, signal_value: float, confidence: float, meta: dict = None):
        """
        Publica una señal al cerebro central.
        signal_value: -1.0 (Fuerte Venta) a 1.0 (Fuerte Compra)
        confidence: 0.0 a 1.0
        """
        payload = {
            "msg_id": str(uuid.uuid4()),
            "timestamp": time.time(),
            "agent_id": self.agent_id,
            "asset": asset,
            "signal": signal_value,
            "confidence": confidence,
            "meta": meta or {}
        }
        
        try:
            # Publicar en el canal (Pub/Sub)
            self.redis_client.publish(self.channel_name, json.dumps(payload))
            self.logger.debug(f"↗️  Señal enviada: {asset} -> {signal_value}")
        except Exception as e:
            self.logger.error(f"Fallo al publicar señal: {e}")

    def _run_loop(self):
        """Bucle interno que los hijos deben sobreescribir con su lógica específica."""
        raise NotImplementedError("Los agentes hijos deben implementar _run_loop()")

    def _daemon_wrapper(self):
        self.logger.info(f"🚀 Iniciando micro-agente {self.agent_id}...")
        try:
            self._run_loop()
        except Exception as e:
            self.logger.error(f"Agente finalizado por error: {e}")
        finally:
            self.running = False

    def start(self):
        """Inicia el agente en un hilo separado (no bloqueante)."""
        if self.running:
            return
        self.running = True
        self._worker_thread = threading.Thread(target=self._daemon_wrapper, daemon=True)
        self._worker_thread.start()

    def stop(self):
        """Cierra el agente suavemente."""
        self.logger.info("🛑 Solicitando detención del agente...")
        self.running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=5)
