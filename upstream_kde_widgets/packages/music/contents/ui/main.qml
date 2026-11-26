pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.private.mpris as Mpris
import "components"
import "widget"

PlasmoidItem {
    id: root

    Plasmoid.backgroundHints: PlasmaCore.Types.NoBackground

    WidgetActions { id: commonActions }

    PlasmaCore.Action {
        id: playPauseAction
        text: root.isPlaying ? i18n("Pause") : i18n("Play")
        icon.name: root.isPlaying ? "media-playback-pause" : "media-playback-start"
        enabled: root._bcConnected || (root._activePlayer !== null && root._activePlayer !== undefined)
        onTriggered: root.togglePlaying()
    }
    PlasmaCore.Action {
        id: nextAction
        text: i18n("Next Track")
        icon.name: "media-skip-forward"
        enabled: root.canGoNext
        onTriggered: root.next()
    }
    PlasmaCore.Action {
        id: previousAction
        text: i18n("Previous Track")
        icon.name: "media-skip-backward"
        enabled: root.canGoPrevious
        onTriggered: root.previous()
    }

    Plasmoid.contextualActions: [playPauseAction, nextAction, previousAction].concat(commonActions.list)
    preferredRepresentation: fullRepresentation

    readonly property bool _shouldShow: {
        if (!plasmoid.configuration.autoHideEnabled) return true
        return root.isPlaying
    }

    function _updateVisibility() {
        if (_shouldShow) {
            root.visible = true
            _autoHideTimer.stop()
        } else if (plasmoid.configuration.autoHideEnabled) {
            _autoHideTimer.restart()
        }
    }

    on_ShouldShowChanged: _updateVisibility()

    // Initialise the auto-hide timer and SMTC listener when widget mounts
    Component.onCompleted: {
        _updateVisibility()
        if (_rawAlbumArt !== "") {
            root.albumArt = root._rawAlbumArt
        }
        if (typeof bitChordBridge !== "undefined" && bitChordBridge) {
            if (bitChordBridge.isConnected) {
                root._bcStatus = bitChordBridge.status
                root._bcTitle = bitChordBridge.title
                root._bcArtist = bitChordBridge.artist
                root._bcAlbum = bitChordBridge.album
                root._bcArt = bitChordBridge.albumArt
                root._bcLengthUs = bitChordBridge.durationMs * 1000.0
                root.position = bitChordBridge.progressMs * 1000.0
                root._lastPosTick = Date.now()
            }
            if (typeof bitChordBridge.start === "function")
                bitChordBridge.start()
        }
        if (typeof backend !== "undefined" && backend && typeof backend.start_media_listener === "function") {
            backend.start_media_listener()
        } else if (typeof globalMediaBackend !== "undefined" && globalMediaBackend && typeof globalMediaBackend.start_media_listener === "function") {
            globalMediaBackend.start_media_listener()
        }
    }

    Component.onDestruction: {
        root._bcArt = ""
        root.albumArt = ""
        if (typeof backend !== "undefined" && backend && typeof backend.stop_media_listener === "function") {
            backend.stop_media_listener()
        } else if (typeof globalMediaBackend !== "undefined" && globalMediaBackend && typeof globalMediaBackend.stop_media_listener === "function") {
            globalMediaBackend.stop_media_listener()
        }
    }

    onVisibleChanged: {
        if (root.visible) {
            if (typeof bitChordBridge !== "undefined" && bitChordBridge) {
                if (bitChordBridge.isConnected) {
                    root._bcStatus = bitChordBridge.status
                    root._bcTitle = bitChordBridge.title
                    root._bcArtist = bitChordBridge.artist
                    root._bcAlbum = bitChordBridge.album
                    root._bcArt = bitChordBridge.albumArt
                    root._bcLengthUs = bitChordBridge.durationMs * 1000.0
                    root.position = bitChordBridge.progressMs * 1000.0
                    root._lastPosTick = Date.now()
                }
                if (typeof bitChordBridge.start === "function")
                    bitChordBridge.start()
            }
            root.albumArt = root._rawAlbumArt !== "" ? root._rawAlbumArt : root._noAlbumUrl
            if (typeof backend !== "undefined" && backend && typeof backend.start_media_listener === "function") {
                backend.start_media_listener()
            } else if (typeof globalMediaBackend !== "undefined" && globalMediaBackend && typeof globalMediaBackend.start_media_listener === "function") {
                globalMediaBackend.start_media_listener()
            }
        } else {
            _artDebounceTimer.stop()
            root.albumArt = ""
        }
    }

    Timer {
        id: _autoHideTimer
        interval: plasmoid.configuration.autoHideTimeout * 1000
        repeat: false
        onTriggered: root.visible = false
    }

    MacOSColors {
        id: colors
        styleMode: plasmoid.configuration.styleMode
        appearance: plasmoid.configuration.appearance
        foregroundDarkOverride: isSolid && root._hasSampledColor ? root._sampledIsDark : null
    }
    readonly property var colorTokens: colors

    FontLoader { id: sfThin;    source: Qt.resolvedUrl("../fonts/sf_pro_display_thin.otf") }
    FontLoader { id: sfRegular; source: Qt.resolvedUrl("../fonts/sf_pro_display_regular.otf") }
    // ── MPRIS ─────────────────────────────────────────────────────────────

    Mpris.Mpris2Model { id: mpris2Model }

    function _isPlayerAllowed(identity) {
        var f = (plasmoid.configuration.playerFilter || "").toLowerCase()
        if (f === "") return true
        var list = f.split(",")
        var id = (identity || "").toLowerCase()
        var inList = false
        for (var i = 0; i < list.length; i++) {
            if (list[i].trim() === id) { inList = true; break }
        }
        return plasmoid.configuration.filterMode === 1 ? !inList : inList
    }

    property var _activePlayer: {
        var cp = mpris2Model.currentPlayer
        var _dep = cp ? (cp.track + "|" + cp.artist + "|" + cp.artUrl + "|" + cp.playbackStatus) : ""
        if (cp && _isPlayerAllowed(cp.identity) && (cp.track || cp.artist))
            return cp
        const CONTAINER_ROLE = Qt.UserRole + 1
        for (var i = 1; i < mpris2Model.rowCount(); i++) {
            var p = mpris2Model.data(mpris2Model.index(i, 0), CONTAINER_ROLE)
            if (p && _isPlayerAllowed(p.identity) && (p.track || p.artist))
                return p
        }
        return null
    }
    readonly property bool _playerAllowed: {
        var cp = mpris2Model.currentPlayer
        return cp ? _isPlayerAllowed(cp.identity) : true
    }

    // ── BitChord WebSocket Bridge State ──────────────────────────────────
    readonly property bool _bcConnected: (typeof bitChordBridge !== "undefined" && bitChordBridge) ? bitChordBridge.isConnected : false
    property string _bcStatus: "stopped"
    property string _bcTitle: ""
    property string _bcArtist: ""
    property string _bcAlbum: ""
    property string _bcArt: ""
    property real _bcLengthUs: 0

    readonly property string track:   _bcConnected ? _bcTitle  : (_activePlayer?.track ?? "")
    readonly property string artist:  _bcConnected ? _bcArtist : (_activePlayer?.artist ?? "")
    readonly property string album:   _bcConnected ? _bcAlbum  : (_activePlayer?.album ?? "")
    readonly property int lyricsOffsetMs: _activePlayer?.lyricsOffsetMs ?? 0
    readonly property string _rawAlbumArt: _bcConnected ? _bcArt : (_activePlayer?.artUrl ?? "")
    readonly property string _noAlbumUrl: Qt.resolvedUrl("icons/no_album.png")
    property string albumArt: _rawAlbumArt !== "" ? _rawAlbumArt : _noAlbumUrl

    on_RawAlbumArtChanged: {
        if (_rawAlbumArt !== "") {
            _artDebounceTimer.restart()
        } else {
            root.albumArt = root._noAlbumUrl
        }
    }

    Timer {
        id: _artDebounceTimer
        interval: 150
        onTriggered: root.albumArt = root._rawAlbumArt
    }
    readonly property int playbackStatus: {
        if (_bcConnected) {
            var st = _bcStatus.toLowerCase()
            if (st === "playing") return Mpris.PlaybackStatus.Playing
            if (st === "paused") return Mpris.PlaybackStatus.Paused
            return 0
        }
        return _activePlayer?.playbackStatus ?? 0
    }
    readonly property bool isPlaying: playbackStatus === Mpris.PlaybackStatus.Playing
    readonly property bool canGoPrevious: _bcConnected ? true : (_activePlayer?.canGoPrevious ?? false)
    readonly property bool canGoNext:     _bcConnected ? true : (_activePlayer?.canGoNext ?? false)
    readonly property bool canPlay:  _bcConnected ? true : (_activePlayer?.canPlay ?? false)
    readonly property bool canPause: _bcConnected ? true : (_activePlayer?.canPause ?? false)
    readonly property bool canSeek:  _bcConnected ? (root.length > 0) : (_activePlayer ? (_activePlayer.canSeek ?? true) : true)
    property real length: _bcConnected ? _bcLengthUs : (_activePlayer?.length ?? 0)
    Binding {
        target: root
        property: "length"
        value: root._bcConnected ? root._bcLengthUs : (root._activePlayer ? (root._activePlayer.length ?? 0) : 0)
        restoreMode: Binding.RestoreBindingOrValue
    }

    Connections {
        target: (typeof bitChordBridge !== "undefined" && bitChordBridge) ? bitChordBridge : null
        function onConnectionStatusChanged(statusText) {
            if (statusText !== "Connected") {
                root._bcStatus = "stopped"
                root._bcTitle = ""
                root._bcArtist = ""
                root._bcAlbum = ""
                root._bcArt = ""
                root._bcLengthUs = 0
                root.position = root._activePlayer ? (root._activePlayer.position ?? 0) : 0
                root._lastPosTick = Date.now()
            }
        }
        function onStateChanged(status, title, artist, album) {
            var trackChanged = (title !== root._bcTitle)
            root._bcStatus = status || "stopped"
            root._bcTitle = title || ""
            root._bcArtist = artist || ""
            root._bcAlbum = album || ""
            if (trackChanged) {
                root.position = 0
                root._lastPosTick = Date.now()
            }
        }
        function onProgressChanged(progressMs, durationMs) {
            var posUs = Math.max(0, progressMs * 1000.0)
            var lenUs = Math.max(0, durationMs * 1000.0)
            root._bcLengthUs = lenUs
            if (root.isSeeking) {
                if (Math.abs(posUs - root.targetSeekPos) < 2000000) {
                    root.isSeeking = false
                    seekWatchdogTimer.stop()
                    root.position = posUs
                    root._lastPosTick = Date.now()
                }
                return
            }
            if (!root.isPlaying || Math.abs(posUs - root.position) > 500000) {
                root.position = posUs
                root._lastPosTick = Date.now()
            }
        }
        function onAlbumArtChanged(base64String) {
            root._bcArt = base64String || ""
        }
    }

    property real position: 0
    property bool lyricsActive: false
    property int _flipDirection: 1

    // ── Lyrics data ──────────────────────────────────────────────────────
    property var _syncedLyrics: []
    property string _plainLyrics: ""
    property int _lyricsState: 0   // 0=idle 1=loading 2=loaded 3=error 4=not-found
    property string _lyricsTrackKey: ""
    property int _lyricsFailCount: 0
    readonly property var _lyricsBackoff: [5000, 10000, 20000, 40000, 80000, 160000, 300000]

    onLyricsActiveChanged: {
        if (lyricsActive && _lyricsState === 0 && track !== "")
            _lyricsFetchTimer.restart()
    }

    Timer {
        id: _lyricsFetchTimer
        interval: 400
        onTriggered: root._fetchLyrics()
    }

    Timer {
        id: _lyricsRetryTimer
        repeat: false
        onTriggered: root._fetchLyrics()
    }

    property real _lastPosTick: 0

    Timer {
        id: lyricsPositionTimer
        interval: 80
        running: root.isPlaying && root.lyricsActive
        repeat: true
        onTriggered: {
            var now = Date.now()
            if (root._lastPosTick > 0 && !root.isSeeking) {
                root.position += (now - root._lastPosTick) * 1000
                if (root.length > 0 && root.position > root.length)
                    root.position = root.length
            }
            root._lastPosTick = now
        }
    }

    function _fetchLyrics() {
        if (track === "" || artist === "") return
        var key = artist + "|" + track
        if (key === _lyricsTrackKey && _lyricsState === 2) return
        _lyricsTrackKey = key
        _lyricsState = 1

        var durSec = length > 0 ? (length / 1000000.0) : 0

        var b = (typeof backend !== "undefined" && backend) ? backend : (root._activePlayer ? root._activePlayer : null)
        if (b && typeof b.fetchLyrics === "function") {
            console.log("[QML] Requesting lyrics from Python backend:", artist, track, album, durSec)
            b.fetchLyrics(artist, track, album, durSec)
            return
        }

        var url = "https://lrclib.net/api/get"
            + "?artist_name=" + encodeURIComponent(artist)
            + "&track_name=" + encodeURIComponent(track)
        if (album !== "")
            url += "&album_name=" + encodeURIComponent(album)
        if (durSec > 0)
            url += "&duration=" + Math.round(durSec)

        var xhr = new XMLHttpRequest()
        xhr.onreadystatechange = function() {
            if (xhr.readyState !== XMLHttpRequest.DONE) return
            if (root._lyricsTrackKey !== key) return  // stale

            if (xhr.status === 200) {
                try {
                    var resp = JSON.parse(xhr.responseText)
                    var synced = resp.syncedLyrics || ""
                    root._plainLyrics = resp.plainLyrics || ""
                    root._syncedLyrics = synced !== "" ? root._parseLrc(synced, (resp.offset || 0) * 1000) : []
                    root._lyricsState = 2
                    root._lyricsFailCount = 0
                    _lyricsRetryTimer.stop()
                } catch(e) {
                    root._lyricsState = 3
                    root._lyricsFailCount = Math.min(root._lyricsFailCount + 1, root._lyricsBackoff.length - 1)
                    _lyricsRetryTimer.interval = root._lyricsBackoff[root._lyricsFailCount]
                    _lyricsRetryTimer.restart()
                }
            } else if (xhr.status === 404) {
                root._lyricsState = 4
                root._lyricsFailCount = 0
                _lyricsRetryTimer.stop()
            } else {
                root._lyricsState = 3
                root._lyricsFailCount = Math.min(root._lyricsFailCount + 1, root._lyricsBackoff.length - 1)
                _lyricsRetryTimer.interval = root._lyricsBackoff[root._lyricsFailCount]
                _lyricsRetryTimer.restart()
            }
        }
        xhr.open("GET", url)
        xhr.send()
    }

    function _parseLrc(lrcContent, apiOffsetMs) {
        var lines = lrcContent.split("\n")
        var result = []
        var re = /\[(\d{1,2}):(\d{2})[.:](\d{2,3})\](.*)/
        var offsetRe = /\[offset:([+-]?\d+)\]/i
        var lrcOffsetMs = 0
        for (var i = 0; i < lines.length; i++) {
            var om = offsetRe.exec(lines[i])
            if (om) {
                lrcOffsetMs += parseInt(om[1])
                continue
            }
            var m = re.exec(lines[i])
            if (m) {
                var ms = m[3].length === 2 ? parseInt(m[3]) * 10 : parseInt(m[3])
                result.push({
                    timestamp: parseInt(m[1]) * 60000 + parseInt(m[2]) * 1000 + ms
                               + lrcOffsetMs + (apiOffsetMs || 0),
                    text: m[4].trim()
                })
            }
        }
        result.sort(function(a, b) { return a.timestamp - b.timestamp })
        return result
    }

    property bool isSeeking: false
    property real targetSeekPos: 0
    readonly property var backend: Mpris.GlobalActivePlayer

    Timer {
        id: seekWatchdogTimer
        interval: 3500
        repeat: false
        onTriggered: {
            console.log("[QML] Seek watchdog expired (3.5s), snapping to targetSeekPos:", root.targetSeekPos)
            root.isSeeking = false
            if (root.targetSeekPos > 0) {
                root.position = root.targetSeekPos
            } else if (!root._bcConnected) {
                var bPos = Mpris.GlobalActivePlayer ? Mpris.GlobalActivePlayer.position : (root._activePlayer ? root._activePlayer.position : 0)
                if (bPos > 0) {
                    root.position = bPos
                }
            }
            root._lastPosTick = Date.now()
        }
    }
    property alias seekCooldownTimer: seekWatchdogTimer

    Connections {
        target: Mpris.GlobalActivePlayer
        function onTrackChanged() {
            if (root._bcConnected) return
            root.position = 0
            root._lastPosTick = Date.now()
        }
        function onPlayerInfoChanged() {
            if (root._bcConnected) return
            var l = Mpris.GlobalActivePlayer ? Mpris.GlobalActivePlayer.length : 0
            if (l > 7200000000 || l < 0) l = 0
            root.length = l
        }
        function onPositionChanged() {
            if (root._bcConnected) return
            var bPos = Mpris.GlobalActivePlayer ? Mpris.GlobalActivePlayer.position : 0
            var bLen = (root.length > 0) ? root.length : (Mpris.GlobalActivePlayer ? Mpris.GlobalActivePlayer.length : 0)
            if (bLen > 0 && bPos > bLen) {
                bPos = bLen
            }
            if (root.isSeeking) {
                if (root.targetSeekPos > 0 && Math.abs(bPos - root.targetSeekPos) < 2000000) {
                    console.log("[QML] OS position caught up to targetSeekPos:", bPos)
                    root.isSeeking = false
                    seekWatchdogTimer.stop()
                    root.position = bPos
                    root._lastPosTick = Date.now()
                }
                return
            }
            if (Math.abs(bPos - root.position) > 1500000) {
                root.position = bPos
                root._lastPosTick = Date.now()
                return
            }
            if (!root.isSeeking) {
                root.position = bPos
            }
            root._lastPosTick = Date.now()
        }
        function onSeekOccurred(newPosMs) {
            console.log("[QML] Widget received seekOccurred from GlobalActivePlayer. New pos:", newPosMs)
            var posUs = (newPosMs > 10000000) ? newPosMs : (newPosMs * 1000)
            root.position = posUs
            root.targetSeekPos = posUs
            root.isSeeking = false
            seekWatchdogTimer.stop()
            root._lastPosTick = Date.now()
        }
        function onLyricsLoaded(key, synced, plain, success) {
            console.log("[QML] lyricsLoaded received from GlobalActivePlayer:", key, success)
            if (key !== root._lyricsTrackKey) return
            if (success) {
                root._plainLyrics = plain || ""
                root._syncedLyrics = synced !== "" ? root._parseLrc(synced, 0) : []
                root._lyricsState = 2
                root._lyricsFailCount = 0
                _lyricsRetryTimer.stop()
            } else {
                root._lyricsState = 4
                root._lyricsFailCount = 0
                _lyricsRetryTimer.stop()
            }
        }
    }

    Connections {
        target: Mpris.GlobalMediaBackend
        function onTrackChanged() {
            if (root._bcConnected) return
            root.position = 0
            root._lastPosTick = Date.now()
        }
        function onPlayerInfoChanged() {
            if (root._bcConnected) return
            var l = Mpris.GlobalActivePlayer ? Mpris.GlobalActivePlayer.length : 0
            if (l > 7200000000 || l < 0) l = 0
            root.length = l
        }
        function onSeekOccurred(newPosMs) {
            console.log("[QML] Widget received seekOccurred from GlobalMediaBackend. New pos:", newPosMs)
            var posUs = (newPosMs > 10000000) ? newPosMs : (newPosMs * 1000)
            root.position = posUs
            root.targetSeekPos = posUs
            root.isSeeking = false
            seekWatchdogTimer.stop()
            root._lastPosTick = Date.now()
        }
        function onLyricsLoaded(key, synced, plain, success) {
            console.log("[QML] lyricsLoaded received from GlobalMediaBackend:", key, success)
            if (key !== root._lyricsTrackKey) return
            if (success) {
                root._plainLyrics = plain || ""
                root._syncedLyrics = synced !== "" ? root._parseLrc(synced, 0) : []
                root._lyricsState = 2
                root._lyricsFailCount = 0
                _lyricsRetryTimer.stop()
            } else {
                root._lyricsState = 4
                root._lyricsFailCount = 0
                _lyricsRetryTimer.stop()
            }
        }
    }

    Timer {
        id: positionTimer
        interval: 100
        running: root.isPlaying && !lyricsPositionTimer.running
        repeat: true
        onTriggered: {
            var now = Date.now()
            if (root._lastPosTick > 0 && !root.isSeeking) {
                root.position += (now - root._lastPosTick) * 1000
                if (root.length > 0 && root.position > root.length)
                    root.position = root.length
            }
            root._lastPosTick = now
        }
    }

    onTrackChanged: {
        root.isSeeking = false
        root.targetSeekPos = 0
        root.position = 0
        root._lastPosTick = Date.now()
        seekWatchdogTimer.stop()

        if (track === "" || track === "Not Playing") {
            _artDebounceTimer.stop()
            albumArt = _noAlbumUrl
            root.length = 0
        }
        root._lastSampledUrl = ""
        _scheduleArtRefresh()
        _resampleTimer.restart()
        root._syncedLyrics = []
        root._plainLyrics = ""
        root._lyricsState = 0
        root._lyricsTrackKey = ""
        root._lyricsFailCount = 0
        _lyricsRetryTimer.stop()
        _lyricsFetchTimer.restart()
    }
    Timer {
        id: _resampleTimer
        interval: 350
        repeat: false
        onTriggered: {
            if (root.albumArt !== "" && root.albumArt !== root._lastSampledUrl)
                sampleCanvas.requestPaint()
        }
    }
    onIsPlayingChanged: {
        root.position = root._bcConnected ? (bitChordBridge.progressMs * 1000.0) : (root._activePlayer?.position ?? 0)
        root._lastPosTick = root.isPlaying ? Date.now() : 0
    }
    onLengthChanged: {
        if (length > 0 && _lyricsState === 0 && track !== "")
            _lyricsFetchTimer.restart()
    }

    Timer {
        id: artRefreshTimer
        interval: 300
        repeat: false
        onTriggered: {
            // Refresh the artwork without touching playback. Pausing and then
            // calling Play() a few ms later used to force players to re-publish
            // their artUrl, but some clients (Spotify, for one) ignore a Play()
            // that arrives right after a Pause() and stay paused, so playback
            // stopped on every track change.
            root._lastSampledUrl = ""
            _artDebounceTimer.restart()
            _resampleTimer.restart()
        }
    }

    function _scheduleArtRefresh() {
        if (!plasmoid.configuration.artRefreshEnabled) return
        artRefreshTimer.stop()
        if (root.isPlaying) artRefreshTimer.start()
    }

    function togglePlaying() {
        if (root._bcConnected) {
            bitChordBridge.togglePlay()
            return
        }
        if (!root._activePlayer) return
        root._activePlayer.PlayPause()
    }
    function next() {
        if (root._bcConnected) {
            root._flipDirection = -1
            bitChordBridge.nextTrack()
            return
        }
        if (!root._activePlayer) return
        root._flipDirection = -1
        root._activePlayer.Next()
    }
    function previous() {
        if (root._bcConnected) {
            root._flipDirection = 1
            bitChordBridge.previousTrack()
            return
        }
        if (!root._activePlayer) return
        root._flipDirection = 1
        root._activePlayer.Previous()
    }
    function seek(positionUs) {
        if (!root._bcConnected && !root._activePlayer) return
        root.isSeeking = true
        root.targetSeekPos = positionUs
        seekWatchdogTimer.restart()
        if (positionUs >= 0) {
            root.position = positionUs
            root._lastPosTick = Date.now()
        }

        if (root._bcConnected) {
            bitChordBridge.seek(Math.round(Math.max(0, positionUs) / 1000.0))
            return
        }

        var posSec = positionUs / 1000000.0
        if (typeof root.backend !== "undefined" && root.backend && typeof root.backend.seekRequested === "function") {
            root.backend.seekRequested(posSec)
        } else if (typeof root._activePlayer.seekRequested === "function") {
            root._activePlayer.seekRequested(posSec)
        } else if (typeof root._activePlayer.setPlaybackPosition === "function") {
            root._activePlayer.setPlaybackPosition(posSec)
        } else if (typeof root._activePlayer.setPlaybackPositionUs === "function") {
            root._activePlayer.setPlaybackPositionUs(positionUs)
        } else if (typeof root._activePlayer.SetPosition === "function") {
            root._activePlayer.SetPosition("", positionUs)
        } else {
            var currentPos = root._activePlayer.position ?? root.position
            root._activePlayer.Seek(positionUs - currentPos)
        }
    }

    function formatTime(us) {
        var totalSec = Math.floor(us / 1000000)
        var h = Math.floor(totalSec / 3600)
        var m = Math.floor((totalSec % 3600) / 60)
        var s = totalSec % 60
        var ss = s < 10 ? "0" + s : "" + s
        if (h > 0) return h + ":" + (m < 10 ? "0" + m : m) + ":" + ss
        return m + ":" + ss
    }

    // ── Album art color sampling ────────────────────────────────────────
    property color _sampledTint: "#000000"
    property color _sampledGradientTop: "#1A1B1E"
    property color _sampledGradientBottom: "#0E0F11"
    property color _sampledPrimaryColor: "#ffffff"
    property bool _hasSampledColor: false
    property bool _sampledIsDark: true

    function _hslToRgb(h, s, l) {
        var c = (1 - Math.abs(2 * l - 1)) * s
        var x = c * (1 - Math.abs((h * 6) % 2 - 1))
        var m = l - c / 2
        var r, g, b
        switch (Math.floor(h * 6) % 6) {
            case 0: r = c; g = x; b = 0; break
            case 1: r = x; g = c; b = 0; break
            case 2: r = 0; g = c; b = x; break
            case 3: r = 0; g = x; b = c; break
            case 4: r = x; g = 0; b = c; break
            case 5: r = c; g = 0; b = x; break
        }
        return Qt.rgba(r + m, g + m, b + m, 1.0)
    }

    function _rgbToHsl(r, g, b) {
        var mx = Math.max(r, g, b), mn = Math.min(r, g, b)
        var l = (mx + mn) / 2, s = 0, h = 0
        if (mx !== mn) {
            var dd = mx - mn
            s = l > 0.5 ? dd / (2 - mx - mn) : dd / (mx + mn)
            if (mx === r)      h = ((g - b) / dd + (g < b ? 6 : 0)) / 6
            else if (mx === g) h = ((b - r) / dd + 2) / 6
            else               h = ((r - g) / dd + 4) / 6
        }
        return { h: h, s: s, l: l }
    }

    property string _lastSampledUrl: ""

    onAlbumArtChanged: {
        if (albumArt !== "") {
            sampleCanvas.loadImage(albumArt)
        } else {
            _hasSampledColor = false
            _sampledTint = "#000000"
            _sampledGradientTop = "#1A1B1E"
            _sampledGradientBottom = "#0E0F11"
            _sampledPrimaryColor = "#ffffff"
            _sampledIsDark = true
            _lastSampledUrl = ""
        }
    }

    Canvas {
        id: sampleCanvas
        width: 64
        height: 64
        visible: true
        opacity: 0

        Component.onCompleted: {
            if (root.albumArt !== "") loadImage(root.albumArt)
        }

        onImageLoaded: {
            if (root.albumArt !== "" && root.albumArt !== root._lastSampledUrl) {
                root._lastSampledUrl = root.albumArt
                _resampleTimer.stop()
                requestPaint()
            }
        }

        onPaint: {
            var url = root.albumArt
            if (!url || !isImageLoaded(url)) return

            var ctx = getContext("2d")
            ctx.reset()
            ctx.drawImage(url, 0, 0, 64, 64)

            var imgData = ctx.getImageData(0, 0, 64, 64)
            var d = imgData.data
            var pixels = []
            for (var i = 0; i < d.length; i += 4) {
                if (d[i+3] < 128) continue
                pixels.push([d[i], d[i+1], d[i+2]])
            }
            if (pixels.length === 0) return

            function medianCut(px, depth) {
                if (depth === 0 || px.length === 0) {
                    var rS = 0, gS = 0, bS = 0
                    for (var j = 0; j < px.length; j++) {
                        rS += px[j][0]; gS += px[j][1]; bS += px[j][2]
                    }
                    var n = px.length || 1
                    return [{ r: rS/n/255, g: gS/n/255, b: bS/n/255, count: px.length }]
                }

                var rMin = 255, rMax = 0, gMin = 255, gMax = 0, bMin = 255, bMax = 0
                for (var j = 0; j < px.length; j++) {
                    var p = px[j]
                    if (p[0] < rMin) rMin = p[0]; if (p[0] > rMax) rMax = p[0]
                    if (p[1] < gMin) gMin = p[1]; if (p[1] > gMax) gMax = p[1]
                    if (p[2] < bMin) bMin = p[2]; if (p[2] > bMax) bMax = p[2]
                }
                var rR = rMax - rMin, gR = gMax - gMin, bR = bMax - bMin
                var ch = rR >= gR && rR >= bR ? 0 : (gR >= bR ? 1 : 2)

                px.sort(function(a, b) { return a[ch] - b[ch] })
                var mid = Math.floor(px.length / 2)

                return medianCut(px.slice(0, mid), depth - 1)
                       .concat(medianCut(px.slice(mid), depth - 1))
            }

            var buckets = medianCut(pixels, 3)

            var accentIdx = 0, maxSat = -1
            for (var i = 0; i < buckets.length; i++) {
                var hsl = root._rgbToHsl(buckets[i].r, buckets[i].g, buckets[i].b)
                buckets[i].h = hsl.h; buckets[i].s = hsl.s; buckets[i].l = hsl.l
                buckets[i].lum = 0.299 * buckets[i].r + 0.587 * buckets[i].g + 0.114 * buckets[i].b
                var score = hsl.s * (0.3 + 0.7 * (1 - Math.abs(2 * hsl.l - 1)))
                if (score > maxSat) { maxSat = score; accentIdx = i }
            }

            var sorted = buckets.slice().sort(function(a, b) { return b.count - a.count })
            var dominant = sorted[0]
            var secondary = sorted.length > 1 ? sorted[1] : sorted[0]
            var accent = buckets[accentIdx]

            var avgSat = 0
            for (var j = 0; j < buckets.length; j++)
                avgSat += buckets[j].s
            avgSat /= buckets.length
            var isMono = avgSat < 0.12

            if (isMono) {
                root._sampledTint = root._hslToRgb(0, 0, Math.min(dominant.l, 0.30))
                root._sampledGradientTop = root._hslToRgb(0, 0, 0.15 + dominant.l * 0.35)
                root._sampledGradientBottom = root._hslToRgb(0, 0, 0.06 + dominant.l * 0.20)
                root._sampledPrimaryColor = Qt.rgba(1, 1, 1, 1)
            } else {
                root._sampledTint = root._hslToRgb(accent.h,
                    Math.min(accent.s, 0.5),
                    Math.min(accent.l, 0.30))
                root._sampledGradientTop = root._hslToRgb(dominant.h,
                    Math.max(dominant.s, 0.30),
                    0.15 + dominant.l * 0.35)
                root._sampledGradientBottom = root._hslToRgb(
                    secondary.h !== dominant.h ? secondary.h : dominant.h,
                    Math.max(secondary.s, 0.25),
                    0.06 + secondary.l * 0.20)
                root._sampledPrimaryColor = root._hslToRgb(accent.h,
                    Math.max(accent.s, 0.55),
                    Math.max(accent.l, 0.75))
            }

            // The generated solid gradient is deliberately dark even when
            // the source cover is bright, so its content must stay light.
            root._sampledIsDark = true
            root._hasSampledColor = true
        }
    }


    // ── UI ─────────────────────────────────────────────────────────────────

    fullRepresentation: Item {
        id: full
        Layout.preferredWidth:  full.width  > 0 ? full.width  : 440
        Layout.preferredHeight: full.height > 0 ? full.height : 220
        Layout.minimumWidth: 80
        Layout.minimumHeight: 60

        readonly property real _ar: full.width / Math.max(1, full.height)
        readonly property string _layout:
            _ar >= 3.0  ? "bar"
          : _ar >= 1.6  ? "wide"
          : _ar <= 0.85 && full.height >= full.width * 1.55 ? "tallwide"
          :               "square"

        LiquidGlass {
            id: glass
            visibilitySource: root
            anchors.fill: parent
            radius: plasmoid.configuration.cornerRadius
            roundness: plasmoid.configuration.roundnessX10 / 10
            refractThickness: plasmoid.configuration.refractThickness
            refractIOR: plasmoid.configuration.refractIORx100 / 100
            refractScale: plasmoid.configuration.refractScale
            tint: colors.isGlass && root._hasSampledColor ? root._sampledTint : colors.glassTint
            tintAlpha: colors.isGlass && root._hasSampledColor
                ? Math.max(plasmoid.configuration.tintAlphaPct / 100, 0.15)
                : plasmoid.configuration.tintAlphaPct / 100
            chromaStrength: plasmoid.configuration.chromaStrengthPct / 100
            specStrength: plasmoid.configuration.specStrengthPct / 100
            blurRadius: plasmoid.configuration.blurRadiusPx
            blurAlgorithm: plasmoid.configuration.blurAlgorithm
            realtimeRefraction: plasmoid.configuration.realtimeRefraction
            fallbackOpacity: colors.glassFallbackOpacity
            solidMode: colors.isSolid
            solidColor: colors.isSolid && root._hasSampledColor ? root._sampledGradientTop : colors.solidBackground
            solidColorBottom: colors.isSolid && root._hasSampledColor ? root._sampledGradientBottom : "transparent"
            overlayDarken: root.lyricsActive && full._layout === "tallwide"
                ? Qt.vector4d(root._sampledGradientBottom.r, root._sampledGradientBottom.g, root._sampledGradientBottom.b, 0.55)
                : Qt.vector4d(0, 0, 0, 0)
        }

        Loader {
            id: activeLayout
            anchors.fill: parent
            sourceComponent: full._layout === "square" ? squareLayoutComponent
                           : full._layout === "tallwide" ? tallWideLayoutComponent
                           : full._layout === "wide" ? wideLayoutComponent
                           : barLayoutComponent
        }

        Component {
            id: squareLayoutComponent
            SquareLayout {
                anchors.fill: parent
                colors: root.colorTokens
                cornerRadius: plasmoid.configuration.cornerRadius
                roundness: plasmoid.configuration.roundnessX10 / 10
                fontFamily: sfRegular.name
                fontFamilyThin: sfThin.name
                track: root.track
                artist: root.artist
                albumArt: root.albumArt
                isPlaying: root.isPlaying
                canGoPrevious: root.canGoPrevious
                canGoNext: root.canGoNext
                canPlay: root.canPlay
                canPause: root.canPause
                position: (root.length > 0 && root.position > root.length) ? root.length : (root.isSeeking ? root.targetSeekPos : root.position)
                length: root.length
                canSeek: root.canSeek
                onTogglePlaying: root.togglePlaying()
                onNextTrack: root.next()
                onPreviousTrack: root.previous()
                onSeek: function(pos) { root.seek(pos) }
                formatTime: root.formatTime
            }
        }

        Component {
            id: tallWideLayoutComponent
            TallWideLayout {
                anchors.fill: parent
                colors: root.colorTokens
                accentColor: root._hasSampledColor ? root._sampledPrimaryColor : root.colorTokens.foreground
                lyricsAccentColor: root._hasSampledColor ? root._sampledTint : Qt.rgba(1, 1, 1, 0.35)
                flipDirection: root._flipDirection
                lyricsActive: root.lyricsActive
                onToggleLyrics: root.lyricsActive = !root.lyricsActive
                syncedLyrics: root._syncedLyrics
                plainLyrics: root._plainLyrics
                lyricsState: root._lyricsState
                lyricsOffsetMs: root.lyricsOffsetMs
                lyricsPositionMs: ((((root.length > 0 && root.position > root.length) ? root.length : (root.isSeeking ? root.targetSeekPos : root.position))) / 1000) + root.lyricsOffsetMs
                lyricsBlur: plasmoid.configuration.lyricsBlur
                showTrackTitleInLyrics: plasmoid.configuration.showTrackTitleInLyrics
                lyricsActiveOpacity: plasmoid.configuration.lyricsActiveOpacity / 100
                lyricsInactiveOpacity: plasmoid.configuration.lyricsInactiveOpacity / 100
                lyricsFontSizeFactor: plasmoid.configuration.lyricsFontSizeTall / 1000
                fontFamily: sfRegular.name
                fontFamilyThin: sfThin.name
                track: root.track
                artist: root.artist
                albumArt: root.albumArt
                isPlaying: root.isPlaying
                canGoPrevious: root.canGoPrevious
                canGoNext: root.canGoNext
                canPlay: root.canPlay
                canPause: root.canPause
                position: (root.length > 0 && root.position > root.length) ? root.length : (root.isSeeking ? root.targetSeekPos : root.position)
                length: root.length
                canSeek: root.canSeek
                onTogglePlaying: root.togglePlaying()
                onNextTrack: root.next()
                onPreviousTrack: root.previous()
                onSeek: function(pos) { root.seek(pos) }
                onRetryLyrics: root._fetchLyrics()
                formatTime: root.formatTime
            }
        }

        Component {
            id: wideLayoutComponent
            WideLayout {
                anchors.fill: parent
                colors: root.colorTokens
                accentColor: root._hasSampledColor ? root._sampledPrimaryColor : root.colorTokens.foreground
                lyricsAccentColor: root._hasSampledColor ? root._sampledTint : Qt.rgba(1, 1, 1, 0.35)
                flipDirection: root._flipDirection
                lyricsActive: root.lyricsActive
                onToggleLyrics: root.lyricsActive = !root.lyricsActive
                syncedLyrics: root._syncedLyrics
                plainLyrics: root._plainLyrics
                lyricsState: root._lyricsState
                lyricsOffsetMs: root.lyricsOffsetMs
                lyricsPositionMs: ((((root.length > 0 && root.position > root.length) ? root.length : (root.isSeeking ? root.targetSeekPos : root.position))) / 1000) + root.lyricsOffsetMs
                lyricsBlur: plasmoid.configuration.lyricsBlur
                showTrackTitleInLyrics: plasmoid.configuration.showTrackTitleInLyrics
                lyricsActiveOpacity: plasmoid.configuration.lyricsActiveOpacity / 100
                lyricsInactiveOpacity: plasmoid.configuration.lyricsInactiveOpacity / 100
                lyricsFontSizeFactor: plasmoid.configuration.lyricsFontSizeWide / 1000
                fontFamily: sfRegular.name
                fontFamilyThin: sfThin.name
                track: root.track
                artist: root.artist
                albumArt: root.albumArt
                isPlaying: root.isPlaying
                canGoPrevious: root.canGoPrevious
                canGoNext: root.canGoNext
                canPlay: root.canPlay
                canPause: root.canPause
                position: (root.length > 0 && root.position > root.length) ? root.length : (root.isSeeking ? root.targetSeekPos : root.position)
                length: root.length
                canSeek: root.canSeek
                onTogglePlaying: root.togglePlaying()
                onNextTrack: root.next()
                onPreviousTrack: root.previous()
                onSeek: function(pos) { root.seek(pos) }
                onRetryLyrics: root._fetchLyrics()
                formatTime: root.formatTime
            }
        }

        Component {
            id: barLayoutComponent
            BarLayout {
                anchors.fill: parent
                colors: root.colorTokens
                accentColor: root._hasSampledColor ? root._sampledPrimaryColor : root.colorTokens.foreground
                cornerRadius: plasmoid.configuration.cornerRadius
                flipDirection: root._flipDirection
                fontFamily: sfRegular.name
                fontFamilyThin: sfThin.name
                track: root.track
                artist: root.artist
                albumArt: root.albumArt
                isPlaying: root.isPlaying
                canGoPrevious: root.canGoPrevious
                canGoNext: root.canGoNext
                canPlay: root.canPlay
                canPause: root.canPause
                position: (root.length > 0 && root.position > root.length) ? root.length : (root.isSeeking ? root.targetSeekPos : root.position)
                length: root.length
                canSeek: root.canSeek
                onTogglePlaying: root.togglePlaying()
                onNextTrack: root.next()
                onPreviousTrack: root.previous()
                onSeek: function(pos) { root.seek(pos) }
                formatTime: root.formatTime
            }
        }
    }
}
