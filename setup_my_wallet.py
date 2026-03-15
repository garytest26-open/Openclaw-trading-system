import os
import getpass
from eth_account import Account
from dotenv import load_dotenv

def setup():
    print("\n=== CONFIGURACIÓN DE TU WALLET (Hyperliquid) ===")
    print("Para que el bot opere la wallet 0x860..., necesita TU Permiso (Clave Privada).")
    print("AVISO: Tu clave se guardará SOLO en tu PC (archivo .env).")
    
    try:
        print("\nPor favor, pega tu Private Key a continuación.")
        print("(Si no sabes cómo obtenerla: En MetaMask -> Tres puntos -> Detalles de cuenta -> Mostrar clave privada)")
        
        # Input standard para asegurar compatibilidad si getpass falla en consola integrada
        private_key = input("Pega tu Private Key y pulsa Enter: ").strip()
        
        # Limpieza básica
        if not private_key.startswith("0x"):
            # Si es hex puro, añadir 0x, si es seed phrase (error), fallará abajo
            if len(private_key) == 64: 
                private_key = "0x" + private_key
            
        # Verificar validez
        try:
            acct = Account.from_key(private_key)
            derived_address = acct.address
        except Exception as e:
            print(f"\n❌ Clave inválida: {e}")
            return

        print(f"\n✅ Clave válida detectada.")
        print(f"Dirección de la Wallet: {derived_address}")
        
        # Confirmar con usuario
        print(f"\n¿Confirmas que esta es la wallet donde tienes los fondos USDC?")
        confirm = input("Escribe 'si' para confirmar guardado: ").lower().strip()
        
        if confirm not in ['si', 's', 'yes', 'y']:
            print("Cancelado.")
            return

        # Actualizar .env
        env_lines = []
        if os.path.exists(".env"):
            with open(".env", "r") as f:
                for line in f:
                    # Filtrar líneas viejas
                    if not line.startswith("WALLET_ADDRESS=") and not line.startswith("PRIVATE_KEY="):
                        if line.strip(): # Mantener lineas no vacias
                            env_lines.append(line)
        
        # Añadir nuevas
        env_lines.append(f"\nWALLET_ADDRESS={derived_address}\n")
        env_lines.append(f"PRIVATE_KEY={private_key}\n")
        
        with open(".env", "w") as f:
            f.writelines(env_lines)
            
        print("\n✅ ¡Configuración Guardada en .env!")
        print("------------------------------------------------")
        print("PASO SIGUIENTE: Ejecuta el bot con:")
        print("python btc_supertrend_testnet.py")
        print("------------------------------------------------")
        
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")

if __name__ == "__main__":
    setup()
