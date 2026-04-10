@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [ERRO] Ambiente virtual nao encontrado em .venv.
  echo Crie com: py -m venv .venv
  echo Instale dependencias com: .venv\Scripts\python.exe -m pip install -e .[dev]
  exit /b 1
)

echo [1/3] Executando testes...
".venv\Scripts\python.exe" -m pytest -q
if errorlevel 1 (
  echo.
  echo [ERRO] Publicacao local abortada: testes falharam.
  pause
  exit /b 1
)

echo [2/3] Executando smoke check da aplicacao...
".venv\Scripts\python.exe" -c "from src.main import create_app; app=create_app(); required={'/healthz','/readyz','/api/v1/downloads'}; routes={getattr(r,'path',None) for r in app.routes}; missing=required-routes; import sys; print('[ERRO] Rotas ausentes:', sorted(missing)) if missing else print('[OK] Smoke check passou.'); sys.exit(1 if missing else 0)"
if errorlevel 1 (
  echo.
  echo [ERRO] Publicacao local abortada: smoke check falhou.
  pause
  exit /b 1
)

echo [3/3] Iniciando API e abrindo Swagger...
start "Baixar Video Panda API" cmd /k "cd /d "%~dp0" && call start_api.bat"
start "" "http://127.0.0.1:8000/docs"

echo [OK] Pipeline local concluido. API iniciada em nova janela.
exit /b 0
