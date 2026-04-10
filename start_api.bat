@echo off
setlocal

cd /d "%~dp0"
set "MODE=%~1"

if not exist ".venv\Scripts\python.exe" (
  echo [ERRO] Ambiente virtual nao encontrado em .venv.
  echo Crie com: py -m venv .venv
  echo Instale dependencias com: .venv\Scripts\python.exe -m pip install -e .[dev]
  exit /b 1
)

if /I "%MODE%"=="--check" (
  echo [OK] Ambiente pronto para iniciar a API.
  exit /b 0
)

echo Iniciando API em http://127.0.0.1:8000 ...
".venv\Scripts\python.exe" -m uvicorn src.main:app --host 127.0.0.1 --port 8000 --reload

set "EXIT_CODE=%ERRORLEVEL%"
if not "%EXIT_CODE%"=="0" (
  echo.
  echo [ERRO] A API foi encerrada com codigo %EXIT_CODE%.
  pause
)

exit /b %EXIT_CODE%
