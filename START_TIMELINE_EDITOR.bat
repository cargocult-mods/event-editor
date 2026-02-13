@echo off
REM Timeline Editor - Quick Launch
REM For: cargocult-mods

echo.
echo ================================================
echo   EventEditor - Timeline Mode
echo ================================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found
    pause
    exit /b 1
)

echo Starting Timeline Editor...
python -m eventeditor.timeline

if errorlevel 1 (
    echo.
    echo ERROR: Failed to start
    echo Make sure you ran: pip install -r requirements.txt
    pause
)
