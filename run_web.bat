@echo off
setlocal
title Bussiwzz - Web Research Dashboard
cd /d "%~dp0"

echo ======================================================================
echo  Bussiwzz - Stock Research Web Dashboard
echo ======================================================================

set PORT_ARG=
if not "%~1"=="" set PORT_ARG=--port %~1

REM Check local .venv first
if exist "%~dp0.venv\Scripts\python.exe" (
    "%~dp0.venv\Scripts\python.exe" -c "import sys" >nul 2>nul
    if not errorlevel 1 (
        "%~dp0.venv\Scripts\python.exe" run.py --web %PORT_ARG% %*
        goto done
    )
)

REM Fall back to py launcher or python
where py >nul 2>nul
if not errorlevel 1 (
    py -3 run.py --web %PORT_ARG% %*
    goto done
)

where python >nul 2>nul
if not errorlevel 1 (
    python run.py --web %PORT_ARG% %*
    goto done
)

echo Python was not found. Please install Python 3.10 or newer.
pause
exit /b 1

:done
