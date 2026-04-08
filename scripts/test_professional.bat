@echo off
REM Waseem Brain - Professional Test Runner
REM Runs all tests with comprehensive reporting

echo ================================================================================
echo WASEEM BRAIN - PROFESSIONAL TEST SUITE
echo ================================================================================
echo Started: %date% %time%
echo.

py -3.11 run_all_professional.py

echo.
echo ================================================================================
echo TEST EXECUTION COMPLETE
echo ================================================================================
echo.
pause
