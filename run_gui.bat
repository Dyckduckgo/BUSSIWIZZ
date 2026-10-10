@echo off
setlocal enabledelayedexpansion
title Bussiwzz - AI Stock Research Agent
cd /d "%~dp0"

echo ======================================================================
echo  Bussiwzz - Stock Research Native Desktop Dashboard
echo ======================================================================

REM 1. Check local .venv first if it runs on this PC
if exist "%~dp0.venv\Scripts\python.exe" (
    "%~dp0.venv\Scripts\python.exe" -c "import tkinter" >nul 2>nul
    if not errorlevel 1 (
        echo Using local .venv Python...
        "%~dp0.venv\Scripts\python.exe" run.py --gui %*
        goto done
    )
)

REM 2. Check py launcher
where py >nul 2>nul
if not errorlevel 1 (
    py -3 -c "import tkinter" >nul 2>nul
    if not errorlevel 1 (
        py -3 run.py --gui %*
        goto done
    )
)

REM 3. Check python on PATH
where python >nul 2>nul
if not errorlevel 1 (
    python -c "import tkinter" >nul 2>nul
    if not errorlevel 1 (
        python run.py --gui %*
        goto done
    )
)

REM 4. Check python3 on PATH
where python3 >nul 2>nul
if not errorlevel 1 (
    python3 -c "import tkinter" >nul 2>nul
    if not errorlevel 1 (
        python3 run.py --gui %*
        goto done
    )
)

echo.
echo [ERROR] Python 3.10+ with Tkinter support was not found on this system.
echo.
echo To fix this:
echo   1. Download Python from: https://www.python.org/downloads/
echo   2. During installation, make sure to check:
echo      - "Add python.exe to PATH"
echo      - "tcl/tk and IDLE" (under Customize installation)
echo.
echo Or run the Web Dashboard instead:
echo   run_web.bat
echo.
pause
exit /b 1

:done
