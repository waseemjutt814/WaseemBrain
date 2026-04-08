@echo off
REM Waseem Brain - Test with Coverage
REM Runs tests and generates coverage report

echo ================================================================================
echo WASEEM BRAIN - TEST WITH COVERAGE
echo ================================================================================
echo.

py -3.11 -m pytest tests/python --cov=brain --cov-report=html --cov-report=term

echo.
echo ================================================================================
echo COVERAGE REPORT GENERATED
echo Open htmlcov/index.html to view detailed report
echo ================================================================================
echo.
pause
