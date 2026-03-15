import os

def create_colab_file():
    with open('nexus_omega_strategy.py', 'r', encoding='utf-8') as f:
        strategy_code = f.read()
    
    with open('nexus_omega_rl_layer.py', 'r', encoding='utf-8') as f:
        rl_code = f.read()
        
    # Eliminar importaciones locales que fallarían en un solo archivo
    rl_code = rl_code.replace(
        "        from nexus_omega_strategy import (\n"
        "            NexusOmegaConfig, precompute_8_signals, detect_squeeze,\n"
        "            detect_market_structure, calc_momentum_direction,\n"
        "            calc_atr, calc_rsi, calc_macd, RegimeDetectorV2\n"
        "        )", 
        ""
    )
    
    # Quitar el bloque main de la estrategia si existe
    if "if __name__ == '__main__':" in strategy_code:
        strategy_code = strategy_code.split("if __name__ == '__main__':")[0]
        
    # Crear archivo combinado
    header = '''"""
# ==============================================================================
# 🚀 NEXUS OMEGA — ENTRENAMIENTO EN GOOGLE COLAB (GPU)
# ==============================================================================
# Instrucciones para Google Colab:
# 1. Abre Google Colab: https://colab.research.google.com/
# 2. Crea un nuevo notebook.
# 3. Ve a Entorno de ejecución -> Cambiar tipo de entorno -> Hardware > T4 GPU.
# 4. Pega este código completo en una celda en blanco.
# 5. Modifica la configuración al final si lo deseas (ticker, episodios).
# 6. Ejecuta la celda (Shift + Enter). 
#    - Se instalarán las librerías necesarias.
#    - Descargará los datos y empezará a entrenar.
# ==============================================================================
"""

import os
# Instalar dependencias directamente desde el código si no están
try:
    import pandas as pd
    import yfinance as yf
    import hmmlearn
except ImportError:
    print("Instalando dependencias requeridas en Colab...")
    os.system('pip install yfinance hmmlearn plotly torch pandas numpy')
    import pandas as pd
    import yfinance as yf
    import hmmlearn

# ==============================================================================
# 1. ESTRATEGIA BASE NEXUS OMEGA (7 CAPAS)
# ==============================================================================
'''
    
    colab_main = '''
# ==============================================================================
# 3. EJECUCIÓN DIRECTA EN COLAB
# ==============================================================================
if __name__ == "__main__":
    print("\\n\\n" + "*"*60)
    print("  🚀 INICIANDO NEXUS OMEGA RL TRAINER EN COLAB")
    print("*"*60 + "\\n")
    
    # ── Configuración Editable ──
    TICKER = "SOL-USD"       # Ej: "BTC-USD", "ETH-USD"
    EPISODIOS = 300          # Número de episodios (aumentar para más precisión)
    LONGITUD_SECUENCIA = 32  # Ventana temporal de velas para el LSTM
    
    config = RLConfig(
        ticker=TICKER,
        n_episodes=EPISODIOS,
        hidden_dim=256,
        lstm_layers=2,
        seq_len=LONGITUD_SECUENCIA,
        lr=3e-4,
    )
    
    # Ejecutar entrenamiento
    train_rl_filter(config)
    
    print("\\n\\n✅ ENTRENAMIENTO FINALIZADO.")
    print("El modelo se ha guardado en la carpeta 'models/'.")
    print("Puedes descargarlo desde la barra lateral izquierda de Colab (icono de carpeta).")
'''
    
    combined_code = header + strategy_code + "\n\n# ==============================================================================\n# 2. CAPA 8: FILTRO DE SEÑALES RL (PPO-LSTM)\n# ==============================================================================\n\n" + rl_code.split('if __name__ == "__main__":')[0] + colab_main
    
    with open('nexus_omega_colab_trainer.py', 'w', encoding='utf-8') as f:
        f.write(combined_code)
        
    print("Archivo nexus_omega_colab_trainer.py creado exitosamente.")

if __name__ == "__main__":
    create_colab_file()
