import QtQuick

Item {
    id: root

    property bool checked: false
    property string text: ""
    property color onColor: "#34C759"
    property color offColor: "#39393d"
    property bool enabled: true

    signal toggled(bool checked)

    implicitWidth: rowLayout.implicitWidth
    implicitHeight: Math.max(26, labelText.implicitHeight)

    Row {
        id: rowLayout
        spacing: 10
        anchors.verticalCenter: parent.verticalCenter

        // Pill Track
        Rectangle {
            id: track
            width: 44
            height: 24
            radius: height / 2
            color: root.checked ? root.onColor : root.offColor
            border.color: root.checked ? "#2cb24e" : Qt.rgba(1, 1, 1, 0.16)
            border.width: 1

            Behavior on color {
                ColorAnimation { duration: 180; easing.type: Easing.OutCubic }
            }

            // Knob subtle drop shadow (3D physical depth)
            Rectangle {
                x: knob.x
                y: knob.y + 1
                width: knob.width
                height: knob.height
                radius: knob.radius
                color: Qt.rgba(0, 0, 0, 0.28)
            }

            // White circular glossy knob
            Rectangle {
                id: knob
                y: 2
                x: root.checked ? (track.width - width - 2) : 2
                width: track.height - 4
                height: width
                radius: width / 2
                gradient: Gradient {
                    GradientStop { position: 0.0; color: "#ffffff" }
                    GradientStop { position: 1.0; color: "#f2f2f7" }
                }
                border.color: Qt.rgba(0, 0, 0, 0.10)
                border.width: 0.5

                Behavior on x {
                    NumberAnimation { duration: 180; easing.type: Easing.OutCubic }
                }
            }

            MouseArea {
                anchors.fill: parent
                cursorShape: root.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                hoverEnabled: true
                onClicked: {
                    if (!root.enabled) return;
                    root.checked = !root.checked;
                    root.toggled(root.checked);
                }
            }
        }

        // Label text if provided
        Text {
            id: labelText
            visible: root.text.length > 0
            text: root.text
            color: root.enabled ? "#e4e4e7" : "#71717a"
            font.pixelSize: 12
            font.weight: Font.Medium
            anchors.verticalCenter: parent.verticalCenter

            MouseArea {
                anchors.fill: parent
                cursorShape: root.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                onClicked: {
                    if (!root.enabled) return;
                    root.checked = !root.checked;
                    root.toggled(root.checked);
                }
            }
        }
    }

    Keys.onSpacePressed: (event) => {
        if (root.enabled) {
            root.checked = !root.checked;
            root.toggled(root.checked);
            event.accepted = true;
        }
    }
}
