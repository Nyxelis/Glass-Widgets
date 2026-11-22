import sys
import os
import glob
from PySide6.QtCore import Qt, QUrl, QObject, Signal, Property, Slot, QPoint
from PySide6.QtGui import QGuiApplication, QIcon, QAction, QCursor
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PySide6.QtQuick import QQuickView, QQuickWindow, QSGRendererInterface
from PySide6.QtQml import QQmlApplicationEngine

# Adjust path so src/ is root
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from compat.plasmoid_item import register_plasmoid_types, PlasmoidAttached
from backends.config_manager import ConfigManager
from backends.wallpaper_backend import WallpaperBackend, WallpaperImageProvider
from backends.media_backend import MediaBackend
from backends.calendar_backend import CalendarBackend
from backends.autostart_backend import is_auto_start_enabled, enable_auto_start, disable_auto_start
from backends.win32_window import pin_widget_to_desktop, ensure_default_desktop
try:
    from paths import get_resource_path, get_writable_appdata_dir
except ImportError:
    from src.paths import get_resource_path, get_writable_appdata_dir

class WindowController(QObject):
    windowMoved = Signal()
    timezoneChanged = Signal()

    def __init__(self, view, pkg_name, config_mgr, manager_service, parent=None):
        super().__init__(parent)
        self.view = view
        self.pkg_name = pkg_name
        self.config_mgr = config_mgr
        self.mgr_service = manager_service
        self.view.xChanged.connect(self.windowMoved)
        self.view.yChanged.connect(self.windowMoved)

    @Property(int, notify=windowMoved)
    def windowX(self):
        return self.view.x()

    @Property(int, notify=windowMoved)
    def windowY(self):
        return self.view.y()

    @Property(int, notify=windowMoved)
    def screenWidth(self):
        scr = self.view.screen() or QGuiApplication.primaryScreen()
        return scr.geometry().width() if scr else 1920

    @Property(int, notify=windowMoved)
    def screenHeight(self):
        scr = self.view.screen() or QGuiApplication.primaryScreen()
        return scr.geometry().height() if scr else 1080

    @Property(int, notify=windowMoved)
    def screenRelativeX(self):
        scr = self.view.screen() or QGuiApplication.primaryScreen()
        offset = scr.geometry().x() if scr else 0
        return self.view.x() - offset

    @Property(int, notify=windowMoved)
    def screenRelativeY(self):
        scr = self.view.screen() or QGuiApplication.primaryScreen()
        offset = scr.geometry().y() if scr else 0
        return self.view.y() - offset

    def _snap(self, val, snap_val):
        if snap_val <= 0:
            return val
        return round(val / snap_val) * snap_val

    @Slot(int, int, int)
    def moveWindow(self, dx, dy, snap):
        new_x = self.view.x() + dx
        new_y = self.view.y() + dy
        if snap > 0:
            new_x = self._snap(new_x, snap)
            new_y = self._snap(new_y, snap)
        self.view.setPosition(new_x, new_y)
        self.windowMoved.emit()
        self.config_mgr.update_layout(self.pkg_name, x=new_x, y=new_y)

    @Slot()
    def startDrag(self):
        from PySide6.QtGui import QCursor
        self._drag_start_cursor = QCursor.pos()
        self._drag_start_pos = self.view.position()

    @Slot(int)
    def updateDrag(self, snap):
        from PySide6.QtGui import QCursor
        if not hasattr(self, "_drag_start_cursor"):
            return
        curr = QCursor.pos()
        dx = curr.x() - self._drag_start_cursor.x()
        dy = curr.y() - self._drag_start_cursor.y()
        new_x = self._drag_start_pos.x() + dx
        new_y = self._drag_start_pos.y() + dy
        if snap > 0:
            new_x = self._snap(new_x, snap)
            new_y = self._snap(new_y, snap)
        self.view.setPosition(new_x, new_y)
        self.windowMoved.emit()
        self.config_mgr.update_layout(self.pkg_name, x=new_x, y=new_y)

    @Slot(str)
    def startResize(self, edge):
        from PySide6.QtGui import QCursor
        self._resize_edge = edge
        self._resize_start_cursor = QCursor.pos()
        self._resize_start_geo = (self.view.x(), self.view.y(), self.view.width(), self.view.height())

    @Slot(int)
    def updateResize(self, snap):
        from PySide6.QtGui import QCursor
        if not hasattr(self, "_resize_start_cursor"):
            return
        curr = QCursor.pos()
        dx = curr.x() - self._resize_start_cursor.x()
        dy = curr.y() - self._resize_start_cursor.y()
        ox, oy, ow, oh = self._resize_start_geo

        new_x, new_y, new_w, new_h = ox, oy, ow, oh

        if "right" in self._resize_edge:
            new_w = max(160, ow + dx)
        elif "left" in self._resize_edge:
            new_w = max(160, ow - dx)
            new_x = ox + (ow - new_w)

        if "bottom" in self._resize_edge:
            new_h = max(160, oh + dy)
        elif "top" in self._resize_edge:
            new_h = max(160, oh - dy)
            new_y = oy + (oh - new_h)

        if snap > 0:
            new_w = self._snap(new_w, snap)
            new_h = self._snap(new_h, snap)
            new_x = self._snap(new_x, snap)
            new_y = self._snap(new_y, snap)

        self.view.setGeometry(new_x, new_y, new_w, new_h)
        self.windowMoved.emit()
        self.config_mgr.update_layout(self.pkg_name, x=new_x, y=new_y, width=new_w, height=new_h)
        self.mgr_service.refreshList()

    @Slot(int, int)
    def resizeRight(self, dx, snap):
        new_w = max(160, self.view.width() + dx)
        if snap > 0:
            new_w = self._snap(new_w, snap)
        self.view.setWidth(new_w)
        self.config_mgr.update_layout(self.pkg_name, width=new_w)
        self.mgr_service.refreshList()

    @Slot(int, int)
    def resizeLeft(self, dx, snap):
        new_w = max(160, self.view.width() - dx)
        new_x = self.view.x() + dx
        if snap > 0:
            new_w = self._snap(new_w, snap)
            new_x = self._snap(new_x, snap)
        self.view.setPosition(new_x, self.view.y())
        self.view.setWidth(new_w)
        self.windowMoved.emit()
        self.config_mgr.update_layout(self.pkg_name, x=new_x, width=new_w)
        self.mgr_service.refreshList()

    @Slot(int, int)
    def resizeBottom(self, dy, snap):
        new_h = max(160, self.view.height() + dy)
        if snap > 0:
            new_h = self._snap(new_h, snap)
        self.view.setHeight(new_h)
        self.config_mgr.update_layout(self.pkg_name, height=new_h)
        self.mgr_service.refreshList()

    @Slot(int, int)
    def resizeTop(self, dy, snap):
        new_h = max(160, self.view.height() - dy)
        new_y = self.view.y() + dy
        if snap > 0:
            new_h = self._snap(new_h, snap)
            new_y = self._snap(new_y, snap)
        self.view.setPosition(self.view.x(), new_y)
        self.view.setHeight(new_h)
        self.windowMoved.emit()
        self.config_mgr.update_layout(self.pkg_name, y=new_y, height=new_h)
        self.mgr_service.refreshList()

    @Slot(float)
    def changeScale(self, delta):
        layout = self.config_mgr.get_layout(self.pkg_name)
        new_scale = max(0.75, min(2.0, round((layout.get("scale", 1.0) + delta) * 100) / 100))
        self.mgr_service.setWidgetScale(self.pkg_name, new_scale)

    @Slot()
    def closeWidget(self):
        self.mgr_service.setWidgetActive(self.pkg_name, False)

    @Slot()
    def requestActivate(self):
        self.view.requestActivate()

    @Property(str, notify=timezoneChanged)
    def currentTimezone(self):
        cfg = self.config_mgr.get_widget_config(self.pkg_name)
        val = getattr(cfg, "clocks", "") or ""
        return str(val)

    @Property(bool, notify=timezoneChanged)
    def isClockWidget(self):
        return any(k in self.pkg_name.lower() for k in ("clock", "city"))

    @Property(bool, notify=windowMoved)
    def isWeatherWidget(self):
        return "weather" in self.pkg_name.lower()

    @Property(str, notify=timezoneChanged)
    def glassText(self):
        return self.mgr_service.glassText

    @Slot(str)
    def setGlassText(self, text):
        self.mgr_service.setGlassText(text)

    @Slot(str)
    def setTimezone(self, tz_str):
        self.config_mgr.set_widget_config(self.pkg_name, "clocks", tz_str)
        self.timezoneChanged.emit()

    @Slot(int, int)
    def setPresetSize(self, target_w, target_h):
        self.view.resize(target_w, target_h)
        self.windowMoved.emit()
        self.config_mgr.update_layout(self.pkg_name, width=target_w, height=target_h)
        self.mgr_service.refreshList()

    @Slot()
    def promptCustomTimezone(self):
        from PySide6.QtWidgets import QInputDialog
        cur = self.currentTimezone
        cur_id = cur.split("|")[0] if cur else ""
        text, ok = QInputDialog.getText(
            None,
            "Set Timezone",
            "Enter IANA Timezone ID (e.g. America/New_York, Asia/Tokyo, Europe/London):",
            text=cur_id
        )
        if ok and text.strip():
            clean_tz = text.strip()
            city = clean_tz.split("/")[-1].replace("_", " ").upper()[:4]
            self.setTimezone(f"{clean_tz}|{city}")

    @Slot(int, int)
    def showContextMenu(self, local_x, local_y):
        menu = QMenu()

        # Add timezone submenu for clock / city widgets
        if self.isClockWidget:
            tz_menu = menu.addMenu("Set Timezone")
            cur = self.currentTimezone.split("|")[0] if self.currentTimezone else ""
            presets = [
                ("Local System Time", ""),
                ("Tokyo (UTC+9)", "Asia/Tokyo|TYO"),
                ("London (UTC+0 / BST)", "Europe/London|LON"),
                ("New York (UTC-5 / EDT)", "America/New_York|NYC"),
                ("Paris / Berlin (UTC+1 / CEST)", "Europe/Paris|PAR"),
                ("Dubai (UTC+4)", "Asia/Dubai|DXB"),
                ("India / New Delhi (UTC+5:30)", "Asia/Kolkata|DEL"),
                ("Singapore / Hong Kong (UTC+8)", "Asia/Singapore|SIN"),
                ("Sydney (UTC+10 / AEST)", "Australia/Sydney|SYD"),
            ]
            for label, val in presets:
                act = tz_menu.addAction(label)
                act.setCheckable(True)
                act.setChecked(cur == val.split("|")[0])
                def make_tz_fn(v):
                    return lambda: self.setTimezone(v)
                act.triggered.connect(make_tz_fn(val))
            tz_menu.addSeparator()
            custom_act = tz_menu.addAction("Custom IANA Timezone…")
            custom_act.triggered.connect(self.promptCustomTimezone)
            menu.addSeparator()

        # Add weather submenu for weather widgets
        if self.isWeatherWidget and hasattr(self.mgr_service, "weather_backend"):
            wb = self.mgr_service.weather_backend
            w_menu = menu.addMenu(f"Weather Location ({wb.locationName})")
            presets = [
                ("New York", 40.7128, -74.0060),
                ("London", 51.5074, -0.1278),
                ("Tokyo", 35.6762, 139.6503),
                ("Paris", 48.8566, 2.3522),
                ("San Francisco", 37.7749, -122.4194),
                ("Sydney", -33.8688, 151.2093),
                ("Dubai", 25.2048, 55.2708),
                ("Delhi", 28.6139, 77.2090),
            ]
            for c_name, c_lat, c_lon in presets:
                act = w_menu.addAction(c_name)
                act.setCheckable(True)
                act.setChecked(wb.locationName.startswith(c_name))
                def make_w_fn(n, la, lo):
                    return lambda: wb.updateLocation(n, la, lo)
                act.triggered.connect(make_w_fn(c_name, c_lat, c_lon))

            w_menu.addSeparator()
            mgr_w_act = w_menu.addAction("Custom Lat / Lon in Manager…")
            mgr_w_act.triggered.connect(self.mgr_service.showManagerWindow)

            ref_act = menu.addAction("🔄 Refresh Weather")
            ref_act.triggered.connect(lambda: wb.refreshWeather(True))
            menu.addSeparator()

        # Add widget-specific actions from Plasmoid.contextualActions if present
        host_root = self.view.rootObject()
        if host_root:
            loader = host_root.findChild(QObject, "widgetLoader")
            if loader and loader.property("item"):
                item = loader.property("item")
                if hasattr(item, "Plasmoid") and item.Plasmoid:
                    actions = item.Plasmoid.contextualActions
                    if actions:
                        act_list = actions.toVariant() if hasattr(actions, "toVariant") else actions
                        if isinstance(act_list, (list, tuple)):
                            for act in act_list:
                                if hasattr(act, "isSeparator") and act.isSeparator:
                                    menu.addSeparator()
                                    continue
                                txt = getattr(act, "text", "")
                                if txt:
                                    qact = menu.addAction(txt)
                                    if hasattr(act, "enabled"):
                                        qact.setEnabled(act.enabled)
                                    if hasattr(act, "checkable") and act.checkable:
                                        qact.setCheckable(True)
                                        qact.setChecked(getattr(act, "checked", False))
                                    def make_trigger(target_act):
                                        return lambda: target_act.triggered.emit() if hasattr(target_act, "triggered") else None
                                    qact.triggered.connect(make_trigger(act))
                        menu.addSeparator()

        # Built-in widget context options
        edit_act = menu.addAction("Lock Layout" if self.mgr_service.globalEditMode else "Unlock / Edit Mode")
        edit_act.triggered.connect(self.mgr_service.toggleGlobalEditMode)

        # Scale submenu
        scale_menu = menu.addMenu("Widget Scale")
        for sc in [0.75, 1.0, 1.25, 1.5, 2.0]:
            s_act = scale_menu.addAction(f"{int(sc*100)}%")
            def make_sc(target_sc):
                return lambda: self.mgr_service.setWidgetScale(self.pkg_name, target_sc)
            s_act.triggered.connect(make_sc(sc))

        mgr_act = menu.addAction("GlassWidgets Manager…")
        mgr_act.triggered.connect(self.mgr_service.showManagerWindow)

        menu.addSeparator()
        hide_act = menu.addAction("Hide Widget")
        hide_act.triggered.connect(self.closeWidget)

        global_pos = self.view.mapToGlobal(QPoint(local_x, local_y))
        menu.exec(global_pos)


