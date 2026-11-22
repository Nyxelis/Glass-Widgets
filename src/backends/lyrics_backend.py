import os
import json
import re
import ssl
import urllib.request
import urllib.parse
from PySide6.QtCore import QObject, Signal, Slot, QRunnable, QThreadPool

def get_lyrics_cache_file():
    appdata = os.environ.get("APPDATA")
    if not appdata:
        appdata = os.path.expanduser("~")
    path = os.path.join(appdata, "GlassWidgets")
    os.makedirs(path, exist_ok=True)
    return os.path.join(path, "lyrics_cache.json")

def clean_metadata(text: str) -> str:
    if not text:
        return ""
    # Strip (Remastered...), [Deluxe Edition], - Live at..., (Bonus Track), etc.
    t = re.sub(r'\(.*?(remaster|deluxe|edition|version|bonus|live|acoustic|anniversary).*?\)', '', text, flags=re.IGNORECASE)
    t = re.sub(r'\[.*?(remaster|deluxe|edition|version|bonus|live|acoustic|anniversary).*?\]', '', t, flags=re.IGNORECASE)
    t = re.sub(r'-\s*(remaster|live|deluxe).*?$', '', t, flags=re.IGNORECASE)
    return t.strip()

class LyricsCache:
    def __init__(self):
        self.file_path = get_lyrics_cache_file()
        self.cache = self._load()

    def _load(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save(self):
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, ensure_ascii=False)
        except Exception:
            pass

    def get(self, artist, track):
        key = f"{artist.strip().lower()}|{track.strip().lower()}"
        return self.cache.get(key)

    def set(self, artist, track, lyrics_data):
        key = f"{artist.strip().lower()}|{track.strip().lower()}"
        self.cache[key] = lyrics_data
        self._save()

