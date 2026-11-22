import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

ApplicationWindow {
    id: mgrWindow
    title: "GlassWidgets Manager — Windows 11"
    width: 940
    height: 840
    minimumWidth: 720
    minimumHeight: 560
    visible: true
    flags: Qt.Window | Qt.FramelessWindowHint
    color: "#121214"

    Component.onCompleted: {
        console.log("[QML] MANAGER WINDOW LOADED Width: " + width + " Height: " + height)
    }

    onClosing: (close) => {
        close.accepted = false;
        mgrWindow.hide();
    }

    // Outer Main Card (Sleek Modern Dark Theme)
    Rectangle {
        id: mainCard
        anchors.fill: parent
        color: "#121214"
        border.color: "#282830"
        border.width: 1
        radius: 12
        clip: true

        // ── 1. Top Title Bar ──────────────────────────────────────────
        Rectangle {
            id: titleBar
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            height: 50
            color: "#18181c"
            border.color: "#26262e"
            border.width: 1
            z: 10

            // Draggable Window Handler
            MouseArea {
                anchors.fill: parent
                acceptedButtons: Qt.LeftButton
                z: 0
                onPressed: mgrWindow.startSystemMove()
                onDoubleClicked: {
                    if (mgrWindow.visibility === Window.Maximized) {
                        mgrWindow.showNormal()
                    } else {
                        mgrWindow.showMaximized()
                    }
                }
            }

            // Left Side: App Brand Icon & Product Name
            RowLayout {
                anchors.left: parent.left
                anchors.leftMargin: 16
                anchors.verticalCenter: parent.verticalCenter
                spacing: 10
                z: 2

                Rectangle {
                    width: 28
                    height: 28
                    radius: 7
                    color: "#0a84ff"

                    Text {
                        anchors.centerIn: parent
                        text: "❄"
                        color: "#ffffff"
                        font.pixelSize: 14
                    }
                }

                ColumnLayout {
                    spacing: 1
                    Text {
                        text: "GlassWidgets"
                        color: "#ffffff"
                        font.bold: true
                        font.pixelSize: 13
                    }
                    Text {
                        text: "Windows 11"
                        color: "#71717a"
                        font.pixelSize: 10
                    }
                }
            }

            // Center: App Title (Requirement 5)
            RowLayout {
                anchors.centerIn: parent
                z: 2
                Text {
                    text: "Desktop Widgets Manager"
                    color: "#f4f4f5"
                    font.bold: true
                    font.pixelSize: 13
                }
            }

            // Right Side: Quick Action Buttons & Window Controls
            RowLayout {
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                spacing: 8
                z: 2

                Button {
                    text: widgetManagerService.globalEditMode ? "🔒 Lock Layout" : "✏️ Move / Edit"
                    highlighted: widgetManagerService.globalEditMode
                    implicitHeight: 30
                    contentItem: Text {
                        text: parent.text
                        color: parent.highlighted ? "#ffffff" : "#e4e4e7"
                        font.pixelSize: 11
                        font.bold: parent.highlighted
                        verticalAlignment: Text.AlignVCenter
                        horizontalAlignment: Text.AlignHCenter
                    }
                    background: Rectangle {
                        radius: 6
                        color: parent.highlighted ? (parent.down ? "#005bb5" : (parent.hovered ? "#0071e3" : "#0a84ff"))
                                                  : (parent.down ? "#1c1c22" : (parent.hovered ? "#2e2e38" : "#24242c"))
                        border.color: parent.highlighted ? "#0a84ff" : (parent.hovered ? "#484856" : "#343440")
                        border.width: 1
                    }
                    onClicked: widgetManagerService.toggleGlobalEditMode()
                }

                Button {
                    text: "↺ Reset Positions"
                    implicitHeight: 30
                    contentItem: Text {
                        text: parent.text
                        color: "#e4e4e7"
                        font.pixelSize: 11
                        verticalAlignment: Text.AlignVCenter
                        horizontalAlignment: Text.AlignHCenter
                    }
                    background: Rectangle {
                        radius: 6
                        color: parent.down ? "#1c1c22" : (parent.hovered ? "#2e2e38" : "#24242c")
                        border.color: parent.hovered ? "#484856" : "#343440"
                        border.width: 1
                    }
                    onClicked: widgetManagerService.resetAllPositions()
                }

                Item { width: 4 } // Spacing before window controls

                // Windows Native Style Window Action Buttons
                Row {
                    // Minimize
                    Rectangle {
                        width: 46
                        height: titleBar.height
                        color: minMouse.containsMouse ? "#2a2a32" : "transparent"

                        Text {
                            anchors.centerIn: parent
                            text: "—"
                            color: "#e4e4e7"
                            font.pixelSize: 11
                        }

                        MouseArea {
                            id: minMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: mgrWindow.showMinimized()
                        }
                    }

                    // Maximize / Restore
                    Rectangle {
                        width: 46
                        height: titleBar.height
                        color: maxMouse.containsMouse ? "#2a2a32" : "transparent"

                        Text {
                            anchors.centerIn: parent
                            text: mgrWindow.visibility === Window.Maximized ? "🗗" : "🗖"
                            color: "#e4e4e7"
                            font.pixelSize: 11
                        }

                        MouseArea {
                            id: maxMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                if (mgrWindow.visibility === Window.Maximized) {
                                    mgrWindow.showNormal()
                                } else {
                                    mgrWindow.showMaximized()
                                }
                            }
                        }
                    }

                    // Close
                    Rectangle {
                        width: 48
                        height: titleBar.height
                        color: closeMouse.containsMouse ? "#e81123" : "transparent"

                        Text {
                            anchors.centerIn: parent
                            text: "✕"
                            color: closeMouse.containsMouse ? "#ffffff" : "#e4e4e7"
                            font.pixelSize: 11
                            font.bold: true
                        }

                        MouseArea {
                            id: closeMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: mgrWindow.hide()
                        }
                    }
                }
            }
        }

        // ── 2. Scrollable Content Area (Strictly Bound, No Left Clipping) ───
        ScrollView {
            id: mainScroll
            anchors.top: titleBar.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            clip: true
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
            ScrollBar.vertical.policy: ScrollBar.AsNeeded
            contentWidth: availableWidth

            Item {
                width: mainScroll.availableWidth
                implicitHeight: contentCol.implicitHeight + 40

                ColumnLayout {
                    id: contentCol
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.leftMargin: 20
                    anchors.rightMargin: 28 // Generous right margin so scrollbar NEVER overlaps cards or buttons
                    anchors.top: parent.top
                    anchors.topMargin: 18
                    spacing: 18

                    // ── SECTION 1: Global Settings Card ─────────────────────────
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        RowLayout {
                            spacing: 8
                            Text { text: "⚙️"; font.pixelSize: 14 }
                            Text {
                                text: "Global Settings"
                                color: "#ffffff"
                                font.bold: true
                                font.pixelSize: 14
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            radius: 12
                            color: "#18181d"
                            border.color: "#282830"
                            border.width: 1
                            implicitHeight: globalCardCol.implicitHeight + 32

                            ColumnLayout {
                                id: globalCardCol
                                anchors.fill: parent
                                anchors.margins: 16
                                spacing: 16

                                // Structured Row 1: Style, Snapping, and Add Calendar Event Button
                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 18

                                    // Style Mode
                                    RowLayout {
                                        spacing: 8
                                        Text { text: "Theme Style:"; color: "#a1a1aa"; font.pixelSize: 12 }
                                        ComboBox {
                                            id: styleModeCombo
                                            model: ["Glass Dark", "Glass Light", "Solid Dark", "Solid Light"]
                                            currentIndex: widgetManagerService.globalStyleMode
                                            Layout.preferredWidth: 130
                                            onActivated: (idx) => widgetManagerService.setGlobalStyleMode(idx)
                                        }
                                    }

                                    // Grid Snapping
                                    RowLayout {
                                        spacing: 8
                                        Text { text: "Snapping:"; color: "#a1a1aa"; font.pixelSize: 12 }
                                        ComboBox {
                                            id: snapCombo
                                            model: ["Off", "16 px", "24 px"]
                                            currentIndex: widgetManagerService.globalGridSnap === 0 ? 0 : (widgetManagerService.globalGridSnap === 16 ? 1 : 2)
                                            Layout.preferredWidth: 95
                                            onActivated: (idx) => {
                                                var snap = idx === 0 ? 0 : (idx === 1 ? 16 : 24)
                                                widgetManagerService.setGlobalGridSnap(snap)
                                            }
                                        }
                                    }

                                    Item { Layout.fillWidth: true }

                                    // Add Calendar Event Button
                                    Button {
                                        text: "+ Add Calendar Event"
                                        highlighted: true
                                        implicitHeight: 32
                                        contentItem: Text {
                                            text: parent.text
                                            color: "#ffffff"
                                            font.pixelSize: 12
                                            font.bold: true
                                            verticalAlignment: Text.AlignVCenter
                                            horizontalAlignment: Text.AlignHCenter
                                        }
                                        background: Rectangle {
                                            radius: 6
                                            color: parent.down ? "#005bb5" : (parent.hovered ? "#0071e3" : "#0a84ff")
                                            border.color: "#0a84ff"
                                            border.width: 1
                                        }
                                        onClicked: addEventDialog.open()
                                    }
                                }

                                Rectangle {
                                    Layout.fillWidth: true
                                    height: 1
                                    color: "#24242c"
                                }

                                // Structured Row 2: Toggles with clean, un-overlapping spacing
                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 24

                                    ToggleSwitch {
                                        text: "Desktop Surface (Pin Behind Windows)"
                                        checked: widgetManagerService.pinToBottom
                                        onToggled: (chk) => widgetManagerService.setPinToBottom(chk)
                                    }

                                    ToggleSwitch {
                                        text: "Start on Login"
                                        checked: widgetManagerService.isAutoStartEnabled
                                        onToggled: (chk) => widgetManagerService.setAutoStart(chk)
                                    }

                                    Item { Layout.fillWidth: true }
                                }
                            }
                        }
                    }

                    // ── SECTION 2: Weather Location & API Card ──────────────────
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8

                            Text { text: "☀️"; font.pixelSize: 14 }
                            Text {
                                text: "Weather Location"
                                color: "#ffffff"
                                font.bold: true
                                font.pixelSize: 14
                            }

                            Item { Layout.fillWidth: true }

                            // Live Status Pill
                            Rectangle {
                                height: 26
                                radius: 13
                                color: "#131317"
                                border.color: weatherBackend && weatherBackend.errorMessage ? "#ef4444" : "#282832"
                                border.width: 1
                                implicitWidth: statusRow.implicitWidth + 18

                                Row {
                                    id: statusRow
                                    anchors.centerIn: parent
                                    spacing: 7

                                    Rectangle {
                                        width: 7; height: 7; radius: 3.5
                                        color: weatherBackend && weatherBackend.isLoading ? "#3b82f6" : (weatherBackend && weatherBackend.errorMessage ? "#ef4444" : "#22c55e")
                                        anchors.verticalCenter: parent.verticalCenter
                                    }

                                    Text {
                                        text: {
                                            if (!weatherBackend) return "Weather inactive"
                                            if (weatherBackend.isLoading) return "Fetching Open-Meteo…"
                                            if (weatherBackend.errorMessage) return weatherBackend.errorMessage
                                            return weatherBackend.locationName + " • " + weatherBackend.currentTemp + "°C " + weatherBackend.condition
                                        }
                                        color: weatherBackend && weatherBackend.errorMessage ? "#fca5a5" : "#e4e4e7"
                                        font.pixelSize: 11
                                        font.bold: true
                                    }
                                }
                            }

                            Button {
                                text: "🔄 Refresh"
                                implicitHeight: 28
                                contentItem: Text {
                                    text: parent.text
                                    color: "#e4e4e7"
                                    font.pixelSize: 11
                                    verticalAlignment: Text.AlignVCenter
                                    horizontalAlignment: Text.AlignHCenter
                                }
                                background: Rectangle {
                                    radius: 6
                                    color: parent.down ? "#1c1c22" : (parent.hovered ? "#2e2e38" : "#22222a")
                                    border.color: parent.hovered ? "#484856" : "#32323e"
                                    border.width: 1
                                }
                                onClicked: if (weatherBackend) weatherBackend.refreshWeather(true)
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            radius: 12
                            color: "#18181d"
                            border.color: weatherBackend && weatherBackend.errorMessage ? "#ef444480" : "#282830"
                            border.width: 1
                            implicitHeight: weatherCol.implicitHeight + 32

                            ColumnLayout {
                                id: weatherCol
                                anchors.fill: parent
                                anchors.margins: 16
                                spacing: 14

                                Connections {
                                    target: weatherBackend
                                    function onCoordinatesChanged() {
                                        if (cityNameInput && !cityNameInput.activeFocus) cityNameInput.text = weatherBackend.locationName
                                        if (latInput && !latInput.activeFocus) latInput.text = weatherBackend.latitude.toFixed(4)
                                        if (lonInput && !lonInput.activeFocus) lonInput.text = weatherBackend.longitude.toFixed(4)
                                    }
                                }

                                // Row 1: Latitude, Longitude, and Apply Button (Requirement 3)
                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 12

                                    RowLayout {
                                        spacing: 6
                                        Text { text: "City:"; color: "#a1a1aa"; font.pixelSize: 12 }
                                        TextField {
                                            id: cityNameInput
                                            text: weatherBackend ? weatherBackend.locationName : "New York"
                                            placeholderText: "City label"
                                            Layout.preferredWidth: 130
                                            selectByMouse: true
                                        }
                                    }

                                    RowLayout {
                                        spacing: 6
                                        Text { text: "Lat:"; color: "#a1a1aa"; font.pixelSize: 12 }
                                        TextField {
                                            id: latInput
                                            text: weatherBackend ? weatherBackend.latitude.toFixed(4) : "40.7128"
                                            placeholderText: "Latitude"
                                            Layout.preferredWidth: 85
                                            selectByMouse: true
                                        }
                                    }

                                    RowLayout {
                                        spacing: 6
                                        Text { text: "Lon:"; color: "#a1a1aa"; font.pixelSize: 12 }
                                        TextField {
                                            id: lonInput
                                            text: weatherBackend ? weatherBackend.longitude.toFixed(4) : "-74.0060"
                                            placeholderText: "Longitude"
                                            Layout.preferredWidth: 85
                                            selectByMouse: true
                                        }
                                    }

                                    Button {
                                        text: "Apply Coordinates"
                                        highlighted: true
                                        implicitHeight: 30
                                        contentItem: Text {
                                            text: parent.text
                                            color: "#ffffff"
                                            font.pixelSize: 11
                                            font.bold: true
                                            verticalAlignment: Text.AlignVCenter
                                            horizontalAlignment: Text.AlignHCenter
                                        }
                                        background: Rectangle {
                                            radius: 6
                                            color: parent.down ? "#005bb5" : (parent.hovered ? "#0071e3" : "#0a84ff")
                                            border.color: "#0a84ff"
                                            border.width: 1
                                        }
                                        onClicked: {
                                            var lat = parseFloat(latInput.text)
                                            var lon = parseFloat(lonInput.text)
                                            if (!isNaN(lat) && !isNaN(lon)) {
                                                weatherBackend.updateLocation(cityNameInput.text.trim(), lat, lon)
                                            }
                                        }
                                    }

                                    Item { Layout.fillWidth: true }
                                }

                                Rectangle {
                                    Layout.fillWidth: true
                                    height: 1
                                    color: "#24242c"
                                }

                                // Row 2: City Search Bar and City Presets (Requirement 3)
                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 10

                                    TextField {
                                        id: searchCityField
                                        placeholderText: "Search city (e.g. Paris)..."
                                        Layout.preferredWidth: 180
                                        selectByMouse: true
                                        onAccepted: if (text.trim().length > 0) weatherBackend.searchCityAndSet(text.trim())
                                    }

                                    Button {
                                        text: "🔍 Search"
                                        implicitHeight: 30
                                        contentItem: Text {
                                            text: parent.text
                                            color: "#e4e4e7"
                                            font.pixelSize: 11
                                            verticalAlignment: Text.AlignVCenter
                                            horizontalAlignment: Text.AlignHCenter
                                        }
                                        background: Rectangle {
                                            radius: 6
                                            color: parent.down ? "#1c1c22" : (parent.hovered ? "#2e2e38" : "#24242c")
                                            border.color: parent.hovered ? "#484856" : "#343440"
                                            border.width: 1
                                        }
                                        onClicked: if (searchCityField.text.trim().length > 0) weatherBackend.searchCityAndSet(searchCityField.text.trim())
                                    }

                                    Rectangle {
                                        width: 1
                                        height: 20
                                        color: "#2a2a34"
                                        Layout.leftMargin: 4
                                        Layout.rightMargin: 4
                                    }

                                    Text {
                                        text: "Presets:"
                                        color: "#71717a"
                                        font.pixelSize: 11
                                        font.bold: true
                                    }

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 6

                                        Repeater {
                                            model: [
                                                { name: "New York", lat: 40.7128, lon: -74.0060 },
                                                { name: "London", lat: 51.5074, lon: -0.1278 },
                                                { name: "Tokyo", lat: 35.6762, lon: 139.6503 },
                                                { name: "Paris", lat: 48.8566, lon: 2.3522 },
                                                { name: "San Francisco", lat: 37.7749, lon: -122.4194 },
                                                { name: "Sydney", lat: -33.8688, lon: 151.2093 },
                                                { name: "Dubai", lat: 25.2048, lon: 55.2708 },
                                                { name: "Delhi", lat: 28.6139, lon: 77.2090 }
                                            ]

                                            Rectangle {
                                                height: 24
                                                radius: 12
                                                color: presetMouse.containsMouse ? "#0a84ff" : "#22222a"
                                                border.color: presetMouse.containsMouse ? "#0a84ff" : "#2e2e38"
                                                border.width: 1
                                                implicitWidth: presetText.implicitWidth + 14

                                                Text {
                                                    id: presetText
                                                    text: modelData.name
                                                    color: presetMouse.containsMouse ? "#ffffff" : "#d4d4d8"
                                                    anchors.centerIn: parent
                                                    font.pixelSize: 11
                                                    font.weight: Font.Medium
                                                }

                                                MouseArea {
                                                    id: presetMouse
                                                    anchors.fill: parent
                                                    hoverEnabled: true
                                                    cursorShape: Qt.PointingHandCursor
                                                    onClicked: {
                                                        cityNameInput.text = modelData.name
                                                        latInput.text = modelData.lat.toFixed(4)
                                                        lonInput.text = modelData.lon.toFixed(4)
                                                        weatherBackend.updateLocation(modelData.name, modelData.lat, modelData.lon)
                                                    }
                                                }

                                                Behavior on color { ColorAnimation { duration: 120 } }
                                            }
                                        }

                                        Item { Layout.fillWidth: true }
                                    }
                                }
                            }
                        }
                    }

                    // ── SECTION 3: Installed Widgets Card ───────────────────────
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8

                            Text { text: "📦"; font.pixelSize: 14 }
                            Text {
                                text: "Installed Widgets"
                                color: "#ffffff"
                                font.bold: true
                                font.pixelSize: 14
                            }

                            // Active count badge
                            Rectangle {
                                height: 22
                                radius: 11
                                color: Qt.rgba(52/255, 199/255, 89/255, 0.16)
                                border.color: "#34C759"
                                border.width: 1
                                implicitWidth: countText.implicitWidth + 14

                                Text {
                                    id: countText
                                    anchors.centerIn: parent
                                    text: widgetManagerService.widgetListModel.length + " widgets"
                                    color: "#34C759"
                                    font.pixelSize: 11
                                    font.bold: true
                                }
                            }

                            Item { Layout.fillWidth: true }

                            // Filter widgets search input
                            TextField {
                                id: filterWidgetInput
                                placeholderText: "Filter widgets..."
                                Layout.preferredWidth: 200
                                selectByMouse: true
                            }
                        }

                        // Outer Card for Widget List Items (Requirement 4)
                        Rectangle {
                            Layout.fillWidth: true
                            radius: 12
                            color: "#18181d"
                            border.color: "#282830"
                            border.width: 1
                            clip: true
                            implicitHeight: widgetItemsCol.implicitHeight + 24

                            ColumnLayout {
                                id: widgetItemsCol
                                anchors.fill: parent
                                anchors.margins: 12
                                spacing: 8

                                Repeater {
                                    model: widgetManagerService.widgetListModel

                                    delegate: Rectangle {
                                        id: widgetCard
                                        required property var modelData
                                        visible: filterWidgetInput.text.trim().length === 0 ||
                                                 modelData.name.toLowerCase().indexOf(filterWidgetInput.text.toLowerCase()) >= 0 ||
                                                 modelData.packageId.toLowerCase().indexOf(filterWidgetInput.text.toLowerCase()) >= 0
                                        Layout.fillWidth: true
                                        implicitHeight: cardRow.implicitHeight + 18
                                        radius: 10
                                        color: cardHover.hovered ? "#25252e" : (modelData.active ? "#1c1c23" : "#151518")
                                        border.color: cardHover.hovered ? (modelData.active ? "#0a84ff" : "#444452") : (modelData.active ? "#0a84ff66" : "#282832")
                                        border.width: modelData.active ? 1.5 : 1

                                        // Subtle hover effect
                                        HoverHandler {
                                            id: cardHover
                                        }

                                        Behavior on color { ColorAnimation { duration: 150 } }
                                        Behavior on border.color { ColorAnimation { duration: 150 } }

                                        RowLayout {
                                            id: cardRow
                                            anchors.fill: parent
                                            anchors.leftMargin: 12
                                            anchors.rightMargin: 14
                                            anchors.topMargin: 8
                                            anchors.bottomMargin: 8
                                            spacing: 12

                                            // Left Side: Active Switch + Category Icon + Titles
                                            RowLayout {
                                                Layout.fillWidth: true
                                                Layout.alignment: Qt.AlignVCenter
                                                spacing: 10

                                                ToggleSwitch {
                                                    checked: modelData.active
                                                    onToggled: (chk) => widgetManagerService.setWidgetActive(modelData.packageId, chk)
                                                }

                                                // Colored Category Squircle Icon
                                                Rectangle {
                                                    width: 34
                                                    height: 34
                                                    radius: 8
                                                    color: modelData.active ? Qt.rgba(10/255, 132/255, 255/255, 0.22) : Qt.rgba(255, 255, 255, 0.05)
                                                    border.color: modelData.active ? "#0a84ff" : Qt.rgba(255, 255, 255, 0.12)
                                                    border.width: 1

                                                    Text {
                                                        anchors.centerIn: parent
                                                        text: {
                                                            var p = modelData.packageId;
                                                            if (p.indexOf("calendar") >= 0) return "📅";
                                                            if (p.indexOf("clock") >= 0 || p.indexOf("city") >= 0) return "🕒";
                                                            if (p.indexOf("weather") >= 0) return "☀️";
                                                            if (p.indexOf("music") >= 0) return "🎵";
                                                            if (p.indexOf("timer") >= 0) return "⏱️";
                                                            return "✨";
                                                        }
                                                        font.pixelSize: 14
                                                    }
                                                }

                                                // Title & Subtitle with Text Truncation
                                                ColumnLayout {
                                                    Layout.fillWidth: true
                                                    Layout.minimumWidth: 80
                                                    spacing: 2

                                                    Text {
                                                        text: modelData.name
                                                        color: modelData.active ? "#ffffff" : "#a1a1aa"
                                                        font.bold: true
                                                        font.pixelSize: 13
                                                        elide: Text.ElideRight
                                                        Layout.fillWidth: true
                                                    }
                                                    Text {
                                                        text: modelData.packageId + " • " + Math.round(modelData.width) + " × " + Math.round(modelData.height) + " px"
                                                        color: "#71717a"
                                                        font.pixelSize: 11
                                                        elide: Text.ElideRight
                                                        Layout.fillWidth: true
                                                    }
                                                }
                                            }

                                            // Right Side Controls: Scale Slider + Presets + Optional TZ / Quote
                                            RowLayout {
                                                Layout.alignment: Qt.AlignRight | Qt.AlignVCenter
                                                spacing: 8

                                                Text {
                                                    text: Math.round(modelData.scale * 100) + "%"
                                                    color: "#a1a1aa"
                                                    font.pixelSize: 11
                                                    Layout.preferredWidth: 36
                                                    horizontalAlignment: Text.AlignRight
                                                }

                                                Slider {
                                                    from: 0.75
                                                    to: 2.0
                                                    stepSize: 0.05
                                                    value: modelData.scale
                                                    Layout.preferredWidth: 70
                                                    onMoved: widgetManagerService.setWidgetScale(modelData.packageId, value)
                                                }

                                                Button {
                                                    text: "1×1"
                                                    implicitHeight: 28
                                                    Layout.preferredWidth: 38
                                                    contentItem: Text {
                                                        text: parent.text
                                                        color: "#e4e4e7"
                                                        font.pixelSize: 10
                                                        font.bold: true
                                                        verticalAlignment: Text.AlignVCenter
                                                        horizontalAlignment: Text.AlignHCenter
                                                    }
                                                    background: Rectangle {
                                                        radius: 5
                                                        color: parent.down ? "#1c1c22" : (parent.hovered ? "#2e2e38" : "#24242c")
                                                        border.color: parent.hovered ? "#484856" : "#343440"
                                                        border.width: 1
                                                    }
                                                    onClicked: widgetManagerService.resizeWidget(modelData.packageId, 300, 300)
                                                }

                                                Button {
                                                    text: "2×1"
                                                    implicitHeight: 28
                                                    Layout.preferredWidth: 38
                                                    contentItem: Text {
                                                        text: parent.text
                                                        color: "#e4e4e7"
                                                        font.pixelSize: 10
                                                        font.bold: true
                                                        verticalAlignment: Text.AlignVCenter
                                                        horizontalAlignment: Text.AlignHCenter
                                                    }
                                                    background: Rectangle {
                                                        radius: 5
                                                        color: parent.down ? "#1c1c22" : (parent.hovered ? "#2e2e38" : "#24242c")
                                                        border.color: parent.hovered ? "#484856" : "#343440"
                                                        border.width: 1
                                                    }
                                                    onClicked: widgetManagerService.resizeWidget(modelData.packageId, 640, 300)
                                                }

                                                // Timezone for clock / city
                                                Button {
                                                    visible: modelData.packageId.indexOf("clock") >= 0 || modelData.packageId.indexOf("city") >= 0
                                                    text: "🌐 TZ"
                                                    implicitHeight: 28
                                                    Layout.preferredWidth: 50
                                                    contentItem: Text {
                                                        text: parent.text
                                                        color: "#e4e4e7"
                                                        font.pixelSize: 10
                                                        font.bold: true
                                                        verticalAlignment: Text.AlignVCenter
                                                        horizontalAlignment: Text.AlignHCenter
                                                    }
                                                    background: Rectangle {
                                                        radius: 5
                                                        color: parent.down ? "#1c1c22" : (parent.hovered ? "#2e2e38" : "#24242c")
                                                        border.color: parent.hovered ? "#484856" : "#343440"
                                                        border.width: 1
                                                    }
                                                    onClicked: widgetManagerService.promptWidgetTimezone(modelData.packageId)
                                                }

                                                // Quote input for test-glass
                                                RowLayout {
                                                    visible: modelData.packageId === "test-glass"
                                                    spacing: 4

                                                    Text {
                                                        text: "Quote:"
                                                        color: "#a1a1aa"
                                                        font.pixelSize: 11
                                                    }

                                                    TextField {
                                                        id: glassTextMgrInput
                                                        text: widgetManagerService.glassText
                                                        placeholderText: "Liquid gLASS"
                                                        Layout.preferredWidth: 120
                                                        onEditingFinished: widgetManagerService.setGlassText(text)
                                                        Connections {
                                                            target: widgetManagerService
                                                            function onGlassTextChanged(newText) {
                                                                if (!glassTextMgrInput.activeFocus) {
                                                                    glassTextMgrInput.text = newText
                                                                }
                                                            }
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        // ── 3. Smooth Window Edge Resize Grips ─────────────────────────
        MouseArea {
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            width: 6
            cursorShape: Qt.SizeHorCursor
            onPressed: mgrWindow.startSystemResize(Qt.LeftEdge)
        }
        MouseArea {
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            width: 6
            cursorShape: Qt.SizeHorCursor
            onPressed: mgrWindow.startSystemResize(Qt.RightEdge)
        }
        MouseArea {
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            height: 6
            cursorShape: Qt.SizeVerCursor
            onPressed: mgrWindow.startSystemResize(Qt.TopEdge)
        }
        MouseArea {
            anchors.bottom: parent.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            height: 6
            cursorShape: Qt.SizeVerCursor
            onPressed: mgrWindow.startSystemResize(Qt.BottomEdge)
        }
        MouseArea {
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            width: 14; height: 14
            cursorShape: Qt.SizeFDiagCursor
            onPressed: mgrWindow.startSystemResize(Qt.RightEdge | Qt.BottomEdge)
        }
        MouseArea {
            anchors.left: parent.left
            anchors.bottom: parent.bottom
            width: 14; height: 14
            cursorShape: Qt.SizeBDiagCursor
            onPressed: mgrWindow.startSystemResize(Qt.LeftEdge | Qt.BottomEdge)
        }
    }

    // Add Event Dialog (Clean Dark Modal)
    Dialog {
        id: addEventDialog
        title: "Add Calendar Event"
        modal: true
        anchors.centerIn: parent
        width: 380
        standardButtons: Dialog.Ok | Dialog.Cancel

        ColumnLayout {
            spacing: 12
            width: parent.width

            TextField {
                id: eventTitleField
                placeholderText: "Event Title"
                maximumLength: 100
                Layout.fillWidth: true
            }
            RowLayout {
                spacing: 8
                TextField {
                    id: eventDateField
                    placeholderText: "YYYY-MM-DD"
                    maximumLength: 10
                    text: Qt.formatDate(new Date(), "yyyy-MM-dd")
                    Layout.fillWidth: true
                }
                TextField {
                    id: eventTimeField
                    placeholderText: "14:00"
                    maximumLength: 5
                    text: "14:00"
                    Layout.preferredWidth: 80
                }
            }
            ComboBox {
                id: eventTypeCombo
                model: ["Event", "Todo", "Holiday", "Journal"]
                Layout.fillWidth: true
            }
        }

        onAccepted: {
            if (eventTitleField.text.trim().length > 0) {
                calendarBackendService.addEvent(
                    eventTitleField.text.trim(),
                    eventDateField.text.trim(),
                    eventTimeField.text.trim(),
                    false,
                    "#0a84ff",
                    eventTypeCombo.currentText
                )
                eventTitleField.text = ""
            }
        }
    }
}
