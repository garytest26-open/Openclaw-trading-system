import time
import json
import asyncio
import websockets
from hive_base_agent import HiveBaseAgent

class OrderFlowAgent(HiveBaseAgent):
    """
    Agente de Microestructura de Mercado (Order-Flow).
    Se conecta al L2 Book de Hyperliquid via WebSockets,
    calcula el desequilibrio entre el volumen de Bids vs Asks en tiempo real,
    y publica la señal al Cerebro Central.
    """
    def __init__(self, asset: str = "SOL"):
        super().__init__(agent_id=f"OrderFlow_L2_{asset}")
        self.asset = asset
        self.ws_url = "wss://api.hyperliquid.xyz/ws"
        
        # Hyperliquid usa el ticker puro para WS ('SOL' no 'SOL-USD')
        self.ws_payload = {
            "method": "subscribe",
            "subscription": {
                "type": "l2Book",
                "coin": self.asset
            }
        }

    async def _listen_to_book(self):
        self.logger.info(f"Conectando a {self.ws_url} para libro L2 de {self.asset}...")
        
        while self.running:
            try:
                async with websockets.connect(self.ws_url) as websocket:
                    # Enviar subscripcion
                    await websocket.send(json.dumps(self.ws_payload))
                    self.logger.info(f"✅ Suscrito al Order Book WebSocket de {self.asset}")
                    
                    while self.running:
                        response = await websocket.recv()
                        data = json.loads(response)
                        
                        if 'channel' in data and data['channel'] == 'l2Book':
                            # Calcular Imbalance
                            signal, confidence = self._calculate_imbalance(data['data'])
                            
                            self.publish_signal(
                                asset=f"{self.asset}-USD", # Standarized hive nomenclature
                                signal_value=signal,
                                confidence=confidence,
                                meta={"source": "HL_L2_Book"}
                            )
                            
                        # Pequeño delay de backoff en loop de WS
                        await asyncio.sleep(0.1)
                        
            except websockets.exceptions.ConnectionClosed:
                self.logger.warning("Desconectado del WebSocket de Hyperliquid. Reconectando en 2s...")
                await asyncio.sleep(2)
            except Exception as e:
                self.logger.error(f"Error fatal en L2 WebSocket: {e}")
                await asyncio.sleep(5)

    def _calculate_imbalance(self, book_data: dict):
        """
        Calcula el desequilibrio de liquidez profunda.
        Retorna: (signal, confidence)
        """
        try:
            levels = book_data.get('levels', [[], []])
            bids = levels[0] # Compradores [price, sz, n, ...]
            asks = levels[1] # Vendedores [price, sz, n, ...]
            
            # Sumamos volumen de los primeros 10 niveles (liquidez cercana)
            depth = 10
            bid_vol = sum([float(b['sz']) for b in bids[:depth]]) if bids else 0.0
            ask_vol = sum([float(a['sz']) for a in asks[:depth]]) if asks else 0.0
            
            total_vol = bid_vol + ask_vol
            if total_vol == 0:
                return 0.0, 0.0
                
            # Ratio de -1.0 a 1.0 (Si hay puro Bid = 1.0, Si puro Ask = -1.0)
            imbalance = (bid_vol - ask_vol) / total_vol
            
            # Confianza crece si el volumen total en los primeros niveles es inusualmente alto
            # (Simplificado: 0.8 fijo por ahora hasta tener media movil del volumen L2)
            confidence = 0.8
            
            return imbalance, confidence
            
        except Exception as e:
            self.logger.debug(f"Error procesando estructura del book: {e}")
            return 0.0, 0.0

    def _run_loop(self):
        """Wrapper para correr el event loop async de WebSockets en el daemon thread."""
        self.logger.info("Iniciando Event Loop Asincrono para WebSockets...")
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        new_loop.run_until_complete(self._listen_to_book())

if __name__ == "__main__":
    # Test individual del Agente Order-Flow
    print("Iniciando test del Order-Flow Agent (L2 Book)...")
    agent = OrderFlowAgent("SOL")
    agent.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        agent.stop()
        print("Fin de prueba Order-Flow.")
