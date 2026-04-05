@echo off
setlocal EnableExtensions
set "ROOT=%~dp0"
cd /d "%ROOT%"

set "PYTHON_CMD=python"
where python >nul 2>nul
if errorlevel 1 (
  where py >nul 2>nul
  if errorlevel 1 (
    echo [ERROR] Python not found.
    pause
    exit /b 1
  )
  set "PYTHON_CMD=py -3"
)

echo [INFO] Starting Lattice Brain Backend...
call %PYTHON_CMD% scripts\manage_router_daemon.py start
if errorlevel 1 (
    echo [ERROR] Failed to start router daemon.
    pause
    exit /b 1
)

echo [INFO] Backend is running.
pause
