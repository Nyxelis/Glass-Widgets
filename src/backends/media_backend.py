import asyncio
import os
import hashlib
import threading
import time
from PySide6.QtCore import QObject, Signal, Property, Slot, QUrl, QRunnable, QThreadPool
try:
    from paths import get_writable_appdata_dir
except ImportError:
    from src.paths import get_writable_appdata_dir
import winrt.windows.media.control as wmc
import winrt.windows.storage.streams as wss

def get_art_cache_dir():
    path = os.path.join(get_writable_appdata_dir(), "art_cache")
    os.makedirs(path, exist_ok=True)
    return path

class SeekWorker(QRunnable):
    def __init__(self, ticks, seconds, backend):
        super().__init__()
        self.ticks = ticks
        self.seconds = seconds
        self.backend = backend

    def run(self):
        async def _do_seek():
            try:
                mgr = await wmc.GlobalSystemMediaTransportControlsSessionManager.request_async()
                session = mgr.get_current_session()
                if not session:
                    sessions = mgr.get_sessions()
                    if sessions and len(sessions) > 0:
                        session = sessions[0]
                if session:
                    success = await session.try_change_playback_position_async(self.ticks)
                    print(f"[PYTHON] Seek API result: {success}", flush=True)
                    if not success:
                        self.backend._seek_failed_signal.emit()
                    else:
                        self.backend._seek_success_signal.emit(self.seconds)
                else:
                    print("[PYTHON] Seek API result: False (no active session)", flush=True)
                    self.backend._seek_failed_signal.emit()
            except Exception as e:
                print(f"[PYTHON] Seek API result: False (exception: {e})", flush=True)
                self.backend._seek_failed_signal.emit()

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(_do_seek())
            loop.close()
        except Exception as e:
            print(f"[PYTHON] SeekWorker loop error: {e}", flush=True)

