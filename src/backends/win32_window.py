import ctypes
from ctypes import wintypes
import threading
import win32gui
import win32con
from PySide6.QtCore import QAbstractNativeEventFilter

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

GWLP_HWNDPARENT = -8
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040
HWND_BOTTOM = 1
HWND_TOP = 0

WM_MOUSEACTIVATE = 0x0021
MA_NOACTIVATE = 3
WS_EX_NOACTIVATE = 0x08000000

_desktop_switched_threads = set()

def ensure_default_desktop():
    """Ensure current thread runs on the user's interactive WinSta0\\Default desktop."""
    tid = threading.get_ident()
    if tid in _desktop_switched_threads:
        return True
    try:
        hdesk = user32.OpenDesktopW("Default", 0, False, 0x10000000)
        if hdesk:
            ret = user32.SetThreadDesktop(hdesk)
            if ret:
                _desktop_switched_threads.add(tid)
            return bool(ret)
    except Exception:
        pass
    return False

def find_shell_desktop_window():
    """Finds Progman or WorkerW that hosts the desktop icons."""
    progman = user32.FindWindowW("Progman", None)
    if progman:
        def_view = user32.FindWindowExW(progman, 0, "SHELLDLL_DefView", None)
        if def_view:
            return progman

    # Search WorkerW windows
    def enum_cb(hwnd, result):
        def_view = user32.FindWindowExW(hwnd, 0, "SHELLDLL_DefView", None)
        if def_view:
            result.append(hwnd)
        return True

    results = []
    win32gui.EnumWindows(enum_cb, results)
    if results:
        return results[0]
    return progman or 0

def pin_widget_to_desktop(hwnd, pin_to_bottom=True):
    if not hwnd:
        return

    # 1. WS_EX_TOOLWINDOW (hides from taskbar) & WS_EX_NOACTIVATE (prevents activation on click)
    ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
    ex_style |= win32con.WS_EX_TOOLWINDOW
    ex_style &= ~win32con.WS_EX_APPWINDOW
    if pin_to_bottom:
        ex_style |= WS_EX_NOACTIVATE
    else:
        ex_style &= ~WS_EX_NOACTIVATE
    win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex_style)

    # 2. Attach to Shell View / Progman so Win+D doesn't hide it (only when pinned)
    h_shell = find_shell_desktop_window() if pin_to_bottom else 0
    try:
        if hasattr(user32, "SetWindowLongPtrW"):
            user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.HWND]
            user32.SetWindowLongPtrW.restype = wintypes.HWND
            user32.SetWindowLongPtrW(hwnd, GWLP_HWNDPARENT, h_shell)
        else:
            win32gui.SetWindowLong(hwnd, GWLP_HWNDPARENT, h_shell)
    except Exception as e:
        print(f"[Win32Window] SetWindowLongPtr parent error: {e}")

    # 3. Z-order positioning
    target_z = HWND_BOTTOM if pin_to_bottom else HWND_TOP
    user32.SetWindowPos(
        hwnd,
        target_z,
        0, 0, 0, 0,
        SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW
    )


class WidgetNativeEventFilter(QAbstractNativeEventFilter):
    def __init__(self, service):
        super().__init__()
        self.service = service

    def nativeEventFilter(self, eventType, message):
        if eventType == b"windows_generic_MSG":
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == WM_MOUSEACTIVATE:
                if msg.hwnd in self.service.widget_hwnds:
                    # Return MA_NOACTIVATE (3): mouse click processed, window not activated/raised
                    # Keeps widgets completely independent without bringing all windows to front
                    return True, MA_NOACTIVATE
        return False, 0

