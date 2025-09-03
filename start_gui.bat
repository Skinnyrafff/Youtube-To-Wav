@echo off
REM Este archivo ejecuta la interfaz grafica de YouTube to WAV.
REM Para usarlo desde el escritorio, haz clic derecho sobre el -> Enviar a -> Escritorio (crear acceso directo).

REM Obtiene el directorio donde se encuentra este archivo .bat
set SCRIPT_DIR=%~dp0

REM Ejecuta el script de Python usando la ruta completa para asegurar que funcione
python "%SCRIPT_DIR%yt_to_wav_gui.py"
