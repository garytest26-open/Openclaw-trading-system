$ErrorActionPreference = "Stop"

Write-Host "Iniciando Agente de Algo Trading (Live Bot)..." -ForegroundColor Cyan

# Check for virtual environment
if (Test-Path "venv\Scripts\activate.ps1") {
    Write-Host "Activando entorno virtual..." -ForegroundColor Green
    & "venv\Scripts\activate.ps1"
}
elseif (Test-Path ".venv\Scripts\activate.ps1") {
    Write-Host "Activando .venv..." -ForegroundColor Green
    & ".venv\Scripts\activate.ps1"
}
else {
    Write-Host "No se encontró entorno virtual. Usando python global..." -ForegroundColor Yellow
}

# Run the bot
try {
    Write-Host "Ejecutando live_bot.py..." -ForegroundColor Cyan
    python live_bot.py
}
catch {
    Write-Host "Error ejecutando bot: $_" -ForegroundColor Red
    exit 1
}