class ActivePlayer(QObject):
    positionChanged = Signal()
    playbackStatusChanged = Signal()
    trackChanged = Signal()
    artUrlChanged = Signal()
    playerInfoChanged = Signal()
    seekOccurred = Signal(int)
    lyricsOffsetMsChanged = Signal()
    lyricsLoaded = Signal(str, str, str, bool)

    def __init__(self, backend, parent=None):
        super().__init__(parent)
        self._backend = backend
        self._identity = "Media"
        self._track = ""
        self._artist = ""
        self._album = ""
        self._art_url = ""
        self._playback_status = 0 # 0=Stopped, 1=Playing, 2=Paused
        self._position = 0.0 # microseconds
        self._length = 0.0 # microseconds
        self._can_play = False
        self._can_pause = False
        self._can_next = False
        self._can_prev = False
        self._can_seek = False
        self._track_id = ""
        self._lyrics_offset_ms = 0

    def get_identity(self): return self._identity
    identity = Property(str, get_identity, notify=playerInfoChanged)

    def get_track(self): return self._track
    track = Property(str, get_track, notify=trackChanged)

    def get_artist(self): return self._artist
    artist = Property(str, get_artist, notify=trackChanged)

    def get_album(self): return self._album
    album = Property(str, get_album, notify=trackChanged)

    def get_art_url(self): return self._art_url
    artUrl = Property(str, get_art_url, notify=artUrlChanged)

    def get_playback_status(self): return self._playback_status
    playbackStatus = Property(int, get_playback_status, notify=playbackStatusChanged)

    def get_position(self): return self._position
    position = Property(float, get_position, notify=positionChanged)

    def get_length(self): return self._length
    length = Property(float, get_length, notify=playerInfoChanged)

    def get_can_play(self): return self._can_play
    canPlay = Property(bool, get_can_play, notify=playerInfoChanged)

    def get_can_pause(self): return self._can_pause
    canPause = Property(bool, get_can_pause, notify=playerInfoChanged)

    def get_can_next(self): return self._can_next
    canGoNext = Property(bool, get_can_next, notify=playerInfoChanged)

    def get_can_prev(self): return self._can_prev
    canGoPrevious = Property(bool, get_can_prev, notify=playerInfoChanged)

    def get_can_seek(self): return self._can_seek
    canSeek = Property(bool, get_can_seek, notify=playerInfoChanged)

    def get_track_id(self): return self._track_id
    trackId = Property(str, get_track_id, notify=trackChanged)

    def get_lyrics_offset(self):
        return self._lyrics_offset_ms

    def set_lyrics_offset(self, val):
        try:
            v = int(val)
            if self._lyrics_offset_ms != v:
                self._lyrics_offset_ms = v
                self.lyricsOffsetMsChanged.emit()
        except Exception:
            pass

    lyricsOffsetMs = Property(int, get_lyrics_offset, set_lyrics_offset, notify=lyricsOffsetMsChanged)

    @Slot(int)
    def setLyricsOffset(self, val):
        self.set_lyrics_offset(val)

    @Slot(int)
    def setLyricsOffsetMs(self, val):
        self.set_lyrics_offset(val)

    @Slot(int)
    def adjustLyricsOffset(self, delta):
        self.set_lyrics_offset(self._lyrics_offset_ms + int(delta))

    @Slot(int)
    def adjustLyricsOffsetMs(self, delta):
        self.set_lyrics_offset(self._lyrics_offset_ms + int(delta))

    @Slot(str, str, str, float)
    def fetchLyrics(self, artist, track, album="", duration_sec=0.0):
        if hasattr(self._backend, "lyrics_backend"):
            self._backend.lyrics_backend.fetchLyrics(artist, track, album, duration_sec)

    @Slot()
    def start_media_listener(self):
        self._backend.start_media_listener()

    @Slot()
    def stop_media_listener(self):
        self._backend.stop_media_listener()

    @Slot()
    def PlayPause(self):
        self._backend.cmd_play_pause()

    @Slot()
    def Play(self):
        self._backend.cmd_play()

    @Slot()
    def Pause(self):
        self._backend.cmd_pause()

    @Slot()
    def Next(self):
        self._backend.cmd_next()

    @Slot()
    def Previous(self):
        self._backend.cmd_previous()

    @Slot(float)
    def Seek(self, offset_us):
        new_pos = max(0.0, self._position + offset_us)
        self.setPlaybackPositionUs(new_pos)

    @Slot(str, float)
    def SetPosition(self, track_id, pos_us):
        self.setPlaybackPositionUs(pos_us)

    @Slot(float)
    def seekRequested(self, seconds):
        if not self._can_seek:
            print("[PYTHON] Seek ignored: canSeek is False for this player", flush=True)
            return
        seconds = max(0.0, float(seconds))
        print(f"[PYTHON] Received seek request for: {seconds} seconds", flush=True)
        ticks = int(seconds * 10_000_000)
        print(f"[PYTHON] Converted to ticks: {ticks}", flush=True)
        self._position = seconds * 1_000_000.0
        self._backend._seek_lock_until = time.time() + 3.5
        self._backend._requested_seek_us = self._position
        self._backend._last_known_pos_us = self._position
        self.positionChanged.emit()
        pos_ms = int(round(seconds * 1000.0))
        print(f"[PYTHON] Broadcasting tentative seek to all widgets: {pos_ms}")
        self.seekOccurred.emit(pos_ms)
        self._backend.seekOccurred.emit(pos_ms)
        worker = SeekWorker(ticks, seconds, self._backend)
        QThreadPool.globalInstance().start(worker)
        self._backend.trigger_burst_poll(seconds)

    @Slot(float)
    def setPlaybackPosition(self, seconds):
        self.seekRequested(seconds)

    @Slot(int)
    def setPlaybackPositionInt(self, seconds):
        self.seekRequested(float(seconds))

    @Slot(float)
    def setPlaybackPositionUs(self, pos_us):
        self.seekRequested(float(pos_us) / 1_000_000.0)

    @Slot(float)
    def setPosition(self, pos_us):
        self.setPlaybackPositionUs(pos_us)


