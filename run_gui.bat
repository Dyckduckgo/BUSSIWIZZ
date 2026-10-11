@echo off
setlocal enabledelayedexpansion
title AI Stock Research
cd /d "%~dp0"

echo ======================================================================
echo  AI Stock Research - Native Desktop Application (Flet)
echo ======================================================================

REM 1. Check local .venv first
if exist "%~dp0.venv\Scripts\python.exe" (
    echo Using local .venv Python...
    "%~dp0.venv\Scripts\python.exe" app.py %*
    goto done
)

REM 2. Check py launcher
where py >nul 2>nul
if not errorlevel 1 (
    py -3 app.py %*
    goto done
)

REM 3. Check python on PATH
where python >nul 2>nul
if not errorlevel 1 (
    python app.py %*
    goto done
)

REM 4. Check python3 on PATH
where python3 >nul 2>nul
if not errorlevel 1 (
    python3 app.py %*
    goto done
)

echo.
echo [ERROR] Python was not found on this system.
echo Please install Python 3.10+ from https://www.python.org/downloads/
echo.
pause
exit /b 1

:done
