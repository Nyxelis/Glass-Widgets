import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: hostRoot
    implicitWidth: widgetLoader.item && widgetLoader.item.implicitWidth > 0 ? widgetLoader.item.implicitWidth : 300
    implicitHeight: widgetLoader.item && widgetLoader.item.implicitHeight > 0 ? widgetLoader.item.implicitHeight : 300

    property string widgetName: "Widget"
    property string widgetPackage: ""
    property string widgetQmlSource: ""
    property bool editMode: false
    property real widgetScale: 1.0
    property real widgetRotation: 0
    property int gridSnap: 16
    property bool isLocked: false

    // --- Wallpaper Refraction Containment Pipeline ---
    Item {
        id: wallpaperContainment
        anchors.fill: parent

        Image {
            id: wallpaperItem
            objectName: "wallpaperItem"
            x: -windowController.screenRelativeX
            y: -windowController.screenRelativeY
            width: windowController.screenWidth
            height: windowController.screenHeight
            source: hostRoot.visible ? wallpaperBackend.wallpaperUrl : ""
            sourceSize.width: windowController.screenWidth
            sourceSize.height: windowController.screenHeight
            cache: false
            smooth: true
            fillMode: Image.PreserveAspectCrop

            onStatusChanged: {
                if (status === Image.Ready) {
                    if (Plasmoid && Plasmoid.containment) {
                        if (typeof Plasmoid.containment.notifyWallpaperChanged === "function") {
                            Plasmoid.containment.notifyWallpaperChanged()
                        } else {
                            Plasmoid.containment.wallpaperChanged()
                        }
                    }
                }
            }
        }
    }

    Connections {
        target: wallpaperBackend
        function onWallpaperChanged() {
            wallpaperItem.source = ""
            if (hostRoot.visible)
                wallpaperItem.source = wallpaperBackend.wallpaperUrl
        }
    }

    onVisibleChanged: {
        if (!visible) {
            wallpaperItem.source = ""
        } else if (wallpaperItem.source === "") {
            wallpaperItem.source = wallpaperBackend.wallpaperUrl
        }
    }

    Component.onDestruction: {
        wallpaperItem.source = ""
        widgetLoader.source = ""
    }

    // --- Actual Upstream Widget Instance ---
    Item {
        id: contentContainer
        anchors.fill: parent
        anchors.margins: editMode ? 6 : 0
        rotation: hostRoot.widgetRotation
        transformOrigin: Item.Center

        Loader {
            id: widgetLoader
            objectName: "widgetLoader"
            anchors.fill: parent
            source: hostRoot.widgetQmlSource

            onLoaded: {
                if (item) {
                    item.width = Qt.binding(() => widgetLoader.width)
                    item.height = Qt.binding(() => widgetLoader.height)
                }
                if (Plasmoid && Plasmoid.containment) {
                    Plasmoid.containment.wallpaperGraphicsObject = wallpaperItem
                }
            }
        }
    }

    Component.onCompleted: {
        if (Plasmoid && Plasmoid.containment) {
            Plasmoid.containment.wallpaperGraphicsObject = wallpaperItem
        }
    }

    // --- Right-click trigger for context menu without blocking hover ---
    TapHandler {
        acceptedButtons: Qt.RightButton
        onTapped: (point) => windowController.showContextMenu(point.position.x, point.position.y)
    }

    // --- Improved On-the-Fly Adjustments Box ---
    Rectangle {
        id: editBorder
        anchors.fill: parent
        visible: hostRoot.editMode
        color: "transparent"
        border.color: "#3b82f6cc"
        border.width: 1.5
        radius: 20

        // Live geometry HUD at bottom
        Rectangle {
            anchors.bottom: parent.bottom
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottomMargin: 8
            height: 20
            width: hudText.implicitWidth + 16
            radius: 10
            color: "#18181bee"
            border.color: "#3f3f4680"
            border.width: 1
            z: 20

            Text {
                id: hudText
                anchors.centerIn: parent
                text: Math.round(hostRoot.width) + " × " + Math.round(hostRoot.height) + " px"
                color: "#93c5fd"
                font.pixelSize: 10
                font.bold: true
            }
        }

        // Top Floating Glass Control Capsule
        Rectangle {
            id: topBar
            height: 32
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.margins: 6
            color: "#18181bf0"
            border.color: "#3f3f46aa"
            border.width: 1
            radius: 16
            z: 10

            // Drag window across whole bar
            MouseArea {
                id: dragArea
                anchors.fill: parent
                cursorShape: Qt.SizeAllCursor
                z: 0

                onPressed: windowController.startDrag()
                onPositionChanged: (mouse) => {
                    if (pressed) windowController.updateDrag(hostRoot.gridSnap)
                }
            }

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 10
                anchors.rightMargin: 10
                spacing: 8

                // Accent dot + Title
                Rectangle {
                    width: 7; height: 7; radius: 3.5
                    color: "#3b82f6"
                }

                Text {
                    text: hostRoot.widgetName.replace("Glass ", "").replace("macOS ", "")
                    color: "#ffffff"
                    font.bold: true
                    font.pixelSize: 11
                    elide: Text.ElideRight
                    Layout.maximumWidth: 100
                }

                // Timezone quick badge for clock widgets
                Rectangle {
                    visible: windowController.isClockWidget
                    height: 20
                    width: tzRow.implicitWidth + 10
                    radius: 10
                    color: tzMouse.containsMouse ? "#3b82f6" : "#27272a"
                    border.color: "#3f3f46"
                    border.width: 1

                    Row {
                        id: tzRow
                        anchors.centerIn: parent
                        spacing: 3
                        Text { text: "🌐"; font.pixelSize: 9 }
                        Text {
                            text: {
                                var tz = windowController.currentTimezone;
                                if (!tz) return "Local";
                                var bar = tz.indexOf("|");
                                var lbl = bar >= 0 ? tz.slice(bar + 1).trim() : "";
                                if (lbl) return lbl;
                                var id = (bar >= 0 ? tz.slice(0, bar) : tz).trim();
                                var parts = id.split("/");
                                return parts[parts.length - 1].replace("_", " ").slice(0, 4);
                            }
                            color: "#ffffff"
                            font.pixelSize: 10
                            font.bold: true
                        }
                    }

                    MouseArea {
                        id: tzMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: windowController.promptCustomTimezone()
                    }
                }

                // Location quick badge for weather widgets
                Rectangle {
                    visible: windowController.isWeatherWidget
                    height: 20
                    width: wBadgeRow.implicitWidth + 10
                    radius: 10
                    color: wBadgeMouse.containsMouse ? "#3b82f6" : "#27272a"
                    border.color: "#3f3f46"
                    border.width: 1

                    Row {
                        id: wBadgeRow
                        anchors.centerIn: parent
                        spacing: 3
                        Text { text: "☀️"; font.pixelSize: 9 }
                        Text {
                            text: typeof weatherBackend !== "undefined" && weatherBackend ? weatherBackend.locationName.split(",")[0].slice(0, 8) : "Weather"
                            color: "#ffffff"
                            font.pixelSize: 10
                            font.bold: true
                        }
                    }

                    MouseArea {
                        id: wBadgeMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: windowController.showContextMenu(x, y)
                    }
                }

                Item { Layout.fillWidth: true }

                // Quick Size Morph Chips (1x1, 2x1)
                Row {
                    spacing: 4
                    Rectangle {
                        width: 28; height: 18; radius: 9
                        color: btn1x1.containsMouse ? "#3b82f6" : "#27272a"
                        Text { text: "1×1"; color: "#fff"; anchors.centerIn: parent; font.pixelSize: 9; font.bold: true }
                        MouseArea {
                            id: btn1x1
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: windowController.setPresetSize(300, 300)
                        }
                    }
                    Rectangle {
                        width: 28; height: 18; radius: 9
                        color: btn2x1.containsMouse ? "#3b82f6" : "#27272a"
                        Text { text: "2×1"; color: "#fff"; anchors.centerIn: parent; font.pixelSize: 9; font.bold: true }
                        MouseArea {
                            id: btn2x1
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: windowController.setPresetSize(640, 300)
                        }
                    }
                }

                // Scale Adjuster: [-] 100% [+]
                Row {
                    spacing: 3
                    Rectangle {
                        width: 18; height: 18; radius: 9
                        color: sMinus.containsMouse ? "#3f3f46" : "#27272a"
                        Text { text: "−"; color: "#fff"; anchors.centerIn: parent; font.pixelSize: 11; font.bold: true }
                        MouseArea {
                            id: sMinus
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: windowController.changeScale(-0.1)
                        }
                    }
                    Text {
                        text: Math.round(hostRoot.widgetScale * 100) + "%"
                        color: "#d4d4d8"
                        font.pixelSize: 10
                        font.bold: true
                        anchors.verticalCenter: parent.verticalCenter
                    }
                    Rectangle {
                        width: 18; height: 18; radius: 9
                        color: sPlus.containsMouse ? "#3f3f46" : "#27272a"
                        Text { text: "+"; color: "#fff"; anchors.centerIn: parent; font.pixelSize: 11; font.bold: true }
                        MouseArea {
                            id: sPlus
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: windowController.changeScale(0.1)
                        }
                    }
                }

                // Close Button (macOS style circle)
                Rectangle {
                    width: 16; height: 16; radius: 8
                    color: closeArea.containsMouse ? "#ef4444" : "#dc2626"
                    Text { text: "✕"; color: "#fff"; anchors.centerIn: parent; font.pixelSize: 8; font.bold: true }
                    MouseArea {
                        id: closeArea
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: windowController.closeWidget()
                    }
                }
            }
        }

        // --- Central Body Drag Surface (allows moving widget by clicking anywhere on it in Edit Mode) ---
        MouseArea {
            id: bodyDragArea
            anchors.fill: parent
            anchors.topMargin: 42
            anchors.bottomMargin: 30
            anchors.leftMargin: 16
            anchors.rightMargin: 16
            cursorShape: Qt.SizeAllCursor
            z: 2
            onPressed: windowController.startDrag()
            onPositionChanged: (mouse) => {
                if (pressed) windowController.updateDrag(hostRoot.gridSnap)
            }
        }

        // --- Visible 8-Direction Handle Grips ---
        // Top-Left Corner Handle
        Rectangle {
            width: tlArea.containsMouse ? 14 : 10; height: tlArea.containsMouse ? 14 : 10
            radius: width / 2
            color: "#ffffff"
            border.color: "#3b82f6"
            border.width: 2
            anchors.top: parent.top; anchors.left: parent.left
            anchors.margins: -4
            z: 15
            Behavior on width { NumberAnimation { duration: 100 } }
            Behavior on height { NumberAnimation { duration: 100 } }
        }
        MouseArea {
            id: tlArea
            width: 24; height: 24; anchors.top: parent.top; anchors.left: parent.left
            cursorShape: Qt.SizeFDiagCursor
            hoverEnabled: true
            z: 16
            onPressed: windowController.startResize("top-left")
            onPositionChanged: (mouse) => {
                if (pressed) windowController.updateResize(hostRoot.gridSnap)
            }
        }

        // Top-Right Corner Handle
        Rectangle {
            width: trArea.containsMouse ? 14 : 10; height: trArea.containsMouse ? 14 : 10
            radius: width / 2
            color: "#ffffff"
            border.color: "#3b82f6"
            border.width: 2
            anchors.top: parent.top; anchors.right: parent.right
            anchors.margins: -4
            z: 15
            Behavior on width { NumberAnimation { duration: 100 } }
            Behavior on height { NumberAnimation { duration: 100 } }
        }
        MouseArea {
            id: trArea
            width: 24; height: 24; anchors.top: parent.top; anchors.right: parent.right
            cursorShape: Qt.SizeBDiagCursor
            hoverEnabled: true
            z: 16
            onPressed: windowController.startResize("top-right")
            onPositionChanged: (mouse) => {
                if (pressed) windowController.updateResize(hostRoot.gridSnap)
            }
        }

        // Bottom-Left Corner Handle
        Rectangle {
            width: blArea.containsMouse ? 14 : 10; height: blArea.containsMouse ? 14 : 10
            radius: width / 2
            color: "#ffffff"
            border.color: "#3b82f6"
            border.width: 2
            anchors.bottom: parent.bottom; anchors.left: parent.left
            anchors.margins: -4
            z: 15
            Behavior on width { NumberAnimation { duration: 100 } }
            Behavior on height { NumberAnimation { duration: 100 } }
        }
        MouseArea {
            id: blArea
            width: 24; height: 24; anchors.bottom: parent.bottom; anchors.left: parent.left
            cursorShape: Qt.SizeBDiagCursor
            hoverEnabled: true
            z: 16
            onPressed: windowController.startResize("bottom-left")
            onPositionChanged: (mouse) => {
                if (pressed) windowController.updateResize(hostRoot.gridSnap)
            }
        }

        // Bottom-Right Corner Handle
        Rectangle {
            width: brArea.containsMouse ? 14 : 10; height: brArea.containsMouse ? 14 : 10
            radius: width / 2
            color: "#ffffff"
            border.color: "#3b82f6"
            border.width: 2
            anchors.bottom: parent.bottom; anchors.right: parent.right
            anchors.margins: -4
            z: 15
            Behavior on width { NumberAnimation { duration: 100 } }
            Behavior on height { NumberAnimation { duration: 100 } }
        }
        MouseArea {
            id: brArea
            width: 24; height: 24; anchors.bottom: parent.bottom; anchors.right: parent.right
            cursorShape: Qt.SizeFDiagCursor
            hoverEnabled: true
            z: 16
            onPressed: windowController.startResize("bottom-right")
            onPositionChanged: (mouse) => {
                if (pressed) windowController.updateResize(hostRoot.gridSnap)
            }
        }

        // Edge Handles: Left
        MouseArea {
            width: 12; anchors.top: parent.top; anchors.bottom: parent.bottom; anchors.left: parent.left
            anchors.margins: 14
            cursorShape: Qt.SizeHorCursor
            z: 14
            onPressed: windowController.startResize("left")
            onPositionChanged: (mouse) => {
                if (pressed) windowController.updateResize(hostRoot.gridSnap)
            }
        }
        // Edge Handles: Right
        MouseArea {
            width: 12; anchors.top: parent.top; anchors.bottom: parent.bottom; anchors.right: parent.right
            anchors.margins: 14
            cursorShape: Qt.SizeHorCursor
            z: 14
            onPressed: windowController.startResize("right")
            onPositionChanged: (mouse) => {
                if (pressed) windowController.updateResize(hostRoot.gridSnap)
            }
        }
        // Edge Handles: Top
        MouseArea {
            height: 12; anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
            anchors.margins: 14
            cursorShape: Qt.SizeVerCursor
            z: 14
            onPressed: windowController.startResize("top")
            onPositionChanged: (mouse) => {
                if (pressed) windowController.updateResize(hostRoot.gridSnap)
            }
        }
        // Edge Handles: Bottom
        MouseArea {
            height: 12; anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
            anchors.margins: 14
            cursorShape: Qt.SizeVerCursor
            z: 14
            onPressed: windowController.startResize("bottom")
            onPositionChanged: (mouse) => {
                if (pressed) windowController.updateResize(hostRoot.gridSnap)
            }
        }
    }
}
