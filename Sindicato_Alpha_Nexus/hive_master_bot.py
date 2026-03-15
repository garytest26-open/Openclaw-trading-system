import os
import time
import logging
from dotenv import load_dotenv
from tamc_sol_live import TAMC_SOL_BotLive # Base bot con PPO y Hyperliquid API

from hive_master_node import HiveMasterNode
from hive_agent_sentiment import SentimentAgent
from hive_agent_orderflow import OrderFlowAgent
from hive_agent_onchain import OnChainAgent

logger = logging.getLogger("Hive_Master_Allocator")

class HiveMasterBot(TAMC_SOL_BotLive):
    """
    El bot final del ecosistema Hive-Mind.
    Combina:
    1. Modelo PPO-LSTM (Análisis multi-timeframe de precios/volumen)
    2. Enjambre Redis (Microestructura L2, OnChain, Sentiment NLP)
    
    Toma la decisión usando una función de "Veto y Amplificación" (Ensemble).
    """
    def __init__(self):
        super().__init__()
        
        # Iniciar Cerebro Receptor (Redis Listener)
        self.hive_listener = HiveMasterNode()
        self.hive_listener.start_listening()
        
        self.asset_usd = "SOL-USD"
        self.asset = "SOL"
        
        logger.warning("=========================================================")
        logger.warning("🧠 HIVE-MIND MASTER ALLOCATOR - MODO LIVE 🚨")
        logger.warning("Iniciando Agentes Sensoriales en Segundo Plano...")
        logger.warning("=========================================================")
        
        # Iniciar Sensores Internos
        self.ag_sentiment = SentimentAgent(self.asset_usd)
        self.ag_orderflow = OrderFlowAgent(self.asset)
        self.ag_onchain = OnChainAgent(self.asset_usd)
        
        self.ag_sentiment.start()
        self.ag_orderflow.start()
        self.ag_onchain.start()

    def agregate_hive_signal(self):
        """
        Calcula un multiplicador para la acción del bot base leyendo a los agentes.
        Returns: 
           - hive_multiplier [-1.0 a 1.0]: Modificador global direccional.
        """
        state = self.hive_listener.get_aggregated_state(self.asset_usd, max_age_seconds=15.0)
        
        if not state:
            return 0.0 # Neural/No data
            
        total_signal = sum(state.values())
        count = len(state)
        
        # Promedio simple direccional
        average_signal = total_signal / count if count > 0 else 0.0
        return average_signal

    def run(self):
        logger.info("Esperando que las señales del Enjambre se acoplen (10s)...")
        time.sleep(10)
        
        while True:
            try:
                # 1. Traer datos de mercado clasicos (Velas)
                df = self.fetch_data(limit=300) 
                if df.empty:
                    time.sleep(10)
                    continue

                df_closed = df.iloc[:-1].copy()
                current_price = df.iloc[-1]['Close'] 
                
                # 2. IA Técnica (Master Brain - PPO)
                action_ppo = self.get_model_action(df_closed)
                
                # 3. Escuchar al enjambre
                hive_consensus = self.agregate_hive_signal()
                
                # ------ LÓGICA DE ALOCACIÓN MÁSTER ------
                # action_ppo: 0 (Flat), 1 (Long 50%), 2 (Long 100%), 3 (Short 50%), 4 (Short 100%)
                final_action = action_ppo
                
                # Reglas de Veto Institucional
                is_long_ppo = action_ppo in [1, 2]
                is_short_ppo = action_ppo in [3, 4]
                
                # VETO BAJISTA: Si la IA Tecnica quiere comprar, pero Twitter/Flujos/L2 están MUY rojos (<-0.5)
                if is_long_ppo and hive_consensus < -0.5:
                    logger.warning(f"🚨 VETO HIVE-MIND: PPO quiere COMPRAR, pero la colmena está BEAR ({hive_consensus:.2f}). Cancelando.")
                    final_action = 0
                    
                # VETO ALCISTA: Si la IA técnica quiere Vender, pero el mundo real está eufórico (>0.5)
                elif is_short_ppo and hive_consensus > 0.5:
                    logger.warning(f"🚨 VETO HIVE-MIND: PPO quiere VENDER, pero la colmena está BULL ({hive_consensus:.2f}). Cancelando.")
                    final_action = 0
                    
                # AMPLIFICACIÓN (Pyramiding)
                elif is_long_ppo and hive_consensus > 0.3:
                    logger.info(f"💎 CONFLUENCIA HIVE-MIND: PPO y Colmena de acuerdo. Long 100%.")
                    final_action = 2
                elif is_short_ppo and hive_consensus < -0.3:
                    logger.info(f"💎 CONFLUENCIA HIVE-MIND: PPO y Colmena de acuerdo. Short 100%.")
                    final_action = 4
                
                # INICIATIVA PROPIA DEL ENJAMBRE (OVERRIDE)
                elif action_ppo == 0:
                    if hive_consensus >= 0.60:
                        logger.info(f"🔥 INICIATIVA HIVE-MIND: PPO está Flat, pero la colmena está EXTREMADAMENTE BULL ({hive_consensus:.2f}). Forzando Long 50%.")
                        final_action = 1
                    elif hive_consensus <= -0.60:
                        logger.info(f"🔥 INICIATIVA HIVE-MIND: PPO está Flat, pero la colmena está EXTREMADAMENTE BEAR ({hive_consensus:.2f}). Forzando Short 50%.")
                        final_action = 3
                
                action_name = self.action_names.get(final_action, "Flat")
                
                logger.info(f"=== DECISION: PPO={self.action_names[action_ppo]} | HIVE_CONSENSUS={hive_consensus:+.2f} | FINAL={action_name} ===")
                
                # Ejecutar la orden final consolidada
                last_time = df_closed.index[-1]
                self.execute_trade(final_action, current_price, current_candle_time=last_time)
                
                # Esperamos 10 segundos solamente para tener alta reactividad a las ballenas (HFT like)
                time.sleep(10)
                
            except Exception as e:
                logger.error(f"Loop Master Error: {e}")
                time.sleep(10)
                
    def __del__(self):
        self.hive_listener.stop_listening()

if __name__ == "__main__":
    bot = HiveMasterBot()
    bot.run()
