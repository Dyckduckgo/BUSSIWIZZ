@echo off
REM ============================================================================
REM   AI Stock Research - Windows Standalone Desktop Build Script
REM   Packages the Flet app into a standalone desktop application.
REM ============================================================================

setlocal enabledelayedexpansion
title AI Stock Research - Build Pipeline

echo ============================================================================
echo   AI Stock Research - Standalone Windows Application Build
echo ============================================================================

REM 1. Identify python executable
set "PYTHON_EXE="
if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
) else if exist "venv\Scripts\python.exe" (
    set "PYTHON_EXE=venv\Scripts\python.exe"
) else (
    set "PYTHON_EXE=python"
)

echo [*] Using Python interpreter: %PYTHON_EXE%

REM 2. Run automated packaging pipeline
%PYTHON_EXE% build_windows.py %*

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [!] Build failed with exit code %ERRORLEVEL%.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo ============================================================================
echo   [OK] Build completed successfully!
echo   Executable folder  : dist\AI Stock Research\
echo   Release ZIP archive: dist\AI_Stock_Research_v1.0.0_Windows_x64.zip
echo   SHA-256 checksum   : dist\AI_Stock_Research_v1.0.0_Windows_x64.zip.sha256
echo ============================================================================
echo.
pause
