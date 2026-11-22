import sys
import winsound
from enum import IntEnum
from PySide6.QtCore import QObject, Signal, Property, Slot, Qt, QTimer, QDateTime, QTimeZone, QByteArray, QEnum
from PySide6.QtGui import QColor, QFont
from PySide6.QtQuick import QQuickItem
from PySide6.QtQml import QmlAttached, qmlRegisterType, qmlRegisterUncreatableType, qmlRegisterSingletonType

# --- MPRIS Playback Status Singleton ---
class MprisPlaybackStatus(QObject):
    @Property(int, constant=True)
    def Stopped(self): return 0
    @Property(int, constant=True)
    def Playing(self): return 1
    @Property(int, constant=True)
    def Paused(self): return 2

_mpris_status_singleton = MprisPlaybackStatus()

# --- Notification ---
class Notification(QObject):
    titleChanged = Signal()
    textChanged = Signal()
    urgencyChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._component_name = ""
        self._event_id = ""
        self._title = ""
        self._text = ""
        self._urgency = 1

    LowUrgency = Property(int, lambda s: 0)
    NormalUrgency = Property(int, lambda s: 1)
    CriticalUrgency = Property(int, lambda s: 2)

    def get_comp(self): return self._component_name
    def set_comp(self, v): self._component_name = v
    componentName = Property(str, get_comp, set_comp)

    def get_eid(self): return self._event_id
    def set_eid(self, v): self._event_id = v
    eventId = Property(str, get_eid, set_eid)

    def get_title(self): return self._title
    def set_title(self, v):
        if self._title != v:
            self._title = v
            self.titleChanged.emit()
    title = Property(str, get_title, set_title, notify=titleChanged)

    def get_text(self): return self._text
    def set_text(self, v):
        if self._text != v:
            self._text = v
            self.textChanged.emit()
    text = Property(str, get_text, set_text, notify=textChanged)

    def get_urg(self): return self._urgency
    def set_urg(self, v):
        if self._urgency != v:
            self._urgency = v
            self.urgencyChanged.emit()
    urgency = Property(int, get_urg, set_urg, notify=urgencyChanged)

    @Slot()
    def sendEvent(self):
        print(f"[Timer Notification] {self._title}: {self._text}")
        try:
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        except Exception:
            pass


# --- Plasma Clock ---
class PlasmaClock(QObject):
    timeChanged = Signal()
    timeZoneChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tz_str = ""
        self._tz = QTimeZone.systemTimeZone()
        self._track_seconds = False
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)
        self._timer.start(1000)

    def get_tz(self): return self._tz_str
    def set_tz(self, v):
        if self._tz_str != v:
            self._tz_str = v
            if v:
                self._tz = QTimeZone(QByteArray(v.encode("utf-8")))
                if not self._tz.isValid():
                    self._tz = QTimeZone.systemTimeZone()
            else:
                self._tz = QTimeZone.systemTimeZone()
            self.timeZoneChanged.emit()
            self.timeChanged.emit()
    timeZone = Property(str, get_tz, set_tz, notify=timeZoneChanged)

    def get_ts(self): return self._track_seconds
    def set_ts(self, v):
        if self._track_seconds != v:
            self._track_seconds = v
    trackSeconds = Property(bool, get_ts, set_ts)

    @Property(QDateTime, notify=timeChanged)
    def dateTime(self):
        if not self._tz_str:
            return QDateTime.currentDateTime()
        now_utc = QDateTime.currentDateTimeUtc()
        target_dt = now_utc.toTimeZone(self._tz)
        return QDateTime(target_dt.date(), target_dt.time())

    @Property(str, notify=timeChanged)
    def timeZoneOffset(self):
        now = QDateTime.currentDateTime()
        offset = self._tz.offsetFromUtc(now)
        sign = "+" if offset >= 0 else "-"
        hours = abs(offset) // 3600
        mins = (abs(offset) % 3600) // 60
        return f"UTC{sign}{hours:02d}:{mins:02d}"

    def _on_tick(self):
        self.timeChanged.emit()


