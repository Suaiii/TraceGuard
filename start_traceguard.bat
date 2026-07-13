@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_CMD=python"
if exist ".venv\Scripts\python.exe" set "PYTHON_CMD=.venv\Scripts\python.exe"
if exist "venv\Scripts\python.exe" set "PYTHON_CMD=venv\Scripts\python.exe"
if defined TRACEGUARD_PYTHON set "PYTHON_CMD=%TRACEGUARD_PYTHON%"

if "%~1"=="--help" goto run
if "%~1"=="-h" goto run

%PYTHON_CMD% -c "import fastapi, torch, uvicorn" >nul 2>&1
if errorlevel 1 (
  echo [TraceGuard] Python dependencies are missing.
  echo Run: %PYTHON_CMD% -m pip install -r requirements.txt
  exit /b 1
)

if not exist "checkpoints\best.pth" if not exist "best.pth" (
  echo [TraceGuard] Model checkpoint not found.
  echo Place best.pth in the project root or checkpoints\best.pth.
  exit /b 1
)

:run
%PYTHON_CMD% server.py %*
exit /b %ERRORLEVEL%
