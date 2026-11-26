@echo off
setlocal
cd /d "%~dp0"

echo ===================================================
echo Building Standalone GlassWidgets.exe (Python 3.14)
echo ===================================================

echo [1/4] Closing any running GlassWidgets instances...
taskkill /F /IM GlassWidgets.exe >nul 2>&1
ping 127.0.0.1 -n 2 >nul 2>&1
if exist "dist\GlassWidgets.exe" del /f /q "dist\GlassWidgets.exe" >nul 2>&1

echo [2/4] Verifying Python 3.14 environment...
py -3.14 --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 3.14 not found via py -3.14!
    if "%~1"=="" pause
    exit /b 1
)

echo [3/4] Ensuring PyInstaller and dependencies are installed in Python 3.14...
py -3.14 -m pip install --quiet pyinstaller
py -3.14 -m pip install --quiet -r requirements.txt

echo [4/4] Running PyInstaller build...
py -3.14 -m PyInstaller --noconfirm GlassWidgets.spec
if errorlevel 1 (
    echo.
    echo ===================================================
    echo [ERROR] PyInstaller build failed! Check output above.
    echo ===================================================
    if "%~1"=="" pause
    exit /b 1
)

if exist "dist\GlassWidgets.exe" (
    echo.
    echo ===================================================
    echo [SUCCESS] Build completed successfully!
    echo Executable: %CD%\dist\GlassWidgets.exe
    echo ===================================================
) else (
    echo.
    echo [ERROR] Build output missing!
)

if "%~1"=="" pause
