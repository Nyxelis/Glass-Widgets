import QtQuick

QtObject {
    id: ds
    property string engine: ""
    property var connectedSources: []
    signal newData(string source, var data)
    function connectSource(source) {
        if (engine === "executable") {
            newData(source, {});
        }
    }
    function disconnectSource(source) {}
}
