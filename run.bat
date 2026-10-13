@echo off
setlocal

cd /d "%~dp0"

set "VENV_PY=.venv\Scripts\python.exe"

if not exist "%VENV_PY%" (
  echo [ERROR] No se encontro la venv en .venv\Scripts\python.exe
  echo Crea la venv con: py -m venv .venv
  pause
  exit /b 1
)

echo [INFO] Verificando dependencias...
"%VENV_PY%" -m pip install -r requirements.txt >nul 2>&1

echo [INFO] Iniciando aplicacion Flask con venv...
"%VENV_PY%" app.py

if errorlevel 1 (
  echo.
  echo [ERROR] La aplicacion finalizo con error.
  pause
)

endlocal
