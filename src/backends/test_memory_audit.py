import base64
import gc
import os
import sys
import tempfile
import weakref
import psutil
from PySide6.QtCore import QBuffer, QIODevice, QTimer, Qt
from PySide6.QtGui import QColor, QGuiApplication, QImage
from PySide6.QtQml import qmlRegisterSingletonType
from PySide6.QtQuick import QQuickWindow, QSGRendererInterface
from PySide6.QtWidgets import QApplication

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from compat.plasmoid_item import register_plasmoid_types
from backends.config_manager import ConfigManager
from backends.wallpaper_backend import WallpaperBackend
from backends.media_backend import MediaBackend, ActivePlayer
from backends.calendar_backend import CalendarBackend
from backends.weather_backend import WeatherBackend
from main import WidgetManagerService


def make_png_data_uri(seed: int) -> str:
    img = QImage(512, 512, QImage.Format.Format_RGBA8888)
    img.fill(QColor((seed * 47) % 255, (seed * 97) % 255, (seed * 151) % 255))
    buf = QBuffer()
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    img.save(buf, "PNG")
    b64 = base64.b64encode(bytes(buf.data())).decode("ascii")
    return f"data:image/png;base64,{b64}"


def rss_mb(proc: psutil.Process) -> float:
    return proc.memory_info().rss / 1048576.0


def run_audit():
    gc.set_threshold(700, 10, 10)
    proc = psutil.Process()

    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    QQuickWindow.setGraphicsApi(QSGRendererInterface.GraphicsApi.Direct3D11)
    app = QApplication(sys.argv)
    register_plasmoid_types()

    repo_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    cfg = ConfigManager(os.path.join(repo_dir, "upstream_kde_widgets", "packages"))
    wp = WallpaperBackend()
    mb = MediaBackend()
    cb = CalendarBackend()
    wb = WeatherBackend(cfg)

    qmlRegisterSingletonType(ActivePlayer, "org.kde.plasma.private.mpris", 2, 0, "GlobalActivePlayer", lambda eng: mb.active_player)
    qmlRegisterSingletonType(MediaBackend, "org.kde.plasma.private.mpris", 2, 0, "GlobalMediaBackend", lambda eng: mb)

    svc = WidgetManagerService(cfg, wp, mb, cb, wb, os.path.join(repo_dir, "src"))

    before_mb = rss_mb(proc)
    print(f"[AUDIT] Before music widget launch: {before_mb:.1f} MB RSS", flush=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        missing_bridge = os.path.join(tmpdir, "missing.json")
        # Create music instance and attach a mock-pointed BitChordBridge
        inst_id = cfg.create_instance("music", x=100, y=100)
        svc.launchWidget(inst_id)
        bridge = svc.bitchord_bridge
        assert bridge is not None
        bridge._bridge_path = missing_bridge
        bridge_ref = weakref.ref(bridge)

        # Wait briefly, then simulate 10 song changes + album art updates
        after_launch_mb = 0.0
        after_10_songs_mb = 0.0

        def play_10_songs():
            nonlocal after_launch_mb, after_10_songs_mb
            app.processEvents()
            after_launch_mb = rss_mb(proc)
            print(f"[AUDIT] After music widget loaded: {after_launch_mb:.1f} MB RSS", flush=True)

            bridge._set_connection_state(True, "Connected")
            for i in range(1, 11):
                art = make_png_data_uri(i)
                bridge._handle_payload({
                    "status": "playing",
                    "song": {"title": f"Track {i}", "artist": f"Artist {i}", "album": f"Album {i}"},
                    "progressMs": i * 5000,
                    "durationMs": 180000,
                    "albumArtBase64": art,
                })
                for _ in range(5):
                    app.processEvents()

            after_10_songs_mb = rss_mb(proc)
            print(f"[AUDIT] After 10 songs + 512x512 album arts: {after_10_songs_mb:.1f} MB RSS", flush=True)
            QTimer.singleShot(250, close_and_gc)

        def close_and_gc():
            nonlocal bridge
            del bridge
            svc.removeWidget(inst_id)
            for _ in range(10):
                app.processEvents()
            if svc._shared_engine is not None:
                svc._shared_engine.clearComponentCache()
                svc._shared_engine.collectGarbage()
            gc.collect()
            QTimer.singleShot(300, report_final)

        def report_final():
            for _ in range(5):
                app.processEvents()
            if svc._shared_engine is not None:
                svc._shared_engine.collectGarbage()
            gc.collect()
            after_close_mb = rss_mb(proc)
            print(f"[AUDIT] After widget closed + GC: {after_close_mb:.1f} MB RSS", flush=True)
            print(f"[AUDIT] BitChordBridge collected? {bridge_ref() is None}", flush=True)
            assert bridge_ref() is None, "BitChordBridge leaked after music widget removal!"
            assert after_10_songs_mb < 350.0, f"Memory too high during 10 songs: {after_10_songs_mb:.1f} MB"
            print("[PASS] Memory & BitChordBridge GC audit passed.")
            app.quit()

        QTimer.singleShot(400, play_10_songs)
        app.exec()


if __name__ == "__main__":
    run_audit()