class WidgetManagerService(QObject):
    globalEditModeChanged = Signal()
    globalStyleModeChanged = Signal()
    globalGridSnapChanged = Signal()
    globalPinToBottomChanged = Signal()
    widgetListModelChanged = Signal()
    glassTextChanged = Signal(str)
    autoStartChanged = Signal(bool)

    def __init__(self, config_mgr, wallpaper_backend, media_backend, calendar_backend, weather_backend, app_dir):
        super().__init__()
        self.config_mgr = config_mgr
        self.wallpaper_backend = wallpaper_backend
        self.media_backend = media_backend
        self.calendar_backend = calendar_backend
        self.weather_backend = weather_backend
        self.app_dir = app_dir

        self._global_edit_mode = False
        self._global_style_mode = 0
        self._global_grid_snap = 16
        self._pin_to_bottom = True
        self._glass_text = self.config_mgr.saved_configs.get("test-glass", {}).get("glassText", "Liquid gLASS")
        self._active_views = {}
        self._widget_hwnds = set()
        self._controllers = {}
        self._manager_window = None

        # Friendly titles
        self.widget_titles = {
            "calendar": "Glass Calendar",
            "clock-analog": "Glass Clock I",
            "clock-analog-2": "Glass Clock II",
            "clock-analog-3": "Glass Clock III",
            "clock-digital": "Glass Clock Digital",
            "clock-glass-text": "Glass Text",
            "city-1": "Glass City I",
            "city-2": "Glass City II",
            "city-3": "Glass City III",
            "city-digital": "Glass City Digital",
            "music": "Glass Music",
            "timer": "Glass Timer",
            "weather": "Glass Weather",
            "weather-panel": "Glass Weather Panel",
            "test-glass": "Glass Test",
            "test-timer": "Glass Timer Test"
        }

    @Property(bool, notify=globalEditModeChanged)
    def globalEditMode(self):
        return self._global_edit_mode

    @Property(int, notify=globalStyleModeChanged)
    def globalStyleMode(self):
        return self._global_style_mode

    @Property(int, notify=globalGridSnapChanged)
    def globalGridSnap(self):
        return self._global_grid_snap

    @Property(bool, notify=globalPinToBottomChanged)
    def pinToBottom(self):
        return self._pin_to_bottom

    @property
    def widget_hwnds(self):
        return self._widget_hwnds

    @Slot(bool)
    def setPinToBottom(self, val):
        self._pin_to_bottom = val
        self.globalPinToBottomChanged.emit()
        for pkg, view in self._active_views.items():
            flags = Qt.Window | Qt.FramelessWindowHint | (Qt.WindowStaysOnBottomHint if val else Qt.WindowType(0))
            view.setFlags(flags)
            hwnd = int(view.winId())
            pin_widget_to_desktop(hwnd, pin_to_bottom=val)

    @Property(str, notify=glassTextChanged)
    def glassText(self):
        return self._glass_text

    @Slot(str)
    def setGlassText(self, text):
        if self._glass_text != text:
            self._glass_text = text
            self.config_mgr.set_widget_config("test-glass", "glassText", text)
            self.glassTextChanged.emit(text)

    @Property(bool, notify=autoStartChanged)
    def isAutoStartEnabled(self):
        return is_auto_start_enabled()

    @Slot(bool)
    def setAutoStart(self, enable):
        if enable:
            enable_auto_start(self.app_dir)
        else:
            disable_auto_start()
        self.autoStartChanged.emit(self.isAutoStartEnabled)

    @Property("QVariantList", notify=widgetListModelChanged)
    def widgetListModel(self):
        items = []
        for pkg, title in sorted(self.widget_titles.items()):
            layout = self.config_mgr.get_layout(pkg)
            items.append({
                "packageId": pkg,
                "name": title,
                "active": bool(layout.get("visible", False)),
                "width": float(layout.get("width", 300)),
                "height": float(layout.get("height", 300)),
                "scale": float(layout.get("scale", 1.0))
            })
        return items

    def refreshList(self):
        self.widgetListModelChanged.emit()

    @Slot()
    def toggleGlobalEditMode(self):
        self._global_edit_mode = not self._global_edit_mode
        self.globalEditModeChanged.emit()
        for pkg, view in self._active_views.items():
            root = view.rootObject()
            if root:
                root.setProperty("editMode", self._global_edit_mode)

    @Slot()
    def toggleAllWidgets(self):
        self._all_widgets_hidden = not getattr(self, "_all_widgets_hidden", False)
        for view in self._active_views.values():
            if self._all_widgets_hidden:
                view.hide()
            else:
                view.show()

    @Slot()
    def clampWidgetsToScreen(self):
        scr = QGuiApplication.primaryScreen()
        if not scr:
            return
        geo = scr.availableGeometry()
        for pkg, view in self._active_views.items():
            vx, vy, vw, vh = view.x(), view.y(), view.width(), view.height()
            nx = max(geo.left() + 20, min(vx, geo.right() - vw - 20))
            ny = max(geo.top() + 20, min(vy, geo.bottom() - vh - 20))
            if nx != vx or ny != vy:
                view.setPosition(nx, ny)
                self.config_mgr.update_layout(pkg, x=nx, y=ny)

    @Slot(int)
    def setGlobalStyleMode(self, mode):
        self._global_style_mode = mode
        self.globalStyleModeChanged.emit()
        # Propagate to all widgets
        for pkg in self.widget_titles.keys():
            cfg = self.config_mgr.get_widget_config(pkg)
            if hasattr(cfg, "styleMode"):
                # mode 0: Glass Dark (styleMode=0, appearance=0)
                # mode 1: Glass Light (styleMode=0, appearance=1)
                # mode 2: Solid Dark (styleMode=1, appearance=0)
                # mode 3: Solid Light (styleMode=1, appearance=1)
                sm = 0 if mode in (0, 1) else 1
                app = 0 if mode in (0, 2) else 1
                cfg.styleMode = sm
                cfg.appearance = app
        self.config_mgr.save_configs()

    @Slot(int)
    def setGlobalGridSnap(self, snap):
        self._global_grid_snap = snap
        self.globalGridSnapChanged.emit()
        for pkg, view in self._active_views.items():
            root = view.rootObject()
            if root:
                root.setProperty("gridSnap", snap)

    @Slot(str)
    def promptWidgetTimezone(self, pkg_name):
        from PySide6.QtWidgets import QInputDialog
        cfg = self.config_mgr.get_widget_config(pkg_name)
        cur = str(getattr(cfg, "clocks", "") or "")
        cur_id = cur.split("|")[0] if cur else ""
        text, ok = QInputDialog.getText(
            None,
            f"Set Timezone for {pkg_name}",
            "Enter IANA Timezone ID (e.g. America/New_York, Asia/Tokyo, Europe/London, Asia/Kolkata):",
            text=cur_id
        )
        if ok:
            clean_tz = text.strip()
            city = clean_tz.split("/")[-1].replace("_", " ").upper()[:4] if clean_tz else ""
            val = f"{clean_tz}|{city}" if clean_tz else ""
            self.config_mgr.set_widget_config(pkg_name, "clocks", val)
            self.refreshList()

    @Slot(str, bool)
    def setWidgetActive(self, pkg_name, active):
        if not pkg_name or pkg_name == "undefined":
            return
        layout = self.config_mgr.get_layout(pkg_name)
        layout["visible"] = active
        self.config_mgr.update_layout(pkg_name, visible=active)
        self.refreshList()

        if active:
            if pkg_name not in self._active_views:
                if pkg_name == "music":
                    self.media_backend.start_media_listener()
                if "weather" in pkg_name.lower():
                    self.weather_backend.resume_polling()
                self.launchWidget(pkg_name)
        else:
            if pkg_name in self._active_views:
                if pkg_name == "music":
                    self.media_backend.stop_media_listener()
                view = self._active_views.pop(pkg_name)
                try:
                    self._widget_hwnds.discard(int(view.winId()))
                except Exception:
                    pass
                view.close()
                view.deleteLater()
                if "weather" in pkg_name.lower():
                    if not any("weather" in p.lower() for p in self._active_views):
                        self.weather_backend.pause_polling()

    @Slot(str, float)
    def setWidgetScale(self, pkg_name, scale_val):
        if not pkg_name or pkg_name == "undefined":
            return
        layout = self.config_mgr.get_layout(pkg_name)
        old_scale = float(layout.get("scale", 1.0))
        layout["scale"] = scale_val
        self.config_mgr.update_layout(pkg_name, scale=scale_val)
        self.refreshList()
        if pkg_name in self._active_views:
            view = self._active_views[pkg_name]
            root = view.rootObject()
            if root:
                root.setProperty("widgetScale", scale_val)
            if old_scale > 0 and abs(scale_val - old_scale) > 0.01:
                ratio = scale_val / old_scale
                nw = max(160, int(round(view.width() * ratio)))
                nh = max(160, int(round(view.height() * ratio)))
                view.resize(nw, nh)
                self.config_mgr.update_layout(pkg_name, width=nw, height=nh)

    @Slot(str, int, int)
    def resizeWidget(self, pkg_name, w, h):
        if not pkg_name or pkg_name == "undefined":
            return
        layout = self.config_mgr.get_layout(pkg_name)
        layout["width"] = w
        layout["height"] = h
        self.config_mgr.update_layout(pkg_name, width=w, height=h)
        self.refreshList()
        if pkg_name in self._active_views:
            view = self._active_views[pkg_name]
            view.resize(w, h)

    @Slot()
    def resetAllPositions(self):
        screen_w = self.wallpaper_backend.screenWidth
        screen_h = self.wallpaper_backend.screenHeight
        start_x = 80
        start_y = 80
        spacing = 340

        x = start_x
        y = start_y
        for pkg, view in self._active_views.items():
            view.setPosition(x, y)
            self.config_mgr.update_layout(pkg, x=x, y=y)
            x += spacing
            if x + 300 > screen_w:
                x = start_x
                y += spacing
                if y + 300 > screen_h:
                    y = start_y
        self.refreshList()

    @Slot()
    def showManagerWindow(self):
        if self._manager_window is None:
            engine = QQmlApplicationEngine()
            engine.addImportPath(get_resource_path("src/compat"))
            engine.addImportPath(get_resource_path("src/ui"))
            ctx = engine.rootContext()
            ctx.setContextProperty("widgetManagerService", self)
            ctx.setContextProperty("wallpaperBackend", self.wallpaper_backend)
            ctx.setContextProperty("calendarBackendService", self.calendar_backend)
            ctx.setContextProperty("weatherBackend", self.weather_backend)

            def _on_warnings(warnings):
                for w in warnings:
                    print(f"[QML Warning] {w.toString()}", flush=True)
            engine.warnings.connect(_on_warnings)

            mgr_path = get_resource_path("src/ui/ManagerWindow.qml")
            engine.load(QUrl.fromLocalFile(mgr_path))
            objs = engine.rootObjects()
            if not objs:
                print(f"[ERROR] Failed to load ManagerWindow.qml from {mgr_path}", flush=True)
            else:
                self._manager_window = objs[0]
                self._manager_engine = engine
                print(f"[Manager] Window initialized: {self._manager_window}", flush=True)

        if self._manager_window:
            try:
                self._manager_window.resize(940, 840)
            except Exception:
                pass
            self._manager_window.show()
            self._manager_window.raise_()
            self._manager_window.requestActivate()

    def launchWidget(self, pkg_name):
        layout = self.config_mgr.get_layout(pkg_name)
        cfg = self.config_mgr.get_widget_config(pkg_name)

        view = QQuickView()
        view.setColor(Qt.transparent)
        # Use Qt.Tool so each widget view remains completely independent without window grouping
        flags = Qt.Tool | Qt.FramelessWindowHint | (Qt.WindowStaysOnBottomHint if self._pin_to_bottom else Qt.WindowType(0))
        view.setFlags(flags)
        view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
        view.setMinimumWidth(160)
        view.setMinimumHeight(160)

        view.engine().addImportPath(get_resource_path("src/compat"))
        view.engine().addImportPath(get_resource_path("src/ui"))
        view.engine().addImageProvider("wallpaper", WallpaperImageProvider(self.wallpaper_backend))

        ctrl = WindowController(view, pkg_name, self.config_mgr, self)
        self._controllers[pkg_name] = ctrl

        attached = PlasmoidAttached()
        attached.set_config(cfg)
        attached.set_w(layout.get("width", 300))
        attached.set_h(layout.get("height", 300))

        view.widthChanged.connect(lambda: attached.set_w(view.width()))
        view.heightChanged.connect(lambda: attached.set_h(view.height()))

        from compat.plasmoid_item import Plasmoid
        Plasmoid._window_map[view] = attached
        Plasmoid._current_attached = attached

        ctx = view.rootContext()
        ctx.setContextProperty("widgetManagerService", self)
        ctx.setContextProperty("Plasmoid", attached)
        ctx.setContextProperty("plasmoid", attached)
        ctx.setContextProperty("wallpaperBackend", self.wallpaper_backend)
        ctx.setContextProperty("globalMediaBackend", self.media_backend)
        ctx.setContextProperty("backend", self.media_backend.active_player)
        ctx.setContextProperty("calendarBackendService", self.calendar_backend)
        ctx.setContextProperty("weatherBackend", self.weather_backend)
        ctx.setContextProperty("windowController", ctrl)

        host_path = get_resource_path("src/ui/WidgetHost.qml")
        view.setSource(QUrl.fromLocalFile(host_path))

        root = view.rootObject()
        if root:
            root.setProperty("widgetName", self.widget_titles.get(pkg_name, pkg_name))
            root.setProperty("widgetPackage", pkg_name)
            target_qml = get_resource_path(f"upstream_kde_widgets/packages/{pkg_name}/contents/ui/main.qml")
            root.setProperty("widgetQmlSource", QUrl.fromLocalFile(target_qml))
            root.setProperty("widgetScale", layout.get("scale", 1.0))
            root.setProperty("gridSnap", self._global_grid_snap)
            root.setProperty("editMode", self._global_edit_mode)

            wp = root.findChild(QObject, "wallpaperItem")
            if wp:
                attached.containment.wallpaperGraphicsObject = wp

        w = int(layout.get("width", 300))
        h = int(layout.get("height", 300))
        x = int(layout.get("x", 100))
        y = int(layout.get("y", 100))
        scr = QGuiApplication.primaryScreen()
        if scr:
            geo = scr.availableGeometry()
            x = max(geo.left() + 20, min(x, geo.right() - w - 20))
            y = max(geo.top() + 20, min(y, geo.bottom() - h - 20))
        view.setGeometry(x, y, w, h)
        view.show()

        # Desktop pinning & HWND tracking
        hwnd = int(view.winId())
        self._widget_hwnds.add(hwnd)
        pin_widget_to_desktop(hwnd, pin_to_bottom=self._pin_to_bottom)

        self._active_views[pkg_name] = view


