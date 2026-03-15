@echo off
TITLE Algo Trading Bot
COLOR 0A
ECHO Iniciando el Bot de Trading...
ECHO ==============================

REM Intentar activar entorno virtual
IF EXIST "venv\Scripts\activate.bat" (
    CALL venv\Scripts\activate.bat
) ELSE (
    IF EXIST ".venv\Scripts\activate.bat" (
        CALL .venv\Scripts\activate.bat
    ) ELSE (
        ECHO [ADVERTENCIA] No se encontro entorno virtual. Usando Python del sistema...
    )
)

REM Ejecutar el bot
python live_bot.py

REM Pausa para que la ventana no se cierre si hay error
ECHO.
ECHO El bot se ha detenido.
PAUSE
