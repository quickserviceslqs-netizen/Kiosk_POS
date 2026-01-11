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

echo All required files found. Starting build...
echo.

echo Attempting build with current directory as source...
ISCC /dSourceDir="%CD%" KioskPOS_Installer.iss

if %ERRORLEVEL% EQU 0 (
    echo.
    echo SUCCESS: Installer created in dist\ folder
    goto :success
) else (
    echo.
    echo Build failed! Trying alternative method...
    echo.
    ISCC KioskPOS_Installer.iss
    
    if %ERRORLEVEL% EQU 0 (
        echo.
        echo SUCCESS: Installer created using default paths
        goto :success
    ) else (
        echo.
        echo ERROR: Both build methods failed!
        echo.
        echo Troubleshooting:
        echo - Ensure you're running from the Kiosk_POS project root
        echo - Check that all files exist: dist\main.exe, assets\, email_config.json
        echo - Try manual command: ISCC /dSourceDir="C:\full\path\to\Kiosk_POS" KioskPOS_Installer.iss
        goto :error
    )
)

:success
echo.
echo Build completed successfully!
echo Installer: dist\KioskPOS_Installer_v1.004.exe
goto :end

:error
echo Build failed with errors.
goto :end

:end
pause
