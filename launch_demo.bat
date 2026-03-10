@echo off
:: Kiosk POS — Demo Mode Launcher
:: Double-click this file to open the app in the isolated demo environment.
:: Your live store data is never touched.

title Kiosk POS Demo

:: Resolve the directory containing this batch file
cd /d "%~dp0"

:: Prefer the virtualenv Python if it exists
if exist ".venv\Scripts\python.exe" (
    set PYTHON=.venv\Scripts\python.exe
) else if exist "venv\Scripts\python.exe" (
    set PYTHON=venv\Scripts\python.exe
) else (
    set PYTHON=python
)

echo.
echo  ================================================
echo   Kiosk POS  ^|  Demo Mode
echo   Isolated test environment -- live data is safe
echo  ================================================
echo.

"%PYTHON%" main.py --demo

if errorlevel 1 (
    echo.
    echo  [ERROR] Failed to launch demo. Check that Python is installed and
    echo          the virtual environment is set up correctly.
    pause
)