def query_lrclib(artist: str, track: str, album: str = "", duration_sec: float = 0.0) -> dict:
    headers = {"User-Agent": "GlassWidgets/1.0 (https://github.com/Nyxelis/Glass-Widgets)"}
    dur_int = int(round(duration_sec)) if duration_sec > 0 else 0
    ssl_ctx = ssl.create_default_context()

    # 1. Exact match via /api/get with album and duration
    params = {
        "artist_name": artist,
        "track_name": track,
    }
    if album:
        params["album_name"] = album
    if dur_int > 0:
        params["duration"] = dur_int

    url = "https://lrclib.net/api/get?" + urllib.parse.urlencode(params)
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5, context=ssl_ctx) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("syncedLyrics") or data.get("plainLyrics"):
                    print(f"[LyricsBackend] LRCLib exact match found for: {track} ({dur_int}s)", flush=True)
                    return data
    except urllib.error.HTTPError as e:
        if e.code != 404:
            print(f"[LyricsBackend] LRCLib /api/get error: {e}", flush=True)
    except Exception as e:
        print(f"[LyricsBackend] LRCLib request error: {e}", flush=True)

    # 2. Try with cleaned track and cleaned album
    c_track = clean_metadata(track)
    c_album = clean_metadata(album)
    if (c_track != track or c_album != album) and c_track:
        c_params = {
            "artist_name": artist,
            "track_name": c_track,
        }
        if c_album:
            c_params["album_name"] = c_album
        if dur_int > 0:
            c_params["duration"] = dur_int
        try:
            url = "https://lrclib.net/api/get?" + urllib.parse.urlencode(c_params)
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=5, context=ssl_ctx) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    if data.get("syncedLyrics") or data.get("plainLyrics"):
                        print(f"[LyricsBackend] LRCLib cleaned metadata match found for: {c_track}", flush=True)
                        return data
        except Exception:
            pass

    # 3. Try /api/get without album name, but STILL WITH DURATION to prevent covers/live tracks
    if album or c_album:
        no_alb_params = {
            "artist_name": artist,
            "track_name": c_track or track,
        }
        if dur_int > 0:
            no_alb_params["duration"] = dur_int
        try:
            url = "https://lrclib.net/api/get?" + urllib.parse.urlencode(no_alb_params)
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=5, context=ssl_ctx) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    if data.get("syncedLyrics") or data.get("plainLyrics"):
                        print(f"[LyricsBackend] LRCLib duration-only match found for: {track} ({dur_int}s)", flush=True)
                        return data
        except Exception:
            pass

    # 4. Fallback: /api/search with duration-matching filter
    try:
        search_params = {
            "track_name": c_track or track,
            "artist_name": artist,
        }
        s_url = "https://lrclib.net/api/search?" + urllib.parse.urlencode(search_params)
        req = urllib.request.Request(s_url, headers=headers)
        with urllib.request.urlopen(req, timeout=6, context=ssl_ctx) as resp:
            if resp.status == 200:
                results = json.loads(resp.read().decode("utf-8"))
                if results and isinstance(results, list):
                    candidates = []
                    target_has_live = "live" in track.lower()
                    for item in results:
                        synced = item.get("syncedLyrics")
                        item_dur = item.get("duration", 0)
                        item_track = item.get("trackName", "")
                        item_album = item.get("albumName", "")

                        # If duration is known, candidate duration must be within +- 4 seconds
                        if dur_int > 0 and item_dur > 0 and abs(item_dur - dur_int) > 4:
                            continue

                        # Unless user specifically requested a live track, reject live/cover versions
                        if not target_has_live and ("live" in item_track.lower() or "live" in item_album.lower()):
                            continue

                        # Score candidate
                        score = 0
                        if synced:
                            score += 10
                        if dur_int > 0 and item_dur > 0:
                            score += max(0, 5 - abs(item_dur - dur_int))
                        if album and item_album and album.lower() in item_album.lower():
                            score += 5
                        candidates.append((score, item))

                    if candidates:
                        candidates.sort(key=lambda x: x[0], reverse=True)
                        best = candidates[0][1]
                        print(f"[LyricsBackend] LRCLib search matched: {best.get('trackName')} ({best.get('duration')}s) album: {best.get('albumName')}", flush=True)
                        return best
    except Exception as e:
        print(f"[LyricsBackend] LRCLib search error: {e}", flush=True)

    print(f"[LyricsBackend] No exact lyrics found on LRCLib for: {artist} - {track}", flush=True)
    return {}

class LyricsWorker(QRunnable):
    def __init__(self, artist, track, album, duration_sec, backend):
        super().__init__()
        self.artist = artist
        self.track = track
        self.album = album
        self.duration_sec = duration_sec
        self.backend = backend

    def run(self):
        key = f"{self.artist}|{self.track}"
        cached = self.backend.cache.get(self.artist, self.track)
        if cached:
            print(f"[LyricsBackend] Serving cached lyrics for: {key}", flush=True)
            self.backend._emit_result(key, cached.get("syncedLyrics", ""), cached.get("plainLyrics", ""), True)
            return

        data = query_lrclib(self.artist, self.track, self.album, self.duration_sec)
        if data and (data.get("syncedLyrics") or data.get("plainLyrics")):
            self.backend.cache.set(self.artist, self.track, data)
            self.backend._emit_result(key, data.get("syncedLyrics", ""), data.get("plainLyrics", ""), True)
        else:
            self.backend._emit_result(key, "", "", False)

class LyricsBackend(QObject):
    lyricsLoaded = Signal(str, str, str, bool) # key, syncedLyrics, plainLyrics, success
    _result_signal = Signal(str, str, str, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.cache = LyricsCache()
        self._result_signal.connect(self._handle_result)

    def _emit_result(self, key, synced, plain, success):
        self._result_signal.emit(key, synced, plain, success)

    def _handle_result(self, key, synced, plain, success):
        self.lyricsLoaded.emit(key, synced, plain, success)

    @Slot(str, str, str, float)
    def fetchLyrics(self, artist, track, album="", duration_sec=0.0):
        if not artist or not track:
            return
        worker = LyricsWorker(artist, track, album, duration_sec, self)
        QThreadPool.globalInstance().start(worker)
