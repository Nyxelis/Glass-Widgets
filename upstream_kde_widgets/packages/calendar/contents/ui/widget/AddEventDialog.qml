import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: dialogRoot
    anchors.fill: parent
    visible: opacity > 0
    opacity: 0

    Behavior on opacity {
        NumberAnimation { duration: 200; easing.type: Easing.OutCubic }
    }

    signal eventSaved()

    property string preselectedDate: ""
    property string selectedColor: "#0a84ff"
    readonly property var colorPills: ["#0a84ff", "#34C759", "#FF9500", "#AF52DE", "#FF453A"]

    function openForDate(year, month, day) {
        var mStr = month < 10 ? ("0" + month) : ("" + month);
        var dStr = day < 10 ? ("0" + day) : ("" + day);
        dateInput.text = year + "-" + mStr + "-" + dStr;
        titleInput.text = "";
        descInput.text = "";
        timeInput.text = "14:00";
        allDayCheck.checked = false;
        selectedColor = "#0a84ff";
        dialogRoot.opacity = 1.0;
        titleInput.forceActiveFocus();
    }

    function close() {
        dialogRoot.opacity = 0;
    }

    // Modal background barrier
    MouseArea {
        anchors.fill: parent
        hoverEnabled: true
        preventStealing: true
        onClicked: dialogRoot.close()
    }

    Rectangle {
        anchors.fill: parent
        color: Qt.rgba(0, 0, 0, 0.65)
        radius: 20
    }

    // Dialog card
    Rectangle {
        id: card
        width: Math.min(parent.width - 20, 320)
        height: Math.min(parent.height - 20, contentCol.implicitHeight + 28)
        anchors.centerIn: parent
        radius: 16
        color: "#1c1c1e"
        border.color: Qt.rgba(1, 1, 1, 0.18)
        border.width: 1

        MouseArea {
            anchors.fill: parent
            // Prevent clicks from dismissing through backdrop
        }

        Flickable {
            id: scrollArea
            anchors.fill: parent
            anchors.margins: 12
            contentHeight: contentCol.implicitHeight
            clip: true
            boundsBehavior: Flickable.StopAtBounds

            ColumnLayout {
                id: contentCol
                width: scrollArea.width
                spacing: 8

            // Header
            RowLayout {
                Layout.fillWidth: true

                Text {
                    text: "New Event"
                    color: "#ffffff"
                    font.pixelSize: 14
                    font.weight: Font.DemiBold
                }

                Item { Layout.fillWidth: true }

                Rectangle {
                    width: 22; height: 22; radius: 11
                    color: closeMouse.containsMouse ? Qt.rgba(1, 1, 1, 0.2) : "transparent"
                    Text {
                        anchors.centerIn: parent
                        text: "×"
                        color: "#a1a1aa"
                        font.pixelSize: 16
                    }
                    MouseArea {
                        id: closeMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: dialogRoot.close()
                    }
                }
            }

            // Title Field
            Rectangle {
                Layout.fillWidth: true
                height: 32
                radius: 8
                color: "#27272a"
                border.color: titleInput.activeFocus ? "#0a84ff" : "#3f3f46"
                border.width: 1

                TextInput {
                    id: titleInput
                    anchors.fill: parent
                    anchors.leftMargin: 10
                    anchors.rightMargin: 10
                    verticalAlignment: TextInput.AlignVCenter
                    color: "#ffffff"
                    font.pixelSize: 12
                    selectByMouse: true

                    Text {
                        anchors.left: parent.left
                        anchors.verticalCenter: parent.verticalCenter
                        text: "Event Title"
                        color: "#71717a"
                        font.pixelSize: 12
                        visible: !titleInput.text && !titleInput.activeFocus
                    }
                }
            }

            // Date & Time Row
            RowLayout {
                Layout.fillWidth: true
                spacing: 8

                // Date Field
                Rectangle {
                    Layout.fillWidth: true
                    height: 32
                    radius: 8
                    color: "#27272a"
                    border.color: dateInput.activeFocus ? "#0a84ff" : "#3f3f46"
                    border.width: 1

                    TextInput {
                        id: dateInput
                        anchors.fill: parent
                        anchors.leftMargin: 8
                        anchors.rightMargin: 8
                        verticalAlignment: TextInput.AlignVCenter
                        color: "#ffffff"
                        font.pixelSize: 11
                        selectByMouse: true
                    }
                }

                // Time Field (hidden if all day)
                Rectangle {
                    Layout.preferredWidth: 60
                    height: 32
                    radius: 8
                    color: "#27272a"
                    border.color: timeInput.activeFocus ? "#0a84ff" : "#3f3f46"
                    border.width: 1
                    visible: !allDayCheck.checked

                    TextInput {
                        id: timeInput
                        anchors.fill: parent
                        anchors.leftMargin: 8
                        anchors.rightMargin: 8
                        verticalAlignment: TextInput.AlignVCenter
                        color: "#ffffff"
                        font.pixelSize: 11
                        text: "14:00"
                        selectByMouse: true
                    }
                }
            }

            // All-day Checkbox & Color selector Row
            RowLayout {
                Layout.fillWidth: true
                spacing: 8

                CheckBox {
                    id: allDayCheck
                    text: "All-day"
                    contentItem: Text {
                        text: allDayCheck.text
                        font.pixelSize: 11
                        color: "#a1a1aa"
                        verticalAlignment: Text.AlignVCenter
                        leftPadding: allDayCheck.indicator.width + 4
                    }
                }

                Item { Layout.fillWidth: true }

                // Color Tag Pills
                Row {
                    spacing: 6
                    Repeater {
                        model: dialogRoot.colorPills
                        delegate: Rectangle {
                            width: 18
                            height: 18
                            radius: 9
                            color: modelData
                            border.color: dialogRoot.selectedColor === modelData ? "#ffffff" : "transparent"
                            border.width: 2

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: dialogRoot.selectedColor = modelData
                            }
                        }
                    }
                }
            }

            // Description Field (Optional)
            Rectangle {
                Layout.fillWidth: true
                height: 28
                radius: 6
                color: "#27272a"
                border.color: descInput.activeFocus ? "#0a84ff" : "#3f3f46"
                border.width: 1

                TextInput {
                    id: descInput
                    anchors.fill: parent
                    anchors.leftMargin: 8
                    anchors.rightMargin: 8
                    verticalAlignment: TextInput.AlignVCenter
                    color: "#d4d4d8"
                    font.pixelSize: 11
                    selectByMouse: true

                    Text {
                        anchors.left: parent.left
                        anchors.verticalCenter: parent.verticalCenter
                        text: "Notes / Description (optional)"
                        color: "#71717a"
                        font.pixelSize: 11
                        visible: !descInput.text && !descInput.activeFocus
                    }
                }
            }

            // Action Buttons
            RowLayout {
                Layout.fillWidth: true
                Layout.topMargin: 4
                spacing: 8

                Rectangle {
                    Layout.fillWidth: true
                    height: 30
                    radius: 7
                    color: cancelMouse.containsMouse ? Qt.rgba(1, 1, 1, 0.15) : Qt.rgba(1, 1, 1, 0.08)
                    Text {
                        anchors.centerIn: parent
                        text: "Cancel"
                        color: "#a1a1aa"
                        font.pixelSize: 11
                        font.weight: Font.Medium
                    }
                    MouseArea {
                        id: cancelMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: dialogRoot.close()
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 30
                    radius: 7
                    color: saveMouse.containsMouse ? "#0071e3" : "#0a84ff"
                    Text {
                        anchors.centerIn: parent
                        text: "Save Event"
                        color: "#ffffff"
                        font.pixelSize: 11
                        font.weight: Font.DemiBold
                    }
                    MouseArea {
                        id: saveMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            var t = titleInput.text.trim();
                            if (!t) return;
                            var d = dateInput.text.trim();
                            var tm = allDayCheck.checked ? "00:00" : timeInput.text.trim();
                            var desc = descInput.text.trim();

                            if (typeof calendarBackendService !== "undefined" && calendarBackendService) {
                                calendarBackendService.addEvent(
                                    t,
                                    d,
                                    tm,
                                    allDayCheck.checked,
                                    dialogRoot.selectedColor,
                                    "Event",
                                    desc,
                                    ""
                                );
                            }
                            dialogRoot.eventSaved();
                            dialogRoot.close();
                        }
                    }
                }
            }
        }
    }
}
}
