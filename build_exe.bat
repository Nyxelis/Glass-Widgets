@echo off
setlocal
cd /d "%~dp0"

echo ===================================================
echo Building Standalone GlassWidgets.exe
echo ===================================================

echo [1/4] Closing any running GlassWidgets instances...
taskkill /F /IM GlassWidgets.exe >nul 2>&1
ping 127.0.0.1 -n 2 >nul 2>&1
if exist "dist\GlassWidgets.exe" del /f /q "dist\GlassWidgets.exe" >nul 2>&1

echo [2/4] Verifying Python environment...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found in PATH!
    if "%~1"=="" pause
    exit /b 1
)

echo [3/4] Ensuring PyInstaller is installed...
python -m pip install --quiet pyinstaller

echo [4/4] Running PyInstaller build...
python -m PyInstaller --noconfirm GlassWidgets.spec
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
