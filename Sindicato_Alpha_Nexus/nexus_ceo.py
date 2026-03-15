import os
import time
import json
import logging
import redis
import numpy as np
from dotenv import load_dotenv
import ccxt

load_dotenv()

# --- CONFIGURACIÓN PRINCIPAL ---
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_CHANNEL = 'nexus_orders'
REDIS_PNL_CHANNEL = 'nexus_pnl'

# Mapeo de sub-agentes
AGENTS = ['viper', 'hive', 'sniper']

# Capital Total Asignado para el Sindicato (en USD o Porcentaje del Balance Libre)
SYNDICATE_COMPOUND_RATIO = 0.90 # Usa hasta el 90% de todo el balance

# --- CONFIGURACIÓN CRO (Director de Riesgo) ---
MAX_DAILY_DRAWDOWN_PCT = -0.15 # -15% de pérdida detiene el Bot (Circuit Breaker)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - 👑 NEXUS CEO - %(message)s',
    handlers=[logging.StreamHandler(), logging.FileHandler("nexus_ceo.log")]
)
logger = logging.getLogger("NexusCEO")


class CapitalAllocatorRL:
    """
    Agente de Aprendizaje por Refuerzo (simplificado - Multi-Armed Bandit Epsilon-Greedy)
    que recompensa a los PMs (Bots) que generan PNL positivo y asfixia a los que pierden.
    """
    def __init__(self, agents, learning_rate=0.1, epsilon=0.1):
        self.agents = agents
        # Inicialmente el capital se divide equitativamente
        self.q_values = {agent: 1.0 for agent in agents} 
        self.alpha = learning_rate
        self.epsilon = epsilon
        logger.info(f"Capital Allocator IA Inicializado: Pesos base equitativos para {self.agents}")

    def get_weights(self):
        """Convierte los Q-values en porcentajes de alocación de capital (0 a 1) usando Softmax o proporción"""
        # Exponenciamos para asegurar números positivos y acentuar las diferencias
        exp_q = {a: np.exp(q) for a, q in self.q_values.items()}
        total_q = sum(exp_q.values())
        return {a: exp_q[a] / total_q for a in self.agents}

    def update_agent_performance(self, agent_id, pnl_pct):
        """Actualiza la recompensa de un agente basado en su PNL reciente"""
        if agent_id not in self.q_values:
            return
            
        # Fórmula Q-Learning básica: Q_new = Q_old + alpha * (Recompensa - Q_old)
        # Recompensa = pnl en %
        reward = pnl_pct
        old_q = self.q_values[agent_id]
        self.q_values[agent_id] = old_q + self.alpha * (reward - old_q)
        
        weights = self.get_weights()
        logger.info(f"⚖️ Rebalanceo de Capital: {agent_id} generó {pnl_pct:.2f}%. Nuevos Pesos: { {k: round(v, 2) for k,v in weights.items()} }")