def main():
    try:
        sys.stdout.reconfigure(line_buffering=True)
        sys.stderr.reconfigure(line_buffering=True)
    except Exception:
        pass

    try:
        import ctypes
        myappid = "GlassWidgets.DesktopWidgets.1.0.0"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass

    ensure_default_desktop()

    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    QQuickWindow.setGraphicsApi(QSGRendererInterface.GraphicsApi.Direct3D11)

    app = QApplication(sys.argv)

    # Single Instance enforcement via QLocalServer / QLocalSocket
    from PySide6.QtNetwork import QLocalServer, QLocalSocket
    single_instance_name = "GlassWidgets_SingleInstance"
    if "--test" not in sys.argv:
        test_socket = QLocalSocket()
        test_socket.connectToServer(single_instance_name)
        if test_socket.waitForConnected(500):
            test_socket.write(b"SHOW_MANAGER\n")
            test_socket.waitForBytesWritten(500)
            test_socket.disconnectFromServer()
            sys.exit(0)

    QLocalServer.removeServer(single_instance_name)
    local_server = QLocalServer(app)
    local_server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
    if not local_server.listen(single_instance_name):
        print(f"[SingleInstance] Warning: Failed to listen on {single_instance_name}: {local_server.errorString()}", flush=True)

    from PySide6.QtQuickControls2 import QQuickStyle
    QQuickStyle.setStyle("Basic")
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("GlassWidgets")
    app.setApplicationDisplayName("Glass Widgets")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("GlassWidgets")
    app.setOrganizationDomain("glasswidgets.local")

    icon_path = get_resource_path("assets/app_icon.ico")
    app_icon = None
    if os.path.exists(icon_path):
        app_icon = QIcon(icon_path)
        app.setWindowIcon(app_icon)

    register_plasmoid_types()

    from PySide6.QtCore import qInstallMessageHandler, QtMsgType
    _SPAM_PATTERNS = (
        "depends on non-bindable properties",
        "The current style does not support customization",
        "Singleton registered by registerSingletonInstance",
        "Cannot set a duration of < 0",
        "Cannot read property",
        "Unable to assign [undefined]",
        "is not a properly capitalized signal handler name",
        "overrides a member of the base object",
        "Cannot open: file:///",
    )

    def _qt_message_handler(mode, context, message):
        if "[QML]" in message or "[MediaBackend]" in message or "[Manager]" in message or "[Desktop]" in message or "[TEST]" in message or "[WeatherBackend]" in message:
            print(message, flush=True)
            return

        if mode == QtMsgType.QtFatalMsg:
            print(f"[FATAL] {message}", file=sys.stderr, flush=True)
            return

        for spam in _SPAM_PATTERNS:
            if spam in message:
                return

        if mode in (QtMsgType.QtWarningMsg, QtMsgType.QtCriticalMsg):
            print(message, flush=True)

    qInstallMessageHandler(_qt_message_handler)

    app_dir = get_resource_path("src")
    packages_dir = get_resource_path("upstream_kde_widgets/packages")

    config_mgr = ConfigManager(packages_dir)
    wallpaper_backend = WallpaperBackend()
    from backends.wallpaper_backend import WallpaperNativeEventFilter
    wp_filter = WallpaperNativeEventFilter(wallpaper_backend)
    app.installNativeEventFilter(wp_filter)
    media_backend = MediaBackend()
    calendar_backend = CalendarBackend()
    from backends.weather_backend import WeatherBackend
    weather_backend = WeatherBackend(config_mgr)

    from PySide6.QtQml import qmlRegisterSingletonType
    from backends.media_backend import ActivePlayer
    qmlRegisterSingletonType(ActivePlayer, "org.kde.plasma.private.mpris", 2, 0, "GlobalActivePlayer", lambda eng: media_backend.active_player)
    qmlRegisterSingletonType(MediaBackend, "org.kde.plasma.private.mpris", 2, 0, "GlobalMediaBackend", lambda eng: media_backend)

    service = WidgetManagerService(config_mgr, wallpaper_backend, media_backend, calendar_backend, weather_backend, app_dir)

    def on_single_instance_connection():
        client = local_server.nextPendingConnection()
        if client:
            client.waitForReadyRead(500)
            msg = client.readAll().data().decode("utf-8", errors="ignore").strip()
            if msg == "SHOW_MANAGER":
                service.showManagerWindow()
            client.disconnectFromServer()
            client.deleteLater()
    local_server.newConnection.connect(on_single_instance_connection)

    primary_screen = QGuiApplication.primaryScreen()
    if primary_screen:
        primary_screen.geometryChanged.connect(service.clampWidgetsToScreen)

    from backends.win32_window import WidgetNativeEventFilter
    widget_filter = WidgetNativeEventFilter(service)
    app.installNativeEventFilter(widget_filter)

    # Initial default widgets: on first launch, only launch Clock and Calendar
    default_active = ["clock-analog", "calendar"]
    has_saved = len(config_mgr.saved_layouts) > 0

    if not has_saved:
        for i, pkg in enumerate(default_active):
            config_mgr.get_layout(pkg, default_x=100 + i*360, default_y=120, default_visible=True)
        # Ensure all other available widgets default to visible: False
        for pkg in service.widget_titles.keys():
            if pkg not in default_active:
                config_mgr.get_layout(pkg, default_visible=False)
        config_mgr.save_layouts()

    has_weather = False
    has_music = False
    for pkg in config_mgr.saved_layouts.keys():
        if config_mgr.get_layout(pkg).get("visible", False):
            if "weather" in pkg.lower():
                has_weather = True
            if pkg == "music":
                has_music = True
            service.launchWidget(pkg)

    if has_weather:
        weather_backend.resume_polling()
    if has_music:
        media_backend.start_media_listener()

    # System Tray Icon
    tray = QSystemTrayIcon(app)
    if app_icon and not app_icon.isNull():
        tray.setIcon(app_icon)
    else:
        # Generate simple fallback icon
        from PySide6.QtGui import QPixmap, QPainter, QColor
        pm = QPixmap(32, 32)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QColor("#0a84ff"))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(2, 2, 28, 28, 8, 8)
        p.setPen(QColor("#ffffff"))
        f = p.font()
        f.setPixelSize(18)
        f.setBold(True)
        p.setFont(f)
        p.drawText(pm.rect(), Qt.AlignCenter, "GW")
        p.end()
        tray.setIcon(QIcon(pm))

    tray.setToolTip("GlassWidgets")

    menu = QMenu()
    show_act = menu.addAction("Show Manager")
    show_act.triggered.connect(service.showManagerWindow)

    toggle_act = menu.addAction("Toggle Widgets")
    def on_toggle_widgets():
        service.toggleAllWidgets()
        toggle_act.setText("Show Widgets" if getattr(service, "_all_widgets_hidden", False) else "Hide Widgets")
    toggle_act.triggered.connect(on_toggle_widgets)

    menu.addSeparator()

    edit_act = menu.addAction("Unlock / Edit Mode")
    def on_edit_toggle():
        service.toggleGlobalEditMode()
        edit_act.setText("Lock Layout" if service.globalEditMode else "Unlock / Edit Mode")
    edit_act.triggered.connect(on_edit_toggle)

    surface_act = menu.addAction("Pin Behind Windows (Desktop Surface)")
    surface_act.setCheckable(True)
    surface_act.setChecked(service.pinToBottom)
    surface_act.triggered.connect(lambda chk: service.setPinToBottom(chk))

    menu.addSeparator()

    style_menu = menu.addMenu("Style Mode")
    for idx, s_name in enumerate(["Glass Dark", "Glass Light", "Solid Dark", "Solid Light"]):
        sa = style_menu.addAction(s_name)
        def make_st(i): return lambda: service.setGlobalStyleMode(i)
        sa.triggered.connect(make_st(idx))

    snap_menu = menu.addMenu("Grid Snapping")
    for s_val, s_name in [(0, "Off"), (16, "16 px"), (24, "24 px")]:
        sna = snap_menu.addAction(s_name)
        def make_snp(sv): return lambda: service.setGlobalGridSnap(sv)
        sna.triggered.connect(make_snp(s_val))

    reset_act = menu.addAction("Reset Widget Positions")
    reset_act.triggered.connect(service.resetAllPositions)

    menu.addSeparator()
    quit_act = menu.addAction("Quit")
    def on_quit():
        try:
            local_server.close()
            QLocalServer.removeServer(single_instance_name)
        except Exception:
            pass
        wallpaper_backend.stop()
        media_backend.stop_media_listener()
        weather_backend.pause_polling()
        config_mgr.save_configs()
        config_mgr.save_layouts()
        app.quit()
        os._exit(0)
    quit_act.triggered.connect(on_quit)

    tray.setContextMenu(menu)

    def on_tray_activated(reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            service.showManagerWindow()
    tray.activated.connect(on_tray_activated)

    tray.show()
    tray.showMessage(
        "GlassWidgets",
        "GlassWidgets is active on your desktop.\nClick the tray icon to open the Manager.",
        QSystemTrayIcon.MessageIcon.Information,
        5000
    )

    # Show Manager window on startup so user sees controls and status
    if "--minimized" not in sys.argv:
        service.showManagerWindow()

    if "--test" in sys.argv:
        from PySide6.QtCore import QTimer
        def run_test_exit():
            print("[TEST] All widgets, backends, and shaders loaded successfully!")
            on_quit()
        QTimer.singleShot(1500, run_test_exit)

    return app.exec()

if __name__ == "__main__":
    sys.exit(main())
