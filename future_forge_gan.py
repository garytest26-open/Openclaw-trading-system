import os
import time
import math
import numpy as np
import pandas as pd
import yfinance as yf
import torch
import torch.nn as nn
import torch.optim as optim
import matplotlib.pyplot as plt
from torch.utils.data import DataLoader, TensorDataset

# --- CONFIGURACION GAN ---
SEQ_LEN = 24       # Proyectamos 24 horas
LATENT_DIM = 32    # Tamaño del vector de ruido
HIDDEN_DIM = 64
NUM_CLASSES = 4    # 0: Sideways, 1: Bull, 2: Bear, 3: High Volatility
EMBEDDING_DIM = 16 # Tamaño del embedding para las clases
BATCH_SIZE = 64
EPOCHS = 150
CRITIC_ITERATIONS = 5 # WGAN requiere entrenar más al Critic que al Generator
LAMBDA_GP = 10     # Penalización del gradiente (Gradient Penalty)
LEARNING_RATE = 2e-4
FEATURES = 3       # LogRet, IntraVol, Volume

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ==========================================
# 0. MECANISMOS DE ATENCIÓN (Self-Attention)
# ==========================================
class SelfAttention(nn.Module):
    def __init__(self, hidden_dim):
        super(SelfAttention, self).__init__()
        self.query = nn.Linear(hidden_dim, hidden_dim)
        self.key = nn.Linear(hidden_dim, hidden_dim)
        self.value = nn.Linear(hidden_dim, hidden_dim)
        self.scale = math.sqrt(hidden_dim)

    def forward(self, x):
        # x shape: [batch, seq_len, hidden_dim]
        Q = self.query(x)
        K = self.key(x)
        V = self.value(x)
        
        # Attention scores: Q * K^T / sqrt(d_k)
        attention = torch.bmm(Q, K.transpose(1, 2)) / self.scale
        attention_weights = torch.softmax(attention, dim=-1)
        
        # O = Softmax(Scores) * V
        out = torch.bmm(attention_weights, V)
        return out

# ==========================================
# 1. ARQUITECTURA: GENERADOR (cGAN + Attention)
# ==========================================
class ConditionalGenerator(nn.Module):
    def __init__(self, latent_dim, num_classes, embed_dim, hidden_dim, seq_len, out_features):
        super(ConditionalGenerator, self).__init__()
        self.seq_len = seq_len
        self.out_features = out_features
        
        # Embedding de la condición (clase de mercado)
        self.label_emb = nn.Embedding(num_classes, embed_dim)
        
        # Entrada total = Ruido Z + Embedding
        input_dim = latent_dim + embed_dim
        
        self.fc = nn.Linear(input_dim, hidden_dim * seq_len)
        self.lstm = nn.LSTM(hidden_dim, hidden_dim, num_layers=2, batch_first=True, dropout=0.2)
        self.attention = SelfAttention(hidden_dim)
        
        self.out = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.LeakyReLU(0.2),
            nn.Linear(hidden_dim // 2, out_features)
        )
        
    def forward(self, z, labels):
        batch_size = z.size(0)
        
        c = self.label_emb(labels) # [batch, embed_dim]
        x = torch.cat([z, c], dim=1) # [batch, latent_dim + embed_dim]
        
        # Expandir temporalmente
        x = self.fc(x).view(batch_size, self.seq_len, -1)
        
        # Procesamiento secuencial
        lstm_out, _ = self.lstm(x)
        
        # Ponderación de Atención
        attn_out = self.attention(lstm_out)
        
        # Mapeo a features de salida
        output = self.out(attn_out)
        return output

