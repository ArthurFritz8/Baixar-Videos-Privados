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

set "PORT=8000"
if not "%START_API_PORT%"=="" set "PORT=%START_API_PORT%"

set "PORT_PID="
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":%PORT% .*LISTENING"') do (
  set "PORT_PID=%%P"
  goto :port_check_done
)

:port_check_done
if not "%PORT_PID%"=="" (
  echo [ERRO] A porta %PORT% ja esta em uso por PID %PORT_PID%.
  echo Encerre o processo com: taskkill /PID %PORT_PID% /F
  echo Ou inicie em outra porta com: set START_API_PORT=8010
  exit /b 1
)

echo Iniciando API em http://127.0.0.1:%PORT% ...
".venv\Scripts\python.exe" -m uvicorn src.main:app --host 127.0.0.1 --port %PORT% --reload

set "EXIT_CODE=%ERRORLEVEL%"
if not "%EXIT_CODE%"=="0" (
  echo.
  echo [ERRO] A API foi encerrada com codigo %EXIT_CODE%.
  pause
)

exit /b %EXIT_CODE%
