import QtQuick
import QtQuick.Controls

Item {
    id: slider
    z: 10
    enabled: true

    property real position: 0
    property real length: 0
    property color fillColor: "#ffffff"
    property color trackColor: "#ffffff"
    property real trackOpacity: 0.20
    property color timeLabelColor: "#ffffff"
    property real timeLabelOpacity: 0.50
    property string fontFamily: ""
    property real fontSize: 10
    property bool showTimeLabels: true
    property bool canSeek: true
    property bool isSeeking: false
    property bool interactive: true
    property var formatTime: function(us) { return "" }

    signal seek(real positionUs)
    signal seekRequested(real seconds)
    signal moved(real value)
    signal released()

    implicitHeight: showTimeLabels ? (barArea.height + timeRow.height + 2) : barArea.height

    property real dragPosition: 0
    readonly property real displayPosition: {
        if (isSeeking) return dragPosition
        if (slider.length > 0 && slider.position > slider.length) return slider.length
        return Math.max(0, slider.position)
    }
    property bool _active: barMouse.containsMouse || isSeeking

    Connections {
        target: (typeof backend !== "undefined" && backend) ? backend : null
        function onSeekOccurred(newPosMs) {
            slider.isSeeking = false
        }
    }

    Item {
        id: barArea
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: 20
        z: 10

        Rectangle {
            id: track
            anchors.centerIn: parent
            width: parent.width
            height: slider._active ? 8 : 4
            radius: height / 2
            color: slider.trackColor
            opacity: slider.trackOpacity

            Behavior on height {
                NumberAnimation { duration: 150; easing.type: Easing.OutCubic }
            }
        }

        Rectangle {
            id: fill
            anchors.verticalCenter: track.verticalCenter
            anchors.left: track.left
            width: slider.length > 0 ? (track.width * Math.min(1, Math.max(0, slider.displayPosition / slider.length))) : 0
            height: track.height
            radius: height / 2
            color: slider.fillColor

            // Animated only during passive playback; instant 1:1 response during manual drag
            Behavior on width {
                enabled: !slider.isSeeking
                NumberAnimation { duration: 150; easing.type: Easing.OutCubic }
            }
        }

        MouseArea {
            id: barMouse
            anchors.fill: parent
            anchors.topMargin: -4
            anchors.bottomMargin: -4
            hoverEnabled: true
            cursorShape: slider.canSeek ? Qt.PointingHandCursor : Qt.ArrowCursor
            enabled: slider.enabled
            z: 10

            ToolTip.visible: barMouse.containsMouse && !slider.canSeek
            ToolTip.text: "Seek not supported by this app"
            ToolTip.delay: 200

            onPressed: function(mouse) {
                if (!slider.canSeek) return
                slider.isSeeking = true
                _updateDrag(mouse.x)
                console.log("[QML] Seek bar pressed at x:", mouse.x)
            }

            onPositionChanged: function(mouse) {
                if (pressed && slider.canSeek) {
                    _updateDrag(mouse.x)
                    slider.moved(slider.dragPosition / 1000000.0)
                }
            }

            onReleased: function(mouse) {
                if (!slider.canSeek) return
                slider.isSeeking = false
                var ratio = Math.max(0, Math.min(1, mouse.x / width))
                var targetUs = ratio * slider.length
                slider.dragPosition = targetUs
                slider.seek(targetUs)
                var targetSec = targetUs / 1000000.0
                slider.seekRequested(targetSec)
                slider.released()
            }

            function _updateDrag(mx) {
                var ratio = Math.max(0, Math.min(1, mx / width))
                slider.dragPosition = ratio * slider.length
            }
        }
    }

    Item {
        id: timeRow
        visible: slider.showTimeLabels
        anchors.top: barArea.bottom
        anchors.topMargin: 2
        anchors.left: parent.left
        anchors.right: parent.right
        height: currentLabel.height

        Text {
            id: currentLabel
            anchors.left: parent.left
            text: slider.formatTime(slider.displayPosition)
            color: slider.timeLabelColor
            opacity: slider.timeLabelOpacity
            font.family: slider.fontFamily
            font.pixelSize: slider.fontSize
            font.features: { "tnum": 1 }
        }

        Text {
            id: totalLabel
            anchors.right: parent.right
            text: (slider.length > 7200000000 || slider.length <= 0) ? "--:--" : slider.formatTime(slider.length)
            color: slider.timeLabelColor
            opacity: slider.timeLabelOpacity
            font.family: slider.fontFamily
            font.pixelSize: slider.fontSize
            font.features: { "tnum": 1 }
        }
    }
}