# ==========================================
# 2. ARQUITECTURA: CRÍTICO (cGAN + TCN + LSTM)
# ==========================================
class ConditionalCritic(nn.Module):
    def __init__(self, input_features, num_classes, embed_dim, hidden_dim):
        super(ConditionalCritic, self).__init__()
        
        self.label_emb = nn.Embedding(num_classes, embed_dim)
        
        # La entrada al crítico es la serie (features) condicionada temporalmente
        # Vamos a expandir el embedding y concatenarlo a cada paso de tiempo
        total_features = input_features + embed_dim
        
        # Convolution temporal para extraer patrones locales (1D CNN)
        self.tcn = nn.Sequential(
            nn.Conv1d(in_channels=total_features, out_channels=hidden_dim, kernel_size=3, padding=1),
            nn.LeakyReLU(0.2),
            nn.BatchNorm1d(hidden_dim),
            nn.Conv1d(in_channels=hidden_dim, out_channels=hidden_dim, kernel_size=3, padding=1),
            nn.LeakyReLU(0.2)
        )
        
        self.lstm = nn.LSTM(hidden_dim, hidden_dim, num_layers=1, batch_first=True)
        
        self.fc = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.LeakyReLU(0.2),
            nn.Dropout(0.3),
            nn.Linear(hidden_dim // 2, 1) # Sin Sigmoid para WGAN
        )

    def forward(self, x, labels):
        batch_size, seq_len, _ = x.size()
        
        # Obtener embedding y expandirlo para cada paso de la secuencia
        c = self.label_emb(labels).unsqueeze(1).repeat(1, seq_len, 1) # [batch, seq_len, embed_dim]
        
        # Combinar Features reales/falsos con su etiqueta
        x_cond = torch.cat([x, c], dim=-1) # [batch, seq_len, total_features]
        
        # TCN espera [batch, channels, seq_len]
        x_cond = x_cond.transpose(1, 2)
        tcn_out = self.tcn(x_cond)
        tcn_out = tcn_out.transpose(1, 2) # Volver a [batch, seq_len, hidden]
        
        # Captura de dependencias largas
        lstm_out, _ = self.lstm(tcn_out)
        
        # Tomar el último hidden state
        last_out = lstm_out[:, -1, :]
        
        validity = self.fc(last_out)
        return validity

# ==========================================
# 3. UTILERIA: WGAN GRADIENT PENALTY CONDICIONAL
# ==========================================
def compute_gradient_penalty(critic, real_samples, fake_samples, labels):
    alpha = torch.rand(real_samples.size(0), 1, 1).to(device)
    alpha = alpha.expand_as(real_samples)
    
    interpolates = (alpha * real_samples + ((1 - alpha) * fake_samples)).requires_grad_(True)
    
    d_interpolates = critic(interpolates, labels)
    
    fake = torch.ones(real_samples.shape[0], 1).to(device)
    
    gradients = torch.autograd.grad(
        outputs=d_interpolates,
        inputs=interpolates,
        grad_outputs=fake,
        create_graph=True,
        retain_graph=True,
        only_inputs=True,
    )[0]
    
    gradients = gradients.reshape(gradients.size(0), -1)
    gradient_penalty = ((gradients.norm(2, dim=1) - 1) ** 2).mean() * LAMBDA_GP
    return gradient_penalty

# ==========================================
# 4. PREPARACIÓN DE DATOS RE-DISEÑADA (Con Labels)
# ==========================================
def discretize_market_regime(returns_seq, vol_seq):
    """
    Clasifica una secuencia de 24h en un régimen (0 a 3)
    0: Sideways (Baja vol, retornos planos)
    1: Bull (Retornos netos positivos)
    2: Bear (Retornos netos negativos)
    3: High Volatility (Choppiness extremo, grandes oscilaciones independientemente de la dirección)
    """
    net_return = np.sum(returns_seq)
    avg_vol = np.mean(vol_seq)
    
    # Umbrales basados empíricamente (los adaptaremos estadísticamente luego)
    # Asumimos que los datos de entrada ya están +- normalizados o trabajamos sobre los raw.
    # Usaremos una heurística sensata:
    
    # Si la volatilidad media (IntraVol) de estas 24h es muy alta (> P80)
    # definimos como High Volatility (3)
    # Por ahora dejaremos un umbral estático de Z-score > 1.5 para alta vol
    if avg_vol > 1.5:
        return 3
        
    # Tendencias direccionales
    if net_return > 0.02: # +2% en 24h normalizadas (aprox)
        return 1
    elif net_return < -0.02: 
        return 2
    else:
        return 0 # Sideways

