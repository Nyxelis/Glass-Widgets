import QtQuick

QtObject {
    id: svgRoot
    property string imagePath: ""
    property bool multipleImages: false
    property size size: Qt.size(32, 32)
    function hasElement(id) { return false; }
}
