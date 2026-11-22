import QtQuick

Item {
    id: card

    property int eventId: -1
    property string title: ""
    property string timeLabel: ""
    property color pillColor: "#FF6B6B"
    property color textColor: "#ffffff"
    property string fontFamily: ""
    property real fontSize: 11
    property color cardBg: "#ffffff"
    property real cardBgOpacity: 0.10

    readonly property real _pad: Math.round(height * 0.22)

    implicitHeight: Math.round(fontSize * 2.8)

    Rectangle {
        anchors.fill: parent
        radius: Math.round(card.height * 0.25)
        color: card.cardBg
        opacity: card.cardBgOpacity
    }

    Rectangle {
        id: pill
        x: card._pad
        y: card._pad
        width: 3
        height: parent.height - 2 * card._pad
        radius: 1.5
        color: card.pillColor
    }

    Text {
        anchors.left: pill.right
        anchors.leftMargin: 6
        anchors.right: timeText.left
        anchors.rightMargin: 4
        anchors.verticalCenter: parent.verticalCenter
        text: card.title
        textFormat: Text.PlainText
        color: card.textColor
        font.family: card.fontFamily
        font.pixelSize: card.fontSize
        elide: Text.ElideRight
    }

    Text {
        id: timeText
        anchors.right: delBtn.visible ? delBtn.left : parent.right
        anchors.rightMargin: delBtn.visible ? 4 : card._pad
        anchors.verticalCenter: parent.verticalCenter
        text: card.timeLabel
        textFormat: Text.PlainText
        color: card.textColor
        opacity: 0.6
        font.family: card.fontFamily
        font.pixelSize: Math.round(card.fontSize * 0.85)
    }

    // Hover delete button for fast event removal
    Item {
        id: delBtn
        visible: card.eventId > 0 && hoverArea.containsMouse
        anchors.right: parent.right
        anchors.rightMargin: 6
        anchors.verticalCenter: parent.verticalCenter
        width: Math.round(card.height * 0.6)
        height: width

        Rectangle {
            anchors.fill: parent
            radius: width / 2
            color: delMouse.containsMouse ? "#ef4444" : Qt.rgba(1, 1, 1, 0.2)
            Text {
                anchors.centerIn: parent
                text: "×"
                color: "#ffffff"
                font.pixelSize: parent.width * 0.85
                font.bold: true
            }
        }
        MouseArea {
            id: delMouse
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: {
                if (typeof calendarBackendService !== "undefined" && calendarBackendService && card.eventId > 0) {
                    calendarBackendService.deleteEvent(card.eventId);
                }
            }
        }
    }

    MouseArea {
        id: hoverArea
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.NoButton
    }
}
