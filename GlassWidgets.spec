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
    excludes=["tkinter", "unittest", "pydoc"],
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
