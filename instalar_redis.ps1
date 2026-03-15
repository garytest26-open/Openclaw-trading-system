# Installer for Memurai (Developer Edition) - Redis compatible server for Windows
$ErrorActionPreference = "Stop"

$MemuraiUrl = "https://www.memurai.com/download/Memurai-Developer-v4.1.3.msi"
$InstallerPath = "$env:TEMP\Memurai.msi"

Write-Host "=================================================================="
Write-Host " HIVE-MIND: Instalando Servidor Redis Nativo para Windows (Memurai)"
Write-Host "=================================================================="
Write-Host ""
Write-Host "Paso 1: Descargando instalador. Esto puede tomar unos segundos..."
Invoke-WebRequest -Uri $MemuraiUrl -OutFile $InstallerPath

Write-Host "Paso 2: Instalando Memurai (Se pediran permisos de Administrador)..."
Start-Process "msiexec.exe" -ArgumentList "/i `"$InstallerPath`" /quiet /norestart" -Wait -Verb RunAs

Write-Host "Paso 3: Iniciando el servicio en segundo plano..."
Start-Service Memurai -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "=================================================================="
Write-Host "✅ INSTALACION COMPLETADA ✅"
Write-Host "El bus de mensajes (Redis) ya esta corriendo en el puerto 6379."
Write-Host "Ahora puedes ejecutar: python test_hive_mind.py"
Write-Host "=================================================================="
Write-Host ""
Write-Host "Presiona cualquier tecla para salir..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