def load_and_preprocess_data(ticker="SOL-USD", limit_years=2):
    print(f"Descargando {limit_years} años de datos 1H para {ticker}...")
    df = yf.download(ticker, period=f"{limit_years}y", interval="1h", progress=False)
    
    # Manejar MultiIndex si se usa yfinance nuevo
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel('Ticker')
        
    df.dropna(inplace=True)
    
    # Features
    df['LogRet'] = np.log(df['Close'] / df['Close'].shift(1))
    df['IntraVol'] = (df['High'] - df['Low']) / df['Close']
    
    # Añadimos Volumen normalizado localmente (tasa de cambio del volumen)
    # Se usa log del volumen + offset para evitar inf, y luego diferencial
    df['LogVol'] = np.log(df['Volume'] + 1)
    df['VolChange'] = df['LogVol'].diff()
    
    df.dropna(inplace=True)
    
    # Normalización Z-score general
    data_raw = df[['LogRet', 'IntraVol', 'VolChange']].values
    mean = np.mean(data_raw, axis=0)
    std = np.std(data_raw, axis=0)
    data_scaled = (data_raw - mean) / (std + 1e-8)
    
    sequences = []
    labels = []
    
    # Pre-calcular umbrales estadísticos reales para etiquetar
    rolling_returns_24 = df['LogRet'].rolling(SEQ_LEN).sum().dropna()
    rolling_vol_24 = df['IntraVol'].rolling(SEQ_LEN).mean().dropna()
    
    vol_p80 = np.percentile((rolling_vol_24.values - mean[1]) / std[1], 85) # Top 15% Volatilidad
    ret_p75 = np.percentile((rolling_returns_24.values - mean[0]*SEQ_LEN) / (std[0]*np.sqrt(SEQ_LEN)), 75)
    ret_p25 = np.percentile((rolling_returns_24.values - mean[0]*SEQ_LEN) / (std[0]*np.sqrt(SEQ_LEN)), 25)

    
    for i in range(len(data_scaled) - SEQ_LEN):
        seq = data_scaled[i:i+SEQ_LEN]
        
        net_ret = sum(seq[:, 0])
        avg_vol = np.mean(seq[:, 1])
        
        # Etiquetar
        if avg_vol > vol_p80:
            label = 3 # High Volatility
        elif net_ret > ret_p75:
            label = 1 # Bull
        elif net_ret < ret_p25:
            label = 2 # Bear
        else:
            label = 0 # Sideways
            
        sequences.append(seq)
        labels.append(label)
        
    sequences = np.array(sequences)
    labels = np.array(labels)
    
    # Ver distribución de clases
    unique, counts = np.unique(labels, return_counts=True)
    print("Distribución de Escenarios (0:Rango, 1:Toro, 2:Oso, 3:Volátil):", dict(zip(unique, counts)))
    
    return sequences, labels, mean, std