# --- Plasma Core Types ---
class PlasmaCoreTypes(QObject):
    @Property(int, constant=True)
    def NoBackground(self): return 0
    @Property(int, constant=True)
    def StandardBackground(self): return 1
    @Property(int, constant=True)
    def TranslucentBackground(self): return 2
    @Property(int, constant=True)
    def DefaultBackground(self): return 3
    @Property(int, constant=True)
    def Planar(self): return 0
    @Property(int, constant=True)
    def Horizontal(self): return 1
    @Property(int, constant=True)
    def Vertical(self): return 2
    @Property(int, constant=True)
    def MediaControllable(self): return 4
    @Property(int, constant=True)
    def Application(self): return 5
    @Property(int, constant=True)
    def Floating(self): return 0
    @Property(int, constant=True)
    def Desktop(self): return 1
    @Property(int, constant=True)
    def TopEdge(self): return 2
    @Property(int, constant=True)
    def BottomEdge(self): return 3
    @Property(int, constant=True)
    def LeftEdge(self): return 4
    @Property(int, constant=True)
    def RightEdge(self): return 5
    @Property(int, constant=True)
    def Mutable(self): return 1
    @Property(int, constant=True)
    def UserImmutable(self): return 2
    @Property(int, constant=True)
    def SystemImmutable(self): return 3
    @Property(int, constant=True)
    def PassiveStatus(self): return 1
    @Property(int, constant=True)
    def ActiveStatus(self): return 2
    @Property(int, constant=True)
    def NeedsAttentionStatus(self): return 3
    @Property(int, constant=True)
    def RequiresAttentionStatus(self): return 3
    @Property(int, constant=True)
    def AcceptingInputStatus(self): return 4
    @Property(int, constant=True)
    def HiddenStatus(self): return 0

_types_singleton = PlasmaCoreTypes()

