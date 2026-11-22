import QtQuick
import QtQuick.Effects
import "../components"

Item {
    id: lv

    required property QtObject colors
    property var syncedLyrics: []
    property string plainLyrics: ""
    property int lyricsState: 0
    property real currentPositionMs: 0
    property string fontFamily: ""
    property real baseFontSize: 20
    property bool blurEnabled: true
    property real activeOpacity: 1.0
    property real inactiveOpacity: 0.40
    readonly property real activeScale: 1.05
    property var backend: null

    signal seekTo(real positionUs)
    signal retryLyrics()

    readonly property int _currentIndex: {
        var adj = currentPositionMs + 200
        var idx = -1
        for (var i = 0; i < syncedLyrics.length; i++) {
            if (syncedLyrics[i].timestamp <= adj) idx = i
            else break
        }
        return idx
    }

    property int _previousIndex: -2
    property bool _hasInitialScrolled: false
    property bool _isUserScrolling: false

    readonly property int _visibleCount: Math.max(3, Math.floor(height / (baseFontSize * 2.5)))

    on_CurrentIndexChanged: {
        if (_currentIndex === _previousIndex) return
        _previousIndex = _currentIndex

        if (_currentIndex < 0) return

        if (_isUserScrolling) {
            _isUserScrolling = false
            _snapBackTimer.stop()
        }

        if (!_hasInitialScrolled) {
            _hasInitialScrolled = true
            lyricsList.positionViewAtIndex(_currentIndex, ListView.Beginning)
            return
        }

        lyricsList.currentIndex = _currentIndex
    }

    onSyncedLyricsChanged: {
        _previousIndex = -2
        _hasInitialScrolled = false
        _isUserScrolling = false
    }

    Timer {
        id: _snapBackTimer
        interval: 2000
        onTriggered: {
            lv._isUserScrolling = false
            if (lv._currentIndex >= 0)
                lyricsList.currentIndex = lv._currentIndex
        }
    }

    // ── Synced lyrics ─────────────────────────────────────────────────────
    ListView {
        id: lyricsList
        anchors.fill: parent
        visible: lv.lyricsState === 2 && lv.syncedLyrics.length > 0
        clip: true
        spacing: Math.round(lv.baseFontSize * 0.15)
        topMargin: Math.round(lv.baseFontSize * 0.3)
        bottomMargin: Math.round(height * 0.7)
        model: lv.syncedLyrics.length
        cacheBuffer: Math.round(lv.baseFontSize * 2.5 * 3)
        boundsBehavior: Flickable.StopAtBounds
        highlightMoveDuration: 600
        highlightMoveVelocity: -1
        preferredHighlightBegin: 0
        preferredHighlightEnd: 0
        highlightRangeMode: ListView.StrictlyEnforceRange
        highlightFollowsCurrentItem: true
        highlight: Item {}

        onMovementStarted: {
            if (!lv._isUserScrolling) {
                lv._isUserScrolling = true
            }
        }
        onMovementEnded: {
            if (lv._isUserScrolling)
                _snapBackTimer.restart()
        }
        onFlickStarted: {
            if (!lv._isUserScrolling)
                lv._isUserScrolling = true
        }

        delegate: Item {
            id: del
            width: lyricsList.width
            height: bg.height

            property bool _clickedFlash: false
            Timer {
                id: flashTimer
                interval: 220
                onTriggered: del._clickedFlash = false
            }

            readonly property bool _isActive: index === lv._currentIndex
            readonly property bool _isInstrumental:
                (lv.syncedLyrics[index] ? lv.syncedLyrics[index].text : "") === ""

            readonly property int _dist: index - lv._currentIndex
            readonly property bool _inRange: Math.abs(_dist) <= lv._visibleCount + 3

            readonly property real _scrollDimOpacity: lv.inactiveOpacity * 0.6

            readonly property real _targetOpacity: {
                if (del._clickedFlash) return 1.0
                if (lv._isUserScrolling)
                    return _isActive ? lv.activeOpacity : _scrollDimOpacity

                if (!_inRange) return _dist < 0 ? 0 : lv.inactiveOpacity * 0.15

                if (_isActive) return lv.activeOpacity
                if (_dist < 0) return lv.inactiveOpacity * 0.25
                var frac = Math.min(1, _dist / lv._visibleCount)
                return lv.inactiveOpacity * (1 - frac * 0.85)
            }

            readonly property real _viewY: del.y - lyricsList.contentY
            readonly property bool _onScreen: _viewY >= 0 && _viewY < lyricsList.height
            readonly property real _blurFrac: lv.blurEnabled && _dist >= 2 && _onScreen && !lv._isUserScrolling
                ? Math.min(1, (_dist - 1) / (lv._visibleCount + 2))
                : 0
            readonly property bool _needsBlur: _blurFrac > 0.01

            Rectangle {
                id: bg
                width: parent.width
                height: lineText.implicitHeight + _vPad * 2
                radius: Math.round(height * 0.22)
                color: {
                    if (del._clickedFlash) return Qt.rgba(1, 1, 1, 0.35)
                    if (hoverArea.pressed) return Qt.rgba(1, 1, 1, 0.18)
                    if (hoverArea.containsMouse) return Qt.rgba(1, 1, 1, 0.09)
                    if (del._isActive) return Qt.rgba(1, 1, 1, 0.04)
                    return "transparent"
                }
                Behavior on color { ColorAnimation { duration: 120 } }

                readonly property real _activeScale: del._isActive ? lv.activeScale : 1.0
                readonly property real _pressScale: (hoverArea.pressed || del._clickedFlash) ? 0.97 : 1.0
                scale: _activeScale * _pressScale
                transformOrigin: Item.Left
                Behavior on scale { NumberAnimation { duration: 200; easing.type: Easing.OutCubic } }

                layer.enabled: _activeScale > 1.01 || del._needsBlur
                layer.smooth: true
                layer.textureSize: Qt.size(width * 2, height * 2)
                layer.effect: MultiEffect {
                    blurEnabled: del._needsBlur
                    blurMax: 48
                    blur: del._blurFrac * 0.7
                }

                readonly property real _vPad: Math.round(lv.baseFontSize * 0.45)
                readonly property real _hPad: Math.round(lv.baseFontSize * 0.6)

                Text {
                    id: lineText
                    x: bg._hPad
                    y: bg._vPad
                    width: bg.width - bg._hPad * 2
                    text: del._isInstrumental ? "♪  ♪  ♪" : lv.syncedLyrics[index].text
                    color: del._clickedFlash ? "#38bdf8" : (del._isActive ? "#ffffff" : Qt.rgba(1, 1, 1, 0.82))
                    font.pixelSize: lv.baseFontSize
                    font.weight: del._isActive ? Font.Bold : Font.DemiBold
                    font.family: lv.fontFamily
                    font.italic: del._isInstrumental
                    wrapMode: Text.WordWrap
                    Behavior on color { ColorAnimation { duration: 150 } }
                }
            }

            opacity: _targetOpacity
            Behavior on opacity { NumberAnimation { duration: 300; easing.type: Easing.OutCubic } }

            MouseArea {
                id: hoverArea
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                    del._clickedFlash = true
                    flashTimer.restart()
                    var lyricItem = (lv.syncedLyrics && index >= 0 && index < lv.syncedLyrics.length)
                        ? lv.syncedLyrics[index] : null
                    var rawTsMs = lyricItem ? (lyricItem.timestamp ?? 0) : 0
                    var timestamp = Number(rawTsMs) / 1000.0

                    console.log("[QML] Lyric clicked, sending:", timestamp)
                    console.log("[QML] Parsed lyric timestamp:", timestamp)
                    console.log("[QML] Sending seek request to backend:", timestamp)

                    var b = lv.backend ?? ((typeof backend !== "undefined" && backend) ? backend : null)
                    if (b && typeof b.seekRequested === "function") {
                        b.seekRequested(timestamp)
                    } else {
                        console.log("[QML] Direct backend not in scope, delegating via seekTo")
                    }
                    lv.seekTo(timestamp * 1000000.0)
                }
            }
        }
    }

    // ── Plain lyrics fallback ─────────────────────────────────────────────
    Flickable {
        anchors.fill: parent
        visible: lv.lyricsState === 2 && lv.syncedLyrics.length === 0 && lv.plainLyrics !== ""
        clip: true
        contentHeight: plainText.implicitHeight + 32
        flickableDirection: Flickable.VerticalFlick
        boundsBehavior: Flickable.StopAtBounds

        Text {
            id: plainText
            x: 16; y: 16
            width: parent.width - 32
            text: lv.plainLyrics
            color: "#ffffff"
            opacity: 0.85
            font.pixelSize: Math.round(lv.baseFontSize * 0.75)
            font.family: lv.fontFamily
            wrapMode: Text.WordWrap
            lineHeight: 1.6
        }
    }

    // ── Loading ───────────────────────────────────────────────────────────
    MacSpinner {
        anchors.centerIn: parent
        width: Math.round(Math.min(lv.width, lv.height) * 0.12)
        height: width
        running: lv.lyricsState === 1
        visible: lv.lyricsState === 1
        color: "#ffffff"
    }

    // ── Not found ─────────────────────────────────────────────────────────
    Text {
        anchors.centerIn: parent
        visible: lv.lyricsState === 4 || (lv.lyricsState === 2 && lv.syncedLyrics.length === 0 && lv.plainLyrics === "")
        text: i18n("No lyrics available")
        color: "#ffffff"
        opacity: 0.45
        font.pixelSize: Math.max(12, Math.round(lv.baseFontSize * 0.8))
        font.weight: Font.Medium
        font.family: lv.fontFamily
    }

    // ── Error (tap to retry) ──────────────────────────────────────────────
    Text {
        id: errorLabel
        anchors.centerIn: parent
        visible: lv.lyricsState === 3
        text: i18n("Couldn't load lyrics\nTap to retry")
        color: "#ffffff"
        opacity: 0.45
        horizontalAlignment: Text.AlignHCenter
        font.pixelSize: Math.max(12, Math.round(lv.baseFontSize * 0.8))
        font.weight: Font.Medium
        font.family: lv.fontFamily
    }

    MouseArea {
        anchors.fill: parent
        enabled: lv.lyricsState === 3
        onClicked: lv.retryLyrics()
        z: 5
    }
}
