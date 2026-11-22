import sys
import os
import shutil
from PySide6.QtCore import QStandardPaths

def get_base_dir():
    """Returns root directory containing bundled assets (sys._MEIPASS when frozen or repository root when source)."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    cur = os.path.abspath(os.path.dirname(__file__))
    if os.path.basename(cur) in ("src", "utils", "backends", "ui"):
        cur = os.path.dirname(cur)
    return cur

def get_resource_path(relative_path=""):
    """Returns absolute path to a bundled asset (QML, shaders, fonts, icons)."""
    base = get_base_dir()
    if not relative_path:
        return base
    return os.path.normpath(os.path.join(base, relative_path))

def get_fallback_appdata_dir():
    """Returns safe fallback directory in %APPDATA% if portable folder is read-only."""
    base = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    if not base or "GlassWidgets" not in base:
        base = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "GlassWidgets")
    os.makedirs(base, exist_ok=True)
    return base

def get_writable_appdata_dir():
    """
    Returns portable data/ directory inside application executable/project folder.
    - Frozen (.exe): [Executable_Dir]/data/
    - Source: [Project_Root]/data/
    - Read-Only Fallback: %APPDATA%/GlassWidgets if permissions fail (e.g. Program Files).
    """
    if getattr(sys, "frozen", False):
        app_dir = os.path.dirname(os.path.abspath(sys.executable))
    else:
        cur = os.path.abspath(os.path.dirname(__file__))
        if os.path.basename(cur) in ("src", "utils", "backends", "ui"):
            app_dir = os.path.dirname(cur)
        else:
            app_dir = cur

    portable_dir = os.path.join(app_dir, "data")

    try:
        os.makedirs(portable_dir, exist_ok=True)
        # Test write permissions
        test_file = os.path.join(portable_dir, ".write_test")
        with open(test_file, "w") as f:
            f.write("ok")
        if os.path.exists(test_file):
            try:
                os.remove(test_file)
            except OSError:
                pass

        return portable_dir

    except (PermissionError, OSError):
        # Read-only directory (e.g. C:\Program Files\) - fallback to %APPDATA%
        return get_fallback_appdata_dir()

# Alias for modern portable naming
get_data_dir = get_writable_appdata_dir
