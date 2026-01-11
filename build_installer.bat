REM Build Kiosk POS Installer
REM This batch file ensures we're in the correct directory
REM Run this from the project root directory

@echo off
echo Building Kiosk POS Installer...
echo Current directory: %CD%
echo.

REM Check if we're in the right directory by looking for dist\main.exe
if not exist "dist\main.exe" (
    echo ERROR: dist\main.exe not found!
    echo Please run this batch file from the Kiosk_POS project root directory.
    echo The directory should contain: dist\, assets\, KioskPOS_Installer.iss
    pause
    exit /b 1
)

if not exist "assets" (
    echo ERROR: assets\ folder not found!
    echo Please run this batch file from the Kiosk_POS project root directory.
    pause
    exit /b 1
)

if not exist "KioskPOS_Installer.iss" (
    echo ERROR: KioskPOS_Installer.iss not found!
    echo Please run this batch file from the Kiosk_POS project root directory.
    pause
    exit /b 1
)

REM Build Kiosk POS Installer
REM This batch file ensures we're in the correct directory
REM Run this from the project root directory

@echo off
echo Building Kiosk POS Installer...
echo Current directory: %CD%
echo.

REM Check if we're in the right directory by looking for dist\main.exe
if not exist "dist\main.exe" (
    echo ERROR: dist\main.exe not found!
    echo.
    echo You must run this batch file from the Kiosk_POS project root directory.
    echo The directory should contain these files/folders:
    echo   - dist\main.exe (main application)
    echo   - assets\ (assets folder)
    echo   - email_config.json (configuration file)
    echo   - KioskPOS_Installer.iss (installer script)
    echo.
    echo Current directory contents:
    dir /b
    pause
    exit /b 1
)

if not exist "assets" (
    echo ERROR: assets\ folder not found!
    pause
    exit /b 1
)

if not exist "email_config.json" (
    echo ERROR: email_config.json not found!
    pause
    exit /b 1
)

if not exist "KioskPOS_Installer.iss" (
    echo ERROR: KioskPOS_Installer.iss not found!
    pause
    exit /b 1
)

echo All required files found. Starting build...
echo.

echo Attempting build...
ISCC KioskPOS_Installer.iss

if %ERRORLEVEL% EQU 0 (
    echo.
    echo SUCCESS: Installer created in dist\ folder
    echo File: dist\KioskPOS_Installer_v1.004.exe
    dir dist\*.exe
) else (
    echo.
    echo ERROR: Build failed with error code %ERRORLEVEL%
    echo.
    echo Possible solutions:
    echo 1. Make sure Inno Setup is installed and ISCC is in your PATH
    echo 2. Try running the command manually: ISCC KioskPOS_Installer.iss
    echo 3. Check the error messages above for specific issues
)

pause
