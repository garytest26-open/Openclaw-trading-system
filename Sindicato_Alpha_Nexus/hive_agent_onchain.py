import time
import random
from hive_base_agent import HiveBaseAgent

class OnChainAgent(HiveBaseAgent):
    """
    Agente On-Chain (Métricas de Red y Movimientos de Ballenas).
    En producción, consultará nodos RPC web3 (Infura, Alchemy) o 
    APIs especializadas como CryptoQuant/Glassnode para monitorizar:
    - Net Inflows a Exchanges (Bearish si entran monedas)
    - Stablecoin Minting (Bullish si se imprime USDT/USDC)
    - Large Transactions (Whale Alerts)
    """
    def __init__(self, asset: str = "SOL-USD"):
        super().__init__(agent_id=f"OnChain_WhaleTracker_{asset}")
        self.asset = asset

    def _fetch_glassnode_mock(self):
        """
        [MOCK] Simula una llamada a una API on-chain.
        Retorna la señal direccional basada en el Net Flow.
        - Valores Positivos: Bullish (Stablecoins entrando, Activo saliendo a Cold Wallets)
        - Valores Negativos: Bearish (Activo entrando a Exchanges masivamente)
        """
        # Emulamos latencia de red de una API REST HTTP
        time.sleep(0.5)
        
        # En esta simulacion, el mercado onchain es neutral-alcista generalmente
        # pero esporádicamente (10% prob) una ballena mueve saldos masivos.
        event = random.random()
        
        if event < 0.05:
            # Huge Exchange Inflow (DUMP INMINENTE)
            signal = -0.9
            conf = 0.95
            meta = "Whale transfer to CEX detected: 50,000 unit deposit."
        elif event < 0.15:
            # Massive USDC Mint (PUMP FUEL)
            signal = 0.8
            conf = 0.85
            meta = "Tether Treasury minted 1B stables."
        else:
            # Ruido habitual de la red, flujos neutrales
            signal = random.uniform(-0.3, 0.4)
            conf = 0.3
            meta = "Normal netflow activity (-$2M net exchange flow)"
            
        return signal, conf, meta

    def _run_loop(self):
        self.logger.info("Agent_OnChain iniciado. Monitoreando Mempool y RPCs...")
        
        while self.running:
            try:
                signal, confidence, meta_desc = self._fetch_glassnode_mock()
                
                self.publish_signal(
                    asset=self.asset,
                    signal_value=signal,
                    confidence=confidence,
                    meta={"alert": meta_desc, "source": "OnChain_Mempool"}
                )
                
                # Los bloques en las blockchains tardan en minarse. 
                # (Ethereum 12s, Bitcoin 10m). Iterar cada 5s es adecuado.
                time.sleep(5)
                
            except Exception as e:
                self.logger.error(f"Falla de conexion RPC On-Chain: {e}")
                time.sleep(10)

if __name__ == "__main__":
    print("Iniciando test del OnChain Whale Tracker...")
    agent = OnChainAgent("SOL-USD")
    agent.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        agent.stop()
        print("Fin de prueba On-Chain.")
