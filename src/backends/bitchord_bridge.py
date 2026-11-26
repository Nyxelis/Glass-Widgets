import asyncio
import json
import os
import threading
import websockets
from PySide6.QtCore import QObject, Property, Signal, Slot


def get_bitchord_bridge_path() -> str:
    """Return the path to BitChord's auto-generated bridge.json discovery file."""
    local_app_data = os.getenv("LOCALAPPDATA") or os.path.expandvars("%LOCALAPPDATA%")
    return os.path.join(local_app_data, "BitChord", "bridge.json")


def read_bridge_config(bridge_path: str | None = None) -> tuple[int, str] | None:
    """Parse (port, token) from bridge.json, or return None if missing/invalid."""
    path = bridge_path or get_bitchord_bridge_path()
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return None
        token = str(data.get("token", "") or "").strip()
        if not token:
            return None
        port = int(data.get("port", 4242) or 4242)
        return port, token
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return None


def _normalize_album_art(raw_art: str) -> str:
    """Normalize incoming base64 artwork to a data URI without touching disk."""
    art = (raw_art or "").strip()
    if not art:
        return ""
    if art.startswith("data:"):
        return art
    return f"data:image/png;base64,{art}"


class BitChordBridge(QObject):
    """Asynchronous WebSocket bridge connecting GlassWidgets to the BitChord player."""

    stateChanged = Signal(str, str, str, str)       # status, title, artist, album
    progressChanged = Signal(int, int)              # progressMs, durationMs
    albumArtChanged = Signal(str)                   # data URI base64 string
    connectionStatusChanged = Signal(str)           # "Waiting for BitChord..." | "Connected"
    isConnectedChanged = Signal(bool)

    WAIT_INTERVAL_SEC = 2.0

    def __init__(self, bridge_path: str | None = None, debug: bool | None = None, parent=None):
        super().__init__(parent)
        self._bridge_path = bridge_path
        if debug is None:
            self._debug = os.getenv("GLASSWIDGETS_DEBUG", "").strip() in ("1", "true", "yes")
        else:
            self._debug = bool(debug)

        self._running = False
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._ws = None
        self._lock = threading.Lock()

        self._is_connected = False
        self._connection_status = ""
        self._status = "stopped"
        self._title = ""
        self._artist = ""
        self._album = ""
        self._progress_ms = 0
        self._duration_ms = 0
        self._album_art = ""

    def _log(self, msg: str):
        if self._debug:
            print(f"[BitChordBridge] {msg}", flush=True)

    @staticmethod
    def _vprint(msg: str):
        print(f"[BitChordBridge] {msg}", flush=True)

    # ── QML Properties ────────────────────────────────────────────────────

    @Property(bool, notify=isConnectedChanged)
    def isConnected(self) -> bool:
        return self._is_connected

    @Property(str, notify=connectionStatusChanged)
    def connectionStatus(self) -> str:
        return self._connection_status or "Waiting for BitChord..."

    @Property(str, notify=stateChanged)
    def status(self) -> str:
        return self._status

    @Property(str, notify=stateChanged)
    def title(self) -> str:
        return self._title

    @Property(str, notify=stateChanged)
    def artist(self) -> str:
        return self._artist

    @Property(str, notify=stateChanged)
    def album(self) -> str:
        return self._album

    @Property(int, notify=progressChanged)
    def progressMs(self) -> int:
        return self._progress_ms

    @Property(int, notify=progressChanged)
    def durationMs(self) -> int:
        return self._duration_ms

    @Property(str, notify=albumArtChanged)
    def albumArt(self) -> str:
        return self._album_art

    # ── Lifecycle ─────────────────────────────────────────────────────────

    @Slot()
    def start(self):
        with self._lock:
            if self._running and self._thread and self._thread.is_alive():
                return
            self._running = True
            self._thread = threading.Thread(target=self._run_thread, name="BitChordBridgeLoop", daemon=True)
            self._thread.start()

    @Slot()
    def stop(self):
        with self._lock:
            self._running = False
            loop = self._loop
            ws = self._ws
        if loop and loop.is_running():
            async def _shutdown():
                if ws is not None:
                    try:
                        await ws.close(code=1000, reason="Client shutdown")
                    except Exception:
                        pass
                for task in asyncio.all_tasks(loop):
                    if task is not asyncio.current_task():
                        task.cancel()
            try:
                asyncio.run_coroutine_threadsafe(_shutdown(), loop)
            except Exception:
                pass

    def _set_connection_state(self, connected: bool, status_text: str):
        if self._is_connected != connected:
            self._is_connected = connected
            self.isConnectedChanged.emit(connected)
        if self._connection_status != status_text:
            self._connection_status = status_text
            self.connectionStatusChanged.emit(status_text)

    def _reset_media_state(self):
        if self._status != "stopped" or self._title or self._artist or self._album:
            self._status = "stopped"
            self._title = ""
            self._artist = ""
            self._album = ""
            self.stateChanged.emit("stopped", "", "", "")
        if self._progress_ms != 0 or self._duration_ms != 0:
            self._progress_ms = 0
            self._duration_ms = 0
            self.progressChanged.emit(0, 0)
        if self._album_art != "":
            self._album_art = ""
            self.albumArtChanged.emit("")

    def _run_thread(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._wait_and_connect_loop())
        except Exception as e:
            self._log(f"Event loop terminated: {e}")
        finally:
            try:
                pending = asyncio.all_tasks(self._loop)
                for task in pending:
                    task.cancel()
                if pending:
                    self._loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                self._loop.close()
            except Exception:
                pass
            self._loop = None
            self._ws = None

    async def _wait_and_connect_loop(self):
        while self._running:
            self._vprint("Attempting to read bridge.json...")
            cfg = read_bridge_config(self._bridge_path)
            if cfg is None:
                self._vprint("bridge.json not found or invalid, retrying in 2s...")
                self._set_connection_state(False, "Waiting for BitChord...")
                self._reset_media_state()
                try:
                    await asyncio.sleep(self.WAIT_INTERVAL_SEC)
                except asyncio.CancelledError:
                    break
                continue

            port, token = cfg
            self._vprint(f"Found token: {token}")
            uri = f"ws://127.0.0.1:{port}/player?token={token}"
            self._vprint(f"Connecting to ws://127.0.0.1:{port}...")
            try:
                async with websockets.connect(
                    uri,
                    max_size=16 * 1024 * 1024,
                    open_timeout=3.0,
                    ping_interval=20.0,
                    ping_timeout=20.0,
                ) as ws:
                    self._ws = ws
                    self._set_connection_state(True, "Connected")
                    self._vprint("SUCCESS: Connected to BitChord!")
                    await self._listen_messages(ws)
            except asyncio.CancelledError:
                break
            except (websockets.exceptions.InvalidStatus, websockets.exceptions.InvalidStatusCode) as e:
                status_code = getattr(getattr(e, "response", None), "status_code", None) or getattr(e, "status_code", None)
                if status_code == 401:
                    self._vprint("ERROR: 401 Unauthorized - Token is stale, retrying...")
                else:
                    self._vprint(f"ERROR: WebSocket handshake rejected (HTTP {status_code}), retrying...")
            except ConnectionRefusedError:
                self._vprint(f"ERROR: ConnectionRefused on port {port} - BitChord is offline, retrying...")
            except TimeoutError:
                self._vprint(f"ERROR: Connection timed out on port {port}, retrying...")
            except Exception as e:
                self._vprint(f"ERROR: Connection failed ({type(e).__name__}: {e}), retrying...")
            finally:
                self._ws = None
                self._set_connection_state(False, "Waiting for BitChord...")
                self._reset_media_state()

            if self._running:
                try:
                    await asyncio.sleep(self.WAIT_INTERVAL_SEC)
                except asyncio.CancelledError:
                    break

    async def _listen_messages(self, ws):
        async for raw_msg in ws:
            if not self._running:
                break
            if not isinstance(raw_msg, str):
                continue
            try:
                payload = json.loads(raw_msg)
            except json.JSONDecodeError:
                self._log("Received malformed JSON payload")
                continue
            if isinstance(payload, dict):
                self._handle_payload(payload)

    def _handle_payload(self, payload: dict):
        status = str(payload.get("status", self._status) or "stopped")
        song = payload.get("song")
        if isinstance(song, dict):
            title = str(song.get("title", "") or "")
            artist = str(song.get("artist", "") or "")
            album = str(song.get("album", "") or "")
        else:
            title = self._title
            artist = self._artist
            album = self._album

        if (
            status != self._status
            or title != self._title
            or artist != self._artist
            or album != self._album
        ):
            self._status = status
            self._title = title
            self._artist = artist
            self._album = album
            self.stateChanged.emit(status, title, artist, album)

        if "progressMs" in payload or "durationMs" in payload:
            try:
                progress_ms = max(0, int(payload.get("progressMs", self._progress_ms) or 0))
            except (TypeError, ValueError):
                progress_ms = self._progress_ms
            try:
                duration_ms = max(0, int(payload.get("durationMs", self._duration_ms) or 0))
            except (TypeError, ValueError):
                duration_ms = self._duration_ms

            self._progress_ms = progress_ms
            self._duration_ms = duration_ms
            self.progressChanged.emit(progress_ms, duration_ms)

        if "albumArtBase64" in payload:
            art_uri = _normalize_album_art(str(payload.get("albumArtBase64", "") or ""))
            if art_uri != self._album_art:
                self._album_art = art_uri
                self.albumArtChanged.emit(art_uri)

    # ── Outgoing Commands (QML -> BitChord) ───────────────────────────────

    def _send_json(self, data: dict):
        loop = self._loop
        ws = self._ws
        if not self._is_connected or loop is None or not loop.is_running() or ws is None:
            return
        msg = json.dumps(data)

        async def _send():
            try:
                await ws.send(msg)
            except Exception as e:
                self._log(f"Send failed: {e}")

        try:
            asyncio.run_coroutine_threadsafe(_send(), loop)
        except Exception as e:
            self._log(f"Schedule send failed: {e}")

    @Slot()
    def togglePlay(self):
        self._send_json({"command": "toggle_play"})

    @Slot()
    def nextTrack(self):
        self._send_json({"command": "next"})

    @Slot()
    def previousTrack(self):
        self._send_json({"command": "previous"})

    @Slot(int)
    def seek(self, position_ms: int):
        self._send_json({"command": "seek", "positionMs": max(0, int(position_ms))})

    @Slot(float)
    def seekSeconds(self, seconds: float):
        self.seek(int(round(max(0.0, float(seconds)) * 1000.0)))
