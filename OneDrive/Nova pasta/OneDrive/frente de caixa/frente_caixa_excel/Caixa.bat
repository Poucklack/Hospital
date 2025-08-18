@echo off
REM Vai para a pasta do script
cd /d "%~dp0"

REM Verifica se o Python está instalado
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo Python não encontrado. Baixando e instalando...

    REM Baixa o instalador oficial do Python
    powershell -Command "Invoke-WebRequest -Uri https://www.python.org/ftp/python/3.12.6/python-3.12.6-amd64.exe -OutFile python-installer.exe"

    REM Instala silenciosamente (com pip incluso e variáveis de ambiente configuradas)
    start /wait python-installer.exe /quiet InstallAllUsers=1 PrependPath=1 Include_pip=1

    REM Remove o instalador
    del python-installer.exe

    echo Python instalado com sucesso!
)

echo Instalando dependências...
pip install flask pandas openpyxl --quiet

REM Roda o Flask em background (sem abrir janela do terminal)
start "" pythonw.exe "%cd%\app.py"

REM Dá um tempinho para o servidor subir antes de abrir o navegador
timeout /t 3 /nobreak >nul

REM Abre o navegador no endereço local
start "" "http://10.0.0.174:5000"

exit


REM Roda o Flask
python app.py

pause