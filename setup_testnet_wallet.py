import os
from eth_account import Account
import secrets

# Generar una nueva wallet segura
priv = secrets.token_hex(32)
private_key = "0x" + priv
acct = Account.from_key(private_key)
address = acct.address

print(f"--- NUEVA WALLET GENERADA ---")
print(f"Address: {address}")
print(f"Private Key: {private_key}")

# Leer .env actual
env_path = ".env"
new_lines = []
if os.path.exists(env_path):
    with open(env_path, "r") as f:
        lines = f.readlines()
        for line in lines:
            if line.startswith("WALLET_ADDRESS="):
                continue
            if line.startswith("PRIVATE_KEY="):
                continue
            new_lines.append(line)
else:
    new_lines = []

# Añadir nuevas claves
new_lines.append(f"WALLET_ADDRESS={address}\n")
new_lines.append(f"PRIVATE_KEY={private_key}\n")

# Guardar .env
with open(env_path, "w") as f:
    f.writelines(new_lines)

print(f"\n[OK] Las claves se han guardado automáticamente en .env")
print(f"AHORA: Ve al Faucet y pide USDC para esta dirección: {address}")
