@echo off
REM Waseem Brain - Quick Test (Fast)
REM Runs unit tests only

echo ================================================================================
echo WASEEM BRAIN - QUICK TEST
echo ================================================================================
echo.

py -3.11 -m pytest tests/python -q --tb=line

echo.
echo ================================================================================
echo QUICK TEST COMPLETE
echo ================================================================================
echo.
pause