# --- Kirigami Theme ---
class KirigamiThemeAttached(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._colorSet = 0
        self._inherit = True
    colorSet = Property(int, lambda s: s._colorSet, lambda s, v: setattr(s, '_colorSet', v))
    inherit = Property(bool, lambda s: s._inherit, lambda s, v: setattr(s, '_inherit', v))
    textColor = Property(QColor, lambda s: QColor('#ffffff'), constant=True)
    highlightColor = Property(QColor, lambda s: QColor('#0a84ff'), constant=True)
    backgroundColor = Property(QColor, lambda s: QColor('#1e1e1e'), constant=True)
    hoverColor = Property(QColor, lambda s: QColor('#2a2a2a'), constant=True)
    focusColor = Property(QColor, lambda s: QColor('#0a84ff'), constant=True)
    disabledTextColor = Property(QColor, lambda s: QColor('#888888'), constant=True)
    defaultFont = Property(QFont, lambda s: QFont(), constant=True)

    Window = Property(int, lambda s: 0, constant=True)
    Button = Property(int, lambda s: 1, constant=True)
    View = Property(int, lambda s: 2, constant=True)
    Complementary = Property(int, lambda s: 3, constant=True)
    Header = Property(int, lambda s: 4, constant=True)
    Tooltip = Property(int, lambda s: 5, constant=True)

@QmlAttached(KirigamiThemeAttached)
class KirigamiTheme(QObject):
    class ColorSet(IntEnum):
        Window = 0
        Button = 1
        View = 2
        Complementary = 3
        Header = 4
        Tooltip = 5
    QEnum(ColorSet)

    Window = Property(int, lambda s: 0, constant=True)
    Button = Property(int, lambda s: 1, constant=True)
    View = Property(int, lambda s: 2, constant=True)
    Complementary = Property(int, lambda s: 3, constant=True)
    Header = Property(int, lambda s: 4, constant=True)
    Tooltip = Property(int, lambda s: 5, constant=True)

    @staticmethod
    def qmlAttachedProperties(*args):
        parent = args[0] if len(args) == 1 else args[1]
        return KirigamiThemeAttached(parent)

# --- Containment ---
class Containment(QObject):
    wallpaperChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._wallpaperGraphicsObject = None

    def get_wallpaper(self):
        return self._wallpaperGraphicsObject

    def set_wallpaper(self, obj):
        if self._wallpaperGraphicsObject != obj:
            self._wallpaperGraphicsObject = obj
            self.wallpaperChanged.emit()

    wallpaperGraphicsObject = Property(QObject, get_wallpaper, set_wallpaper, notify=wallpaperChanged)

    @Slot()
    def notifyWallpaperChanged(self):
        self.wallpaperChanged.emit()

# --- Plasmoid Attached ---
class PlasmoidAttached(QObject):
    backgroundHintsChanged = Signal()
    contextualActionsChanged = Signal()
    configurationChanged = Signal()
    containmentChanged = Signal()
    formFactorChanged = Signal()
    sizeChanged = Signal()
    expandedChanged = Signal()
    locationChanged = Signal()
    immutabilityChanged = Signal()
    statusChanged = Signal()
    busyChanged = Signal()
    titleChanged = Signal()
    iconChanged = Signal()
    rotationChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._bg_hints = 0
        self._actions = []
        self._containment = Containment(self)
        self._configuration = None
        self._form_factor = 0 # 0 = Planar, 1 = Horizontal, 2 = Vertical
        self._implicit_width = 300.0
        self._implicit_height = 300.0
        self._width = 300.0
        self._height = 300.0
        self._expanded = False
        self._location = 0 # 0 = Floating
        self._immutability = 1 # 1 = Mutable
        self._status = 1 # 1 = PassiveStatus
        self._busy = False
        self._title = ""
        self._icon = ""
        self._rotation = 0.0

    def get_bg(self): return self._bg_hints
    def set_bg(self, v):
        if self._bg_hints != v:
            self._bg_hints = v
            self.backgroundHintsChanged.emit()
    backgroundHints = Property(int, get_bg, set_bg, notify=backgroundHintsChanged)

    def get_actions(self): return self._actions
    def set_actions(self, v):
        self._actions = v
        self.contextualActionsChanged.emit()
    contextualActions = Property("QVariant", get_actions, set_actions, notify=contextualActionsChanged)

    def get_containment(self): return self._containment
    containment = Property(QObject, get_containment, notify=containmentChanged)

    def get_config(self): return self._configuration
    def set_config(self, v):
        if self._configuration != v:
            self._configuration = v
            self.configurationChanged.emit()
    configuration = Property(QObject, get_config, set_config, notify=configurationChanged)

    def get_ff(self): return self._form_factor
    def set_ff(self, v):
        if self._form_factor != v:
            self._form_factor = v
            self.formFactorChanged.emit()
    formFactor = Property(int, get_ff, set_ff, notify=formFactorChanged)

    def get_loc(self): return self._location
    def set_loc(self, v):
        if self._location != v:
            self._location = v
            self.locationChanged.emit()
    location = Property(int, get_loc, set_loc, notify=locationChanged)

    def get_immut(self): return self._immutability
    def set_immut(self, v):
        if self._immutability != v:
            self._immutability = v
            self.immutabilityChanged.emit()
    immutability = Property(int, get_immut, set_immut, notify=immutabilityChanged)

    def get_status(self): return self._status
    def set_status(self, v):
        if self._status != v:
            self._status = v
            self.statusChanged.emit()
    status = Property(int, get_status, set_status, notify=statusChanged)

    @Property(int, constant=True)
    def switchWidth(self): return 0

    @Property(int, constant=True)
    def switchHeight(self): return 0

    def get_busy(self): return self._busy
    def set_busy(self, v):
        if self._busy != v:
            self._busy = v
            self.busyChanged.emit()
    busy = Property(bool, get_busy, set_busy, notify=busyChanged)

    def get_title(self): return self._title
    def set_title(self, v):
        if self._title != v:
            self._title = v
            self.titleChanged.emit()
    title = Property(str, get_title, set_title, notify=titleChanged)

    def get_icon(self): return self._icon
    def set_icon(self, v):
        if self._icon != v:
            self._icon = v
            self.iconChanged.emit()
    icon = Property(str, get_icon, set_icon, notify=iconChanged)

    @Property(str, constant=True)
    def pluginName(self): return ""

    @Property(QObject, constant=True)
    def nativeInterface(self): return None

    @Property(str, constant=True)
    def toolTipMainText(self): return ""

    @Property(str, constant=True)
    def toolTipSubText(self): return ""

    def get_iw(self): return self._implicit_width
    def set_iw(self, v):
        if self._implicit_width != v:
            self._implicit_width = v
            self.sizeChanged.emit()
    implicitWidth = Property(float, get_iw, set_iw, notify=sizeChanged)

    def get_ih(self): return self._implicit_height
    def set_ih(self, v):
        if self._implicit_height != v:
            self._implicit_height = v
            self.sizeChanged.emit()
    implicitHeight = Property(float, get_ih, set_ih, notify=sizeChanged)

    def get_w(self): return self._width
    def set_w(self, v):
        if self._width != v:
            self._width = v
            self.sizeChanged.emit()
    width = Property(float, get_w, set_w, notify=sizeChanged)

    def get_h(self): return self._height
    def set_h(self, v):
        if self._height != v:
            self._height = v
            self.sizeChanged.emit()
    height = Property(float, get_h, set_h, notify=sizeChanged)

    def get_expanded(self): return self._expanded
    def set_expanded(self, v):
        if self._expanded != v:
            self._expanded = v
            self.expandedChanged.emit()
    expanded = Property(bool, get_expanded, set_expanded, notify=expandedChanged)

    def get_rot(self): return self._rotation
    def set_rot(self, v):
        try:
            val = float(v)
            if self._rotation != val:
                self._rotation = val
                self.rotationChanged.emit()
        except Exception:
            pass
    rotation = Property(float, get_rot, set_rot, notify=rotationChanged)

    @Slot(str, result=QObject)
    def action(self, name):
        return None

    @Slot(str, str, str, str)
    def setAction(self, name, text, icon, shortcut):
        pass


@QmlAttached(PlasmoidAttached)
class Plasmoid(QObject):
    _window_map = {}
    _current_attached = None

    @staticmethod
    def qmlAttachedProperties(*args):
        parent = args[0] if len(args) == 1 else args[1]
        try:
            if hasattr(parent, "window") and parent.window():
                win = parent.window()
                if win in Plasmoid._window_map:
                    return Plasmoid._window_map[win]
        except Exception:
            pass
        if Plasmoid._current_attached:
            return Plasmoid._current_attached
        inst = PlasmoidAttached(parent)
        return inst


class PlasmoidItem(QQuickItem):
    preferredChanged = Signal()
    expandedChanged = Signal()
    implicitWidthChanged = Signal()
    implicitHeightChanged = Signal()
    fullRepresentationChanged = Signal()
    compactRepresentationChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._full = None
        self._compact = None
        self._preferred = None
        self._hide_on_deactivate = False
        self._expanded = False
        self.widthChanged.connect(self._sync_preferred)
        self.heightChanged.connect(self._sync_preferred)

    def _sync_preferred(self):
        if self._preferred:
            w = self.width()
            h = self.height()
            if w > 0 and h > 0:
                self._preferred.setWidth(w)
                self._preferred.setHeight(h)

    def get_full(self): return self._full
    def set_full(self, item):
        if self._full != item:
            self._full = item
            if not self._preferred and item:
                self.set_preferred(item)
            elif self._preferred == item:
                self._sync_preferred()
            self.fullRepresentationChanged.emit()
    fullRepresentation = Property(QQuickItem, get_full, set_full, notify=fullRepresentationChanged)

    def get_compact(self): return self._compact
    def set_compact(self, item):
        if self._compact != item:
            self._compact = item
            self.compactRepresentationChanged.emit()
    compactRepresentation = Property(QQuickItem, get_compact, set_compact, notify=compactRepresentationChanged)

    def get_preferred(self): return self._preferred
    def set_preferred(self, item):
        if self._preferred == item:
            return
        if self._preferred:
            self._preferred.setVisible(False)
        self._preferred = item
        if self._preferred:
            self._preferred.setParentItem(self)
            w = self.width() if self.width() > 0 else (self.parentItem().width() if self.parentItem() else 300)
            h = self.height() if self.height() > 0 else (self.parentItem().height() if self.parentItem() else 300)
            self._preferred.setWidth(w)
            self._preferred.setHeight(h)
            self._preferred.setVisible(True)
        self.preferredChanged.emit()
        self.implicitWidthChanged.emit()
        self.implicitHeightChanged.emit()
    preferredRepresentation = Property(QQuickItem, get_preferred, set_preferred, notify=preferredChanged)

    @Property(float, notify=implicitWidthChanged)
    def implicitWidth(self):
        if self._preferred and hasattr(self._preferred, "implicitWidth") and self._preferred.implicitWidth() > 0:
            return self._preferred.implicitWidth()
        return 300.0

    @Property(float, notify=implicitHeightChanged)
    def implicitHeight(self):
        if self._preferred and hasattr(self._preferred, "implicitHeight") and self._preferred.implicitHeight() > 0:
            return self._preferred.implicitHeight()
        return 300.0

    def get_hide(self): return self._hide_on_deactivate
    def set_hide(self, v): self._hide_on_deactivate = v
    hideOnWindowDeactivate = Property(bool, get_hide, set_hide)

    @Property(QObject, constant=True)
    def plasmoid(self):
        return Plasmoid.qmlAttachedProperties(self)

    @Property(QObject, constant=True)
    def Plasmoid(self):
        return Plasmoid.qmlAttachedProperties(self)

    def get_exp(self): return self._expanded
    def set_exp(self, v):
        if self._expanded != v:
            self._expanded = v
            self.expandedChanged.emit()
    expanded = Property(bool, get_exp, set_exp, notify=expandedChanged)

    def geometryChange(self, newGeo, oldGeo):
        super().geometryChange(newGeo, oldGeo)
        if self._preferred:
            self._preferred.setWidth(newGeo.width())
            self._preferred.setHeight(newGeo.height())

    @Slot(str, result=str)
    @Slot(str, 'QVariant', result=str)
    @Slot(str, 'QVariant', 'QVariant', result=str)
    @Slot(str, 'QVariant', 'QVariant', 'QVariant', result=str)
    def i18n(self, text, a1=None, a2=None, a3=None):
        if text is None: return ""
        text = str(text)
        if a1 is not None: text = text.replace("%1", str(a1))
        if a2 is not None: text = text.replace("%2", str(a2))
        if a3 is not None: text = text.replace("%3", str(a3))
        return text

    @Slot(str, str, result=str)
    @Slot(str, str, 'QVariant', result=str)
    @Slot(str, str, 'QVariant', 'QVariant', result=str)
    def i18nc(self, ctx, text, a1=None, a2=None):
        return self.i18n(text, a1, a2)

    @Slot(str, str, int, result=str)
    @Slot(str, str, int, 'QVariant', result=str)
    def i18np(self, s, p, n, a1=None):
        txt = s if n == 1 else p
        return self.i18n(txt, n if a1 is None else a1)


def register_plasmoid_types():
    qmlRegisterType(PlasmoidItem, "org.kde.plasma.plasmoid", 2, 0, "PlasmoidItem")
    qmlRegisterUncreatableType(Plasmoid, "org.kde.plasma.plasmoid", 2, 0, "Plasmoid", "Attached type only")
    qmlRegisterSingletonType(PlasmaCoreTypes, "org.kde.plasma.core", 2, 0, "Types", lambda eng: _types_singleton)
    qmlRegisterSingletonType(MprisPlaybackStatus, "org.kde.plasma.private.mpris", 2, 0, "PlaybackStatus", lambda eng: _mpris_status_singleton)
    qmlRegisterUncreatableType(KirigamiTheme, "org.kde.kirigami", 2, 0, "Theme", "Attached only")
    qmlRegisterType(Notification, "org.kde.notification", 1, 0, "Notification")
    qmlRegisterType(Notification, "org.kde.notification", 2, 0, "Notification")
    qmlRegisterType(PlasmaClock, "org.kde.plasma.clock", 2, 0, "Clock")