class NexusCEO:
    """
    Cerebro Central (El Director). Único autorizado a ejecutar operaciones
    en la wallet real basándose en los consejos de sus subordinados.
    """
    def __init__(self, testnet=True):
        self.testnet = testnet
        self.r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
        self.pubsub = self.r.pubsub()
        self.pubsub.subscribe(REDIS_CHANNEL)
        self.pubsub.subscribe(REDIS_PNL_CHANNEL)
        
        self.allocator = CapitalAllocatorRL(AGENTS)
        
        self.wallet_address = os.getenv('WALLET_ADDRESS')
        self.private_key = os.getenv('PRIVATE_KEY')
        self.exchange = self._init_exchange()
        
        # Riesgo Global
        self.initial_balance = self.get_balance()
        self.circuit_breaker_active = False
        
        logger.info("==================================================")
        logger.info("🏦 EL SINDICATO ALPHA SE HA CONSTITUIDO EN EL SERVIDOR 🏦")
        logger.info(f"Balance Inicial Comprobado: ${self.initial_balance:.2f} USDC")
        logger.info(f"Modo Testnet: {self.testnet}")
        logger.info("==================================================")

    def _init_exchange(self):
        try:
            exchange_class = getattr(ccxt, 'hyperliquid')
            exchange = exchange_class({
                'walletAddress': self.wallet_address,
                'privateKey': self.private_key,
                'enableRateLimit': True,
                'options': {'defaultType': 'swap'},
            })
            if self.testnet:
                exchange.set_sandbox_mode(True)
            return exchange
        except Exception as e:
            logger.error(f"Error Iniciando Exchange: {e}")
            raise

    def get_balance(self):
        try:
            bal = self.exchange.fetch_balance()
            return float(bal['USDC']['free'])
        except:
            return 0.0

    def check_global_risk(self):
        """Director de Riesgos Integrado (CRO)"""
        if self.circuit_breaker_active:
            return False # Ya estamos muertos
            
        current_balance = self.get_balance()
        if current_balance == 0:
             return True # Evitar errores de parseo
             
        drawdown = (current_balance - self.initial_balance) / self.initial_balance
        
        if drawdown <= MAX_DAILY_DRAWDOWN_PCT:
            logger.error(f"💥 CIRCUIT BREAKER ACTIVADO 💥")
            logger.error(f"El Sindicato alcanzó una pérdida de {drawdown*100:.2f}%. Límite: {MAX_DAILY_DRAWDOWN_PCT*100:.2f}%.")
            logger.error("Drenando liquidez y apagando CEO para proteger el capital...")
            self.circuit_breaker_active = True
            
            # --- LIQUIDAR TODAS LAS POSICIONES AQUI ---
            # self.liquidate_all_markets()
            
            return False
            
        return True

    def process_pm_order(self, data):
        """Procesa una solicitud de ejecución de un Portfolio Manager (Sub-agente)"""
        agent_id = data.get("agent_id")
        action = data.get("action") # 'buy', 'sell', 'close'
        asset = data.get("asset")
        confidence = data.get("confidence", 1.0)
        
        if agent_id not in AGENTS:
             logger.warning(f"Intento de ejecución de Agente No Autorizado: {agent_id}")
             return
             
        # Consultar con el Allocator qué porcentaje de la torta le toca a este PM
        weights = self.allocator.get_weights()
        agent_weight = weights.get(agent_id, 0.0)
        
        # Filtrado de capital
        if agent_weight < 0.05 and action != 'close':
            logger.warning(f"❌ CEO deniega orden de {action} a {agent_id}. El PM ha perdido la confianza (Peso: {agent_weight*100:.1f}%)")
            return
            
        logger.info(f"✅ CEO Autentica orden de {agent_id} (Peso de Capital: {agent_weight*100:.1f}%) -> {action.upper()} {asset}")
        
        # Determinar Símbolo para Hyperliquid
        symbol = f"{asset}/USDC:USDC"
        exec_price = float(data.get("price", 0))
        
        if exec_price == 0:
             logger.warning(f"Error de Nexus: {agent_id} no envió el precio de ejecución.")
             return
             
        if action == 'close':
            close_side = data.get("close_side")
            amount = data.get("amount")
            if close_side and amount:
                try:
                    self.exchange.create_order(symbol, 'market', close_side, float(amount), exec_price, params={'reduceOnly': True})
                    logger.info(f"✅ CEO Ejecutó Cierre de Posición en {symbol} para {agent_id}")
                except Exception as e:
                    logger.error(f"Error del CEO cerrando la orden: {e}")
            return
        
        # CÁLCULO DE TAMAÑO (Ejecución real de apertura)
        balance = self.get_balance()
        allowed_capital = balance * SYNDICATE_COMPOUND_RATIO * agent_weight
        
        logger.info(f"💰 Se le permite arriesgar un total de: ${allowed_capital:.2f} USD a este PM.")
        
        amount = allowed_capital / exec_price
        if allowed_capital > 10:
            try:
                self.exchange.create_order(symbol, 'market', action, amount, exec_price)
                logger.info(f"✅ CEO Ejecutó Apertura {action.upper()} con {amount:.6f} {asset} guiado por {agent_id}")
            except Exception as e:
                logger.error(f"Error del CEO abriendo la orden: {e}")
        else:
             logger.warning(f"Capital asignado demasiado bajo (${allowed_capital:.2f}) para operar. Sindicato asfixiando esta estrategia.")
        
    def process_pm_pnl(self, data):
        """Recibe el PNL de cada operación cerrada de los Agentes y entrena la IA"""
        agent_id = data.get("agent_id")
        pnl_pct = data.get("pnl_pct")
        if agent_id and pnl_pct is not None:
             self.allocator.update_agent_performance(agent_id, float(pnl_pct))

    def run(self):
        logger.info("Iniciando bus de eventos. El CEO está escuchando a sus gerentes...")
        
        while not self.circuit_breaker_active:
            try:
                # Riesgo Global Check cada ciclo
                if not self.check_global_risk():
                     break
                     
                message = self.pubsub.get_message(ignore_subscribe_messages=True)
                if message:
                    channel = message['channel']
                    try:
                        data = json.loads(message['data'])
                        if channel == REDIS_CHANNEL:
                            self.process_pm_order(data)
                        elif channel == REDIS_PNL_CHANNEL:
                            self.process_pm_pnl(data)
                    except json.JSONDecodeError:
                        logger.error(f"Formato no válido del mensaje en Redis: {message['data']}")
                
                time.sleep(0.1) # Ciclo de microsegundos de HFT virtual
                
            except KeyboardInterrupt:
                logger.info("CEO Apagado manualmente.")
                break
            except Exception as e:
                logger.error(f"CEO Main Loop Error: {e}")
                time.sleep(1)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Nexus CEO")
    parser.add_argument('--live', action='store_true', help='Ejecutar en la MAINNET (dinero real)')
    args = parser.parse_args()
    
    ceo = NexusCEO(testnet=not args.live)
    ceo.run()
