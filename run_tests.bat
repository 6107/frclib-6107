@echo off
REM ========================================================================
REM Batch file to run tox unit tests and all test executables in tests dir
REM ========================================================================

setlocal enabledelayedexpansion

REM Get the directory where this script is located
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

echo.
echo ========================================================================
echo Running Tox Unit Tests and Test Executables
echo ========================================================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    exit /b 1
)

echo [INFO] Python version:
python --version
echo.

REM Check if tox is available
python -m tox --version >nul 2>&1
if errorlevel 1 (
    echo WARNING: tox is not installed, attempting to install it...
    python -m pip install tox-uv >nul 2>&1
    if errorlevel 1 (
        echo ERROR: Failed to install tox
        exit /b 1
    )
)

echo [INFO] Running tox tests...
echo.
python -m tox
if errorlevel 1 (
    echo.
    echo ERROR: Tox tests failed with exit code !errorlevel!
    set TOX_FAILED=1
) else (
    echo.
    echo [SUCCESS] Tox tests passed
    set TOX_FAILED=0
)

echo.
echo ========================================================================
echo Running pytest on tests subdirectory
echo ========================================================================
echo.

REM Check if pytest is available
python -m pytest --version >nul 2>&1
if errorlevel 1 (
    echo WARNING: pytest is not installed, attempting to install it...
    python -m pip install pytest pytest-cov >nul 2>&1
    if errorlevel 1 (
        echo ERROR: Failed to install pytest
        exit /b 1
    )
)

REM Check if pytest-cov is available and install if needed
python -m pip show pytest-cov >nul 2>&1
if errorlevel 1 (
    echo WARNING: pytest-cov is not installed, attempting to install it...
    python -m pip install pytest-cov >nul 2>&1
    if errorlevel 1 (
        echo ERROR: Failed to install pytest-cov, falling back to pytest without coverage
        set COVERAGE_AVAILABLE=0
    ) else (
        set COVERAGE_AVAILABLE=1
    )
) else (
    set COVERAGE_AVAILABLE=1
)

echo [INFO] Running pytest on ./tests directory with code coverage...
echo.

REM Create coverage directory if it doesn't exist
if not exist "htmlcov" mkdir htmlcov

REM Run pytest with coverage reporting if available
if "!COVERAGE_AVAILABLE!"=="1" (
    python -m pytest ./tests -v --tb=short --cov=src/lib_6107 --cov-report=html --cov-report=term-missing --cov-report=xml
) else (
    python -m pytest ./tests -v --tb=short
)

if errorlevel 1 (
    echo.
    echo ERROR: Pytest failed with exit code !errorlevel!
    set PYTEST_FAILED=1
) else (
    echo.
    echo [SUCCESS] Pytest passed
    set PYTEST_FAILED=0
)

echo.
echo ========================================================================
echo Test Summary
echo ========================================================================
echo.

if "!TOX_FAILED!"=="1" (
    echo [FAILED] Tox tests - see output above for details
) else (
    echo [PASSED] Tox tests
)

if "!PYTEST_FAILED!"=="1" (
    echo [FAILED] Pytest tests - see output above for details
) else (
    echo [PASSED] Pytest tests
)

echo.
echo Coverage Report Generated:
if exist "htmlcov\index.html" (
    echo [GENERATED] HTML coverage report: htmlcov\index.html
) else (
    echo [NO COVERAGE] HTML coverage report not found
)

if exist "coverage.xml" (
    echo [GENERATED] XML coverage report: coverage.xml
) else (
    echo [NO COVERAGE] XML coverage report not found
)

echo.

REM Exit with failure code if any test failed
if "!TOX_FAILED!"=="1" goto FAILED
if "!PYTEST_FAILED!"=="1" goto FAILED

echo ========================================================================
echo All tests completed successfully!
echo ========================================================================
echo.
exit /b 0

:FAILED
echo ========================================================================
echo Some tests failed! Review output above for details.
echo ========================================================================
echo.
exit /b 1

