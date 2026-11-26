import os
import ctypes
import threading
import time
from ctypes import wintypes
import winreg

from PySide6.QtCore import QObject, Signal, Property, Slot, QTimer, QMetaObject, Qt, QAbstractNativeEventFilter
from PySide6.QtGui import QImage, QColor, QGuiApplication, QPainter, QLinearGradient
from PySide6.QtQuick import QQuickImageProvider

user32 = ctypes.windll.user32

SPI_GETDESKWALLPAPER = 0x0073
SPI_SETDESKWALLPAPER = 0x0014
WM_SETTINGCHANGE = 0x001A


class WallpaperNativeEventFilter(QAbstractNativeEventFilter):
    def __init__(self, backend):
        super().__init__()
        self.backend = backend

    def nativeEventFilter(self, eventType, message):
        if eventType == b"windows_generic_MSG":
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == WM_SETTINGCHANGE:
                # Catch wallpaper change message
                if msg.wParam in (0, SPI_SETDESKWALLPAPER):
                    QTimer.singleShot(150, self.backend.refresh_wallpaper)
        return False, 0


class WallpaperImageProvider(QQuickImageProvider):
    def __init__(self, backend):
        super().__init__(QQuickImageProvider.ImageType.Image)
        self.backend = backend

    def requestImage(self, id_str, size, reqSize):
        img = self.backend.get_wallpaper_image()
        if img is None or img.isNull():
            img = self.backend.create_fallback_acrylic_image()
        elif reqSize.isValid() and reqSize.width() > 0 and reqSize.height() > 0:
            if img.width() > reqSize.width() or img.height() > reqSize.height():
                img = img.scaled(reqSize, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
        return img


class WallpaperBackend(QObject):
    wallpaperChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cached_image = None
        self._last_wallpaper_path = ""
        self._last_mtime = 0
        self._revision = 0
        self._watcher_thread = None
        self._running = True

        self.refresh_wallpaper()
        self._start_registry_watcher()

    def get_accent_color(self) -> str:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\DWM") as key:
                val, _ = winreg.QueryValueEx(key, "ColorizationColor")
                return f"#{val & 0xFFFFFF:06x}"
        except Exception:
            return "#0a84ff"

    def _scale_to_screen(self, img: QImage) -> QImage:
        if img is None or img.isNull():
            return img
        sw = max(1, self.screenWidth)
        sh = max(1, self.screenHeight)
        if img.width() > sw or img.height() > sh:
            scaled = img.scaled(sw, sh, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
            if scaled.width() > sw or scaled.height() > sh:
                cx = max(0, (scaled.width() - sw) // 2)
                cy = max(0, (scaled.height() - sh) // 2)
                return scaled.copy(cx, cy, min(sw, scaled.width()), min(sh, scaled.height()))
            return scaled
        return img

    def create_fallback_acrylic_image(self) -> QImage:
        accent_hex = self.get_accent_color()
        base_col = QColor(accent_hex)
        sw = max(1, self.screenWidth)
        sh = max(1, self.screenHeight)
        img = QImage(sw, sh, QImage.Format_ARGB32_Premultiplied)
        top_col = QColor(int(base_col.red() * 0.35), int(base_col.green() * 0.35), int(base_col.blue() * 0.35))
        bottom_col = QColor(int(base_col.red() * 0.12), int(base_col.green() * 0.12), int(base_col.blue() * 0.12))
        painter = QPainter(img)
        grad = QLinearGradient(0, 0, sw, sh)
        grad.setColorAt(0.0, top_col)
        grad.setColorAt(1.0, bottom_col)
        painter.fillRect(0, 0, sw, sh, grad)
        painter.end()
        return img

    def get_wallpaper_path(self) -> str:
        # 1. Try SystemParametersInfoW
        buf = ctypes.create_unicode_buffer(1024)
        if user32.SystemParametersInfoW(SPI_GETDESKWALLPAPER, 1024, buf, 0):
            path = buf.value.strip()
            if path and os.path.exists(path):
                return path

        # 2. Try registry
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop") as key:
                val, _ = winreg.QueryValueEx(key, "Wallpaper")
                if val and os.path.exists(val):
                    return val
        except Exception:
            pass

        # 3. Try Windows Themes TranscodedWallpaper
        transcoded = os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Themes\TranscodedWallpaper")
        if os.path.exists(transcoded) and os.path.getsize(transcoded) > 0:
            return transcoded

        return ""

    @Slot()
    def refresh_wallpaper(self):
        path = self.get_wallpaper_path()
        img = None
        mtime = 0
        if path and os.path.exists(path):
            try:
                mtime = os.path.getmtime(path)
            except Exception:
                pass
            img = QImage(path)

        # Fallback to TranscodedWallpaper if primary path fails or is empty
        transcoded = os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Themes\TranscodedWallpaper")
        if (img is None or img.isNull()) and os.path.exists(transcoded) and os.path.getsize(transcoded) > 0:
            try:
                mtime = os.path.getmtime(transcoded)
                path = transcoded
            except Exception:
                pass
            img = QImage(transcoded)

        # Fallback to acrylic gradient based on desktop accent color if image still null
        if img is None or img.isNull():
            img = self.create_fallback_acrylic_image()

        if img is not None and not img.isNull():
            self._cached_image = None
            self._cached_image = self._scale_to_screen(img)
            self._last_wallpaper_path = path
            self._last_mtime = mtime
            self._revision += 1
            self.wallpaperChanged.emit()

    def get_wallpaper_image(self):
        if self._cached_image is None or self._cached_image.isNull():
            self.refresh_wallpaper()
        return self._cached_image

    @Property(str, notify=wallpaperChanged)
    def wallpaperUrl(self):
        return f"image://wallpaper/current?rev={self._revision}"

    @Property(str, notify=wallpaperChanged)
    def accentColor(self):
        return self.get_accent_color()

    @Property(int, notify=wallpaperChanged)
    def screenWidth(self):
        scr = QGuiApplication.primaryScreen()
        return scr.geometry().width() if scr else user32.GetSystemMetrics(0)

    @Property(int, notify=wallpaperChanged)
    def screenHeight(self):
        scr = QGuiApplication.primaryScreen()
        return scr.geometry().height() if scr else user32.GetSystemMetrics(1)

    def _start_registry_watcher(self):
        def watcher():
            try:
                import win32api, win32event
                hkey = win32api.RegOpenKeyEx(winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop", 0, winreg.KEY_NOTIFY)
                event = win32event.CreateEvent(None, False, False, None)
                transcoded = os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Themes\TranscodedWallpaper")
                last_tc_mtime = os.path.getmtime(transcoded) if os.path.exists(transcoded) else 0

                while self._running:
                    win32api.RegNotifyChangeKeyValue(hkey, True, win32api.REG_NOTIFY_CHANGE_LAST_SET, event, True)
                    ret = win32event.WaitForSingleObject(event, 1000)
                    if ret == 0 and self._running:
                        time.sleep(0.3)  # allow disk write to complete
                        QMetaObject.invokeMethod(self, "refresh_wallpaper", Qt.QueuedConnection)
                    elif self._running:
                        # Check TranscodedWallpaper mtime on timeout
                        if os.path.exists(transcoded):
                            try:
                                cur_tc_mtime = os.path.getmtime(transcoded)
                                if cur_tc_mtime != last_tc_mtime:
                                    last_tc_mtime = cur_tc_mtime
                                    QMetaObject.invokeMethod(self, "refresh_wallpaper", Qt.QueuedConnection)
                            except Exception:
                                pass
                win32api.RegCloseKey(hkey)
            except Exception as e:
                print(f"[WallpaperBackend] Watcher fallback: {e}")
                while self._running:
                    time.sleep(2)
                    p = self.get_wallpaper_path()
                    if p != self._last_wallpaper_path:
                        QMetaObject.invokeMethod(self, "refresh_wallpaper", Qt.QueuedConnection)

        t = threading.Thread(target=watcher, daemon=True)
        t.start()
        self._watcher_thread = t

    def stop(self):
        self._running = False
