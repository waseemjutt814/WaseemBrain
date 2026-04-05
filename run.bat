@echo off
setlocal EnableExtensions

set "ROOT=%~dp0"
cd /d "%ROOT%"

set "PYTHON_CMD=python"
where python >nul 2>nul
if errorlevel 1 (
  where py >nul 2>nul
  if errorlevel 1 (
    echo [ERROR] Python not found in PATH.
    exit /b 1
  )
  set "PYTHON_CMD=py -3"
)

where pnpm >nul 2>nul
if errorlevel 1 (
  echo [ERROR] pnpm not found in PATH.
  exit /b 1
)

set "ACTION=%~1"
if "%ACTION%"=="" set "ACTION=dev"

if /I "%ACTION%"=="dev" goto dev
if /I "%ACTION%"=="start" goto dev
if /I "%ACTION%"=="prepare" goto prepare
if /I "%ACTION%"=="chat" goto chat
if /I "%ACTION%"=="bench" goto bench
if /I "%ACTION%"=="knowledge" goto knowledge
if /I "%ACTION%"=="assets" goto assets
if /I "%ACTION%"=="build" goto build
if /I "%ACTION%"=="test" goto test
if /I "%ACTION%"=="doctor" goto doctor
if /I "%ACTION%"=="router-start" goto router_start
if /I "%ACTION%"=="router-stop" goto router_stop
if /I "%ACTION%"=="router-status" goto router_status
if /I "%ACTION%"=="runtime-start" goto runtime_start
if /I "%ACTION%"=="runtime-stop" goto runtime_stop
if /I "%ACTION%"=="runtime-status" goto runtime_status
if /I "%ACTION%"=="skills" goto skills
if /I "%ACTION%"=="help" goto help

echo [ERROR] Unknown action: %ACTION%
goto help

:dev
echo [INFO] Starting local router daemon...
call %PYTHON_CMD% scripts\manage_router_daemon.py start
if errorlevel 1 exit /b %errorlevel%
echo [INFO] Launching Fastify dev server...
call pnpm run dev
exit /b %errorlevel%

:prepare
echo [INFO] Preparing local runtime artifacts and warm caches...
call %PYTHON_CMD% scripts\prepare_runtime.py %2 %3 %4 %5 %6 %7 %8 %9
exit /b %errorlevel%

:chat
echo [INFO] Ensuring local router daemon is available...
call %PYTHON_CMD% scripts\manage_router_daemon.py start --skip-build
if errorlevel 1 exit /b %errorlevel%
echo [INFO] Ensuring hot Python runtime daemon is available...
call %PYTHON_CMD% scripts\manage_runtime_daemon.py start
if errorlevel 1 exit /b %errorlevel%
echo [INFO] Launching CLI chat...
call %PYTHON_CMD% scripts\chat_cli.py %2 %3 %4 %5 %6 %7 %8 %9
exit /b %errorlevel%

:bench
echo [INFO] Running runtime benchmark...
call %PYTHON_CMD% scripts\benchmark.py %2 %3 %4 %5 %6 %7 %8 %9
exit /b %errorlevel%

:knowledge
echo [INFO] Building real local knowledge packs from curated online sources...
call %PYTHON_CMD% scripts\build_knowledge_store.py %2 %3 %4 %5 %6 %7 %8 %9
exit /b %errorlevel%

:assets
echo [INFO] Warming runtime models and building the local knowledge store...
call %PYTHON_CMD% scripts\download_models.py %2 %3 %4 %5 %6 %7 %8 %9
exit /b %errorlevel%

:build
echo [INFO] Building TypeScript interface...
call pnpm run build
if errorlevel 1 exit /b %errorlevel%
echo [INFO] Validating Python types...
call %PYTHON_CMD% -m mypy brain
exit /b %errorlevel%

:test
echo [INFO] Running Python tests...
call %PYTHON_CMD% -m pytest tests\python -q
if errorlevel 1 exit /b %errorlevel%
echo [INFO] Running TypeScript tests...
call pnpm test
if errorlevel 1 exit /b %errorlevel%
echo [INFO] Running Rust tests...
powershell -ExecutionPolicy Bypass -File scripts\test_rust.ps1
exit /b %errorlevel%

:doctor
echo [INFO] Running backend diagnostics...
call %PYTHON_CMD% scripts\diagnose_backends.py
exit /b %errorlevel%

:router_start
call %PYTHON_CMD% scripts\manage_router_daemon.py start
exit /b %errorlevel%

:router_stop
call %PYTHON_CMD% scripts\manage_router_daemon.py stop
exit /b %errorlevel%

:router_status
call %PYTHON_CMD% scripts\manage_router_daemon.py status
exit /b %errorlevel%

:runtime_start
call %PYTHON_CMD% scripts\manage_runtime_daemon.py start
exit /b %errorlevel%

:runtime_stop
call %PYTHON_CMD% scripts\manage_runtime_daemon.py stop
exit /b %errorlevel%

:runtime_status
call %PYTHON_CMD% scripts\manage_runtime_daemon.py status
exit /b %errorlevel%

:skills
echo [INFO] Syncing generated Codex skills into tmp\skills...
call %PYTHON_CMD% scripts\sync_codex_skills.py --output-root tmp\skills
if errorlevel 1 exit /b %errorlevel%
call %PYTHON_CMD% scripts\validate_codex_skills.py tmp\skills
exit /b %errorlevel%

:help
echo Usage: run.bat [dev^|prepare^|chat^|bench^|knowledge^|assets^|build^|test^|doctor^|router-start^|router-stop^|router-status^|runtime-start^|runtime-stop^|runtime-status^|skills^|help]
echo.
echo   dev            Start router daemon and run the Fastify dev server.
echo   prepare        Validate artifacts, warm local models, and run a smoke query.
echo   chat           Start the real CLI chat with streamed answers and metrics.
echo   bench          Run the Python runtime benchmark script.
echo   knowledge      Build generated knowledge packs from curated online sources.
echo   assets         Warm runtime models and build the generated knowledge store.
echo   build          Build TypeScript and run Python mypy.
echo   test           Run Python, TypeScript, and Rust tests.
echo   doctor         Run backend diagnostics.
echo   router-start   Start the detached Rust router daemon.
echo   router-stop    Stop the detached Rust router daemon.
echo   router-status  Show router daemon status.
echo   runtime-start  Start the detached Python runtime daemon.
echo   runtime-stop   Stop the detached Python runtime daemon.
echo   runtime-status Show Python runtime daemon status.
echo   skills         Sync and validate generated Codex skills.
echo   help           Show this help.
exit /b 0
