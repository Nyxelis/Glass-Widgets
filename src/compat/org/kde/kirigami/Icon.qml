import QtQuick

Item {
    id: iconItem
    property var source: ""
    property color color: "transparent"
    Image {
        anchors.fill: parent
        source: iconItem.source ? iconItem.source.toString() : ""
        fillMode: Image.PreserveAspectFit
        smooth: true
    }
}
