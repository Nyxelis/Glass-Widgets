import os
import sys
import winreg

REG_RUN_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "GlassWidgets"
LEGACY_APP_NAMES = ["LiquidGlassDesktopWidgets", "LiquidGlassWidgets", "LiquidGlass"]

def cleanup_legacy_autostart():
    for name in LEGACY_APP_NAMES:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_RUN_PATH, 0, winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, name)
                print(f"[AutoStart] Removed legacy auto-start entry: {name}", flush=True)
        except (FileNotFoundError, OSError):
            pass
        except Exception:
            pass

def get_launch_command(app_dir=None):
    if getattr(sys, "frozen", False):
        exe_path = sys.executable
        return f'"{exe_path}" --minimized'

    # Running from source: use pythonw.exe if available to launch silently without console
    py_dir = os.path.dirname(sys.executable)
    pythonw = os.path.join(py_dir, "pythonw.exe")
    python_bin = pythonw if os.path.exists(pythonw) else sys.executable

    if app_dir:
        main_py = os.path.join(app_dir, "main.py")
    else:
        main_py = os.path.abspath(sys.argv[0])

    return f'"{python_bin}" "{main_py}" --minimized'

def is_auto_start_enabled():
    cleanup_legacy_autostart()
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_RUN_PATH, 0, winreg.KEY_READ) as key:
            val, _ = winreg.QueryValueEx(key, APP_NAME)
            return bool(val)
    except FileNotFoundError:
        return False
    except Exception as e:
        print(f"[AutoStart] Error checking registry key: {e}")
        return False

def enable_auto_start(app_dir=None):
    try:
        cmd = get_launch_command(app_dir)
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_RUN_PATH, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
        print(f"[AutoStart] Enabled auto-start: {cmd}")
        return True
    except PermissionError as pe:
        print(f"[AutoStart] Permission denied enabling auto-start: {pe}")
        return False
    except Exception as e:
        print(f"[AutoStart] Error enabling auto-start: {e}")
        return False

def disable_auto_start():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_RUN_PATH, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, APP_NAME)
        print("[AutoStart] Disabled auto-start")
        return True
    except FileNotFoundError:
        return True
    except PermissionError as pe:
        print(f"[AutoStart] Permission denied disabling auto-start: {pe}")
        return False
    except Exception as e:
        print(f"[AutoStart] Error disabling auto-start: {e}")
        return False
