@echo off
setlocal
cd /d "%~dp0"

echo ============================================
echo        KING STORE DISCORD BOT V3
echo ============================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo Criando ambiente virtual...
    py -3.12 -m venv .venv
    if errorlevel 1 (
        echo [ERRO] Python 3.12 nao encontrado.
        pause
        exit /b 1
    )
)

echo Instalando/atualizando dependencias...
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERRO] Falha ao instalar dependencias.
    pause
    exit /b 1
)

echo.
echo Iniciando bot...
echo.
.venv\Scripts\python.exe bot.py
pause
