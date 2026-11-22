import QtQuick

Item {
    id: iconItem
    property var source: ""
    property int status: 0
    property bool valid: true
    Image {
        anchors.fill: parent
        source: iconItem.source ? iconItem.source.toString() : ""
        fillMode: Image.PreserveAspectFit
        smooth: true
    }
}