class MediaBackend(QObject):
    trackChanged = Signal()
    positionChanged = Signal()
    playerInfoChanged = Signal()
    seekOccurred = Signal(int)
    lyricsLoaded = Signal(str, str, str, bool)
    _seek_success_signal = Signal(float)
    _seek_failed_signal = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.active_player = ActivePlayer(self, self)
        self.active_player.trackChanged.connect(self.trackChanged)
        self.active_player.positionChanged.connect(self.positionChanged)
        self.active_player.playerInfoChanged.connect(self.playerInfoChanged)
        self.active_player.seekOccurred.connect(self.seekOccurred)
        try:
            from backends.lyrics_backend import LyricsBackend
        except ImportError:
            from src.backends.lyrics_backend import LyricsBackend
        self.lyrics_backend = LyricsBackend(self)
        self.lyrics_backend.lyricsLoaded.connect(self._on_lyrics_loaded)
        self._seek_success_signal.connect(self._apply_seek_success)
        self._seek_failed_signal.connect(self._on_seek_failed)

        self.art_dir = get_art_cache_dir()
        self._loop = None
        self._mgr = None
        self._current_session = None
        self._running = False
        self._thread = None
        self._lock = threading.Lock()
        self._session_tokens = [] # list of (session, ev_name, token)
        self._mgr_tokens = []     # list of (mgr, ev_name, token)
        self._last_art_hash = ""
        self._seek_lock_until = 0.0
        self._requested_seek_us = 0.0
        self._burst_poll_until = 0.0
        self._burst_target_seconds = 0.0
        self._last_known_pos_us = 0.0
        self._last_reported_pos_sec = 0.0
        self._last_reported_time = 0.0
        self._track_poll_until = 0.0
        self._track_poll_task = None

    def trigger_track_change_poll(self):
        self._track_poll_until = time.time() + 5.0
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._start_track_change_poll(), self._loop)

    async def _start_track_change_poll(self):
        if self._track_poll_task and not self._track_poll_task.done():
            self._track_poll_task.cancel()
        self._track_poll_task = asyncio.create_task(self._run_track_change_poll())

    async def _run_track_change_poll(self):
        print("[MediaBackend] Track changed: Starting aggressive timeline polling (every 250ms for 5s)...", flush=True)
        for _ in range(20):
            if not self._running:
                break
            await asyncio.sleep(0.25)
            try:
                cur = self._get_or_find_session()
                if not cur:
                    continue
                tinfo = cur.get_timeline_properties()
                raw_pos = tinfo.position.total_seconds() if (tinfo and tinfo.position) else 0.0
                raw_len = tinfo.end_time.total_seconds() if (tinfo and tinfo.end_time) else 0.0
                print(f"[DEBUG] SMTC Timeline - Pos: {raw_pos:.2f}s, Length: {raw_len:.2f}s", flush=True)

                if raw_len > 0:
                    len_us = raw_len * 1_000_000.0
                    pos_us = raw_pos * 1_000_000.0
                    p = self.active_player
                    p._length = len_us
                    p._position = pos_us
                    self._last_reported_pos_sec = raw_pos
                    self._last_reported_time = time.time()
                    self._last_known_pos_us = pos_us
                    p.positionChanged.emit()
                    p.playerInfoChanged.emit()
                    self.positionChanged.emit()
                    self.playerInfoChanged.emit()
                    print(f"[MediaBackend] Track change timeline acquired: Length={raw_len:.2f}s, Pos={raw_pos:.2f}s", flush=True)
                    await self._update_session_info(cur, force_emit=True)
                    break
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[MediaBackend] Track change poll error: {e}", flush=True)

    def trigger_burst_poll(self, target_seconds: float):
        self._burst_poll_until = time.time() + 3.5
        self._burst_target_seconds = float(target_seconds)
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._run_burst_poll(target_seconds), self._loop)

    async def _run_burst_poll(self, target_seconds: float):
        target_us = target_seconds * 1_000_000.0
        print(f"[MediaBackend] Starting burst poll for target {target_seconds}s (polling every 250ms for 3.5s)...", flush=True)
        for _ in range(14):
            if not self._running:
                break
            await asyncio.sleep(0.25)
            try:
                cur = self._get_or_find_session()
                if cur:
                    await self._update_session_info(cur, force_emit=True)
                    cur_pos = self.active_player._position
                    if abs(cur_pos - target_us) < 2_000_000:
                        pos_ms = int(round(cur_pos / 1000.0))
                        print(f"[MediaBackend] Burst poll confirmed target position: {pos_ms}ms", flush=True)
                        print(f"[PYTHON] Broadcasting seek to all widgets: {pos_ms}")
                        self.seekOccurred.emit(pos_ms)
                        self.active_player.seekOccurred.emit(pos_ms)
                        break
            except Exception as e:
                print(f"[MediaBackend] Burst poll iteration error: {e}", flush=True)

    def _on_lyrics_loaded(self, key, synced, plain, success):
        self.lyricsLoaded.emit(key, synced, plain, success)
        self.active_player.lyricsLoaded.emit(key, synced, plain, success)

    def _apply_seek_success(self, seconds):
        print(f"[MediaBackend] Seek succeeded to {seconds}s", flush=True)
        pos_us = float(seconds) * 1_000_000.0
        self._seek_lock_until = time.time() + 3.5
        self._requested_seek_us = pos_us
        self._last_known_pos_us = pos_us
        self.active_player._position = pos_us
        self.active_player.positionChanged.emit()
        pos_ms = int(round(seconds * 1000.0))
        print(f"[PYTHON] Broadcasting seek to all widgets: {pos_ms}")
        self.seekOccurred.emit(pos_ms)
        self.active_player.seekOccurred.emit(pos_ms)

    def _on_seek_failed(self):
        print("[MediaBackend] Seek not supported or failed by current media player", flush=True)
        self._seek_lock_until = 0.0
        self.active_player._can_seek = False
        self.active_player.playerInfoChanged.emit()

    @Slot()
    def start_media_listener(self):
        with self._lock:
            if self._running and self._thread and self._thread.is_alive():
                print("[MediaBackend] Listener already active, triggering immediate refresh", flush=True)
                if self._loop and self._loop.is_running():
                    asyncio.run_coroutine_threadsafe(self._poll_session(force_refresh=True), self._loop)
                else:
                    self._force_emit_all()
                return

            print("[MediaBackend] Starting media listener...", flush=True)
            self._running = True
            self._thread = threading.Thread(target=self._run_async_loop, daemon=True)
            self._thread.start()

    @Slot()
    def stop_media_listener(self):
        with self._lock:
            print("[MediaBackend] Stopping media listener...", flush=True)
            self._running = False
            if self._loop and self._loop.is_running():
                try:
                    self._loop.call_soon_threadsafe(self._loop.stop)
                except Exception:
                    pass
            self._unhook_all_events()
            self._current_session = None
            self._mgr = None

    def _run_async_loop(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._main_async())
        except Exception as e:
            print(f"[MediaBackend] Loop exception: {e}", flush=True)
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
            print("[MediaBackend] Async loop closed cleanly", flush=True)

    async def _main_async(self):
        print("[MediaBackend] Main async loop entered", flush=True)
        # Immediate first poll
        try:
            await self._poll_session(force_refresh=True)
        except Exception as e:
            print(f"[MediaBackend] Initial poll error: {e}", flush=True)

        while self._running:
            try:
                await self._poll_session()
            except Exception as e:
                print(f"[MediaBackend] Polling error: {e}", flush=True)

            try:
                sleep_interval = 0.25 if (time.time() < self._burst_poll_until or time.time() < self._track_poll_until) else 0.5
                await asyncio.sleep(sleep_interval)
            except asyncio.CancelledError:
                break

        self._unhook_all_events()
        print("[MediaBackend] Main async loop exited", flush=True)

    async def _poll_session(self, force_refresh=False):
        if not self._running:
            return

        # 1. Acquire or re-acquire session manager if disconnected
        if self._mgr is None:
            try:
                self._mgr = await wmc.GlobalSystemMediaTransportControlsSessionManager.request_async()
                if self._mgr:
                    self._hook_mgr_events()
                    print("[MediaBackend] Connected to Windows SMTC SessionManager", flush=True)
            except Exception as e:
                print(f"[MediaBackend] Could not acquire SessionManager: {e}", flush=True)
                self._mgr = None
                return

        # 2. Get active session
        cur = None
        try:
            cur = self._mgr.get_current_session()
            if not cur:
                sessions = self._mgr.get_sessions()
                if sessions and len(sessions) > 0:
                    for s in sessions:
                        pinfo = s.get_playback_info()
                        if pinfo and int(pinfo.playback_status) == 4: # Playing
                            cur = s
                            break
                    if not cur:
                        cur = sessions[0]
        except Exception as e:
            print(f"[MediaBackend] Session retrieval failed ({e}), reconnecting SessionManager...", flush=True)
            self._unhook_all_events()
            self._mgr = None
            self._current_session = None
            return

        # 3. Handle session transition
        if cur != self._current_session or force_refresh:
            self._unhook_session_events()
            self._current_session = cur
            if cur:
                self._hook_session_events(cur)

        # 4. Update session data
        if cur:
            await self._update_session_info(cur, force_emit=force_refresh)
        else:
            self._clear_player()

    def _hook_mgr_events(self):
        if not self._mgr:
            return
        self._unhook_mgr_events()
        try:
            def _on_curr_changed(sender, args):
                if self._loop and self._loop.is_running() and self._running:
                    asyncio.run_coroutine_threadsafe(self._poll_session(force_refresh=True), self._loop)
            token1 = self._mgr.add_current_session_changed(_on_curr_changed)
            self._mgr_tokens.append(("current_session_changed", token1))

            def _on_sessions_changed(sender, args):
                if self._loop and self._loop.is_running() and self._running:
                    asyncio.run_coroutine_threadsafe(self._poll_session(force_refresh=True), self._loop)
            token2 = self._mgr.add_sessions_changed(_on_sessions_changed)
            self._mgr_tokens.append(("sessions_changed", token2))
        except Exception as e:
            print(f"[MediaBackend] Hook manager events error: {e}", flush=True)

    def _unhook_mgr_events(self):
        if self._mgr:
            for ev_name, tok in self._mgr_tokens:
                try:
                    if ev_name == "current_session_changed":
                        self._mgr.remove_current_session_changed(tok)
                    elif ev_name == "sessions_changed":
                        self._mgr.remove_sessions_changed(tok)
                except Exception:
                    pass
        self._mgr_tokens.clear()

    def _hook_session_events(self, session):
        self._unhook_session_events()
        if not session:
            return
        try:
            def _on_media_changed(s, a):
                if self._loop and self._loop.is_running() and self._running:
                    p = self.active_player
                    p._position = 0.0
                    self._last_known_pos_us = 0.0
                    self._seek_lock_until = 0.0
                    self._last_reported_pos_sec = 0.0
                    self._last_reported_time = time.time()
                    p.positionChanged.emit()
                    p.playerInfoChanged.emit()
                    p.trackChanged.emit()
                    self.positionChanged.emit()
                    self.playerInfoChanged.emit()
                    self.trackChanged.emit()
                    self.trigger_track_change_poll()
                    asyncio.run_coroutine_threadsafe(self._poll_session(force_refresh=True), self._loop)
            t1 = session.add_media_properties_changed(_on_media_changed)
            self._session_tokens.append((session, "media_properties_changed", t1))

            def _on_playback_changed(s, a):
                if self._loop and self._loop.is_running() and self._running:
                    asyncio.run_coroutine_threadsafe(self._poll_session(force_refresh=True), self._loop)
            t2 = session.add_playback_info_changed(_on_playback_changed)
            self._session_tokens.append((session, "playback_info_changed", t2))

            def _on_timeline_changed(s, a):
                if self._loop and self._loop.is_running() and self._running:
                    asyncio.run_coroutine_threadsafe(self._poll_session(force_refresh=True), self._loop)
            t3 = session.add_timeline_properties_changed(_on_timeline_changed)
            self._session_tokens.append((session, "timeline_properties_changed", t3))
        except Exception as e:
            print(f"[MediaBackend] Hook session events error: {e}", flush=True)

    def _unhook_session_events(self):
        for sess, ev_name, tok in self._session_tokens:
            try:
                if ev_name == "media_properties_changed":
                    sess.remove_media_properties_changed(tok)
                elif ev_name == "playback_info_changed":
                    sess.remove_playback_info_changed(tok)
                elif ev_name == "timeline_properties_changed":
                    sess.remove_timeline_properties_changed(tok)
            except Exception:
                pass
        self._session_tokens.clear()

    def _unhook_all_events(self):
        self._unhook_session_events()
        self._unhook_mgr_events()

    async def _update_session_info(self, session, force_emit=False):
        # Identity
        app_id = session.source_app_user_model_id or "Media"
        if "." in app_id:
            app_id = app_id.split(".")[0]

        # Properties
        info = await session.try_get_media_properties_async()
        title = info.title if info else ""
        artist = info.artist if info else ""
        album = info.album_title if info else ""

        p = self.active_player
        real_song_changed = bool(title and p._track and title.strip().lower() != p._track.strip().lower())

        # Playback info
        pinfo = session.get_playback_info()
        pstatus = 0
        can_play = False
        can_pause = False
        can_next = False
        can_prev = False
        controls = None
        if pinfo:
            status_val = int(pinfo.playback_status)
            if status_val == 4: # Playing
                pstatus = 1
            elif status_val == 5: # Paused
                pstatus = 2
            else:
                pstatus = 0

            controls = pinfo.controls
            if controls:
                can_play = bool(controls.is_play_enabled)
                can_pause = bool(controls.is_pause_enabled)
                can_next = bool(controls.is_next_enabled)
                can_prev = bool(controls.is_previous_enabled)

        # Timeline
        tinfo = session.get_timeline_properties()
        pos_us = 0.0
        len_us = 0.0
        can_seek = False
        if tinfo:
            raw_pos_sec = tinfo.position.total_seconds() if tinfo.position else 0.0
            raw_end_sec = tinfo.end_time.total_seconds() if tinfo.end_time else 0.0
            print(f"[DEBUG] SMTC Timeline - Pos: {raw_pos_sec:.2f}s, Length: {raw_end_sec:.2f}s", flush=True)
            raw_pos_ticks = int(raw_pos_sec * 10_000_000)
            raw_end_ticks = int(raw_end_sec * 10_000_000)

            if raw_end_sec > 0:
                len_us = raw_end_sec * 1_000_000.0
                if len_us > 7_200_000_000.0 or len_us < 0:
                    len_us = 0.0
            elif p._length > 0 and not real_song_changed:
                len_us = p._length

            can_seek = bool(controls and controls.is_playback_position_enabled and len_us > 0)

            cur_time = time.time()
            pos_delta = abs(raw_pos_sec - self._last_reported_pos_sec)

            if self._last_reported_time == 0.0 or pos_delta > 0.5 or real_song_changed:
                self._last_reported_pos_sec = raw_pos_sec
                self._last_reported_time = cur_time
                pos_sec = raw_pos_sec
            else:
                if pstatus == 1:
                    elapsed = cur_time - self._last_reported_time
                    pos_sec = self._last_reported_pos_sec + max(0.0, elapsed)
                else:
                    self._last_reported_time = cur_time
                    pos_sec = self._last_reported_pos_sec

            if len_us > 0 and (pos_sec * 1_000_000.0) > len_us:
                pos_sec = len_us / 1_000_000.0

            pos_us = max(0.0, pos_sec * 1_000_000.0)

            print(f"[MediaBackend] SMTC: raw_pos={raw_pos_sec:.2f}s ({raw_pos_ticks} ticks), raw_len={raw_end_sec:.2f}s ({raw_end_ticks} ticks), local_pos={pos_sec:.2f}s, len={len_us/1e6:.2f}s", flush=True)

        # Thumbnail
        art_path = ""
        if info and info.thumbnail:
            try:
                stream = await info.thumbnail.open_read_async()
                size = stream.size
                if size > 0:
                    reader = wss.DataReader(stream)
                    await reader.load_async(size)
                    bytes_data = bytearray(size)
                    reader.read_bytes(bytes_data)
                    h = hashlib.md5(bytes_data).hexdigest()
                    if h != self._last_art_hash or not os.path.exists(self.active_player._art_url.replace("file:///", "")):
                        fname = f"{h}.jpg"
                        out_path = os.path.join(self.art_dir, fname)
                        with open(out_path, "wb") as f:
                            f.write(bytes_data)
                        self._last_art_hash = h
                        art_path = QUrl.fromLocalFile(out_path).toString()
                    else:
                        art_path = self.active_player._art_url
            except Exception:
                pass

        # Update QObject properties
        p = self.active_player
        metadata_changed = force_emit or (p._track != title or p._artist != artist or p._album != album)
        real_song_changed = bool(title and p._track and title.strip().lower() != p._track.strip().lower())

        if real_song_changed:
            p._position = 0.0
            if len_us > 0:
                p._length = len_us
            self._last_known_pos_us = 0.0
            self._seek_lock_until = 0.0
            self._last_reported_pos_sec = 0.0
            self._last_reported_time = time.time()
            p.positionChanged.emit()
            p.playerInfoChanged.emit()
            self.positionChanged.emit()
            self.playerInfoChanged.emit()
            self.trigger_track_change_poll()

        if metadata_changed:
            p._track = title
            p._artist = artist
            p._album = album
            p._track_id = f"{artist}_{title}"
            p.trackChanged.emit()

        if force_emit or p._playback_status != pstatus:
            p._playback_status = pstatus
            p.playbackStatusChanged.emit()

        now = time.time()
        is_seeking_locked = (now < self._seek_lock_until)

        # Position Delta Detection (Safety Net):
        # Constantly compare last_known_position with new_position from the polling loop.
        # If there is a sudden jump (forward > 1.5s or rewind > 0.5s), trigger seekOccurred signal.
        # Metadata flickering (e.g. artist changing from 'A' to 'A & B') does NOT block rewind detection.
        delta_us = abs(pos_us - self._last_known_pos_us)
        is_rewind = (self._last_known_pos_us > 0 and pos_us > 0 and (self._last_known_pos_us - pos_us) > 500_000)
        is_forward_jump = (self._last_known_pos_us > 0 and pos_us > 0 and (pos_us - self._last_known_pos_us) > 1_500_000)
        has_sudden_jump = (is_rewind or is_forward_jump) and not real_song_changed

        if has_sudden_jump and not is_seeking_locked:
            pos_ms = int(round(pos_us / 1000.0))
            direction = "Rewind" if is_rewind else "Forward"
            print(f"[MediaBackend] {direction} delta jump detected: {delta_us/1000000.0:.2f}s (from {self._last_known_pos_us/1000000.0:.2f}s to {pos_us/1000000.0:.2f}s)", flush=True)
            print(f"[PYTHON] Broadcasting seek to all widgets: {pos_ms}")
            self._seek_lock_until = 0.0
            p._position = pos_us
            p.positionChanged.emit()
            self.seekOccurred.emit(pos_ms)
            self.active_player.seekOccurred.emit(pos_ms)
            self._last_known_pos_us = pos_us
        elif is_seeking_locked:
            # Check if OS reported position has arrived at or near the requested seek position
            if pos_us > 0.0 and abs(pos_us - self._requested_seek_us) < 2_000_000:
                self._seek_lock_until = 0.0 # Seek confirmed by OS!
                p._position = pos_us
                p.positionChanged.emit()
                pos_ms = int(round(pos_us / 1000.0))
                print(f"[PYTHON] Broadcasting confirmed seek to all widgets: {pos_ms}")
                self.seekOccurred.emit(pos_ms)
                self.active_player.seekOccurred.emit(pos_ms)
                self._last_known_pos_us = pos_us
            else:
                # Seek lock is active and OS position has not caught up to requested target yet.
                # Do not let stale OS position overwrite p._position.
                pass
        else:
            diff = abs(p._position - pos_us)
            if diff > 100_000 or force_emit:
                p._position = pos_us
                p.positionChanged.emit()

            if pos_us > 0.0:
                self._last_known_pos_us = pos_us

        if (art_path and p._art_url != art_path) or (force_emit and art_path):
            p._art_url = art_path
            p.artUrlChanged.emit()

        info_changed = force_emit or (
            p._identity != app_id or
            p._length != len_us or
            p._can_play != can_play or
            p._can_pause != can_pause or
            p._can_next != can_next or
            p._can_prev != can_prev or
            p._can_seek != can_seek
        )
        if info_changed:
            p._identity = app_id
            p._length = len_us
            p._can_play = can_play
            p._can_pause = can_pause
            p._can_next = can_next
            p._can_prev = can_prev
            p._can_seek = can_seek
            p.playerInfoChanged.emit()

    def _force_emit_all(self):
        p = self.active_player
        p.trackChanged.emit()
        p.playbackStatusChanged.emit()
        p.positionChanged.emit()
        p.artUrlChanged.emit()
        p.playerInfoChanged.emit()

    def _clear_player(self):
        p = self.active_player
        p._lyrics_offset_ms = 0
        if p._track != "" or p._playback_status != 0:
            p._track = ""
            p._artist = ""
            p._album = ""
            p._art_url = ""
            p._playback_status = 0
            p._position = 0.0
            p._length = 0.0
            p.trackChanged.emit()
            p.playbackStatusChanged.emit()
            p.positionChanged.emit()
            p.artUrlChanged.emit()
            p.playerInfoChanged.emit()
            self.trackChanged.emit()
            self.positionChanged.emit()
            self.playerInfoChanged.emit()

    def _run_async(self, winrt_op):
        async def _wrapper():
            try:
                await winrt_op
            except Exception as e:
                print(f"[MediaBackend] WinRT async op failed: {e}", flush=True)
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(_wrapper(), self._loop)

    def _get_or_find_session(self):
        if self._current_session:
            return self._current_session
        if self._mgr:
            try:
                cur = self._mgr.get_current_session()
                if not cur:
                    sessions = self._mgr.get_sessions()
                    if sessions and len(sessions) > 0:
                        cur = sessions[0]
                self._current_session = cur
                return cur
            except Exception:
                pass
        return None

    def cmd_play_pause(self):
        sess = self._get_or_find_session()
        if sess:
            self._run_async(sess.try_toggle_play_pause_async())

    def cmd_play(self):
        sess = self._get_or_find_session()
        if sess:
            self._run_async(sess.try_play_async())

    def cmd_pause(self):
        sess = self._get_or_find_session()
        if sess:
            self._run_async(sess.try_pause_async())

    def cmd_next(self):
        sess = self._get_or_find_session()
        if sess:
            self._run_async(sess.try_skip_next_async())

    def cmd_previous(self):
        sess = self._get_or_find_session()
        if sess:
            self._run_async(sess.try_skip_previous_async())

    @Slot(float)
    def seekRequested(self, seconds):
        self.active_player.seekRequested(seconds)

    @Slot(float)
    def setPlaybackPosition(self, seconds):
        self.active_player.seekRequested(seconds)

    @Slot(float)
    def setPlaybackPositionUs(self, pos_us):
        self.active_player.seekRequested(float(pos_us) / 1_000_000.0)

    def cmd_seek(self, pos_us):
        self.active_player.seekRequested(float(pos_us) / 1_000_000.0)

    def stop(self):
        self.stop_media_listener()
