@echo off
setlocal EnableExtensions
set "ROOT=%~dp0"
cd /d "%ROOT%"

set "PYTHON_CMD=python"
where python >nul 2>nul
if errorlevel 1 (
  where py >nul 2>nul
  if errorlevel 1 (
    echo [ERROR] Python 3.11 was not found.
    pause
    exit /b 1
  )
  set "PYTHON_CMD=py -3.11"
)

echo [INFO] Starting Waseem Brain backend runtime daemon...
call %PYTHON_CMD% scripts\manage_runtime_daemon.py start
if errorlevel 1 (
  echo [ERROR] Failed to start the Waseem Brain runtime daemon.
  pause
  exit /b 1
)

echo [INFO] Backend is ready.
pause