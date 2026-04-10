@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [ERRO] Ambiente virtual nao encontrado em .venv.
  echo Crie com: py -m venv .venv
  echo Instale dependencias com: .venv\Scripts\python.exe -m pip install -e .[dev]
  exit /b 1
)

if "%~1"=="" (
  echo Uso:
  echo   download_link.bat "URL_DO_VIDEO" [provider]
  echo.
  echo Exemplos:
  echo   download_link.bat "https://www.youtube.com/watch?v=abc123"
  echo   download_link.bat "https://cdn.exemplo.com/video.mp4" panda_video
  exit /b 1
)

set "VIDEO_URL=%~1"
set "PROVIDER=%~2"

if "%PROVIDER%"=="" (
  ".venv\Scripts\python.exe" scripts\download_from_cmd.py --url "%VIDEO_URL%"
) else (
  ".venv\Scripts\python.exe" scripts\download_from_cmd.py --url "%VIDEO_URL%" --provider "%PROVIDER%"
)

set "EXIT_CODE=%ERRORLEVEL%"
if not "%EXIT_CODE%"=="0" (
  echo.
  echo [ERRO] Download falhou com codigo %EXIT_CODE%.
  pause
)

exit /b %EXIT_CODE%
