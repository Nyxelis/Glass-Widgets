@echo off
setlocal
cd /d "%~dp0"

echo [GlassWidgets for Windows 11]
echo Checking Python 3.14 environment...

py -3.14 --version >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set "PY_CMD=py -3.14"
) else (
    where python >nul 2>nul
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Python 3.14 not found.
        pause
        exit /b 1
    )
    set "PY_CMD=python"
)

%PY_CMD% -c "import PySide6, winrt.windows.media.control, win32gui, websockets" >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [INFO] Installing required dependencies...
    %PY_CMD% -m pip install -r requirements.txt
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to install dependencies.
        pause
        exit /b 1
    )
)

echo [INFO] Launching GlassWidgets...
%PY_CMD% src\main.py %*
