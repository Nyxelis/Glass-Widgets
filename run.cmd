@echo off
setlocal
cd /d "%~dp0"

echo [GlassWidgets for Windows 11]
echo Checking Python environment...

where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python not found in PATH. Please install Python 3.10+ and add to PATH.
    pause
    exit /b 1
)

python -c "import PySide6, winrt.windows.media.control, win32gui" >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [INFO] Installing required dependencies...
    python -m pip install -r requirements.txt
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to install dependencies.
        pause
        exit /b 1
    )
)

echo [INFO] Launching GlassWidgets...
python src\main.py %*
