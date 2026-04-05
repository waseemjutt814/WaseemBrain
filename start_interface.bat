@echo off
setlocal EnableExtensions
set "ROOT=%~dp0"
cd /d "%ROOT%"

where pnpm >nul 2>nul
if errorlevel 1 (
  echo [ERROR] pnpm not found. Please install pnpm first.
  pause
  exit /b 1
)

echo [INFO] Starting Lattice Brain Interface...
call pnpm run dev
if errorlevel 1 (
    echo [ERROR] Failed to start interface.
    pause
    exit /b 1
)