# ==========================================
# 5. LOOP DE ENTRENAMIENTO cWGAN
# ==========================================
def train_multiverse_gan():
    print("="*50)
    print("INICIANDO CONDITIONAL FUTURE FORGE (cWGAN-GP)")
    print("Arquitectura: Self-Attention + TCN + Etiquetas de Régimen")
    print("="*50)
    
    real_data_seq, labels_seq, mean_stat, std_stat = load_and_preprocess_data()
    
    dataset = TensorDataset(torch.FloatTensor(real_data_seq), torch.LongTensor(labels_seq))
    dataloader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=True, drop_last=True)
    
    generator = ConditionalGenerator(LATENT_DIM, NUM_CLASSES, EMBEDDING_DIM, HIDDEN_DIM, SEQ_LEN, FEATURES).to(device)
    critic = ConditionalCritic(input_features=FEATURES, num_classes=NUM_CLASSES, embed_dim=EMBEDDING_DIM, hidden_dim=HIDDEN_DIM).to(device)
    
    opt_G = optim.Adam(generator.parameters(), lr=LEARNING_RATE, betas=(0.5, 0.9))
    opt_C = optim.Adam(critic.parameters(), lr=LEARNING_RATE, betas=(0.5, 0.9))
    
    # Scheduler para estabilizar entrenamiento largo
    scheduler_G = optim.lr_scheduler.StepLR(opt_G, step_size=50, gamma=0.5)
    scheduler_C = optim.lr_scheduler.StepLR(opt_C, step_size=50, gamma=0.5)
    
    generator.train()
    critic.train()
    
    print(f"Entrenando por {EPOCHS} Epocas en {device}...")
    start_time = time.time()
    
    for epoch in range(EPOCHS):
        d_loss_val = 0
        g_loss_val = 0
        
        for i, (real_samples, batch_labels) in enumerate(dataloader):
            batch_size_cur = real_samples.size(0)
            real_samples = real_samples.to(device)
            batch_labels = batch_labels.to(device)
            
            # --- Entrenar CRÍTICO ---
            for _ in range(CRITIC_ITERATIONS):
                opt_C.zero_grad()
                
                z = torch.randn(batch_size_cur, LATENT_DIM).to(device)
                fake_samples = generator(z, batch_labels)
                
                real_validity = critic(real_samples, batch_labels)
                fake_validity = critic(fake_samples.detach(), batch_labels)
                
                gp = compute_gradient_penalty(critic, real_samples.data, fake_samples.data, batch_labels)
                d_loss = -torch.mean(real_validity) + torch.mean(fake_validity) + gp
                
                d_loss.backward()
                opt_C.step()
                
            d_loss_val = d_loss.item()
            
            # --- Entrenar GENERADOR ---
            opt_G.zero_grad()
            
            # Recalculamos fake validity pero esta vez propaga gen loss
            gen_fake_validity = critic(fake_samples, batch_labels)
            g_loss = -torch.mean(gen_fake_validity)
            
            g_loss.backward()
            opt_G.step()
            g_loss_val = g_loss.item()
            
        scheduler_G.step()
        scheduler_C.step()
            
        elapsed = time.time() - start_time
        if (epoch + 1) % 5 == 0:
            print(f"[Epoca {epoch+1}/{EPOCHS}] | D Loss: {d_loss_val:.4f} | G Loss: {g_loss_val:.4f} | LR: {scheduler_G.get_last_lr()[0]:.6f} | T: {elapsed:.0f}s")
            
    # Guardar El Creador de Mundos
    os.makedirs("models", exist_ok=True)
    torch.save({
        'generator_state_dict': generator.state_dict(),
        'critic_state_dict': critic.state_dict(),
        'mean_stat': mean_stat,
        'std_stat': std_stat
    }, "models/cgan_future_forge.pth")
    print("\ncGAN Guardado exitosamente. Ahora puedes solicitar escenarios a la carta.")
    
    generate_stress_test_preview(generator, mean_stat, std_stat)

# ==========================================
# 6. VISUALIZAR EL MULTIVERSO (Escenarios Controlados)
# ==========================================
def generate_stress_test_preview(generator, mean_stat, std_stat):
    generator.eval()
    
    # Solicitar 4 escenarios distintos
    conditions = torch.LongTensor([0, 1, 2, 3]).to(device) # Sideways, Bull, Bear, High Vol
    
    with torch.no_grad():
        z = torch.randn(4, LATENT_DIM).to(device)
        fake_seqs = generator(z, conditions).cpu().numpy() # [4, seq_len, 3]
        
    plt.figure(figsize=(15, 8))
    plt.style.use('dark_background')
    colors = ['gray', 'green', 'red', 'yellow']
    titles = ['Sideways (0)', 'Bull Market (1)', 'Flash Crash / Bear (2)', 'High Volatility Storm (3)']
    
    for i in range(4):
        plt.subplot(2, 2, i+1)
        # Des-normalizar retornos (Feature 0)
        fake_returns = (fake_seqs[i, :, 0] * std_stat[0]) + mean_stat[0]
        
        # Reconstruir precio
        price = [100.0]
        for r in fake_returns: price.append(price[-1] * math.exp(r))
            
        plt.plot(price, color=colors[i], linewidth=2)
        plt.title(f"cGAN Escenario Solicitado: {titles[i]}")
        plt.ylabel("Precio Relativo")
        plt.grid(color='gray', linestyle='dotted', alpha=0.5)
        
    plt.tight_layout()
    plt.savefig("cgan_multiverse_scenarios.png", dpi=200)
    print("Previsualización de los 4 escenarios guardada en 'cgan_multiverse_scenarios.png'")

if __name__ == "__main__":
    train_multiverse_gan()
