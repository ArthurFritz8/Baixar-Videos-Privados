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
  echo [OK] Ambiente pronto para executar testes.
  exit /b 0
)

set "PYTEST_ARGS=%*"
if "%PYTEST_ARGS%"=="" set "PYTEST_ARGS=-q"

echo Executando testes com argumentos: %PYTEST_ARGS%
".venv\Scripts\python.exe" -m pytest %PYTEST_ARGS%

set "EXIT_CODE=%ERRORLEVEL%"
if not "%EXIT_CODE%"=="0" (
  echo.
  echo [ERRO] Testes falharam com codigo %EXIT_CODE%.
  pause
)

exit /b %EXIT_CODE%
