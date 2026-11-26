# -*- mode: python ; coding: utf-8 -*-
import sys
import os

block_cipher = None
repo_dir = os.path.abspath(SPECPATH)

datas = [
    (os.path.join(repo_dir, "upstream_kde_widgets"), "upstream_kde_widgets"),
    (os.path.join(repo_dir, "src", "ui"), "src/ui"),
    (os.path.join(repo_dir, "src", "compat"), "src/compat"),
    (os.path.join(repo_dir, "assets"), "assets"),
]

hiddenimports = [
    "PySide6.QtQuick",
    "PySide6.QtQml",
    "PySide6.QtNetwork",
    "PySide6.QtGui",
    "PySide6.QtCore",
    "PySide6.QtWidgets",
    "sqlite3",
    "winreg",
    "ctypes",
    "urllib.request",
    "urllib.parse",
    "json",
    "xml.etree.ElementTree",
    "winrt.windows.media.control",
    "winrt.windows.foundation",
    "winrt.windows.foundation.collections",
    "winrt.windows.storage.streams",
    "win32gui",
    "win32con",
    "win32api",
    "websockets",
    "websockets.asyncio.client",
    "psutil",
]

a = Analysis(
    [os.path.join(repo_dir, "src", "main.py")],
    pathex=[repo_dir, os.path.join(repo_dir, "src")],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter", "unittest", "pydoc",
        "PySide6.QtWebEngineCore", "PySide6.QtWebEngineQuick", "PySide6.QtWebEngineWidgets",
        "PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets",
        "PySide6.Qt3DCore", "PySide6.Qt3DRender", "PySide6.Qt3DInput", "PySide6.Qt3DLogic",
        "PySide6.Qt3DExtras", "PySide6.Qt3DAnimation",
        "PySide6.QtPdf", "PySide6.QtPdfWidgets", "PySide6.QtQuick3D",
        "PySide6.QtCharts", "PySide6.QtDataVisualization",
        "PySide6.QtBluetooth", "PySide6.QtNfc", "PySide6.QtSensors", "PySide6.QtSerialPort",
        "PySide6.QtPositioning", "PySide6.QtLocation", "PySide6.QtRemoteObjects",
        "PySide6.QtScxml", "PySide6.QtSql", "PySide6.QtTest",
        "PySide6.QtDesigner", "PySide6.QtHelp", "PySide6.QtSvgWidgets",
        "PySide6.QtVirtualKeyboard",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='GlassWidgets',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(repo_dir, "assets", "app_icon.ico"),
    version=os.path.join(repo_dir, "version_info.txt"),
)
