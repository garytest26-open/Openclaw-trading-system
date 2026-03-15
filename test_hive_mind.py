import time
import logging
from hive_master_node import HiveMasterNode
from hive_agent_sentiment import SentimentAgent
from hive_agent_orderflow import OrderFlowAgent
from hive_agent_onchain import OnChainAgent

# Configurar log principal del test
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Hive_Integration_Test")

def run_integration_test():
    asset = "SOL"
    asset_usd = "SOL-USD"
    
    logger.info("="*50)
    logger.info("🧠 INICIANDO TEST DE INTEGRACIÓN HIVE-MIND 🧠")
    logger.info("========================================")
    
    # 1. Iniciar Master Node (Cerebro Central / Redis Subscriber)
    master = HiveMasterNode()
    master.start_listening()
    time.sleep(1) # Dar tiempo a que conecte a Redis
    
    # 2. Instanciar Sensores (Micro-Agentes)
    ag_sentiment = SentimentAgent(asset_usd)
    ag_orderflow = OrderFlowAgent(asset)
    ag_onchain = OnChainAgent(asset_usd)
    
    # 3. Lanzar Sensores (Hilos en background que publican a Redis)
    logger.info("🚀 Lanzando escuadrón de micro-agentes...")
    ag_sentiment.start()
    ag_orderflow.start()
    ag_onchain.start()
    
    logger.info("✅ Todos los agentes iniciados. Leyendo la mente colmena por 30 segundos...")
    
    try:
        # Loop principal del simulador PPO (Test)
        for i in range(30):
            time.sleep(1)
            
            # El Master Node expone el diccionario agregado de todos los inputs recientes
            current_state = master.get_aggregated_state(asset_usd, max_age_seconds=15.0)
            
            if current_state:
                logger.info(f"[T+{i}s] ESTADO AGREGADO DE LA COLMENA para {asset_usd}:")
                for agent_name, signal in current_state.items():
                    # Format signal with color-like text
                    trend = "🟢 BULL" if signal > 0.1 else ("🔴 BEAR" if signal < -0.1 else "⚪ NEUTRAL")
                    logger.info(f"   -> {agent_name}: {signal:+.3f} ({trend})")
            else:
                logger.info(f"[T+{i}s] Esperando señales en el bus Redis...")
                
    except KeyboardInterrupt:
        logger.info("Test interrumpido manualmente.")
        
    finally:
        # Apagado grácil
        logger.info("🛑 Apagando Enjambre...")
        ag_sentiment.stop()
        ag_orderflow.stop()
        ag_onchain.stop()
        master.stop_listening()
        logger.info("Test Finalizado.")

if __name__ == "__main__":
    run_integration_test()
